"""PROJECT.md carries a required `design_style` key (Tyler, 2026-11-25).

Every studio project names its architectural design style - Craftsman,
Traditional, Modern, Commercial, or a mix with a reason. There is no studio
default and Atlas never writes a value:

- New projects and conform stubs carry the key blank under a REQUIRED comment.
- Conform backfills the blank key into an older dossier missing it, and never
  touches one that has it.
- Doctor warns while the value is blank; the warning is report-only, never the
  status - only Tyler can fill it.
- The /project-dossier skill's template and key table carry it too.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from atlas.cli import main
from atlas.core.conform import DONE, apply_plan, build_plan
from atlas.core.doctor import report_project
from atlas.core.mapfile import find_map, load_map
from atlas.core.ops import new_project
from atlas.core.project_data import load_project_record
from atlas.core.projectmd import DESIGN_STYLE_LINES, front_matter_scalar
from atlas.core.scan import scan_drive

from conftest import agent_files, make_intake, make_project

DESIGN_STYLE_BYTES = b"".join(line.encode() + b"\r\n" for line in DESIGN_STYLE_LINES)
SKILL = (Path(__file__).resolve().parents[3] / "plugins" / "09-project-dossier"
         / "skills" / "project-dossier" / "SKILL.md")


def _front_matter(raw: bytes) -> dict:
    text = raw.decode("utf-8")
    return yaml.safe_load(text.split("---", 2)[1])


def _report(drive: Path, name: str):
    inventory = scan_drive(drive)
    inv = next(p for p in inventory.projects if p.name == name)
    return inv, report_project(inv, inventory.map)


def _conform(drive: Path, name: str):
    inv, report = _report(drive, name)
    m = load_map(find_map(drive))
    plan = build_plan(report, m, project=inv.path)
    return report, apply_plan(drive, inv.path, m, plan)


def _project_md_action(applied):
    return next(a for a in applied.actions if a.dst == "PROJECT.md")


# ---- scaffolded blank, with the REQUIRED marker ------------------------------

def test_new_project_md_carries_a_blank_required_design_style(fixture_drive):
    m = load_map(find_map(fixture_drive))
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Style House"))
    raw = (result.path / "PROJECT.md").read_bytes()

    assert DESIGN_STYLE_BYTES in raw                  # marker comment + bare key
    assert raw.count(b"\r\ndesign_style:\r\n") == 1
    front = _front_matter(raw)
    assert "design_style" in front and front["design_style"] is None
    assert b"\r\n| Design style | |\r\n" in raw
    # Atlas still reads and edits a dossier carrying the key.
    assert load_project_record(result.path).intake.project_name == "Style House"


def test_conform_stub_carries_the_same_blank_design_style(fixture_drive):
    project = make_project(fixture_drive, "230301_Stub Job", sections=["01 Model"])
    _report_, applied = _conform(fixture_drive, project.name)

    assert _project_md_action(applied).status == DONE
    raw = (project / "PROJECT.md").read_bytes()
    assert DESIGN_STYLE_BYTES in raw
    assert _front_matter(raw)["design_style"] is None
    assert b"\r\n| Design style | |\r\n" in raw


# ---- conform backfill ---------------------------------------------------------

OLDER = (
    b"---\r\n"
    b'project: "Old Job"\r\n'
    b"jurisdiction: california\r\n"
    b"revit:\r\n"
    b"  model:\r\n"
    b"basis: []\r\n"
    b"---\r\n"
    b"\r\n"
    b"# 230302_Old Job\r\n"
)


def test_conform_backfills_a_blank_design_style_into_an_older_dossier(fixture_drive):
    project = make_project(fixture_drive, "230302_Old Job", sections=["01 Model"])
    (project / "PROJECT.md").write_bytes(OLDER)
    report, applied = _conform(fixture_drive, project.name)

    assert "PROJECT.md" in report.missing_control_plane
    action = _project_md_action(applied)
    assert action.status == DONE and action.note == "blank design_style key added"
    raw = (project / "PROJECT.md").read_bytes()
    head, _, body = OLDER.partition(b"---\r\n\r\n")
    assert raw == head + DESIGN_STYLE_BYTES + b"---\r\n\r\n" + body
    assert _front_matter(raw)["design_style"] is None

    # Idempotent: the next pass plans nothing for PROJECT.md.
    report2, _applied2 = _conform(fixture_drive, project.name)
    assert "PROJECT.md" not in report2.missing_control_plane
    assert (project / "PROJECT.md").read_bytes() == raw


def test_backfill_adds_both_missing_keys_in_one_pass(fixture_drive):
    older = OLDER.replace(b"revit:\r\n  model:\r\n", b"")
    project = make_project(fixture_drive, "230303_Older Job", sections=["01 Model"])
    (project / "PROJECT.md").write_bytes(older)
    _report_, applied = _conform(fixture_drive, project.name)

    assert _project_md_action(applied).note == "blank design_style key and revit block added"
    front = _front_matter((project / "PROJECT.md").read_bytes())
    assert front["design_style"] is None and set(front["revit"]) >= {"model", "version"}


@pytest.mark.parametrize("line", [
    b"design_style: Craftsman\r\n",
    b'design_style: "Modern; Craftsman at the addition to match the existing house"\r\n',
    b"design_style:\r\n",                              # blank stays blank: Tyler fills it
    b"design_style: [Modern, Craftsman]\r\n",          # any shape is the dossier's
])
def test_conform_never_touches_an_existing_design_style(fixture_drive, line):
    raw = OLDER.replace(b"basis: []\r\n", line + b"basis: []\r\n")
    project = make_project(fixture_drive, "230304_Has Style", sections=["01 Model"])
    (project / "PROJECT.md").write_bytes(raw)
    report, _applied = _conform(fixture_drive, project.name)

    assert "PROJECT.md" not in report.missing_control_plane
    assert (project / "PROJECT.md").read_bytes() == raw


# ---- doctor flags it while blank ----------------------------------------------

def _doctor_project(drive: Path, name: str, design_line: str):
    files = {"PROJECT.md": f"---\nproject: x\n{design_line}revit:\n---\n",
             "decisions/README.md": "# Decisions\n",
             "06 Research/Code/.keep": ""}
    files.update(agent_files(drive))
    make_project(drive, name, sections=["01 Model", "06 Research", "08 OUT", "11 Meetings"],
                 files=files)
    return _report(drive, name)[1]


@pytest.mark.parametrize("design_line", [
    "design_style:\n",
    "design_style:   # REQUIRED - ask Tyler\n",
    "design_style: ''\n",
    'design_style: ""  # blank\n',
    "",                                                # absent
])
def test_doctor_flags_a_blank_or_absent_design_style(fixture_drive, design_line):
    p = _doctor_project(fixture_drive, "260501_Blank Style", design_line)
    assert p.design_style_unset


@pytest.mark.parametrize("design_line", [
    "design_style: Craftsman\n",
    "design_style: 'Modern; Craftsman at the addition'  # mixed\n",
    "design_style: Commercial # trailing comment\n",
])
def test_doctor_is_quiet_once_design_style_is_filled(fixture_drive, design_line):
    p = _doctor_project(fixture_drive, "260502_Filled Style", design_line)
    assert not p.design_style_unset
    assert p.status == "conform"


def test_blank_design_style_is_a_warning_never_the_status(fixture_drive, capsys):
    p = _doctor_project(fixture_drive, "260503_Warn Only", "design_style:\n")
    assert p.design_style_unset
    assert p.status == "conform" and not p.actionable

    assert main(["doctor", "--drive", str(fixture_drive)]) == 0
    out = capsys.readouterr().out
    assert "warning: PROJECT.md design_style is blank - ask Tyler" in out

    assert main(["doctor", "--drive", str(fixture_drive), "--json"]) == 0
    (proj,) = [q for q in json.loads(capsys.readouterr().out)["projects"]
               if q["name"] == "260503_Warn Only"]
    assert proj["design_style_unset"] is True


def test_a_project_without_a_readable_contract_is_not_flagged(fixture_drive):
    make_project(fixture_drive, "260504_Prose", sections=["01 Model"],
                 files={"PROJECT.md": "# Prose only\n"})
    p = _report(fixture_drive, "260504_Prose")[1]
    assert "PROJECT.md" in p.missing_control_plane     # conform's job first
    assert not p.design_style_unset


# ---- the reader ---------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("---\ndesign_style: Modern\n---\n", "Modern"),
    ("---\ndesign_style:   Craftsman   # note\n---\n", "Craftsman"),
    ("---\n'design_style': \"Modern # not a comment\"\n---\n", "Modern # not a comment"),
    ("---\ndesign_style:\n---\n", ""),
    ("---\nproject: x\n---\n", ""),
    ("---\nlinks:\n  design_style: Modern\n---\n", ""),     # nested, not the root key
    ("---\n# design_style: Modern\n---\n", ""),             # a comment, not the key
    ("no front matter\ndesign_style: Modern\n", None),
    ("---\n{design_style: Modern}\n---\n", None),           # shape it cannot vouch for
])
def test_front_matter_scalar(text, expected):
    assert front_matter_scalar(text, "design_style") == expected


# ---- the dossier skill --------------------------------------------------------

def test_dossier_skill_template_and_key_table_carry_design_style():
    text = SKILL.read_text(encoding="utf-8")
    template = text.split("## Template", 1)[1]
    front = template.split("```markdown\n", 1)[1].split("\n---\n", 1)[0]
    assert any(line.startswith("design_style:") for line in front.split("\n"))
    assert "| Design style | |" in template
    assert "| `design_style` |" in text
    assert "ask Tyler" in text
