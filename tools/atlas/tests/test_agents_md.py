"""AGENTS.md holds the instructions; CLAUDE.md points at it (ADR 0010)."""

from __future__ import annotations

from atlas.core.conform import CONFLICT, apply_plan, build_plan, build_repair_plan
from atlas.core.doctor import report_project
from atlas.core.mapfile import find_map, load_map
from atlas.core.ops import new_project
from atlas.core.projectmd import (
    AGENTS_BEGIN,
    AGENTS_END,
    agents_block_current,
    agents_block_lines,
    agents_md_lines,
    carried_by,
    legacy_claude_md_lines,
    with_agents_block,
)
from atlas.core.scan import scan_drive

from conftest import make_intake, make_project

POINTER = "@AGENTS.md"


def drive_map(drive):
    return load_map(find_map(drive))


def project_report_for(drive, name):
    inventory = scan_drive(drive)
    inv = next(p for p in inventory.projects if p.name == name)
    return report_project(inv, inventory.map), inv, inventory.map


def conform(drive, name, node=""):
    report, inv, m = project_report_for(drive, name)
    plan = (build_repair_plan(report, m, node, project=inv.path) if node
            else build_plan(report, m, project=inv.path))
    return apply_plan(drive, inv.path, m, plan), inv, m


def text_of(path):
    return path.read_text(encoding="utf-8")


def stock_claude(m):
    return "\n".join(legacy_claude_md_lines(m)) + "\n"


# ---- what Atlas writes ------------------------------------------------------

def test_new_project_writes_agents_and_a_pointer(fixture_drive):
    m = drive_map(fixture_drive)
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Pointer House"))

    agents = (result.path / "AGENTS.md").read_bytes()
    assert not agents.startswith(b"\xef\xbb\xbf")
    assert AGENTS_BEGIN.encode() in agents and AGENTS_END.encode() in agents
    assert b"absolute path" in agents

    assert (result.path / "CLAUDE.md").read_bytes() == b"@AGENTS.md\r\n"


def test_the_index_names_the_control_plane_from_the_map(fixture_drive):
    m = drive_map(fixture_drive)
    block = "\n".join(agents_block_lines(m))
    for expected in (m.project_file, m.decisions_dir, m.handoffs_dir, m.analysis_dir, m.path.name):
        assert expected in block


# ---- what doctor reports ----------------------------------------------------

def test_missing_agents_file_is_reported(fixture_drive):
    make_project(fixture_drive, "260301_NoAgents", sections=["01 Model"],
                 files={"CLAUDE.md": POINTER + "\n"})
    report, _inv, _m = project_report_for(fixture_drive, "260301_NoAgents")
    assert "AGENTS.md" in report.missing_control_plane


def test_a_claude_that_is_not_a_pointer_is_reported(fixture_drive):
    m = drive_map(fixture_drive)
    make_project(fixture_drive, "260302_Prose", sections=["01 Model"],
                 files={"AGENTS.md": "\n".join(agents_md_lines(m)) + "\n",
                        "CLAUDE.md": "# workspace\n\nread me\n"})
    report, _inv, _m = project_report_for(fixture_drive, "260302_Prose")
    assert "CLAUDE.md" in report.missing_control_plane
    assert "AGENTS.md" not in report.missing_control_plane


def test_a_stale_atlas_block_is_reported(fixture_drive):
    make_project(fixture_drive, "260303_Stale", sections=["01 Model"],
                 files={"AGENTS.md": "# workspace\n\n" + AGENTS_BEGIN + "\nold rules\n" + AGENTS_END + "\n",
                        "CLAUDE.md": POINTER + "\n"})
    report, _inv, _m = project_report_for(fixture_drive, "260303_Stale")
    assert "AGENTS.md" in report.missing_control_plane


def test_the_agent_files_are_not_unfiled(fixture_drive):
    m = drive_map(fixture_drive)
    make_project(fixture_drive, "260304_Filed", sections=["01 Model"],
                 files={"AGENTS.md": "\n".join(agents_md_lines(m)) + "\n",
                        "CLAUDE.md": POINTER + "\n"})
    report, _inv, _m = project_report_for(fixture_drive, "260304_Filed")
    assert report.unfiled == ()


# ---- what conform does ------------------------------------------------------

