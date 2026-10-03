"""PROJECT.md / control-plane file generation.

Generated files preserve the machine-facing encoding contract: UTF-8 without a
BOM, CRLF line endings, and a trailing newline. Atlas 0.2 owns complete intake
metadata; legacy PowerShell writers may emit only blank compatibility stubs.
The canonical-map section remains marker-wrapped so Doctor can regenerate it
idempotently.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .intake import CONTROL_PATTERN, ContactSnapshot, ResolvedProjectIntake
from .mapfile import DriveMap
from .templates import read_template

MAP_BEGIN = "<!-- atlas:map-begin -->"
MAP_END = "<!-- atlas:map-end -->"

# The machine contract - identical in New-Project.ps1 and Conform-Project.ps1.
# Bare keys, no inline comments (a tiny YAML fallback parser reads comments as
# values), and never a BOM ahead of the opening '---'.
FRONT_MATTER_HEAD = (
    "---",
    "# Machine contract - tool-authoritative project facts. Norma and other",
    "# architect skills read THIS YAML block, not the prose below. A blank field",
    "# is ignored, not assumed; Norma adopts this project only once jurisdiction /",
    "# occupancy_group / edition are real. Run /project-dossier to fill it in, and",
    "# keep it in sync with the Identity + Code tables (the human mirror).",
)
FRONT_MATTER_KEYS = (
    "jurisdiction:",
    "edition:",
    "occupancy_group:",
    "construction_type:",
    "sprinklered:",
    "stories:",
    "building_area_sf:",
    "frontage_ft:",
    "existing_co_occupant_load:",
    "existing_exits:",
    "place_of_assembly_strategy:",
    "tenancy:",
    "---",
)


def _crlf_bytes(lines: list[str]) -> bytes:
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def write_crlf_no_bom(path: Path, lines: list[str]) -> None:
    """The PS1 writer's exact byte behavior: WriteAllLines = line + CRLF each."""
    path.write_bytes(_crlf_bytes(lines))


def create_crlf_no_bom(path: Path, lines: list[str]) -> bool:
    """Create a control file exclusively; never replace a concurrent arrival."""

    try:
        with path.open("xb") as stream:
            stream.write(_crlf_bytes(lines))
    except FileExistsError:
        return False
    return True


# json.dumps escapes C0 but writes these raw. Raw, U+2028/U+2029/U+0085 split a
# line for any reader that uses str.splitlines(), and DEL/C1/BOM are
# non-printable to PyYAML - either way the dossier stops loading.
_UNSAFE_IN_YAML = re.compile("[\x7f-\x9f\u2028\u2029\ufeff\ufffe\uffff]")


def yaml_quote(value: str) -> str:
    """One YAML double-quoted scalar, safe on a single physical line."""

    return _UNSAFE_IN_YAML.sub(
        lambda match: f"\\u{ord(match.group()):04x}",
        json.dumps(value, ensure_ascii=False),
    )


_yaml = yaml_quote


def table_cell(value: str) -> str:
    """One Markdown table cell on one line, pipes and backslashes escaped."""

    escaped = value.replace("\\", "\\\\").replace("|", r"\|")
    return CONTROL_PATTERN.sub(" ", " ".join(escaped.splitlines())).strip()


_table = table_cell


def blank_intake_front_matter(project: str) -> list[str]:
    """Blank expanded intake contract for legacy-project conform stubs."""

    lines = [
        f"project: {_yaml(project)}",
        "address:",
        "address_street:",
        "address_unit:",
        "address_city:",
        "address_state:",
        "address_postal_code:",
        "description:",
        "project_use_case:",
        "project_use_case_category:",
    ]
    for role in ("billing", "client"):
        lines += [
            f"{role}_contact_id:",
            f"{role}_contact_name:",
            f"{role}_contact_email:",
            f"{role}_contact_phone:",
            f"{role}_contact_company:",
            f"{role}_contact_address:",
        ]
    return lines + list(FRONT_MATTER_KEYS)


def blank_intake_identity_rows(project: str) -> list[str]:
    return [
        f"| Project | {_table(project)} |",
        "| Address / BBL | |",
        "| Project Use Case | |",
        "| Client | |",
        "| Billing Contact | |",
        "| Billing Email | |",
        "| Billing Phone | |",
        "| Billing Company | |",
        "| Billing Address | |",
        "| Client Contact | |",
        "| Client Email | |",
        "| Client Phone | |",
        "| Client Company | |",
        "| Client Address | |",
        "| Jurisdiction | |",
        "| Virtual tour | |",
        "| Descriptor | |",
        "| Created | |",
    ]


