"""The Dossier Facts Table (ticket 36; ticket 09, the ADR 0005 amendment).

The DOSSIER Companion Mode renders the dossier's facts contract, not its
prose: the validated intake record from
``core/project_data.py::load_project_record`` - identity, the billing/client
Contact Snapshots, and the decisions summary - never raw Markdown (`o` is the
prose surface), never an editor. Read-only is architecture, not caution:
`project edit` (the `e` key) and conform are the two write paths, and both
carry the rename preview and Plan a panel cannot, so the table's last line
advertises them instead of becoming a third path.

Errors are spoken, never blank (ADR 0001: blank means unknown): a missing
PROJECT.md points at the unmet control-plane Expectation one mode away, and a
malformed or legacy dossier renders ``ProjectDataError``'s reason.

Pure string building, like ``tui.layout`` and ``tui.repair``: the TUI, the
CLI and the tests cross this module without Textual.
"""

from __future__ import annotations

from ..core.project_data import ProjectDataError, ProjectRecord

# The read-only line: the two keys that leave the panel for the surfaces that
# can actually do something. What they do is the console's own (`e` edits the
# intake through `project edit`; `o` opens the folder).
KEYS_LINE = "e edit   o open"


def _contact_lines(role: str, snapshot) -> list[str]:
    """One Contact Snapshot as labelled lines; absent parts are simply not
    drawn - never an empty label pretending to be a fact."""
    lines = [f"{role}:"]
    lines.append(f"  {snapshot.full_name}")
    for value in (snapshot.email, snapshot.phone, snapshot.company, snapshot.address):
        if value:
            lines.append(f"  {value}")
    return lines


def dossier_lines(record: ProjectRecord) -> list[str]:
    """The facts table for one validated record, as display lines."""
    intake = record.intake
    lines = [
        "Identity",
        f"  Project     {intake.project_name}",
        f"  Address     {intake.project_address.formatted}",
        f"  Use case    {intake.project_use_case.display}",
    ]
    if intake.description:
        lines.append(f"  Descriptor  {intake.description}")
    lines.append(f"  Created     {intake.created:%Y-%m-%d}")
    if record.crm_id:
        lines.append(f"  CRM id      {record.crm_id}")
    lines.append("")
    lines.extend(_contact_lines("Billing", record.billing_contact))
    lines.append("")
    lines.extend(_contact_lines("Client", record.client_contact))
    lines.append("")
    decisions = record.decisions
    if decisions.count:
        noun = "decision" if decisions.count == 1 else "decisions"
        lines.append(f"Decisions ({decisions.count} {noun} recorded)")
        lines.extend(f"  {title}" for title in decisions.latest)
    else:
        lines.append("Decisions (none recorded)")
    lines.append("")
    lines.append(KEYS_LINE)
    return lines


def dossier_error_lines(error: ProjectDataError, dossier, project_file: str) -> list[str]:
    """A malformed, legacy or unreadable dossier renders its reason.

    The core error names the absolute path; the panel names the file - the
    operator is looking at one project's Companion, and the path is chrome.
    """
    reason = str(error).replace(str(dossier), project_file)
    return [reason, "", "Blank would mean unknown (ADR 0001) - this dossier "
            "could not be read safely, so its facts are not shown."]


def dossier_missing_lines(project_file: str) -> list[str]:
    """No dossier at all: the unmet control-plane Expectation, one mode away.

    The mode offers nothing itself - backfill lives in Unmet Expectations
    (`f` there), not here (ticket 09).
    """
    return [
        f"No {project_file} - the control plane is incomplete.",
        "",
        "It is the unmet Expectation in the Companion's default mode (`d` "
        "cycles back); `f` there backfills it.",
    ]
