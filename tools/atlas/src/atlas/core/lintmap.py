"""Validate the map itself: `atlas lint`.

Catches the bug classes the v1.1 ARCHITECTURE map actually shipped with:
an analysisDir pointing at an unblessed folder, the same child blessed in two
sections (Invoices), spelling drift inside the anti-drift file (PunchList vs
Punch List), and mixed numeric prefix widths that break sort order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .mapfile import DriveMap
from .templates import template_path

# Levels: "error" = the map contradicts itself and tools may misbehave;
# "warn" = legal but suspicious, a human should look once.
ERROR = "error"
WARN = "warn"


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str


def _first_segment(path: str) -> str:
    return path.replace("\\", "/").split("/", 1)[0]


# Where a destination path lands, for anything in the map that moves a thing.
_BLESSED = "blessed"
_UNBLESSED_CHILD = "unblessed-child"
_NOWHERE = "nowhere"


def _landing(m: DriveMap, dst: str) -> str:
    """Whether ``dst`` is a canonical section, a blessed child, or control plane."""
    ids = m.section_ids
    cp_roots = {
        _first_segment(v) for v in m.control_plane.values() if isinstance(v, str) and v
    }
    head = _first_segment(dst)
    if head in ids:
        section = m.section(head)
        rest = dst.replace("\\", "/").removeprefix(head).strip("/")
        if rest and section is not None and rest not in section.children:
            # Check parent paths too: "10 Legal/Invoices" is blessed even if
            # a deeper target like "10 Legal/Invoices/2026" is not listed.
            if not any(rest.startswith(c + "/") or rest == c for c in section.children):
                return _UNBLESSED_CHILD
        return _BLESSED
    if head in cp_roots:
        return _BLESSED  # control-plane destination (.agent/handoff etc.)
    return _NOWHERE


def lint_map(m: DriveMap) -> list[Finding]:
    findings: list[Finding] = []
    ids = m.section_ids

    # -- sections ------------------------------------------------------------
    seen: set[str] = set()
    for s in m.sections:
        if s.id in seen:
            findings.append(Finding(ERROR, "DUP-SECTION", f"section '{s.id}' listed twice"))
        seen.add(s.id)
        if not re.match(r"^\d{2} ", s.id):
            findings.append(
                Finding(WARN, "SECTION-PREFIX", f"section '{s.id}' lacks a two-digit 'NN ' prefix")
            )

    # -- driftMap targets must be canonical sections --------------------------
    for src, dst in m.drift_map.items():
        if dst not in ids:
            findings.append(
                Finding(ERROR, "DRIFT-TARGET", f"driftMap '{src}' -> '{dst}': target is not a canonical section")
            )
        if "/" in dst or "\\" in dst:
            findings.append(
                Finding(ERROR, "DRIFT-IS-MOVE", f"driftMap '{src}' -> '{dst}': targets a path; moves belong in relocations (PS1 Rename-Item cannot move)")
            )

    # -- relocations targets must land somewhere blessed ----------------------
    for src, dst in m.relocations.items():
        verdict = _landing(m, dst)
        head = _first_segment(dst)
        if verdict == _UNBLESSED_CHILD:
            rest = dst.replace("\\", "/").removeprefix(head).lstrip("/")
            findings.append(
                Finding(WARN, "RELOC-UNBLESSED-CHILD", f"relocation '{src}' -> '{dst}': '{rest}' is not a blessed child of '{head}'")
            )
        elif verdict == _NOWHERE:
            findings.append(
                Finding(ERROR, "RELOC-TARGET", f"relocation '{src}' -> '{dst}': target root '{head}' is neither a canonical section nor a control-plane dir")
            )

    # -- file rules land somewhere blessed, and are told apart by name ---------
    # Structure is load_map's job and refuses the map outright (ADR 0009); what
    # is left here is whether a well-formed rule points somewhere sensible.
    rule_names: dict[str, int] = {}
    for rule in m.file_rules:
        rule_names[rule.name] = rule_names.get(rule.name, 0) + 1
        verdict = _landing(m, rule.target)
        head = _first_segment(rule.target)
        if verdict == _UNBLESSED_CHILD:
            rest = rule.target.replace("\\", "/").removeprefix(head).lstrip("/")
            findings.append(
                Finding(WARN, "FILE-RULE-UNBLESSED-CHILD", f"file rule '{rule.name}' -> '{rule.target}': '{rest}' is not a blessed child of '{head}'")
            )
        elif verdict == _NOWHERE:
            findings.append(
                Finding(ERROR, "FILE-RULE-TARGET", f"file rule '{rule.name}' -> '{rule.target}': target root '{head}' is neither a canonical section nor a control-plane dir")
            )
    for name, count in rule_names.items():
        if count > 1:
            findings.append(
                Finding(WARN, "FILE-RULE-DUP-NAME", f"file rule name '{name}' is used {count} times; doctor names the rule that filed each file, and cannot tell these apart")
            )

    # -- controlPlane.analysisDir must be a blessed path ----------------------
    if m.analysis_dir:
        head = _first_segment(m.analysis_dir)
        rest = m.analysis_dir.replace("\\", "/").removeprefix(head).lstrip("/")
        section = m.section(head)
        if section is None:
            findings.append(
                Finding(ERROR, "ANALYSIS-DIR", f"controlPlane.analysisDir '{m.analysis_dir}': '{head}' is not a canonical section")
            )
        elif rest and rest not in section.children:
            findings.append(
                Finding(ERROR, "ANALYSIS-DIR", f"controlPlane.analysisDir '{m.analysis_dir}': '{rest}' is not a blessed child of '{head}' (Add-Section cannot create it)")
            )

    # -- same child name blessed in two sections ------------------------------
    homes: dict[str, list[str]] = {}
    for s in m.sections:
        for child in s.children:
            leaf = child.replace("\\", "/").split("/")[-1]
            homes.setdefault(leaf, []).append(s.id)
    for leaf, in_sections in sorted(homes.items()):
        if len(in_sections) > 1:
            findings.append(
                Finding(WARN, "DUP-CHILD", f"'{leaf}' is blessed in {len(in_sections)} sections: {', '.join(in_sections)} - one artifact class, one home?")
            )

    # -- mixed numeric prefix widths inside one section ------------------------
    for s in m.sections:
        widths = set()
        for child in s.children:
            top = _first_segment(child)
            match = re.match(r"^(\d+) ", top)
            if match:
                widths.add(len(match.group(1)))
        if len(widths) > 1:
            findings.append(
                Finding(WARN, "MIXED-PREFIX", f"section '{s.id}' mixes numeric prefix widths {sorted(widths)}; sort order will lie")
            )

    # -- seeded children only take effect under a seeded section ---------------
    for s in m.sections:
        if s.seed_children and not s.seed:
            findings.append(
                Finding(WARN, "SEED-CHILD-UNSEEDED", f"section '{s.id}' seeds {', '.join(s.seed_children)} but is not itself seeded; a new project gets neither")
            )

    # -- templates: a real template, landing in a blessed place ----------------
    for t in m.templates:
        parent = t.path.rpartition("/")[0]
        if parent and _landing(m, parent) == _NOWHERE:
            findings.append(
                Finding(ERROR, "TEMPLATE-TARGET", f"template '{t.template}' -> '{t.path}': '{_first_segment(parent)}' is neither a canonical section nor a control-plane dir")
            )
        elif parent and _landing(m, parent) == _UNBLESSED_CHILD:
            findings.append(
                Finding(WARN, "TEMPLATE-UNBLESSED-CHILD", f"template '{t.template}' -> '{t.path}': '{parent}' is not a blessed folder")
            )
        if not template_path(t.template).is_file():
            findings.append(
                Finding(ERROR, "TEMPLATE-MISSING", f"template '{t.template}' is not in {template_path(t.template).parent}")
            )
    if m.agents_rules and not template_path(m.agents_rules).is_file():
        findings.append(
            Finding(ERROR, "TEMPLATE-MISSING", f"controlPlane.agentsRules '{m.agents_rules}' is not in {template_path(m.agents_rules).parent}")
        )

    return findings