def _contact_front_matter(role: str, contact: ContactSnapshot) -> list[str]:
    return [
        f"{role}_contact_id: {_yaml(contact.id)}",
        f"{role}_contact_name: {_yaml(contact.full_name)}",
        f"{role}_contact_email: {_yaml(contact.email)}",
        f"{role}_contact_phone: {_yaml(contact.phone)}",
        f"{role}_contact_company: {_yaml(contact.company)}",
        f"{role}_contact_address: {_yaml(contact.address)}",
    ]


def project_md_lines(m: DriveMap, folder_name: str, intake: ResolvedProjectIntake) -> list[str]:
    name = intake.project_name
    desc = intake.description
    created = intake.request.created
    full_address = intake.project_address.formatted
    lines: list[str] = []
    lines += FRONT_MATTER_HEAD
    lines += [
        f"project: {_yaml(name)}",
        f"address: {_yaml(full_address)}",
        f"address_street: {_yaml(intake.project_address.street)}",
        f"address_unit: {_yaml(intake.project_address.unit)}",
        f"address_city: {_yaml(intake.project_address.city)}",
        f"address_state: {_yaml(intake.project_address.state)}",
        f"address_postal_code: {_yaml(intake.project_address.postal_code)}",
        f"description: {_yaml(desc)}",
        f"project_use_case: {_yaml(intake.project_use_case.display)}",
        f"project_use_case_category: {_yaml(intake.project_use_case.category)}",
    ]
    lines += _contact_front_matter("billing", intake.billing_contact)
    lines += _contact_front_matter("client", intake.client_contact)
    lines += FRONT_MATTER_KEYS
    lines += [
        "",
        f"# {folder_name}",
        "",
        "> Maintained by Architecture Studio skills and the project team. Facts only -",
        "> rationale lives in `decisions/`. The YAML front-matter above is the machine",
        "> mirror of the Identity + Code tables; keep them in agreement.",
        "> **Next:** run `/project-dossier` to fill in the project facts.",
        "",
        "## Identity",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Project | {_table(name)} |",
        f"| Address / BBL | {_table(full_address)} |",
        f"| Project Use Case | {_table(intake.project_use_case.display)} |",
        f"| Client | {_table(intake.client_contact.full_name)} |",
        f"| Billing Contact | {_table(intake.billing_contact.full_name)} |",
        f"| Billing Email | {_table(intake.billing_contact.email)} |",
        f"| Billing Phone | {_table(intake.billing_contact.phone)} |",
        f"| Billing Company | {_table(intake.billing_contact.company)} |",
        f"| Billing Address | {_table(intake.billing_contact.address)} |",
        f"| Client Contact | {_table(intake.client_contact.full_name)} |",
        f"| Client Email | {_table(intake.client_contact.email)} |",
        f"| Client Phone | {_table(intake.client_contact.phone)} |",
        f"| Client Company | {_table(intake.client_contact.company)} |",
        f"| Client Address | {_table(intake.client_contact.address)} |",
        "| Jurisdiction | |",
        "| Virtual tour | |",
        f"| Descriptor | {_table(desc)} |",
        f"| Created | {created.strftime('%Y-%m-%d')} |",
        f"| Drive | {m.drive} |",
        "| Status | Active |",
        "",
        "## Site",
        "",
        "<!-- site-planner skills append here: climate, flood, transit, demographics, context -->",
        "",
        "## Zoning",
        "",
        "<!-- zoning skills append here: district, FAR, envelope, overlays, landmark status -->",
        "",
        "## Program",
        "",
        "<!-- programming skills append here: headcount, space program, occupant loads -->",
        "",
        "## Code",
        "",
        "<!-- Mirrors the machine contract in the front-matter. Change a value here -> change it there too. -->",
        "",
        "| Item | Value | Source | Date |",
        "|------|-------|--------|------|",
        "| Building code edition | | | |",
        "| Occupancy group | | | |",
        "| Construction type | | | |",
        "| Sprinklered | | | |",
        "| Stories | | | |",
        "| Building area (SF) | | | |",
        "| Frontage (ft) | | | |",
        "| Existing C-of-O occupant load | | | |",
        "| Existing exits | | | |",
        "| Place-of-assembly strategy | | | |",
        "| Tenancy | | | |",
        "",
        "## Decisions",
        "",
        "<!-- maintained by /decision - do not edit by hand -->",
        "",
        "| # | Decision | Status | Date |",
        "|---|----------|--------|------|",
        "",
    ]
    lines += canonical_map_lines(m)
    return lines


