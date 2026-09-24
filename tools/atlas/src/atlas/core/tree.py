"""The ProjectTree seam: one project's folders and files, read lazily.

The TUI owns interaction and the widget; this module owns filesystem facts. It
hands out immutable ``TreeNode`` values and keeps a mutable cache behind them,
the same division ``tui.model.ProjectRow`` makes between a stable value and the
scan that produced it.

Reading is lazy - one ``os.scandir`` per displayed folder, never a walk - and
every call is side-effect free, so a TUI worker that abandons one mid-flight
costs nothing but the read. See ADR 0007.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .conform import CONFLICT, DONE, SWEEP, Plan, parent_key
from .doctor import ProjectReport
from .mapfile import DriveMap
from .scan import READ, UNREAD, Listing, ProjectInventory, list_entries

# Filing State, per ADR 0004: what the drive map says about a node that exists.
MAPPED = "mapped"
DRIFTED = "drifted"
MISPLACED = "misplaced"
LOOSE = "loose"
UNFILED = "unfiled"

# How long a listing may be trusted. Ticket 06 ruled out filesystem watching over
# the Drive redirector, so someone else's change reaches the tree when the TTL
# expires or when the operator asks for a refresh, and never any sooner.
DEFAULT_TTL = 60.0

# The rest of ticket 12's budgets, measured on the live drive
# (docs/research/atlas-drive-latency-measurement.md) and recorded here, where the
# tree reads them. They interact, so they live together.
#
# LOADING_DELAY: seconds before a load shows a loading state. Above the cold p99
#   of 91 ms, below the perceptual boundary; at p90 of 1.74 ms almost no
#   expansion ever shows it, so the tree does not flicker.
# CONCURRENCY_CAP: node loads in flight at once. Most of the measured gain
#   (2.15x at 8 workers, already flat), and it leaves the shared pool free.
# PREFETCH_CAP: nodes that may be read ahead of the cursor. The tree does not
#   prefetch today; any prefetch that is added stays one level ahead, under this.
# COUNT_CAP: entries read from one folder before its listing stops as PARTIAL.
#   The pathological tail, not the median, is what this bounds.
LOADING_DELAY = 0.120
CONCURRENCY_CAP = 4
PREFETCH_CAP = 50
COUNT_CAP = 500

# What kind of thing an unmet Expectation is. The distinction is not cosmetic:
# conform backfills the control plane and has never created a mapped section, so
# only one of the two can be offered as a Repair.
CONTROL_PLANE = "control-plane"
SECTION = "section"


def _sort_key(entry) -> tuple[int, str]:
    """Folders first, then files, each case-insensitively by name.

    A deterministic order is a fact, not a presentation choice: Textual restores
    the tree cursor by line number rather than by node identity, so a listing
    that came back in a different order would silently move the selection.
    """
    return (0 if entry.is_dir else 1, entry.name.casefold())


@dataclass(frozen=True)
class TreeNode:
    """One folder or file on disk inside a Project.

    ``key`` is the Node Key: the project-relative path, forward-slashed, stable
    across refreshes and across the writes Atlas itself performs.
    """

    key: str
    name: str
    is_dir: bool
    filing: str = MAPPED
    # Load State, and the Child Count that comes free with it. Both are empty
    # until Atlas has opened the folder, and a file never has either.
    load: str = ""
    folders: int = 0
    files: int = 0

    def __post_init__(self) -> None:
        # Two states the type would otherwise permit and ADR 0004 does not: a
        # folder Atlas knows nothing about yet is Unread, not blank, and a file
        # has no Load State at all. Enforced here rather than at each call site,
        # because this record is handed to the TUI and built in tests.
        load = self.load or UNREAD if self.is_dir else ""
        if load != self.load:
            object.__setattr__(self, "load", load)


@dataclass(frozen=True)
class Expectation:
    """A folder or file the drive map requires that this Project does not have."""

    path: str
    kind: str

    @property
    def repairable(self) -> bool:
        return self.kind == CONTROL_PLANE


def _root_filing_states(report: ProjectReport) -> dict[str, str]:
    """Every node the report has an opinion about, by Node Key.

    The first rule that matches decides, in the order conform applies them -
    drift, relocations, sweeps - so a name two rules claim reads as the action
    conform will actually take, not the last one listed (ADR 0004).
    """
    states: dict[str, str] = {}
    for found, _canonical in report.drift:
        states.setdefault(found, DRIFTED)
    for hit in report.relocations:
        states.setdefault(hit.source, MISPLACED)
    for name, _target in report.sweeps:
        states.setdefault(name, LOOSE)
    for name in report.unfiled:
        states.setdefault(name, UNFILED)
    return states


class ProjectTree:
    """A lazily-expanding handle on one Project's folders and files."""

    def __init__(self, project: Path, drive_map: DriveMap, report: ProjectReport,
                 *, ttl: float = DEFAULT_TTL, count_cap: int | None = COUNT_CAP,
                 clock: Callable[[], float] = time.monotonic):
        self.project = project
        self.drive_map = drive_map
        self.report = report
        self.ttl = ttl
        self.count_cap = count_cap
        self._clock = clock
        self._listings: dict[str, Listing] = {}
        self._read_at: dict[str, float] = {}
        self._filing = _root_filing_states(report)

    def filing_state(self, key: str) -> str:
        """What the drive map says about the node at ``key``.

        A path the map names explicitly keeps its own verdict at any depth. Below
        that, containment decides: a node under a canonical path is accounted for,
        and a node under an Unfiled one is not - calling it Mapped would hide the
        one thing about it that needs a person.
        """
        if key in self._filing:
            return self._filing[key]
        parts = key.split("/")
        for depth in range(len(parts) - 1, 0, -1):
            ancestor = self._filing.get("/".join(parts[:depth]))
            if ancestor is not None:
                return UNFILED if ancestor == UNFILED else MAPPED
        return MAPPED

    def load_state(self, key: str) -> str:
        """What Atlas knows about the children of the folder at ``key``."""
        listing = self._listings.get(key)
        return listing.state if listing is not None else UNREAD

    def _node(self, key: str, name: str, is_dir: bool) -> TreeNode:
        if not is_dir:
            return TreeNode(key=key, name=name, is_dir=False,
                            filing=self.filing_state(key))
        listing = self._listings.get(key)
        folders = sum(1 for e in listing if e.is_dir) if listing is not None else 0
        return TreeNode(
            key=key, name=name, is_dir=True, filing=self.filing_state(key),
            load=listing.state if listing is not None else UNREAD,
            folders=folders,
            files=(len(listing) - folders) if listing is not None else 0,
        )

    def _fresh(self, key: str) -> bool:
        read_at = self._read_at.get(key)
        return read_at is not None and self._clock() - read_at < self.ttl

    def _listing(self, key: str) -> Listing:
        if not self._fresh(key):
            self._listings[key] = list_entries(
                self.project / key if key else self.project, limit=self.count_cap)
            self._read_at[key] = self._clock()
        return self._listings[key]

    def expectations(self) -> tuple[Expectation, ...]:
        """Every unmet Expectation, listed beside the tree and never inside it.

        Reads each mapped section that is present, which is bounded by the number
        of sections in the map and is exactly the set of folders the operator is
        about to expand anyway. A section that is absent is reported without
        looking inside it - there is nothing to look inside.
        """
        unmet = [Expectation(path=item, kind=CONTROL_PLANE)
                 for item in self.report.missing_control_plane]
        root = self._listing("")
        if root.state != READ:
            # Nothing is known to be missing from a folder Atlas could not
            # read, or read only up to the count cap; listing every section as
            # unmet would draw it exactly like an empty project (ADR 0004).
            return tuple(sorted(unmet, key=lambda e: e.path))
        present = {e.name for e in root if e.is_dir}
        for section in self.drive_map.sections:
            if section.id not in present:
                unmet.append(Expectation(path=section.id, kind=SECTION))
                continue
            listing = self._listing(section.id)
            if listing.state != READ:
                # Unreadable, or stopped at the count cap: a child absent from
                # what was read is not known to be absent from disk.
                continue
            here = {e.name for e in listing}
            unmet.extend(
                Expectation(path=f"{section.id}/{child}", kind=SECTION)
                for child in section.children if child not in here
            )
        return tuple(sorted(unmet, key=lambda e: e.path))

    # ---- after Atlas writes (ticket 15) ---------------------------------

    def reconcile(self, applied: Plan, report: ProjectReport | None = None) -> tuple[str, ...]:
        """Bring the tree back in line with a Plan Atlas just applied.

        Textual has no way to re-parent a node, so the folders a move touched have
        to be rebuilt. The Move Manifest names exactly which those are, which is
        the same pair the scoped Guard watched - two enumerations rather than a
        walk of everything under a common ancestor. A project-wide conform uses
        ``invalidate_all`` instead; its manifest can span the whole project, and
        at that point rebuilding it wholesale is the cheaper honest answer.

        Pass the freshly built ``report`` when there is one: a repair changes what
        the map says about the nodes around it, and a tree serving the pre-write
        verdict would offer a repair that has already happened.
        """
        touched: list[str] = []
        for action in applied.actions:
            # A conflicted merge still moved what its manifest says it moved.
            if action.status != DONE and not (action.status == CONFLICT and action.moved):
                continue
            keys = [parent_key(mv.src) for mv in action.moved]
            keys += [parent_key(mv.dst) for mv in action.moved]
            # The Action's own endpoints, not only its manifest's, and for every
            # applied action whether or not it moved anything. A merge moves
            # children one at a time, so every Move names a child and the parents
            # of those children are the two merged folders - never the folder
            # that just lost the source from its own listing. A backfill and a
            # removed empty duplicate have no manifest at all. Leaving any of
            # those cached draws a row for something not on disk, or none for
            # something that is, which ADR 0004 rules out.
            if action.src:
                keys.append(parent_key(action.src))
            dst = action.dst.replace("\\", "/").rstrip("/")
            keys.append(dst if action.kind == SWEEP else parent_key(dst))
            # Folders the write created on the way, and those an undo pruned:
            # their parents gained or lost a child no Move names.
            keys += [parent_key(key) for key in action.created + action.prune]
            for key in keys:
                if key not in touched:
                    touched.append(key)
        self.invalidate(touched, report)
        return tuple(sorted(touched))

    def invalidate(self, keys, report: ProjectReport | None = None) -> None:
        """Forget what Atlas knew about these folders, and about their subtrees."""
        for key in keys:
            prefix = f"{key}/" if key else ""
            for cached in [k for k in self._listings
                           if k == key or (prefix and k.startswith(prefix))]:
                self._listings.pop(cached, None)
                self._read_at.pop(cached, None)
        if report is not None:
            self._adopt(report)

    def invalidate_all(self, report: ProjectReport | None = None) -> None:
        """Forget the whole project. What a drive-wide conform earns."""
        self._listings.clear()
        self._read_at.clear()
        if report is not None:
            self._adopt(report)

    def _adopt(self, report: ProjectReport) -> None:
        self.report = report
        self._filing = _root_filing_states(report)

    def follow(self, key: str, applied: Plan) -> str:
        """Where the node at ``key`` ended up, so the cursor can follow it.

        The cursor is restored by line number rather than by node identity, so
        after a rebuild it lands on whatever now occupies that line unless
        something says where the node went. This is that something.
        """
        for action in applied.actions:
            if action.status != DONE:
                continue
            for mv in action.moved:
                if key == mv.src:
                    return mv.dst
                if key.startswith(f"{mv.src}/"):
                    return mv.dst + key[len(mv.src):]
            # A merge moves children one at a time; nothing in the manifest names
            # the folder itself, which is now gone. The Action does.
            if key == action.src and action.moved:
                return action.dst.replace("\\", "/").rstrip("/")
        return key

    def children(self, key: str = "") -> tuple[TreeNode, ...]:
        """The children of one folder, read on demand and cached."""
        listing = self._listing(key)
        prefix = f"{key}/" if key else ""
        return tuple(
            self._node(f"{prefix}{entry.name}", entry.name, entry.is_dir)
            for entry in sorted(listing, key=_sort_key)
        )


def open_project_tree(inv: ProjectInventory, m: DriveMap, report: ProjectReport,
                      **options) -> ProjectTree:
    """A tree over one scanned project, sharing the report the list already built."""
    return ProjectTree(project=inv.path, drive_map=m, report=report, **options)
