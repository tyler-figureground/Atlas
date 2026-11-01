"""The PERMITS Companion Mode (roadmap F3, ADR 0024): the selected project's
AHJ register applications, whose court the ball is in, and where the round
folders disagree with the register.

Read-only, like the dossier: the register is edited by people and agents, so
the panel's last line points at the file rather than becoming a write path.
Pure string building - the TUI, CLI and tests cross it without Textual.
"""

from __future__ import annotations

from datetime import date

from ..core.permits import PermitScan, describe

NO_RULE = "  The map has no 'permits' rule, so the permit tracker is off."


def permit_mode_lines(scan: PermitScan, today: date) -> list[str]:
    if not scan.register_readable:
        return ["Cannot read the AHJ register - permit status is unknown, not absent.",
                *(f"  {line}" for line in scan.unreadable)]
    lines: list[str] = []
    if not scan.register_present:
        lines.append(f"No register at {scan.register}.")
    elif not scan.applications:
        lines.append("No applications in the register.")
    for a in scan.applications:
        label = " ".join(x for x in (a.agency, a.number) if x and x != "-")
        lines.append(f"[{a.court}] {label}")
        lines.append(f"  {describe(a, today)}")
        if a.next_action and a.next_action != "-":
            lines.append(f"  next: {a.next_action}")
    for finding in scan.findings:
        lines += ["", f"! {finding}"]
    if scan.misnamed:
        lines += ["", "Round folders not named R<n>_YYMMDD (no dates from them):"]
        lines += [f"  {m}" for m in scan.misnamed]
    for line in scan.unreadable:
        lines.append(f"cannot read: {line}")
    if scan.register_present:
        lines += ["", f"Edit the register: {scan.register}"]
    return lines