def canonical_map_lines(m: DriveMap) -> list[str]:
    """The regenerable 'Where things go' block, marker-wrapped for --fix-project-md."""
    lines = [
        MAP_BEGIN,
        "## Where things go (canonical map)",
        "",
        "Sections tagged **[seed]** exist now. Everything else is created on demand:",
        "open `_tools\\Atlas.bat`, select this project, press `a`, pick the folder.",
        "**Do not hand-create canonical folders** - use Atlas so names never drift.",
        "",
    ]
    for section in m.sections:
        tag = " _[seed]_" if section.seed else " _[on demand]_"
        lines.append(f"- **{section.id}**{tag}")
        seeded = set(section.seed_children) if section.seed else set()
        for child in section.children:
            lines.append(f"  - {child}" + (" _[seed]_" if child in seeded else ""))
    lines += [
        "",
        f"_Naming: {m.project_naming}. Generated by Atlas._",
        MAP_END,
    ]
    return lines


def decisions_readme_lines() -> list[str]:
    return [
        "# Decisions",
        "",
        "ADR-style decision records for this project - one per file (`NNNN-slug.md`),",
        "maintained by the `/decision` skill. Rationale lives here; current facts live",
        "in `../PROJECT.md`.",
    ]


# ---- agent files: AGENTS.md holds the instructions, CLAUDE.md points at it --
# ADR 0010. AGENTS.md is what every coding agent reads; Claude Code reads
# CLAUDE.md, so CLAUDE.md is a one-line import of AGENTS.md and nothing else.

AGENTS_BEGIN = "<!-- atlas:agents-begin -->"
AGENTS_END = "<!-- atlas:agents-end -->"
AGENTS_TITLE = "# Architecture project workspace"


class AgentsBlockError(ValueError):
    """AGENTS.md carries Atlas markers that do not delimit exactly one block."""


def legacy_claude_md_lines(m: DriveMap) -> list[str]:
    """The CLAUDE.md every writer emitted before AGENTS.md (Atlas 0.3 and earlier,
    New-Project.ps1, Conform-Project.ps1). Kept to recognise it: stock output is
    safe to replace with the pointer, and a person's edits are not."""
    return [
        AGENTS_TITLE,
        "",
        "Project facts live in `PROJECT.md` (the YAML machine contract every architect",
        "skill reads - most importantly Norma, which scopes code answers from it).",
        "Decisions live in `decisions/`. Norma writes cited code analyses to",
        f"`{m.analysis_dir}`.",
        "",
        "Start with `/project-dossier` to fill in `PROJECT.md`, then run `/code-analysis`,",
        "`/egress`, `/ibc`, etc. from this folder.",
    ]


def claude_md_lines(m: DriveMap) -> list[str]:
    """The pointer. Claude Code expands the import; every other agent reads
    AGENTS.md directly. Relative on purpose: the absolute pointer a person wrote
    by hand went stale the day its project folder was renamed."""
    if not m.agents_file:
        return legacy_claude_md_lines(m)
    return [f"@{m.agents_file}"]


def agents_block_lines(m: DriveMap) -> list[str]:
    """The Atlas-owned part of AGENTS.md: house working style, then the index.

    Marker-wrapped so conform can refresh it in place when the map or the house
    rules change, as the canonical-map block in PROJECT.md is. Everything outside
    the markers belongs to the project and is never rewritten.
    """
    rows = []
    if m.project_file:
        rows.append(f"| Project facts - YAML machine contract; Norma scopes code answers from it | `{m.project_file}` |")
    if m.decisions_dir:
        rows.append(f"| Decision records, one per file (`/decision`) | `{m.decisions_dir}/` |")
    for template in m.templates:
        if template.index:
            rows.append(f"| {template.index} | `{template.path}` |")
    if m.handoffs_dir:
        rows.append(f"| Agent session handoffs (`HANDOFF-*.md`) | `{m.handoffs_dir}/` |")
    if m.runs_dir:
        rows.append(f"| Agent run scratch - one folder per run, `RUN.md` inside | `{m.runs_dir}/` |")
    if m.backups_dir:
        rows.append(f"| Copies of control files taken before an agent edits them | `{m.backups_dir}/` |")
    if m.archive_dir:
        rows.append(f"| Closed agent runs, zipped by Atlas after {m.run_retention_days} idle days | `{m.archive_dir}/` |")
    if m.analysis_dir:
        rows.append(f"| Norma code analyses | `{m.analysis_dir}/` |")
    rows.append(f"| Canonical folder names - add folders with Atlas, never by hand | `..\\_tools\\{m.path.name}` |")
    style = [
        "- Sacrifice grammar for concision. Brevity always: fragments over sentences, no preamble, no filler.",
        "- Give every file or handoff path as a full absolute path, drive letter first, so it copy-pastes. Never a bare relative path.",
    ]
    if m.claude_file:
        style.append(f"- `{m.claude_file}` only points here (`@{m.agents_file}`). Agent instructions go in this file, never that one.")
    return [
        AGENTS_BEGIN,
        "<!-- Generated by Atlas from the drive map. Conform rewrites this block; keep project notes outside it. -->",
        "",
        "## Working style",
        "",
        *style,
        "",
        *_agents_rules_lines(m),
        "## Index",
        "",
        "| What | Where (relative to this folder) |",
        "|------|-------|",
        *rows,
        AGENTS_END,
    ]