def test_backfill_writes_both_files_from_nothing(fixture_drive):
    make_project(fixture_drive, "260305_Bare", sections=["01 Model"])
    conform(fixture_drive, "260305_Bare")
    report, inv, _m = project_report_for(fixture_drive, "260305_Bare")
    assert text_of(inv.path / "CLAUDE.md") == POINTER + "\n"
    assert AGENTS_BEGIN in text_of(inv.path / "AGENTS.md")
    assert report.missing_control_plane == ()


def test_stock_claude_becomes_the_template_not_a_copy(fixture_drive):
    m = drive_map(fixture_drive)
    make_project(fixture_drive, "260306_Stock", sections=["01 Model"],
                 files={"CLAUDE.md": stock_claude(m)})
    _result, inv, _m = conform(fixture_drive, "260306_Stock")
    assert text_of(inv.path / "AGENTS.md") == "\n".join(agents_md_lines(m)) + "\n"
    assert text_of(inv.path / "CLAUDE.md") == POINTER + "\n"


def test_a_hand_written_claude_moves_into_agents_before_the_pointer_lands(fixture_drive):
    custom = "# Montez Radio\n\nOccupancy is held at B. 74 occupants, floor-wide.\n"
    make_project(fixture_drive, "260307_Custom", sections=["01 Model"],
                 files={"CLAUDE.md": custom})
    result, inv, _m = conform(fixture_drive, "260307_Custom")
    agents = text_of(inv.path / "AGENTS.md")
    for line in custom.splitlines():
        assert line in agents
    # the block lands under the project heading, never above it
    assert agents.index("# Montez Radio") < agents.index(AGENTS_BEGIN) < agents.index("74 occupants")
    assert text_of(inv.path / "CLAUDE.md") == POINTER + "\n"
    assert next(a.note for a in result.actions if a.dst == "AGENTS.md") == "created from CLAUDE.md"


def test_claude_is_left_alone_when_agents_lacks_its_words(fixture_drive):
    custom = "# House rules\n\nNever sync the central model while another session is open.\n"
    make_project(fixture_drive, "260308_Clash", sections=["01 Model"],
                 files={"CLAUDE.md": custom, "AGENTS.md": "# Other notes\n\nUnrelated.\n"})
    result, inv, _m = conform(fixture_drive, "260308_Clash")
    action = next(a for a in result.actions if a.dst == "CLAUDE.md")
    assert action.status == CONFLICT and "merge" in action.note
    assert text_of(inv.path / "CLAUDE.md") == custom


def test_a_case_variant_is_renamed_not_duplicated(fixture_drive):
    make_project(fixture_drive, "260309_Case", sections=["01 Model"],
                 files={"Agents.md": "# workspace\n\nHand written.\n",
                        "CLAUDE.md": POINTER + "\n"})
    result, inv, _m = conform(fixture_drive, "260309_Case")
    names = sorted(p.name for p in inv.path.iterdir() if p.is_file())
    assert "AGENTS.md" in names and "Agents.md" not in names
    agents = text_of(inv.path / "AGENTS.md")
    assert "Hand written." in agents and AGENTS_BEGIN in agents
    action = next(a for a in result.actions if a.dst == "AGENTS.md")
    assert "renamed Agents.md -> AGENTS.md" in action.note


def test_the_block_refreshes_and_the_project_notes_survive(fixture_drive):
    stale = ("# workspace\n\n" + AGENTS_BEGIN + "\nrules from last year\n" + AGENTS_END
             + "\n\n## Project notes\n\nKeep me.\n")
    make_project(fixture_drive, "260310_Refresh", sections=["01 Model"],
                 files={"AGENTS.md": stale, "CLAUDE.md": POINTER + "\n"})
    _result, inv, m = conform(fixture_drive, "260310_Refresh")
    agents = text_of(inv.path / "AGENTS.md")
    assert "rules from last year" not in agents
    assert "Keep me." in agents
    assert "\n".join(agents_block_lines(m)) in agents


