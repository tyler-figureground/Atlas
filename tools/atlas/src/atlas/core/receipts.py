"""Receipt Rules: machine-file sweeps below the project root (ticket 31).

The deep pass. Opt-in only (`doctor --deep PROJECT`, `conform --deep`) - the
default doctor/conform report stays root-only and its cost bound depends on
it. One project's walk is bounded by that project; `--all --deep` pays the
full drive walk by flag, never by default.

The walk enumerates and never opens a file: Receipt Rules carry name filters
only, so a match costs nothing beyond the listing Atlas already holds. It
prunes the agent workspace itself (runsDir, backupsDir, and the rest of the
map's agent_dirs) - files already there are where receipts belong - and never
descends into a junction. A folder it cannot open is reported, never read as
empty (ADR 0004). A match is a finding with a Sweep Offer, not a Filing State:
containment (ADR 0007) still decides those at every depth. Root files are File
Rules' ground (ADR 0009) and are never matched here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .filerules import names_match
from .mapfile import DriveMap
from .scan import is_link, long_path


@dataclass(frozen=True)
class ReceiptHit:
    """One Receipt Rule match: the project-relative path, the workspace target
    the rule files it to, and the rule's name, so doctor can attribute it the
    way it attributes File Rule sweeps (ADR 0009)."""

    path: str
    target: str
    rule: str


@dataclass(frozen=True)
class ReceiptScan:
    hits: tuple[ReceiptHit, ...] = ()
    # "relpath  reason" lines, in the shape doctor's own unreadable list uses.
    unreadable: tuple[str, ...] = ()


def scan_receipts(project: Path, m: DriveMap) -> ReceiptScan:
    """Walk one project for Receipt Rule matches below its root.

    Bounded by the project, one enumeration per folder, long_path() at every
    level (ticket 19). Never touches a second project - the caller scopes that.
    """
    if not m.receipt_rules:
        return ReceiptScan()
    workspace = {d.replace("\\", "/").strip("/").casefold() for d in m.agent_dirs}
    hits: list[ReceiptHit] = []
    unreadable: list[str] = []

    def visit(rel: str) -> None:
        try:
            with os.scandir(long_path(project / rel if rel else project)) as it:
                entries = list(it)
        except OSError as exc:
            unreadable.append(f"{rel or '.'}  {type(exc).__name__}: {exc.strerror or exc}")
            return
        for entry in entries:
            child = f"{rel}/{entry.name}" if rel else entry.name
            try:
                if is_link(entry):
                    continue    # links are leaves; never descend, never move
                directory = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue        # the entry itself failed; its folder was read
            if directory:
                if child.casefold() not in workspace:
                    visit(child)
            elif rel:
                # Files at the root are File Rules' ground, not receipts.
                rule = next((r for r in m.receipt_rules if names_match(r, entry.name)), None)
                if rule is not None:
                    hits.append(ReceiptHit(path=child, target=rule.target, rule=rule.name))

    visit("")
    return ReceiptScan(hits=tuple(hits), unreadable=tuple(unreadable))
