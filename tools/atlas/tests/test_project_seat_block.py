"""The six-topic Pyvoid project-seat orientation lives in the AGENTS.md block.

Pyvoid #1541 / PRD-220 REQ-010 and section 8.6, as ruled by Tyler 2026-10-07:
the orientation ships inside the Atlas-generated block of every job folder's
AGENTS.md (never as a drive-root file), and conform backfills existing folders.
"""

from __future__ import annotations

import copy
import re

from atlas.core.conform import DONE, apply_plan, build_plan
from atlas.core.doctor import report_project
from atlas.core.mapfile import find_map, load_map
from atlas.core.ops import new_project
from atlas.core.projectmd import AGENTS_BEGIN, AGENTS_END, agents_block_lines
from atlas.core.scan import scan_drive

from conftest import FIXTURE_MAP, make_intake, make_project, write_map

SEAT_HEADING = "## Pyvoid project seat"

# One marker set per topic, in PRD-220 section 8.6's order. Every phrase of a
# topic must sit on that topic's own numbered line.
TOPICS = (
    ("$PYVOID_HOME",),
    ("pyvoid-fleet ensure", "live-model"),
    ("/jdp", "/maestro", "Norma"),
    ("PROJECT.md", "only source of project facts"),
    ("handoff", ".agent/handoff/"),
    ("never sync on their own initiative", "ADR-022", "honoured", "recorded",
     "user-authority.md", "$PYVOID_HOME/.agent/CONTEXT.md"),
)


def _rules_drive(drive):
    data = copy.deepcopy(FIXTURE_MAP)
    data["controlPlane"]["agentsRules"] = "agents-rules.md"
    write_map(drive, data)
    return load_map(find_map(drive))


def _seat_items(lines: list[str]) -> list[str]:
    """The numbered items of the seat section, continuation lines folded in."""
    start = lines.index(SEAT_HEADING)
    items: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("## ") or line.strip() == AGENTS_END:
            break
        if re.match(r"^\d+\. ", line):
            items.append(line)
        elif items and line.startswith("   ") and line.strip():
            items[-1] += " " + line.strip()
    return items


def test_block_names_the_six_seat_topics_in_order(fixture_drive):
    m = _rules_drive(fixture_drive)
    lines = agents_block_lines(m)
    assert lines.count(SEAT_HEADING) == 1
    items = _seat_items(lines)
    assert len(items) == 6, items
    for number, (item, markers) in enumerate(zip(items, TOPICS), start=1):
        assert item.startswith(f"{number}. "), item
        for marker in markers:
            assert marker in item, (number, marker, item)


def test_seat_section_sits_inside_the_atlas_markers(fixture_drive):
    m = _rules_drive(fixture_drive)
    lines = agents_block_lines(m)
    assert lines[0] == AGENTS_BEGIN and lines[-1] == AGENTS_END
    assert 0 < lines.index(SEAT_HEADING) < len(lines) - 1


def test_ensure_wording_matches_the_jdp_skill_step_zero(fixture_drive):
    """Topic 2 restates jdp SKILL.md Preconditions step 0, not a paraphrase of it."""
    item = _seat_items(agents_block_lines(_rules_drive(fixture_drive)))[1]
    assert "non-zero exit" in item and "verbatim" in item
    assert "`ping_revit`" in item and "`get_document_info`" in item
    assert "`revit:`" in item and "`model`" in item


def test_new_project_agents_md_carries_the_seat_section(fixture_drive):
    m = _rules_drive(fixture_drive)
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Seat House"))
    text = (result.path / "AGENTS.md").read_bytes().decode("utf-8")
    assert len(_seat_items(text.split("\r\n"))) == 6
    # Ruling 2026-10-07: no drive-root orientation file.
    assert not (fixture_drive / "AGENTS.md").exists()
    assert not (fixture_drive / "CLAUDE.md").exists()


def test_conform_backfills_the_seat_section_into_an_existing_folder(fixture_drive):
    m = _rules_drive(fixture_drive)
    older = ("# Architecture project workspace\n\n" + AGENTS_BEGIN
             + "\n## Working style\n\n- older house rules, no seat section\n" + AGENTS_END
             + "\n\n## Project notes\n\nKeep me.\n")
    make_project(fixture_drive, "260401_Older Job", sections=["01 Model"],
                 files={"AGENTS.md": older, "CLAUDE.md": "@AGENTS.md\n"})
    inventory = scan_drive(fixture_drive)
    inv = next(p for p in inventory.projects if p.name == "260401_Older Job")
    report = report_project(inv, m)
    assert "AGENTS.md" in report.missing_control_plane

    applied = apply_plan(fixture_drive, inv.path, m, build_plan(report, m, project=inv.path))
    action = next(a for a in applied.actions if a.dst == "AGENTS.md")
    assert action.status == DONE

    text = (inv.path / "AGENTS.md").read_text(encoding="utf-8")
    assert "older house rules" not in text
    assert "Keep me." in text
    assert len(_seat_items(text.splitlines())) == 6
    assert not (fixture_drive / "AGENTS.md").exists()
