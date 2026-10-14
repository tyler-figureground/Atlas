"""Pure presentation model for the Atlas operations console.

Keeps project identity, filtering, sorting, and studio-language diagnosis out of
Textual callbacks. The TUI and its tests cross this small interface; filesystem
facts remain owned by ``atlas.core``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.deep import BUDGET_WARN_FRACTION, DRIVE_ITEM_CAP, DeepScan
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
        # Never a zero for a project Atlas could not read (ticket 13).
        present = self.report.sections_present if self.report.root_readable else "?"
        return f"{present}/{self.section_total}"

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


# ----------------------------------------------------------- the deep pass

# The DEEP Companion Mode's empty state - a walk nobody has asked for yet is
# exactly that, never a silent blank (ADR 0004).
DEEP_EMPTY = (
    "No deep pass has run for this project.\n"
    "  D runs one - it walks every folder below the project root."
)


def deep_findings_count(scan: DeepScan) -> int:
    """What the summary line counts for a finished pass."""
    return (len(scan.hits) + len(scan.unreadable) + len(scan.overlong)
            + len(scan.depth_capped))


def deep_lines(scan: DeepScan, walked: str) -> str:
    """The DEEP Companion Mode's body for one finished pass.

    Same finding words as `doctor --deep` prints on the CLI - the surfaces
    disagree in vocabulary only when one of them is wrong. Receipt sweeps are
    listed, never repaired from here (ticket 26): the pointer to
    `conform --deep --apply` is the whole repair surface.
    """
    lines = [f"Walked {walked} - D re-runs."]

    lines.extend(("", "SWEEP PENDING (deep)"))
    if scan.hits:
        lines.extend(f"  {hit.path} -> {hit.target} (rule: {hit.rule})"
                     for hit in scan.hits)
        lines.append("  No inline repair key - `atlas conform --deep --apply` sweeps these.")
    else:
        lines.append("  No receipt-rule matches below the root")

    if scan.unreadable:
        # Never folded into anything else: a folder the walk could not open is
        # not one it found empty (ADR 0004).
        lines.extend(("", "COULD NOT READ (deep)"))
        lines.extend(f"  {line}" for line in scan.unreadable)

    if scan.overlong:
        lines.extend(("", "OVER-LONG PATHS"))
        lines.extend(f"  over-long path ({entry.length} chars): {entry.path}"
                     for entry in scan.overlong)
        lines.append("  Shortening a path is a person's call - Atlas never repairs these.")

    if scan.depth_capped:
        lines.extend(("", "DEPTH GUARD"))
        lines.extend(f"  not scanned below {line}" for line in scan.depth_capped)

    items = scan.items
    lines.extend(("", "ITEMS"))
    item_line = (f"  {items.files} files, {items.folders} folders "
                 f"({items.total} items)")
    if items.total > DRIVE_ITEM_CAP * BUDGET_WARN_FRACTION:
        percent = round(items.total / DRIVE_ITEM_CAP * 100)
        item_line += f" - {percent}% of the {DRIVE_ITEM_CAP:,} shared-drive item cap"
    lines.append(item_line)
    return "\n".join(lines)