def test_broken_markers_are_a_conflict(fixture_drive):
    broken = "# workspace\n\n" + AGENTS_BEGIN + "\nhalf a block\n"
    make_project(fixture_drive, "260311_Broken", sections=["01 Model"],
                 files={"AGENTS.md": broken, "CLAUDE.md": POINTER + "\n"})
    result, inv, _m = conform(fixture_drive, "260311_Broken")
    action = next(a for a in result.actions if a.dst == "AGENTS.md")
    assert action.status == CONFLICT and "markers" in action.note
    assert text_of(inv.path / "AGENTS.md") == broken


def test_conform_settles(fixture_drive):
    make_project(fixture_drive, "260312_Twice", sections=["01 Model"],
                 files={"CLAUDE.md": "# workspace\n\nCustom.\n"})
    conform(fixture_drive, "260312_Twice")
    report, _inv, _m = project_report_for(fixture_drive, "260312_Twice")
    assert report.missing_control_plane == ()
    again, _inv, _m = conform(fixture_drive, "260312_Twice")
    assert [a for a in again.actions if a.dst in ("AGENTS.md", "CLAUDE.md")] == []


def test_one_node_repairs_alone(fixture_drive):
    make_project(fixture_drive, "260313_Node", sections=["01 Model"])
    _result, inv, _m = conform(fixture_drive, "260313_Node", node="AGENTS.md")
    assert (inv.path / "AGENTS.md").is_file()
    assert not (inv.path / "CLAUDE.md").exists()
    assert not (inv.path / "PROJECT.md").exists()


def test_the_pointer_waits_for_something_to_point_at(fixture_drive):
    make_project(fixture_drive, "260314_Orphan", sections=["01 Model"],
                 files={"CLAUDE.md": "# workspace\n\nCustom.\n"})
    result, inv, _m = conform(fixture_drive, "260314_Orphan", node="CLAUDE.md")
    action = next(a for a in result.actions if a.dst == "CLAUDE.md")
    assert action.status == CONFLICT and "AGENTS.md" in action.note
    assert "Custom." in text_of(inv.path / "CLAUDE.md")


# ---- the helpers the writers lean on ---------------------------------------

def test_block_lands_after_a_heading_and_at_the_top_without_one(fixture_drive):
    m = drive_map(fixture_drive)
    with_heading = with_agents_block(["# Title", "", "Body."], m)
    assert with_heading[0] == "# Title" and with_heading[2] == AGENTS_BEGIN
    assert with_heading[-1] == "Body."
    headless = with_agents_block(["Body."], m)
    assert headless[0] == AGENTS_BEGIN and headless[-1] == "Body."
    assert with_agents_block(with_heading, m) == with_heading   # idempotent


def test_carried_by_wants_every_line_in_order():
    assert carried_by("a\nb", "a\nx\nb")
    assert not carried_by("a\nb", "b\na")
    assert not carried_by("a\nc", "a\nb")



def test_a_refresh_keeps_unicode_line_separators_in_the_notes(fixture_drive):
    """#61: str.splitlines() broke on U+2028, form feed, U+0085 and 0x1C-0x1E,
    and the CRLF rewrite made them real line breaks in the person's notes."""
    notes = "Note: line one\u2028still the same line\x0cpage\x85next\x1dgroup"
    stale = ("# workspace\n\n" + AGENTS_BEGIN + "\nrules from last year\n" + AGENTS_END
             + "\n\n## Project notes\n\n" + notes + "\n")
    make_project(fixture_drive, "260313_Seps", sections=["01 Model"],
                 files={"AGENTS.md": stale, "CLAUDE.md": POINTER + "\n"})
    _result, inv, _m = conform(fixture_drive, "260313_Seps")
    agents = text_of(inv.path / "AGENTS.md")
    assert "rules from last year" not in agents
    assert notes in agents, "every separator inside the line survives"


def test_a_current_block_with_separators_in_the_notes_is_current(fixture_drive):
    """The doctor's check splits the way the writer does, so a refreshed file
    never reads as stale (and is never rewritten again)."""
    make_project(fixture_drive, "260314_Settle", sections=["01 Model"],
                 files={"AGENTS.md": "# workspace\n\nkeep\u2028this\n",
                        "CLAUDE.md": POINTER + "\n"})
    conform(fixture_drive, "260314_Settle")
    _m = drive_map(fixture_drive)
    text = text_of(fixture_drive / "260314_Settle" / "AGENTS.md")
    assert agents_block_current(text, _m)
