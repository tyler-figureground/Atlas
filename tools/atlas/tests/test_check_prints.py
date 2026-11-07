"""ADR 0026: check prints have one seeded home with a filing card.

Runs the real map v4.6 migration script over a v4.5-shaped map and uses the real
bundled CHECK-PRINTS-README.md and agents rules.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

from atlas.core.conform import apply_plan, build_plan
from atlas.core.doctor import report_project
from atlas.core.lintmap import ERROR, lint_map
from atlas.core.mapfile import find_map, load_map
from atlas.core.ops import new_project
from atlas.core.scan import ProjectInventory, list_entries
from atlas.core.templates import read_template

from conftest import FIXTURE_MAP, make_intake, make_project, write_map

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "migrate_map_v4_6.py"
CHECK = "02 Sheets/_Check Prints"
CARD = f"{CHECK}/README.md"

V45 = copy.deepcopy(FIXTURE_MAP)
V45["version"] = "4.5"
V45["sections"].insert(1, {"id": "02 Sheets", "seed": True,
                           "children": ["_Check Prints", "0 Feasibility", "4 Construction"]})
V45["templates"] = []
V45["relocations"]["02 Sheets/Test Prints"] = CHECK


def _migrated(tmp_path, drive):
    src = tmp_path / "v45.json"
    src.write_text(json.dumps(V45), encoding="utf-8")
    out = tmp_path / "v46.json"
    run = subprocess.run([sys.executable, str(SCRIPT), str(src), str(out)],
                         capture_output=True, text=True, encoding="utf-8")
    assert run.returncode == 0, run.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    write_map(drive, data)
    return data, load_map(find_map(drive))


def _report(project, m):
    inv = ProjectInventory(path=project, name=project.name, root_entries=list_entries(project))
    return report_project(inv, m)


def test_migration_seeds_check_prints_with_a_card_and_lints_clean(tmp_path, fixture_drive):
    data, m = _migrated(tmp_path, fixture_drive)
    assert data["version"] == "4.6"
    sheets = m.section("02 Sheets")
    assert "_Check Prints" in sheets.seed_children
    assert sheets.description("_Check Prints")
    assert any(t.path == CARD and not t.on_create for t in m.templates)
    assert data["relocations"]["02 Sheets/Check Set"] == CHECK
    assert [f for f in lint_map(m) if f.level == ERROR] == []


def test_migration_refuses_a_map_that_is_not_v4_5(tmp_path):
    src = tmp_path / "v44.json"
    src.write_text(json.dumps({**V45, "version": "4.4"}), encoding="utf-8")
    run = subprocess.run([sys.executable, str(SCRIPT), str(src), str(tmp_path / "o.json")],
                         capture_output=True, text=True, encoding="utf-8")
    assert run.returncode != 0
    assert not (tmp_path / "o.json").exists()


def test_new_project_gets_the_folder_and_its_card(tmp_path, fixture_drive):
    _data, m = _migrated(tmp_path, fixture_drive)
    project = new_project(fixture_drive, m, make_intake(fixture_drive, "Print House")).path
    card = (project / CARD).read_text(encoding="utf-8")
    assert card.startswith("# Check prints - Print House")
    assert _report(project, m).missing_control_plane == ()


def test_conform_backfills_the_card_and_merges_a_hand_made_check_set(tmp_path, fixture_drive):
    _data, m = _migrated(tmp_path, fixture_drive)
    project = make_project(fixture_drive, "250101_Old Print House", sections=["02 Sheets"])
    (project / "02 Sheets/Check Set").mkdir()
    (project / "02 Sheets/Check Set/261002_A101_Check.pdf").write_bytes(b"%PDF-1.7")
    (project / CHECK).mkdir()
    (project / CHECK / "1.pdf").write_bytes(b"%PDF-1.7")
    apply_plan(fixture_drive, project, m, build_plan(_report(project, m), m, project))
    assert (project / CARD).is_file()
    assert (project / CHECK / "261002_A101_Check.pdf").is_file()
    assert (project / CHECK / "1.pdf").is_file()
    assert not (project / "02 Sheets/Check Set").exists()


def test_card_is_plain_staff_copy_and_the_agent_rules_name_the_folder():
    card = read_template("CHECK-PRINTS-README.md")
    assert "—" not in card                      # no em dashes in staff copy
    assert "| I have... | It goes in |" in card
    rules = read_template("agents-rules.md")
    assert "02 Sheets/_Check Prints/YYMMDD_<Scope>/" in rules
    assert ".agent/runs/<run>/print/" in rules
