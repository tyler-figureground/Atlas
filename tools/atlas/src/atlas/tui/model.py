"""Pure presentation model for the Atlas operations console.

Keeps project identity, filtering, sorting, and studio-language diagnosis out of
Textual callbacks. The TUI and its tests cross this small interface; filesystem
facts remain owned by ``atlas.core``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.doctor import ProjectReport
from ..core.mapfile import DriveMap

STATUS_LABELS = {
    "conform": "READY",
    "drift": "ACTION",
    "unfiled": "REVIEW",
    "stub": "SETUP",
}

STATUS_PRIORITY = {"drift": 0, "unfiled": 1, "stub": 2, "conform": 3}
SORT_COLUMNS = ("health", "project", "sections", "fixes", "review")


@dataclass(frozen=True)
class ProjectRow:
    """One stable table row derived from a conformance report."""

    report: ProjectReport
    section_total: int

    @property
    def key(self) -> str:
        return self.report.name

    @property
    def health(self) -> str:
        return STATUS_LABELS.get(self.report.status, self.report.status.upper())

    @property
    def fixes(self) -> int:
        report = self.report
        return (
            len(report.missing_control_plane)
            + len(report.drift)
            + len(report.relocations)
            + len(report.sweeps)
        )

    @property
    def review(self) -> int:
        return len(self.report.unfiled)

    @property
    def sections(self) -> str:
        return f"{self.report.sections_present}/{self.section_total}"

    @property
    def search_text(self) -> str:
        return " ".join(
            (
                self.report.name,
                self.report.status,
                self.health,
                "needs attention" if self.report.status != "conform" else "ready",
            )
        ).casefold()


def project_rows(reports: tuple[ProjectReport, ...], drive_map: DriveMap) -> tuple[ProjectRow, ...]:
    """Build immutable rows from current scan facts."""

    section_total = len(drive_map.sections)
    return tuple(ProjectRow(report, section_total) for report in reports)


def visible_rows(
    rows: tuple[ProjectRow, ...],
    *,
    query: str = "",
    sort_column: str = "health",
    reverse: bool = False,
) -> tuple[ProjectRow, ...]:
    """Filter and sort rows while retaining project-name identity."""

    needle = query.strip().casefold()
    filtered = (row for row in rows if not needle or needle in row.search_text)

    def sort_key(row: ProjectRow) -> tuple[object, ...]:
        report = row.report
        if sort_column == "project":
            primary: object = report.name.casefold()
        elif sort_column == "sections":
            primary = report.sections_present
        elif sort_column == "fixes":
            primary = row.fixes
        elif sort_column == "review":
            primary = row.review
        else:
            primary = STATUS_PRIORITY.get(report.status, 99)
        return primary, report.name.casefold()

    return tuple(sorted(filtered, key=sort_key, reverse=reverse))


def project_detail(row: ProjectRow) -> str:
    """Render selected-project diagnosis in studio language."""

    report = row.report
    if report.unreadable:
        headline = "Cannot read - Atlas could not open part of this project."
    elif report.status == "conform":
        headline = "Ready - project follows the current drive map."
    elif report.status == "unfiled":
        headline = "Review - Atlas found items that need a filing decision."
    elif report.status == "stub":
        headline = "Setup needed - no canonical project sections found."
    else:
        headline = "Action available - Atlas can repair mapped differences."

    lines = [
        headline,
        f"Sections  {row.sections}",
        "",
        "ATLAS CAN FIX",
    ]

    fix_lines: list[str] = []
    fix_lines.extend(f"Backfill {name}" for name in report.missing_control_plane)
    fix_lines.extend(f"Rename {source} -> {target}" for source, target in report.drift)
    fix_lines.extend(
        f"Move {hit.source} -> {hit.target} "
        + ("(files unknown)" if hit.file_count is None else f"({hit.file_count} files)")
        for hit in report.relocations
    )
    rules = dict(report.sweep_rules)
    fix_lines.extend(
        f"File {name} -> {target}" + (f" (rule: {rules[name]})" if name in rules else "")
        for name, target in report.sweeps
    )
    lines.extend(f"  {line}" for line in fix_lines)
    if not fix_lines:
        lines.append("  No mapped repairs pending")

    if report.unreadable:
        # Never folded into "no unfiled items": a folder Atlas could not open is
        # not a folder it looked inside and found empty. ADR 0004.
        lines.extend(("", "COULD NOT READ"))
        lines.extend(f"  {detail}" for detail in report.unreadable)
        lines.append("  Nothing above is trustworthy for this project.")

    lines.extend(("", "REVIEW REQUIRED"))
    if report.unfiled:
        lines.extend(f"  Unfiled: {name}" for name in report.unfiled)
    else:
        lines.append("  No unfiled items")

    lines.extend(
        (
            "",
            "ACTIONS",
            "  f conform   a add folders",
            "  c clean     o open folder",
            "  space mark  x conform marked",
        )
    )
    return "\n".join(lines)
