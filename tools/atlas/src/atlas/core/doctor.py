"""Build the read-only conformance report: `atlas doctor`.

Pure over scan facts wherever possible; the only extra I/O is existence and
file-count probes on relocation sources (small by construction). P1 is strictly
read-only - the fix flags (--fix-index, --fix-project-md) land in later phases.
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path

from .filerules import first_match
from .mapfile import DriveMap
from .projectmd import agents_block_current, is_claude_pointer
from .scan import DriveInventory, ProjectInventory, long_path, tally_files

# Files tolerated at a project root without being flagged: OS noise plus the
# PRD-209 time-ledger family, which is blessed control plane per the map note.
TOLERATED_ROOT_FILES = ("desktop.ini", "jdp-time-ledger.ndjson", "jdp-time-ledger.ndjson.*")

STATUS_CONFORM = "conform"
STATUS_DRIFT = "drift"
STATUS_UNFILED = "unfiled"
STATUS_STUB = "stub"


@dataclass(frozen=True)
class RelocationHit:
    source: str
    target: str
    # None when part of the source could not be read: unknown, never zero.
    file_count: int | None


@dataclass(frozen=True)
class ProjectReport:
    name: str
    status: str
    sections_present: int
    missing_control_plane: tuple[str, ...] = ()
    drift: tuple[tuple[str, str], ...] = ()          # (found-name, canonical)
    relocations: tuple[RelocationHit, ...] = ()
    sweeps: tuple[tuple[str, str], ...] = ()          # (root file, target dir)
    # Which File Rule produced a sweep, by root file. A sweep from a glob
    # relocation has no entry: the relocation is its own explanation. ADR 0009.
    sweep_rules: tuple[tuple[str, str], ...] = ()     # (root file, rule name)
    unfiled: tuple[str, ...] = ()
    # Folders Atlas could not enumerate. Not actionable - Atlas cannot repair what
    # it cannot read - but never silently treated as empty. See ADR 0004.
    unreadable: tuple[str, ...] = ()
    # False when the project root itself could not be listed. Every other finding
    # is then empty and ``sections_present`` means nothing: an unreadable project
    # never reads as an empty one (#13, ADR 0004).
    root_readable: bool = True

    @property
    def actionable(self) -> bool:
        return bool(self.missing_control_plane or self.drift or self.relocations or self.sweeps)


@dataclass(frozen=True)
class DriveReport:
    root: Path
    drive: str
    map_version: str
    projects: tuple[ProjectReport, ...]

    def summary(self) -> dict[str, int]:
        counts = {STATUS_CONFORM: 0, STATUS_DRIFT: 0, STATUS_UNFILED: 0, STATUS_STUB: 0}
        for p in self.projects:
            counts[p.status] += 1
        return counts


def _control_plane_paths(m: DriveMap) -> dict[str, str]:
    paths = {
        m.project_file: m.project_file,
        m.decisions_dir: m.decisions_dir,
        m.claude_file: m.claude_file,
    }
    if m.agents_file:
        paths[m.agents_file] = m.agents_file
    if m.analysis_dir:
        paths[m.analysis_dir] = m.analysis_dir
    return paths


def _tolerated(name: str) -> bool:
    return any(fnmatch.fnmatch(name.lower(), pat.lower()) for pat in TOLERATED_ROOT_FILES)


class _CannotRead(Exception):
    """A control-plane file that exists and could not be read. Unreadable, not
    missing: reporting it missing would have conform "backfill" over it."""


def _reason(path: Path, exc: OSError) -> str:
    return f"{path.name}  {type(exc).__name__}: {exc.strerror or exc}"


def _read_control_file(path: Path) -> str | None:
    """The file's text, or None when it is not UTF-8. Raises _CannotRead."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise _CannotRead(_reason(path, exc)) from exc
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def _agents_file_current(project: Path, m: DriveMap, root_names: set[str]) -> bool:
    if m.agents_file not in root_names:
        return False
    text = _read_control_file(project / m.agents_file)
    return text is not None and agents_block_current(text, m)


