"""The Deep Pass: the opt-in walk below one project's root (ticket 31,
robustness plan 1.4-1.6).

Opt-in only (`doctor --deep PROJECT`, `conform --deep`) - the default
doctor/conform report stays root-only and its cost bound depends on it. One
project's walk is bounded by that project; `--all --deep` pays the full drive
walk by flag, never by default.

One enumeration per folder gathers everything the pass knows, so no fact ever
pays a second walk:

- **Receipt Rule hits** (ticket 31): name filters only, so a match costs
  nothing beyond the listing Atlas already holds. The agent workspace itself
  (runsDir, backupsDir, the map's agent_dirs) is exempt from *matching* -
  files already there are where receipts belong - but it is walked and
  counted like anywhere else: run volume is exactly what eats the drive's
  item cap (ADR 0011).
- **Unreadable folders** (plan 1.5): a folder the walk cannot open is
  reported, never read as empty (ADR 0004).
- **Over-long paths** (plan 1.4): ticket 04's Path Length Warning covers what
  Atlas is about to create; this names paths already on disk that nobody is
  moving. A directory fails one character earlier than a file - Win32 needs
  room for the enumeration suffix, and the latency report's live failure is
  a 259-character folder - so dirs flag at 259, files past 260, the same bar
  conform's warning uses. Only the first crossing per branch is named:
  everything below an over-long folder is over-long by inheritance, and
  listing each child is noise on the finding, not information.
- **Item counts** (plan 1.6): files and folders, free on top of the
  enumeration, against the shared-drive item cap.

The walk enumerates and never opens a file. It never descends into a
junction, and it stops DEEP_MAX_DEPTH levels below the project root - a
per-folder depth guard bounding cost and stack on a pathological tree. A
folder at the boundary is named in ``depth_capped``: a truncated scan is a
fact, never a silent zero.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .filerules import names_match
from .mapfile import DriveMap
from .scan import WINDOWS_MAX_PATH, is_link, long_path

# Per-folder depth guard. Real project trees sit under a dozen levels; 64 is
# far past anything legitimate (at 64 levels even short names blow past
# MAX_PATH) and bounds the walk when something below is pathological. Read at
# call time so tests can shrink it.
DEEP_MAX_DEPTH = 64

# Google's per-shared-drive item limit (files + folders). The studio drive
# paid for every agent-run file against it (ADR 0011); the budget finding
# makes the number visible instead of a periodic surprise (plan 1.6).
DRIVE_ITEM_CAP = 400_000

# The text report speaks once the drive is past half the cap; --json always
# carries the number.
BUDGET_WARN_FRACTION = 0.5


@dataclass(frozen=True)
class ReceiptHit:
    """One Receipt Rule match: the project-relative path, the workspace target
    the rule files it to, and the rule's name, so doctor can attribute it the
    way it attributes File Rule sweeps (ADR 0009)."""

    path: str
    target: str
    rule: str


@dataclass(frozen=True)
class OverlongPath:
    """One existing path past the length Win32 opens without the
    extended-length prefix: project-relative path and absolute length."""

    path: str
    length: int


@dataclass(frozen=True)
class ItemCount:
    """Files and folders below the project root. Links count as files: a
    junction still spends one of the drive's items, it is just never
    descended."""

    files: int = 0
    folders: int = 0

    @property
    def total(self) -> int:
        return self.files + self.folders


@dataclass(frozen=True)
class DeepScan:
    hits: tuple[ReceiptHit, ...] = ()
    # "relpath  reason" lines, in the shape doctor's own unreadable list uses.
    unreadable: tuple[str, ...] = ()
    overlong: tuple[OverlongPath, ...] = ()
    depth_capped: tuple[str, ...] = ()
    items: ItemCount = ItemCount()


def scan_deep(project: Path, m: DriveMap) -> DeepScan:
    """Walk one project, gathering the deep pass's facts in one enumeration
    per folder.

    Bounded by the project, long_path() at every level (ticket 19). Never
    touches a second project - the caller scopes that.
    """
    workspace = {d.replace("\\", "/").strip("/").casefold() for d in m.agent_dirs}
    hits: list[ReceiptHit] = []
    unreadable: list[str] = []
    overlong: list[OverlongPath] = []
    depth_capped: list[str] = []
    files = folders = 0

    # Iterative with an explicit stack: the depth guard, not Python's
    # recursion limit, is what bounds a pathological tree.
    stack: list[tuple[str, int, bool]] = [("", 0, False)]  # rel, depth, under over-long
    while stack:
        rel, depth, under_overlong = stack.pop()
        try:
            with os.scandir(long_path(project / rel if rel else project)) as it:
                entries = list(it)
        except OSError as exc:
            unreadable.append(f"{rel or '.'}  {type(exc).__name__}: {exc.strerror or exc}")
            continue
        children: list[tuple[str, int, bool]] = []
        for entry in entries:
            child = f"{rel}/{entry.name}" if rel else entry.name
            try:
                if is_link(entry):
                    files += 1  # links are leaves; never descend, never move
                    continue
                directory = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue        # the entry itself failed; its folder was read
            # Measure what Windows will see, not the string given (long_path's
            # rule): a short relative path can be far longer absolute.
            length = len(os.path.abspath(os.path.join(os.fspath(project), child)))
            over = length + (2 if directory else 0) > WINDOWS_MAX_PATH
            if over and not under_overlong:
                overlong.append(OverlongPath(path=child, length=length))
            if directory:
                folders += 1
                if depth + 1 >= DEEP_MAX_DEPTH:
                    depth_capped.append(child)
                else:
                    children.append((child, depth + 1, under_overlong or over))
            else:
                files += 1
                # Files at the root are File Rules' ground, not receipts, and
                # files in the agent workspace are already where receipts
                # belong.
                if rel and not any(child.casefold() == w or
                                   child.casefold().startswith(w + "/")
                                   for w in workspace):
                    rule = next((r for r in m.receipt_rules
                                 if names_match(r, entry.name)), None)
                    if rule is not None:
                        hits.append(ReceiptHit(path=child, target=rule.target,
                                               rule=rule.name))
        # Reversed so the walk stays pre-order like the recursive one it
        # replaced.
        stack.extend(reversed(children))
    return DeepScan(hits=tuple(hits), unreadable=tuple(unreadable),
                    overlong=tuple(overlong), depth_capped=tuple(depth_capped),
                    items=ItemCount(files=files, folders=folders))
