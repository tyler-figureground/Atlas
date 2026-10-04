"""P3: conform a project to the map - plan, then apply.

The plan is derived from doctor's ProjectReport (one fact-gathering pass, one
brain). Apply executes in fixed order: control-plane backfill, driftMap
renames, relocations, sweeps. Safety rules are the spec's section 6, verbatim:
deletions are rmdir-shaped (file-empty only), moves never clobber (collisions
survive in place and are reported), case-only renames go through a temp name,
every applied action is logged.

Control-plane backfill is constructive, with two bounded exceptions (ADR 0010).
Missing files are created exclusively. An existing PROJECT.md without the
machine contract is reported as a conflict and left unchanged. AGENTS.md's
marker-wrapped Atlas block is refreshed in place and nothing outside the markers
is touched. CLAUDE.md is rewritten to its one-line pointer only when its words
are stock generator output or already present in AGENTS.md; otherwise it is a
conflict and a person merges it.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from .doctor import ProjectReport, report_project
from .mapfile import DriveMap, TemplateFile, find_map, load_map
from .templates import TemplateError, render_template, template_values
from .ops import OpsError, append_log, mkdir_below
from .projectmd import (
    FRONT_MATTER_HEAD,
    AgentsBlockError,
    agents_md_lines,
    blank_intake_front_matter,
    blank_intake_identity_rows,
    carried_by,
    claude_md_lines,
    create_crlf_no_bom,
    decisions_readme_lines,
    is_claude_pointer,
    is_legacy_claude,
    meaningful_lines,
    with_agents_block,
    write_crlf_no_bom,
)
from .scan import (
    Listing,
    ProjectInventory,
    list_entries,
    long_path,
    scan_drive,
    tally_files,
    walk,
)

# Action kinds, in apply order.
BACKFILL = "backfill"
RENAME = "rename"
RELOCATE = "relocate"
SWEEP = "sweep"

# Statuses after apply.
DONE = "done"
CONFLICT = "conflict"   # no-clobber leftovers; a human resolves
SKIPPED = "skipped"
FAILED = "failed"       # an OS error stopped it; ``moved`` holds what moved first


# Windows refuses a path longer than this without the extended-length prefix,
# and so do Explorer, Revit, and the studio's PowerShell tools. Atlas warns when a
# move would create one and never applies long_path() on the write side: routing
# around the limit would make the warning dishonest. See ADR 0006 and ticket 19.
WINDOWS_MAX_PATH = 260


class NotInvertible(OpsError):
    """The applied Plan changed the drive in a way its manifests cannot reverse."""


@dataclass(frozen=True)
class Move:
    """One source-and-destination pair an Action actually moved.

    ``is_dir`` is recorded rather than re-read at inversion time: sending a
    merged child back needs to know whether it is a file (a sweep) or a folder
    (a relocate), and asking the filesystem later is both an extra read and a
    race against whatever happened in between.
    """

    src: str
    dst: str
    is_dir: bool


@dataclass(frozen=True)
class Action:
    kind: str
    src: str
    dst: str
    file_count: int = 0
    status: str = ""    # empty until applied
    note: str = ""
    # The Move Manifest: every pair this action actually moved. Empty until
    # applied, and still empty after a backfill, which creates rather than moves.
    moved: tuple[Move, ...] = ()
    # Longest absolute path this action would create, measured at preview time.
    # Zero when the plan was built without a project path to measure against.
    path_length: int = 0
    # What the write brought into existence that was not a Move: the file or
    # folder a backfill made, and any parent folder a move or sweep had to create
    # on the way. Empty until applied. The tree reconciles by it (ADR 0007), and
    # the undo removes created folders it leaves empty.
    created: tuple[str, ...] = ()
    # On an inverse Action only: folders the write being undone created, removed
    # after this action if they are then empty. Deepest first.
    prune: tuple[str, ...] = ()

    @property
    def path_warning(self) -> bool:
        return self.path_length > WINDOWS_MAX_PATH


@dataclass(frozen=True)
class Plan:
    project: str
    actions: tuple[Action, ...]
    # True for a Plan built by invert_plan. An undo puts things back; it never
    # takes the empty-duplicate shortcut, which deletes rather than moves.
    inverse: bool = False

    @property
    def empty(self) -> bool:
        return not self.actions


def _deepest_tail(src: Path) -> int:
    """Longest path below ``src``, measured from ``src`` itself; 0 when empty.

    One walk per previewed action, never per render (ticket 13). What matters
    after a move is not the folder's own path but the deepest thing under it,
    re-hung beneath a destination that may be longer than where it sits now.
    """
    # scan.walk prefixes every level, not only the top: a short source with a
    # deep subtree is otherwise under-measured on a machine without
    # LongPathsEnabled, exactly where the warning matters.
    base = os.fspath(src)
    root_len = len(base)
    deepest = 0
    for root, _dirs, files, links in walk(base):
        tail = len(root) - root_len
        deepest = max(deepest, tail)
        for name in (*files, *links):
            deepest = max(deepest, tail + 1 + len(name))
    return deepest


def measure_plan(plan: Plan, project: Path) -> Plan:
    """The Plan with every Action's path length measured against ``project``.

    For Plans ``build_plan`` did not make - an inverse above all. Undo moves
    things too, and can push them past MAX_PATH just as a repair can.
    """
    return replace(plan, actions=tuple(
        replace(a, path_length=_path_length(project, a)) for a in plan.actions))


def _path_length(project: Path | None, action: Action) -> int:
    """Longest absolute path the action would leave behind, or 0 if unmeasured."""
    if project is None:
        return 0
    # Absolute, always: a relative --drive measured 40 where Windows sees 220.
    project = Path(os.path.abspath(project))
    dst = action.dst.replace("\\", "/").rstrip("/")
    if action.kind == BACKFILL:
        return len(str(project / dst))
    if action.kind == SWEEP:
        return len(str(project / dst / Path(action.src).name))
    src = project / action.src
    if not src.is_dir():
        return len(str(project / dst))
    return len(str(project / dst)) + _deepest_tail(src)


def build_plan(report: ProjectReport, m: DriveMap, project: Path | None = None) -> Plan:
    """The Plan for everything the report found wrong with one project.

    ``project`` is the project folder on disk. Given it, every Action carries the
    longest path it would create, which is how the operator finds out before the
    write that a move would push something past MAX_PATH.
    """
    actions: list[Action] = []
    for item in report.missing_control_plane:
        actions.append(Action(kind=BACKFILL, src="", dst=item))
    for found, canonical in report.drift:
        actions.append(Action(kind=RENAME, src=found, dst=canonical))
    for hit in report.relocations:
        actions.append(Action(kind=RELOCATE, src=hit.source, dst=hit.target, file_count=hit.file_count))
    for name, target in report.sweeps:
        actions.append(Action(kind=SWEEP, src=name, dst=target))
    measured = tuple(
        replace(a, path_length=_path_length(project, a)) for a in actions
    )
    return Plan(project=report.name, actions=measured)


def node_key(*parts: str) -> str:
    """Project-relative path(s) joined in Node Key form: forward slashes, no
    empty segments, no leading or trailing slash.

    One function for both jobs. Normalising: what an operator types on Windows
    ("08 OUT\\Invoices", "Meetings/") and what the tree hands over must match
    the same Action. Joining: a plain f-string turns a root parent into
    ``/name``, which is not a Node Key, and on Windows ``project / "/name"``
    resolves against the drive root rather than the project.
    """
    return "/".join(seg for part in parts for seg in part.replace("\\", "/").split("/") if seg)


def build_repair_plan(report: ProjectReport, m: DriveMap, path: str,
                      project: Path | None = None) -> Plan:
    """The Plan for one node's Repair, holding one Action or none.

    ``path`` is project-relative: the Tree Node's own path for a Drifted,
    Misplaced or Loose node, and the Expectation's path for a Backfill. A Mapped
    or Unfiled node earns no Repair and yields an empty Plan, as does a path the
    report knows nothing about.

    The Action is taken from the full Plan rather than derived a second way. The
    tree introduces no action kinds of its own (ADR 0006), and two derivations of
    "what does this node need" would eventually disagree.
    """
    path = node_key(path)
    # Unmeasured first, then only the match: measuring walks each source's
    # subtree, and a one-node repair has no business walking the others (#46).
    full = build_plan(report, m, project=None)
    match = next(
        (a for a in full.actions if a.src == path),
        next((a for a in full.actions if not a.src and a.dst == path), None),
    )
    if match is None:
        return Plan(project=report.name, actions=())
    return Plan(project=report.name,
                actions=(replace(match, path_length=_path_length(project, match)),))


def action_to_dict(action: Action) -> dict:
    """One Action as JSON. The record is read by six surfaces; this is the one
    that leaves the process, so it names its own fields rather than shipping
    whatever ``__dict__`` happens to hold."""
    return {
        "kind": action.kind,
        "src": action.src,
        "dst": action.dst,
        "file_count": action.file_count,
        "status": action.status,
        "note": action.note,
        "moved": [{"src": mv.src, "dst": mv.dst, "is_dir": mv.is_dir}
                  for mv in action.moved],
        "path_length": action.path_length,
        "path_warning": action.path_warning,
        "created": list(action.created),
        "prune": list(action.prune),
    }


def plan_from_dict(payload: dict) -> Plan:
    """A Plan back from the JSON ``action_to_dict`` produced.

    The return leg. Without it the Move Manifest is write-only: six surfaces can
    read one and nothing can feed one back, which leaves ``invert_plan``
    reachable only from inside a live session. A stateless undo needs this.

    Refuses a manifest missing a field rather than defaulting it. By the time a
    manifest comes back it is operator-supplied input, and a silently defaulted
    ``moved`` becomes an uninvertible Plan two steps later, where the message no
    longer names the real problem. ``path_warning`` is derived and ignored on the
    way in - it is a property, and honouring a supplied one would let a manifest
    contradict its own ``path_length``. ``created`` and ``prune`` came later and
    default to empty, so a manifest an older Atlas printed still reads back.
    """
    try:
        actions = tuple(
            Action(
                kind=_known_kind(a["kind"]),
                src=_inside(a["src"], "src"),
                dst=_inside(a["dst"], "dst"),
                file_count=a["file_count"],
                status=a["status"],
                note=a["note"],
                moved=tuple(
                    Move(src=_inside(mv["src"], "moved src", required=True),
                         dst=_inside(mv["dst"], "moved dst", required=True),
                         is_dir=mv["is_dir"])
                    for mv in a["moved"]
                ),
                path_length=a["path_length"],
                # Both name folders Atlas will rmdir: the same path rule applies.
                created=tuple(_inside(k, "created", required=True)
                              for k in a.get("created", ())),
                prune=tuple(_inside(k, "prune", required=True)
                            for k in a.get("prune", ())),
            )
            for a in payload["actions"]
        )
        return Plan(project=_one_folder(payload["project"]), actions=actions)
    except (KeyError, TypeError) as error:
        raise OpsError(f"manifest is missing {error}") from error


def _known_kind(kind: object) -> str:
    if kind not in (BACKFILL, RENAME, RELOCATE, SWEEP):
        raise OpsError(f"manifest names an unknown action kind {kind!r}")
    return kind


def _inside(path: object, field: str, *, required: bool = False) -> str:
    """A project-relative path from an operator-supplied manifest, or refuse.

    Every path in a manifest is joined onto the project folder. Without this, a
    crafted ``..``, absolute or drive-lettered path moved things in from - or
    out to - anywhere the operator could write (#9).
    """
    if not isinstance(path, str):
        raise OpsError(f"manifest {field} is not a path: {path!r}")
    normalised = path.replace("\\", "/")
    parts = normalised.split("/")
    if (normalised.startswith("/") or re.match(r"^[A-Za-z]:", normalised)
            or ".." in parts or (required and not node_key(normalised))):
        raise OpsError(f"manifest {field} '{path}' is not a path inside the project")
    return path


def _one_folder(name: object) -> str:
    """A manifest's project: one folder name, never a path."""
    if (not isinstance(name, str) or not name or name in (".", "..")
            or any(c in name for c in "/\\:")):
        raise OpsError(f"manifest project {name!r} is not a project folder name")
    return name


# ----------------------------------------------------------------- inverse


def parent_key(rel: str) -> str:
    """Project-relative parent of a project-relative path; "" at the root."""
    normalised = rel.replace("\\", "/").rstrip("/")
    return normalised.rpartition("/")[0]


def child_key(parent: str, name: str) -> str:
    """The Node Key of ``name`` inside ``parent``; the root's key is "".
    ``node_key`` under the name that reads right at a join."""
    return node_key(parent, name)


def invert_plan(plan: Plan) -> Plan:
    """The Plan that reverses an applied one, built from the Move Manifests.

    Undo is not a special execution mode: it is an ordinary Plan that happens to
    move things back, and it goes through ``apply_plan`` like anything else.

    Invertibility is all-or-nothing. An action that changed the drive in a way
    its manifest does not describe - a backfill, which creates, or a removed
    file-empty source, which deletes - makes the whole Plan uninvertible. A
    partial undo would leave a third state that is neither before nor after, and
    the operator pressed one key expecting one thing.

    A conflicted move is not that. A merge that meets a name collision leaves the
    colliding item where it was and records every item it did move, so reversing
    its manifest restores the drive exactly - the collision never left. Seeded
    skeletons make that the common merge (issue #48). A conflicted backfill is
    still refused: its manifest never describes what it changed.
    """
    for action in plan.actions:
        if action.status == SKIPPED or (action.status == FAILED and not action.moved):
            continue    # nothing happened, so there is nothing to reverse
        if action.status == FAILED:
            continue    # stopped part-way: what its manifest moved goes back
        if action.status == CONFLICT and action.kind in (RENAME, RELOCATE, SWEEP):
            continue    # the manifest names exactly what moved, possibly nothing
        if action.status != DONE:
            raise NotInvertible(
                f"{action.kind} {action.src or action.dst} is "
                f"{action.status or 'not applied'}; the plan cannot be reversed"
            )
        if not action.moved:
            raise NotInvertible(
                f"{action.kind} {action.src or action.dst} moved nothing Atlas can "
                f"put back; the plan cannot be reversed"
            )
    # Last applied, first undone. One action's destination can contain another's
    # (rename `10 Legal Business` -> `10 Legal`, then relocate into `10 Legal`),
    # and undoing the outer move first carries the inner one away with it. The
    # applied Plan is already in apply order, so reversing it is the whole rule;
    # apply_plan keeps an inverse Plan's order rather than re-sorting by kind.
    actions: list[Action] = []
    for action in reversed(plan.actions):
        start = len(actions)
        for mv in reversed(action.moved):
            if mv.is_dir:
                actions.append(Action(kind=RELOCATE, src=mv.dst, dst=mv.src))
            else:
                # A file goes back by sweep, whose destination is the folder it
                # came from. _apply_move refuses files outright.
                actions.append(Action(kind=SWEEP, src=mv.dst, dst=parent_key(mv.src)))
        if action.created and len(actions) > start:
            # The folders this action had to create go once its moves are back,
            # so the undo leaves no empty parent that existed neither before nor
            # after. Removed only if empty: someone may have filed into them.
            prune = tuple(sorted(action.created, key=lambda k: k.count("/"), reverse=True))
            actions[-1] = replace(actions[-1], prune=prune)
    return Plan(project=plan.project, actions=tuple(actions), inverse=True)


# ------------------------------------------------------------------ guards

# What one watched directory looked like at preview time.
_Snapshot = tuple[str, str, tuple[tuple[str, bool], ...]]


def _watched_dirs(plan: Plan) -> tuple[str, ...]:
    """The project-relative directories a Plan's actions read and write.

    A move watches the parents its item leaves and arrives in. A sweep's
    destination is already a directory, so it is watched as itself. A backfill
    watches whatever would contain the thing it creates.
    """
    dirs: set[str] = set()
    for action in plan.actions:
        if action.src:
            dirs.add(parent_key(action.src))
        dst = action.dst.replace("\\", "/").rstrip("/")
        dirs.add(dst if action.kind == SWEEP else parent_key(dst))
    return tuple(sorted(dirs))


def _identity(action: Action) -> tuple[str, str, str]:
    """What an action does, without what it costs to describe."""
    return action.kind, action.src, action.dst


def _snapshot(project: Path, dirs: tuple[str, ...]) -> tuple[_Snapshot, ...]:
    """Enumerate the watched directories, carrying Load State so that a folder
    that became unreadable reads as a change rather than as an empty one."""
    shots: list[_Snapshot] = []
    for rel in dirs:
        listing = list_entries(project / rel if rel else project)
        shots.append((rel, listing.state,
                      tuple(sorted((e.name, e.is_dir) for e in listing))))
    return tuple(shots)


@dataclass(frozen=True)
class Guard:
    """What a preview saw, and what has to still be true before Atlas writes.

    Guard strength scales with action scope (ADR 0006). A project-wide conform
    keeps the rescan it has always had; a one-action Plan from a Tree Node
    re-reads only the map and the directories that action touches, because a
    keystroke cannot afford a walk of the whole drive.

    Both scopes abort the same way and for the same reasons: the map changed, the
    project went away, the rebuilt actions differ, or a watched directory differs.
    The scoped guard deliberately does not see a change elsewhere in the project -
    that is what makes it cheap, and it is safe because such a change cannot alter
    what the guarded action does.
    """

    project: str
    drive_map: DriveMap
    actions: tuple[Action, ...]
    watched: tuple[_Snapshot, ...]
    whole_project: bool
    node: str = ""
    # Whether the guarded actions can be re-derived from the drive map at all.
    # A repair can: it is a slice of the Plan conform builds, so rebuilding it
    # and comparing is the strongest check available. An undo cannot, because
    # its Plan reverses the map rather than following it - see for_undo.
    derived: bool = True

    @classmethod
    def for_project(cls, drive_root: Path, project: str, m: DriveMap, plan: Plan,
                    root_listing: Listing | None = None) -> Guard:
        """Guard a whole-project conform: every action, and the project root.

        ``root_listing`` is the root as the preview's scan saw it. Pass it when
        the plan came from that scan, so a change between scan and confirm is
        caught too; without it the root is snapshotted now.
        """
        if root_listing is None:
            watched = _snapshot(drive_root / project, ("",))
        else:
            watched = (("", root_listing.state,
                        tuple(sorted((e.name, e.is_dir) for e in root_listing))),)
        return cls(project=project, drive_map=m, actions=plan.actions,
                   watched=watched, whole_project=True)

    @classmethod
    def for_action(cls, drive_root: Path, project: str, m: DriveMap, plan: Plan) -> Guard:
        """Guard one node's Repair: that action, and the directories it touches."""
        node = plan.actions[0].src or plan.actions[0].dst if plan.actions else ""
        return cls(project=project, drive_map=m, actions=plan.actions,
                   watched=_snapshot(drive_root / project, _watched_dirs(plan)),
                   whole_project=False, node=node)

    @classmethod
    def for_undo(cls, drive_root: Path, project: str, m: DriveMap, inverse: Plan) -> Guard:
        """Guard an undo: the map, and the directories the inverse touches.

        Not ``for_action``. That one re-derives the Plan from the drive map and
        compares, which is the strongest check available for a repair - and
        impossible for an undo, whose Plan reverses the map instead of following
        it. Guarding an inverse that way refuses every time, on a drive nothing
        has changed on. ADR 0006 assumed one guard served both; it does not, and
        ADR 0008's ticket found out by pressing the key.

        What an undo actually has to verify is not "does the map still want this
        work" - it never did - but "are these folders still as they were when the
        repair applied". That is the snapshot, and the snapshot is unchanged.
        """
        node = inverse.actions[0].src or inverse.actions[0].dst if inverse.actions else ""
        return cls(project=project, drive_map=m, actions=inverse.actions,
                   watched=_snapshot(drive_root / project, _watched_dirs(inverse)),
                   whole_project=False, node=node, derived=False)

    def check(self, drive_root: Path) -> str | None:
        """Re-read what was watched. Returns why the Plan is stale, or None."""
        project_path = drive_root / self.project
        if not project_path.is_dir():
            return f"{self.project} is no longer available"

        if self.whole_project:
            # The rescan conform has always paid for: it also refreshes the
            # drive-wide view the operator is looking at.
            fresh_map = scan_drive(drive_root).map
        else:
            map_path = find_map(drive_root)
            if map_path is None:
                return "the drive map is no longer there"
            fresh_map = load_map(map_path)
        if fresh_map != self.drive_map:
            return "the drive map changed"

        if self.derived:
            inv = ProjectInventory(path=project_path, name=self.project,
                                   root_entries=list_entries(project_path))
            if self.whole_project:
                report = report_project(inv, fresh_map)
                fresh = build_plan(report, fresh_map, project=project_path).actions
                if fresh != self.actions:
                    return f"{self.project} no longer needs the same work"
            else:
                # What ADR 0006 promised and the first version did not do: no
                # walk. File counts and path lengths describe the work, they do
                # not decide it - the action is its kind and its two ends, and
                # the watched parents below catch anything that moved (#46).
                report = report_project(inv, fresh_map, count_files=False)
                fresh = build_repair_plan(report, fresh_map, self.node).actions
                if [_identity(a) for a in fresh] != [_identity(a) for a in self.actions]:
                    return f"{self.project} no longer needs the same work"

        if _snapshot(project_path, tuple(rel for rel, _s, _e in self.watched)) != self.watched:
            return f"{self.project} changed on disk since the preview"
        return None


# ------------------------------------------------------------------- apply

def apply_plan(drive_root: Path, project: Path, m: DriveMap, plan: Plan,
               only: set[str] | None = None) -> Plan:
    """Execute the plan; returns it with per-action statuses filled in."""
    if not project.is_dir():
        raise OpsError(f"project folder is no longer available: {project}")
    applied: list[Action] = []
    order = {BACKFILL: 0, RENAME: 1, RELOCATE: 2, SWEEP: 3}
    ordered = plan.actions if plan.inverse else sorted(plan.actions, key=lambda a: order[a.kind])
    try:
        for action in ordered:
            if only and action.kind not in only:
                applied.append(replace(action, status=SKIPPED, note="filtered by --only"))
                continue
            # One failed action fails that action, not the process: a file held
            # open in Revit or Excel refuses the rename, and everything that
            # already moved must still be recorded, logged and undoable.
            try:
                absent = _absent_chain(project, _created_root(action))
                result = _apply_one(project, m, action, inverse=plan.inverse)
            except OSError as error:
                applied.append(replace(action, status=FAILED, note=_os_note(error)))
                continue
            created = tuple(rel for rel in absent if (project / rel).exists())
            if created:
                result = replace(result, created=created)
            if result.status == DONE and action.prune:
                _prune_empty(project, action.prune)
            applied.append(result)
    finally:
        _log_applied(drive_root, project, applied)
    return Plan(project=plan.project, actions=tuple(applied), inverse=plan.inverse)


def _apply_one(project: Path, m: DriveMap, action: Action, *, inverse: bool = False) -> Action:
    if action.kind == BACKFILL:
        return _apply_backfill(project, m, action)
    if action.kind in (RENAME, RELOCATE):
        return _apply_move(project, action, merge_into_existing=True,
                           remove_empty_duplicate=not inverse)
    if action.kind == SWEEP:
        return _apply_sweep(project, action)
    return replace(action, status=SKIPPED, note=f"unknown action kind '{action.kind}'")


def _os_note(error: OSError, where: str = "") -> str:
    name = Path(error.filename).name if error.filename else where
    reason = error.strerror or str(error)
    return f"{name}: {reason}" if name else reason


def _log_applied(drive_root: Path, project: Path, applied: list[Action]) -> None:
    """One drive-log line for whatever changed the drive, failures included.

    Written in a ``finally`` so a failure part-way still leaves a record of
    what moved before it. A failed action is logged only when it moved
    something - its manifest is the record.
    """
    parts = []
    for a in applied:
        if a.status == DONE:
            parts.append(f"{a.kind} {a.src or a.dst} -> {a.dst}")
        elif a.status == FAILED and a.moved:
            moved = ", ".join(f"{mv.src} -> {mv.dst}" for mv in a.moved)
            parts.append(f"{a.kind} {a.src} -> {a.dst} FAILED ({a.note}) after moving {moved}")
    if parts:
        try:
            append_log(drive_root, f"[{project.name}] conform: " + "; ".join(parts))
        except OSError:
            pass    # the log is a record, never a reason to lose the result


def _created_root(action: Action) -> str:
    """The deepest path an action may bring into existence other than by a Move:
    a backfill's target, a sweep's destination folder, a move's parent."""
    dst = action.dst.replace("\\", "/").rstrip("/")
    if action.kind in (BACKFILL, SWEEP):
        return dst
    return parent_key(dst)


def _absent_chain(project: Path, rel: str) -> tuple[str, ...]:
    """``rel`` and each of its ancestors that does not exist yet, shallowest first."""
    absent: list[str] = []
    parts = [p for p in rel.split("/") if p]
    for depth in range(1, len(parts) + 1):
        key = "/".join(parts[:depth])
        if not (project / key).exists():
            absent.append(key)
    return tuple(absent)


def _prune_empty(project: Path, keys: tuple[str, ...]) -> None:
    """Remove each folder that is now entirely empty, deepest first. rmdir is the
    whole check: it refuses a folder with anything at all in it."""
    for key in keys:
        try:
            (project / key).rmdir()
        except OSError:
            pass


# ---- control plane ---------------------------------------------------------

_HAS_FRONT_MATTER = re.compile(r"^\s*---")  # same test Conform-Project.ps1 uses


def _conform_project_md_lines(m: DriveMap, leaf: str) -> list[str]:
    """The Conform-Project.ps1 stub (leaner than New-Project's - no Site/
    Zoning/Program sections, no folder map; Conform never invents metadata)."""
    display = re.sub(r"^\d{6}_", "", leaf)
    lines = list(FRONT_MATTER_HEAD)
    lines += blank_intake_front_matter(display)
    lines += [
        "",
        f"# {leaf}",
        "",
        "> Maintained by Architecture Studio skills and the project team. Facts only -",
        "> rationale lives in `decisions/`. The YAML front-matter above is the machine",
        "> mirror of the Identity + Code tables; keep them in agreement.",
        "> **Next:** run `/project-dossier` to fill in the project facts.",
        "",
        "## Identity", "",
        "| Field | Value |", "|-------|-------|",
    ]
    lines += blank_intake_identity_rows(display)
    lines += [
        "",
        "## Code", "",
        "<!-- Mirrors the machine contract in the front-matter. Change a value here -> change it there too. -->", "",
        "| Item | Value | Source | Date |", "|------|-------|--------|------|",
        "| Building code edition | | | |", "| Occupancy group | | | |", "| Construction type | | | |",
        "| Sprinklered | | | |", "| Stories | | | |", "| Building area (SF) | | | |", "| Frontage (ft) | | | |",
        "| Existing C-of-O occupant load | | | |", "| Existing exits | | | |",
        "| Place-of-assembly strategy | | | |", "| Tenancy | | | |",
        "",
        "## Decisions", "",
        "<!-- maintained by /decision - do not edit by hand -->", "",
        "| # | Decision | Status | Date |", "|---|----------|--------|------|",
    ]
    return lines


def _apply_backfill(project: Path, m: DriveMap, action: Action) -> Action:
    target = action.dst
    if target == m.project_file:
        path = project / m.project_file
        if not path.exists():
            if create_crlf_no_bom(path, _conform_project_md_lines(m, project.name)):
                return replace(action, status=DONE, note="created stub")
            return replace(action, status=SKIPPED, note="appeared during apply; rerun")
        raw = path.read_text(encoding="utf-8-sig")
        if _HAS_FRONT_MATTER.match(raw):
            return replace(action, status=SKIPPED, note="machine contract already present")
        return replace(
            action,
            status=CONFLICT,
            note="existing PROJECT.md lacks machine contract; left unchanged",
        )
    if target == m.decisions_dir:
        mkdir_below(project, m.decisions_dir)
        dec = project / m.decisions_dir
        readme = dec / "README.md"
        if not readme.exists() and not create_crlf_no_bom(readme, decisions_readme_lines()):
            return replace(action, status=SKIPPED, note="README appeared during apply; rerun")
        return replace(action, status=DONE)
    if m.agents_file and target == m.agents_file:
        return _backfill_agents(project, m, action)
    if target == m.claude_file:
        return _backfill_claude(project, m, action)
    if target == m.analysis_dir:
        mkdir_below(project, m.analysis_dir)
        return replace(action, status=DONE)
    if target in m.workspace_dirs:
        mkdir_below(project, target)
        return replace(action, status=DONE, note="agent workspace")
    template = next((t for t in m.templates if t.path == target), None)
    if template is not None:
        return _backfill_template(project, template, action)
    if target in m.seed_child_paths():
        if not (project / target.split("/")[0]).is_dir():
            return replace(action, status=SKIPPED, note="its section is gone; rerun")
        mkdir_below(project, target)
        return replace(action, status=DONE, note="seeded folder")
    return replace(action, status=SKIPPED, note=f"unknown control-plane item '{target}'")


def _backfill_template(project: Path, template: TemplateFile, action: Action) -> Action:
    """Create a template file and its folder. Create-only: a file already there
    is the project's own, however different, and stays (ADR 0012)."""
    try:
        lines = render_template(template.template,
                                template_values(project.name, created=date.today().isoformat()))
    except TemplateError as error:
        return replace(action, status=SKIPPED, note=str(error))
    parent = template.path.rpartition("/")[0]
    if parent:
        mkdir_below(project, parent)
    if not create_crlf_no_bom(project / template.path, lines):
        return replace(action, status=SKIPPED, note="already there; left unchanged")
    return replace(action, status=DONE, note=f"from template {template.template}")


# ---- agent files (ADR 0010) ---------------------------------------------------

def _root_spelling(project: Path, name: str) -> str | None:
    """How the root file ``name`` is actually spelled, or None if it is absent.

    Path.exists() is case-insensitive on this mount, so it cannot tell AGENTS.md
    from the Agents.md a person saved by hand. Only a listing can.
    """
    variant = None
    for e in list_entries(project):
        if e.is_dir or e.name.lower() != name.lower():
            continue
        if e.name == name:
            return name
        variant = e.name
    return variant


def _canonical_spelling(project: Path, name: str) -> tuple[bool, str]:
    """Give the root file ``name`` exactly that spelling.

    Returns whether it exists, plus a note when a case variant was renamed. Two
    steps through a temp name, as for folders: a one-step case-only rename is a
    no-op on a case-insensitive mount.
    """
    found = _root_spelling(project, name)
    if found is None:
        return False, ""
    if found == name:
        return True, ""
    tmp = project / f"{found}.atlas-tmp"
    (project / found).rename(tmp)
    tmp.rename(project / name)
    return True, f"renamed {found} -> {name}"


def _read_utf8(path: Path) -> tuple[bytes, str] | None:
    raw = path.read_bytes()
    try:
        return raw, raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def _notes(*parts: str) -> str:
    return "; ".join(p for p in parts if p)


def _backfill_agents(project: Path, m: DriveMap, action: Action) -> Action:
    exists, renamed = _canonical_spelling(project, m.agents_file)
    path = project / m.agents_file
    if not exists:
        claude = project / m.claude_file
        seed = _read_utf8(claude) if m.claude_file and claude.is_file() else None
        text = seed[1] if seed else ""
        if meaningful_lines(text) and not is_claude_pointer(text, m) and not is_legacy_claude(text, m):
            # A person's CLAUDE.md becomes AGENTS.md with its words intact; the
            # CLAUDE.md backfill points at it once it can see them here.
            lines, note = with_agents_block(text.splitlines(), m), f"created from {m.claude_file}"
        else:
            lines, note = agents_md_lines(m), ""
        if not create_crlf_no_bom(path, lines):
            return replace(action, status=SKIPPED, note="appeared during apply; rerun")
        return replace(action, status=DONE, note=note)

    read = _read_utf8(path)
    if read is None:
        return replace(action, status=CONFLICT, note=_notes(renamed, "not UTF-8; left unchanged"))
    raw, text = read
    try:
        lines = with_agents_block(text.splitlines(), m)
    except AgentsBlockError as error:
        return replace(action, status=CONFLICT, note=_notes(renamed, str(error)))
    if lines == text.splitlines():
        return replace(action, status=DONE if renamed else SKIPPED,
                       note=renamed or "Atlas block already current")
    if path.read_bytes() != raw:
        return replace(action, status=SKIPPED, note=_notes(renamed, "changed during apply; rerun"))
    write_crlf_no_bom(path, lines)
    return replace(action, status=DONE, note=_notes(renamed, "Atlas block written"))


def _backfill_claude(project: Path, m: DriveMap, action: Action) -> Action:
    exists, renamed = _canonical_spelling(project, m.claude_file)
    path = project / m.claude_file
    if not exists:
        if not create_crlf_no_bom(path, claude_md_lines(m)):
            return replace(action, status=SKIPPED, note="appeared during apply; rerun")
        return replace(action, status=DONE)
    if not m.agents_file:
        return replace(action, status=DONE if renamed else SKIPPED, note=renamed or "exists")

    read = _read_utf8(path)
    if read is None:
        return replace(action, status=CONFLICT, note=_notes(renamed, "not UTF-8; left unchanged"))
    raw, text = read
    if is_claude_pointer(text, m):
        return replace(action, status=DONE if renamed else SKIPPED,
                       note=renamed or "already a pointer")
    agents = project / m.agents_file
    host = _read_utf8(agents) if agents.is_file() else None
    if host is None:
        return replace(action, status=CONFLICT, note=_notes(
            renamed, f"no readable {m.agents_file} to point at; left unchanged"))
    if not (is_legacy_claude(text, m) or carried_by(text, host[1])):
        return replace(action, status=CONFLICT, note=_notes(
            renamed, f"has words {m.agents_file} lacks; merge them there, then rerun"))
    if path.read_bytes() != raw:
        return replace(action, status=SKIPPED, note=_notes(renamed, "changed during apply; rerun"))
    write_crlf_no_bom(path, claude_md_lines(m))
    return replace(action, status=DONE, note=_notes(renamed, f"now points at {m.agents_file}"))


# ---- moves (renames + relocations share one engine) -------------------------

def _empty_levels(path: Path):
    """The bottom-up walk of ``path`` if nothing beneath holds a file or a link
    and every folder could be read; otherwise None. Not known empty is not empty."""
    errors: list[tuple[str, str]] = []
    levels = list(walk(path, topdown=False, errors=errors))
    if errors or any(files or links for _root, _dirs, files, links in levels):
        return None
    return levels


def _remove_if_file_empty(path: Path) -> bool:
    """rmdir ``path`` and its folders if nothing beneath holds a file or a link.

    A link is content: its target lives elsewhere, and walking into a junction
    here once removed empty folders outside the project.
    """
    levels = _empty_levels(path)
    if levels is None:
        return False
    for root, dirs, _files, _links in levels:
        for d in dirs:
            os.rmdir(long_path(os.path.join(root, d)))
    path.rmdir()
    return True


MOVE = "move"
MERGE = "merge"
REMOVE = "remove"


def _same_folder(src: Path, dst: Path) -> bool:
    """Whether two spellings name one folder - a case-only rename on a
    case-insensitive mount, where ``dst.exists()`` is true of the source itself."""
    try:
        return os.path.samefile(src, dst)
    except OSError:
        return False


def move_effect(project: Path, action: Action, *, inverse: bool = False) -> str:
    """What applying a RENAME or RELOCATE would do right now: MOVE, MERGE or REMOVE.

    The same rule ``_apply_move`` follows, so a preview cannot promise a rename
    and then delete. REMOVE is the empty-duplicate shortcut: the source holds no
    files and the destination is a separate folder that already exists. An
    inverse Plan never removes - an undo puts things back.
    """
    src = project / action.src
    dst = project / action.dst
    if not dst.exists() or _same_folder(src, dst):
        return MOVE
    if not inverse and src.is_dir() and _empty_levels(src) is not None:
        return REMOVE
    return MERGE


def _apply_move(project: Path, action: Action, merge_into_existing: bool,
                remove_empty_duplicate: bool = True) -> Action:
    src = project / action.src
    dst = project / action.dst
    if not src.is_dir():
        return replace(action, status=SKIPPED, note="source gone")

    # A source with a folder Atlas cannot read is not known to be empty, and
    # what cannot be seen cannot be accounted for in a manifest. Leave it.
    tally = tally_files(src)
    if not tally.known:
        rel, _why = tally.unreadable[0]
        where = action.src if rel == "." else f"{action.src}/{rel}"
        return replace(action, status=CONFLICT, note=f"cannot read {where}; left in place")

    if _same_folder(src, dst) and action.src != action.dst:
        # Case-only rename on a case-insensitive mount: two-step via temp.
        tmp = src.with_name(src.name + ".atlas-tmp")
        src.rename(tmp)
        try:
            tmp.rename(dst)
        except OSError as error:
            # Never strand the folder under its temp name: put it back first.
            try:
                tmp.rename(src)
            except OSError:
                return replace(action, status=FAILED, note=(
                    f"{_os_note(error, action.src)}; left as {tmp.name}"),
                    moved=(Move(src=action.src, dst=f"{action.src}.atlas-tmp", is_dir=True),))
            return replace(action, status=FAILED, note=_os_note(error, action.src))
        return replace(action, status=DONE, note="case-only rename",
                       moved=(Move(src=action.src, dst=action.dst, is_dir=True),))

    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        return replace(action, status=DONE,
                       moved=(Move(src=action.src, dst=action.dst, is_dir=True),))

    # Empty duplicate: the canonical home already exists and owns the artifact
    # class, so a source with no files in it is removed rather than merged. Only
    # here, where the destination is a separate existing folder - anywhere
    # earlier it deletes a folder the preview said it would rename.
    if remove_empty_duplicate and _remove_if_file_empty(src):
        return replace(action, status=DONE, note="removed file-empty source")

    if not merge_into_existing:
        return replace(action, status=CONFLICT, note="target exists")

    # Merge, never clobber: move each child whose name is free at the target.
    manifest: list[Move] = []
    left = 0
    try:
        for child in list(src.iterdir()):
            target = dst / child.name
            if target.exists():
                left += 1
                continue
            is_dir = child.is_dir()
            child.rename(target)
            manifest.append(Move(src=child_key(action.src, child.name),
                                 dst=child_key(action.dst, child.name), is_dir=is_dir))
        emptied = left == 0 and _remove_if_file_empty(src)
    except OSError as error:
        # Earlier children already moved. The manifest is the only record of
        # which, so it leaves with the failure rather than being lost to it.
        return replace(action, status=FAILED, note=_os_note(error),
                       moved=tuple(manifest))
    moved = len(manifest)
    if emptied:
        return replace(action, status=DONE, note=f"merged {moved} item(s)",
                       moved=tuple(manifest))
    return replace(action, status=CONFLICT,
                   note=f"merged {moved}, {left} name collision(s) left in {action.src}",
                   moved=tuple(manifest))


def _apply_sweep(project: Path, action: Action) -> Action:
    src = project / action.src
    if not src.is_file():
        return replace(action, status=SKIPPED, note="source gone")
    dst_rel = action.dst.replace("\\", "/").rstrip("/")
    dst_dir = project / dst_rel
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / src.name
    if target.exists():
        return replace(action, status=CONFLICT, note="name exists at target")
    src.rename(target)
    return replace(action, status=DONE,
                   moved=(Move(src=action.src, dst=child_key(dst_rel, src.name), is_dir=False),))