def _agents_rules_lines(m: DriveMap) -> list[str]:
    """The filing-rules template, with a trailing blank line, or nothing.

    Read from the bundled template (core/templates.py), so editing that file
    makes every project's block stale and conform rewrites it in place. Lines
    are right-stripped because the block is compared that way.
    """
    if not m.agents_rules:
        return []
    lines = [line.rstrip() for line in read_template(m.agents_rules).splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return [*lines, ""] if lines else []


def agents_md_lines(m: DriveMap) -> list[str]:
    return [
        AGENTS_TITLE,
        "",
        *agents_block_lines(m),
        "",
        "## Start here",
        "",
        f"Run `/project-dossier` to fill in `{m.project_file}`, then `/code-analysis`, `/egress`,",
        "`/ibc`, etc. from this folder.",
    ]


def meaningful_lines(text: str) -> list[str]:
    """Non-blank lines, trailing space dropped: what two copies of a file share
    when they carry the same words, whatever their line endings or spacing."""
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def is_claude_pointer(text: str, m: DriveMap) -> bool:
    return meaningful_lines(text) == [f"@{m.agents_file}"]


def is_legacy_claude(text: str, m: DriveMap) -> bool:
    return meaningful_lines(text) == meaningful_lines("\n".join(legacy_claude_md_lines(m)))


def carried_by(text: str, host: str) -> bool:
    """Whether every line of ``text`` appears in ``host``, in order.

    What CLAUDE.md must pass before conform replaces it with the pointer: its
    words are already in AGENTS.md. In order rather than as one substring,
    because the Atlas block is inserted after the first heading.
    """
    have = iter(meaningful_lines(host))
    return all(any(line == got for got in have) for line in meaningful_lines(text))


def _agents_block_span(lines: list[str]) -> tuple[int, int] | None:
    marks = [line.strip() for line in lines]
    begins = [i for i, mark in enumerate(marks) if mark == AGENTS_BEGIN]
    ends = [i for i, mark in enumerate(marks) if mark == AGENTS_END]
    if not begins and not ends:
        return None
    if len(begins) != 1 or len(ends) != 1 or ends[0] < begins[0]:
        raise AgentsBlockError("Atlas markers in AGENTS.md are broken; fix them by hand")
    return begins[0], ends[0]


def agents_block_current(text: str, m: DriveMap) -> bool:
    lines = text.splitlines()
    try:
        span = _agents_block_span(lines)
    except AgentsBlockError:
        return False
    if span is None:
        return False
    start, end = span
    return [line.rstrip() for line in lines[start:end + 1]] == agents_block_lines(m)


def with_agents_block(lines: list[str], m: DriveMap) -> list[str]:
    """``lines`` with the Atlas block refreshed in place, or inserted after the
    first heading (else at the top). Raises AgentsBlockError on broken markers."""
    block = agents_block_lines(m)
    span = _agents_block_span(lines)
    if span is not None:
        start, end = span
        return lines[:start] + block + lines[end + 1:]
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first is not None and lines[first].startswith("# "):
        head, rest = lines[:first + 1], lines[first + 1:]
    else:
        head, rest = [], list(lines)
    while rest and not rest[0].strip():
        rest = rest[1:]
    out = head + ([""] if head else []) + block
    return out + ([""] + rest if rest else [])