def _claude_file_current(project: Path, m: DriveMap, root_names: set[str]) -> bool:
    if m.claude_file not in root_names:
        return False
    if not m.agents_file:
        return True     # no agents file configured: any CLAUDE.md will do, as before
    text = _read_control_file(project / m.claude_file)
    return text is not None and is_claude_pointer(text, m)


def _dir_exists_exact(base: Path, rel: str) -> bool:
    """Directory existence with exact-case name matching.

    Path.is_dir() is case-insensitive on the Windows/Google Drive mount, so a
    relocation whose source and target differ only by case ("change Orders" ->
    "Change Orders") false-positives forever after the rename. Walk each
    segment and require the exact on-disk name.
    """
    current = base
    for segment in rel.replace("\\", "/").split("/"):
        try:
            with os.scandir(long_path(current)) as it:
                match = next(
                    (e for e in it if e.name == segment and e.is_dir(follow_symlinks=False)),
                    None,
                )
        except OSError:
            return False
        if match is None:
            return False
        current = current / segment
    return True


def report_project(inv: ProjectInventory, m: DriveMap, *,
                   count_files: bool = True) -> ProjectReport:
    """One project's conformance facts.

    ``count_files=False`` skips the one walk here - the file count under each
    relocation source - leaving ``file_count`` None (unknown). For the scoped
    Guard, which needs to know what work is due, not how big it is (#46).
    """
    if not inv.root_entries.readable:
        # Nothing below is knowable. Every check would run against the failed
        # listing's empty names and report a present control plane as missing,
        # zero sections, and a backfill conform would then "repair". REVIEW,
        # never STUB or CONFORM: a person has to look.
        return ProjectReport(
            name=inv.name, status=STATUS_UNFILED, sections_present=0,
            unreadable=(f".  {inv.root_entries.error}",), root_readable=False,
        )

    section_ids = set(m.section_ids)
    drift_lower = {k.lower(): v for k, v in m.drift_map.items()}
    root_names = {e.name for e in inv.root_entries}

    sections_present = sum(1 for e in inv.root_entries if e.is_dir and e.name in section_ids)
    unreadable: list[str] = []

    # Control plane: report what Conform would backfill. PROJECT.md counts as
    # missing when absent OR present without the YAML machine contract - the
    # prose-only file is exactly what Conform-Project.ps1 prepends into. A file
    # that is there and cannot be read is unreadable, never missing.
    missing: list[str] = []
    if m.project_file:
        if m.project_file not in root_names:
            missing.append(m.project_file)
        else:
            path = inv.path / m.project_file
            try:
                head = path.read_text(encoding="utf-8-sig", errors="replace")[:64]
            except OSError as exc:
                unreadable.append(_reason(path, exc))
            else:
                if not head.lstrip().startswith("---"):
                    missing.append(m.project_file)
    if m.decisions_dir and m.decisions_dir not in root_names:
        missing.append(m.decisions_dir)
    # Agent files, AGENTS.md first so conform migrates before it points: AGENTS.md
    # must carry a current Atlas block, CLAUDE.md must be the bare pointer. Names
    # are exact-case, so a hand-saved "Agents.md" reads as missing and conform
    # renames it. ADR 0010.
    for name, current in ((m.agents_file, _agents_file_current),
                          (m.claude_file, _claude_file_current)):
        if not name:
            continue
        try:
            if not current(inv.path, m, root_names):
                missing.append(name)
        except _CannotRead as error:
            unreadable.append(str(error))
    if m.analysis_dir and not (inv.path / m.analysis_dir).exists():
        missing.append(m.analysis_dir)

    # driftMap: top-level dirs whose (case-insensitive) name is a known drift.
    drift: list[tuple[str, str]] = []
    for e in inv.root_entries:
        if e.is_dir and e.name not in section_ids and e.name.lower() in drift_lower:
            drift.append((e.name, drift_lower[e.name.lower()]))

    # relocations: dir sources that exist, glob sources matched at root.
    reloc_hits: list[RelocationHit] = []
    sweeps: list[tuple[str, str]] = []
    for src, dst in m.relocations.items():
        if "*" in src or "?" in src:
            for e in inv.root_entries:
                if not e.is_dir and fnmatch.fnmatch(e.name, src):
                    sweeps.append((e.name, dst))
            continue
        if _dir_exists_exact(inv.path, src):
            if not count_files:
                reloc_hits.append(RelocationHit(source=src, target=dst, file_count=None))
                continue
            tally = tally_files(inv.path / src)
            unreadable.extend(
                f"{src}/{rel}  {why}" if rel != "." else f"{src}  {why}"
                for rel, why in tally.unreadable
            )
            reloc_hits.append(RelocationHit(
                source=src, target=dst,
                file_count=tally.files if tally.known else None))

    # Unfiled: whatever the canon, control plane, pending actions, and
    # tolerated set do not explain.
    explained = set(section_ids)
    explained.update(p.split("/")[0].split("\\")[0] for p in _control_plane_paths(m))
    if m.handoffs_dir:
        explained.add(m.handoffs_dir.replace("\\", "/").split("/")[0])
    explained.update(name for name, _ in drift)
    explained.update(h.source for h in reloc_hits)
    swept = {name for name, _ in sweeps}

    # File Rules: organize-style filing, for root files nothing above has
    # claimed. After the glob relocations so an older rule's meaning never shifts
    # under a newer one, and never over the control plane - a rule for *.md must
    # not file PROJECT.md away. ADR 0009.
    sweep_rules: list[tuple[str, str]] = []
    if m.file_rules:
        for e in inv.root_entries:
            if e.is_dir or e.name in swept or e.name in explained or _tolerated(e.name):
                continue
            rule = first_match(m.file_rules, e.name, inv.path / e.name)
            if rule is not None:
                sweeps.append((e.name, rule.target))
                sweep_rules.append((e.name, rule.name))
                swept.add(e.name)
    unfiled = sorted(
        e.name
        for e in inv.root_entries
        if e.name not in explained and e.name not in swept and not _tolerated(e.name)
    )

    if unreadable:
        # A person has to look. Never STUB - "no sections found" would claim we
        # looked and saw nothing, and never CONFORM, which would claim it is fine.
        status = STATUS_UNFILED
    elif sections_present == 0:
        status = STATUS_STUB
    elif missing or drift or reloc_hits or sweeps:
        status = STATUS_DRIFT
    elif unfiled:
        status = STATUS_UNFILED
    else:
        status = STATUS_CONFORM

    return ProjectReport(
        name=inv.name,
        status=status,
        sections_present=sections_present,
        missing_control_plane=tuple(missing),
        drift=tuple(drift),
        relocations=tuple(reloc_hits),
        sweeps=tuple(sweeps),
        sweep_rules=tuple(sweep_rules),
        unfiled=tuple(unfiled),
        unreadable=tuple(unreadable),
    )


def report_drive(inventory: DriveInventory) -> DriveReport:
    return DriveReport(
        root=inventory.root,
        drive=inventory.map.drive,
        map_version=inventory.map.version,
        projects=tuple(report_project(p, inventory.map) for p in inventory.projects),
    )


def report_to_dict(report: DriveReport) -> dict:
    return {
        "drive": report.drive,
        "root": str(report.root),
        "map_version": report.map_version,
        "summary": report.summary(),
        "projects": [
            {
                "name": p.name,
                "status": p.status,
                "sections_present": p.sections_present if p.root_readable else None,
                "missing_control_plane": list(p.missing_control_plane),
                "drift": [{"from": a, "to": b} for a, b in p.drift],
                "relocations": [
                    {"source": h.source, "target": h.target, "files": h.file_count}
                    for h in p.relocations
                ],
                "sweeps": [
                    {"file": a, "target": b, "rule": dict(p.sweep_rules).get(a)}
                    for a, b in p.sweeps
                ],
                "unfiled": list(p.unfiled),
                "unreadable": list(p.unreadable),
            }
            for p in report.projects
        ],
    }
