"""ADR 0025: child descriptions, on-create templates, filing cards, off-map count.

Uses the real bundled templates (PROGRAM.md, CLIENT-ITEMS.md, SELECTIONS.md).
"""

from __future__ import annotations

import copy

import pytest

from atlas.core.conform import apply_plan, build_plan
from atlas.core.deep import scan_deep
from atlas.core.doctor import report_project
from atlas.core.filingcard import CARD_BEGIN, CARD_END, card_block_lines
from atlas.core.lintmap import WARN, lint_map
from atlas.core.mapfile import MapError, find_map, load_map
from atlas.core.ops import add_sections, new_project
from atlas.core.projectmd import agents_block_lines, canonical_map_lines
from atlas.core.scan import ProjectInventory, list_entries
from atlas.tui.app import AddSectionModal

from conftest import FIXTURE_MAP, make_intake, make_project, write_map

PROGRAM = "06 Research/Client Program/PROGRAM.md"
ITEMS_DIR = "06 Research/Client Program/Client Items"
ITEMS = f"{ITEMS_DIR}/CLIENT-ITEMS.md"
SELECTIONS = "05 Specs/00 Selections/SELECTIONS.md"

MAP = copy.deepcopy(FIXTURE_MAP)
MAP["version"] = "4.5"
research = next(s for s in MAP["sections"] if s["id"] == "06 Research")
research["filingCard"] = True
research["children"] = [
    {"name": "Zoning", "description": "Zoning code, overlays and setbacks"},
    "Code",
    {"name": "Client Program", "seed": True,
     "description": "What the client needs: rooms, sizes, must-haves (PROGRAM.md)"},
    {"name": "Client Program/Client Items",
     "description": "Photos and sizes of the client's appliances and equipment"},
    "Site Review/Field Measurements",
]
MAP["sections"].insert(1, {"id": "05 Specs", "children": [
    {"name": "00 Selections", "description": "What was chosen, by whom, and its status"},
    "11 Equipment",
]})
MAP["templates"] = [
    {"path": PROGRAM, "template": "PROGRAM.md", "index": "Client program"},
    {"path": ITEMS, "template": "CLIENT-ITEMS.md", "index": "Client items", "when": "on-create"},
    {"path": SELECTIONS, "template": "SELECTIONS.md", "index": "Selections register",
     "when": "on-create"},
]


@pytest.fixture
def drive(fixture_drive):
    write_map(fixture_drive, MAP)
    return fixture_drive


def _load(drive):
    return load_map(find_map(drive))


def _report(project, m, **deep):
    inv = ProjectInventory(path=project, name=project.name, root_entries=list_entries(project))
    return report_project(inv, m, **deep)


# ---------------------------------------------------------------- map schema

def test_descriptions_on_create_and_filing_card_load(drive):
    m = _load(drive)
    section = m.section("06 Research")
    assert section.filing_card
    assert section.description("Client Program").startswith("What the client needs")
    assert section.description("Code") == ""
    by_path = {t.path: t for t in m.templates}
    assert not by_path[PROGRAM].on_create
    assert by_path[ITEMS].on_create and by_path[ITEMS].folder == ITEMS_DIR


def test_a_map_without_the_new_keys_loads_unchanged(fixture_drive):
    m = _load(fixture_drive)
    assert all(s.descriptions == () and not s.filing_card for s in m.sections)


@pytest.mark.parametrize("mutate", [
    lambda d: d["sections"][2]["children"].append({"name": "X", "description": ""}),
    lambda d: d["sections"][2]["children"].append({"name": "X", "description": "two\nlines"}),
    lambda d: d["sections"][2]["children"].append({"name": "X", "description": 3}),
    lambda d: d["templates"].append({"path": "05 Specs/X.md", "template": "SELECTIONS.md",
                                     "when": "sometimes"}),
    lambda d: d["templates"].append({"path": "ROOT.md", "template": "SELECTIONS.md",
                                     "when": "on-create"}),
    lambda d: d["sections"][2].update(filingCard="yes"),
    lambda d: d["sections"][0].update(filingCard=True),   # no descriptions to build from
])
def test_malformed_new_keys_refuse_the_map(fixture_drive, mutate):
    data = copy.deepcopy(MAP)
    mutate(data)
    write_map(fixture_drive, data)
    with pytest.raises(MapError):
        _load(fixture_drive)


# ---------------------------------------------------------------- new project

def test_new_project_gets_the_program_and_card_but_no_on_demand_folders(drive):
    m = _load(drive)
    result = new_project(drive, m, make_intake(drive, "Coffee House"))
    project = result.path
    assert (project / PROGRAM).read_text(encoding="utf-8").startswith("---")
    assert "# Program - Coffee House" in (project / PROGRAM).read_text(encoding="utf-8")
    assert not (project / ITEMS_DIR).exists()
    assert not (project / "05 Specs").exists()
    assert PROGRAM in result.templates and ITEMS not in result.templates
    card = (project / "06 Research/README.md").read_text(encoding="utf-8")
    assert card.startswith("# 06 Research")
    assert "| Zoning code, overlays and setbacks | `Zoning` |" in card
    report = _report(project, m)
    assert report.missing_control_plane == ()


def test_add_section_brings_its_on_create_template(drive):
    m = _load(drive)
    project = new_project(drive, m, make_intake(drive, "Kitchen House")).path
    created = add_sections(drive, m, project, [ITEMS_DIR])
    assert created == [ITEMS_DIR, ITEMS]
    # Named from the folder, as conform's backfill names it.
    text = (project / ITEMS).read_text(encoding="utf-8")
    assert text.startswith("# Client items - ") and "Kitchen House" in text and "{{" not in text
    # Again: the folder and the file are already there, so nothing new.
    assert add_sections(drive, m, project, [ITEMS_DIR]) == []
    created = add_sections(drive, m, project, ["05 Specs/00 Selections"])
    assert created == ["05 Specs/00 Selections", SELECTIONS]
    assert (project / SELECTIONS).is_file()


def test_add_section_never_overwrites_an_existing_register(drive):
    m = _load(drive)
    project = new_project(drive, m, make_intake(drive, "Ours House")).path
    (project / ITEMS_DIR).mkdir(parents=True)
    (project / ITEMS).write_text("# ours\n", encoding="utf-8")
    assert add_sections(drive, m, project, [ITEMS_DIR]) == []
    assert (project / ITEMS).read_text(encoding="utf-8") == "# ours\n"


# ---------------------------------------------------------------- doctor / conform

def test_doctor_owes_an_on_create_template_only_once_its_folder_exists(drive):
    m = _load(drive)
    project = make_project(drive, "250101_Old House", sections=["06 Research"])
    missing = _report(project, m).missing_control_plane
    assert PROGRAM in missing and ITEMS not in missing and SELECTIONS not in missing
    (project / ITEMS_DIR).mkdir(parents=True)
    assert ITEMS in _report(project, m).missing_control_plane
    apply_plan(drive, project, m, build_plan(_report(project, m), m, project))
    assert (project / ITEMS).is_file() and (project / PROGRAM).is_file()
    assert not (project / "05 Specs").exists()
    assert _report(project, m).missing_control_plane == ()


def test_conform_writes_and_refreshes_the_card_keeping_notes_outside_it(drive):
    m = _load(drive)
    project = make_project(drive, "250101_Card House", sections=["06 Research"], files={
        "06 Research/README.md": "# Research\n\nOur note stays.\n",
    })
    assert "06 Research/README.md" in _report(project, m).missing_control_plane
    apply_plan(drive, project, m, build_plan(_report(project, m), m, project))
    text = (project / "06 Research/README.md").read_text(encoding="utf-8")
    assert text.startswith("# Research") and "Our note stays." in text
    assert CARD_BEGIN in text and CARD_END in text
    assert "06 Research/README.md" not in _report(project, m).missing_control_plane

    # The map changes: the card is stale until conform refreshes it.
    data = copy.deepcopy(MAP)
    next(s for s in data["sections"] if s["id"] == "06 Research")["children"][0]["description"] = "Zoning only"
    write_map(drive, data)
    m2 = _load(drive)
    assert "06 Research/README.md" in _report(project, m2).missing_control_plane
    apply_plan(drive, project, m2, build_plan(_report(project, m2), m2, project))
    text = (project / "06 Research/README.md").read_text(encoding="utf-8")
    assert "| Zoning only | `Zoning` |" in text and "Our note stays." in text
    assert text.count(CARD_BEGIN) == 1



def test_a_card_refresh_keeps_unicode_line_separators_in_the_notes(drive):
    """#61: the card rewrite turned U+2028 and form feed into line breaks."""
    m = _load(drive)
    note = "Our note\u2028stays one line\x0cand this too."
    project = make_project(drive, "250101_Seps House", sections=["06 Research"], files={
        "06 Research/README.md": f"# Research\n\n{note}\n",
    })
    apply_plan(drive, project, m, build_plan(_report(project, m), m, project))
    text = (project / "06 Research/README.md").read_text(encoding="utf-8")
    assert CARD_BEGIN in text and note in text
    assert "06 Research/README.md" not in _report(project, m).missing_control_plane


def test_broken_card_markers_are_a_conflict_not_a_rewrite(drive):
    m = _load(drive)
    broken = f"# Research\n{CARD_BEGIN}\nhalf a card\n"
    project = make_project(drive, "250101_Broken House", sections=["06 Research"],
                           files={"06 Research/README.md": broken})
    applied = apply_plan(drive, project, m, build_plan(_report(project, m), m, project))
    card = next(a for a in applied.actions if a.dst == "06 Research/README.md")
    assert card.status == "conflict"
    assert (project / "06 Research/README.md").read_text(encoding="utf-8") == broken


def test_no_card_for_an_absent_section_nothing_will_create(drive):
    data = copy.deepcopy(MAP)
    data["templates"] = []          # no backfill makes 06 Research here
    write_map(drive, data)
    m = _load(drive)
    project = make_project(drive, "250101_Bare House", sections=["01 Model"])
    assert "06 Research/README.md" not in _report(project, m).missing_control_plane


# ---------------------------------------------------------------- generated text

def test_agents_index_marks_on_create_rows_and_the_map_block_shows_descriptions(drive):
    m = _load(drive)
    rows = "\n".join(agents_block_lines(m))
    assert f"| Client items - only once its folder is added | `{ITEMS}` |" in rows
    assert f"| Client program | `{PROGRAM}` |" in rows
    block = "\n".join(canonical_map_lines(m))
    assert "  - Client Program _[seed]_ - What the client needs" in block
    assert "  - Code\n" in block + "\n"


def test_card_is_plain_staff_copy(drive):
    lines = card_block_lines(_load(drive).section("06 Research"))
    assert all("—" not in line for line in lines)   # no em dashes in staff copy
    assert "| I have... | It goes in |" in lines


def test_add_menu_label_carries_the_description():
    label = AddSectionModal._option_label("06 Research/Zoning", "Zoning code")
    assert label.plain == "  06 Research / Zoning  Zoning code"
    assert AddSectionModal._option_label("06 Research/Code").plain == "  06 Research / Code"


# ---------------------------------------------------------------- lint

def test_lint_warns_on_undescribed_seeded_children_once_descriptions_are_used(drive):
    data = copy.deepcopy(MAP)
    model = next(s for s in data["sections"] if s["id"] == "01 Model")
    model["children"] = [{"name": "01 Site Model", "seed": True}, "02 Design"]
    data["templates"].append({"path": "06 Research/Client Program/X.md",
                              "template": "SELECTIONS.md", "when": "on-create"})
    write_map(drive, data)
    findings = [(f.level, f.code, f.message) for f in lint_map(_load(drive))]
    assert any(code == "CHILD-UNDESCRIBED" and "01 Site Model" in msg
               for level, code, msg in findings if level == WARN)
    assert any(code == "TEMPLATE-ON-CREATE-SEEDED" for _l, code, _m in findings)


def test_lint_is_quiet_about_descriptions_on_a_map_that_uses_none(fixture_drive):
    codes = {f.code for f in lint_map(_load(fixture_drive))}
    assert "CHILD-UNDESCRIBED" not in codes


# ---------------------------------------------------------------- off-map (deep)

def test_deep_pass_names_folders_off_the_map(drive):
    m = _load(drive)
    project = make_project(drive, "250101_Drift House", sections=["06 Research"])
    for rel in ("06 Research/Program and client Reqs",       # off: hand-made home
                "06 Research/Program and client Reqs/Inner",  # below an off folder: not named
                "06 Research/Zoning/Anything Goes",           # inside a blessed child: free
                "06 Research/Site Review",                    # on the way to a blessed child
                "06 Research/Site Review/Stray",              # off
                "06 Research/.dicta",                         # app state
                "06 Research/260101 Site Visit",              # dated instance
                "06 Research/Model_backup",                   # Revit backup
                "06 Research/_sources",
                "Unmapped Top/Deep"):                         # root report's business
        (project / rel).mkdir(parents=True, exist_ok=True)
    scan = scan_deep(project, m)
    assert scan.off_map == ("06 Research/Program and client Reqs", "06 Research/Site Review/Stray")
    report = _report(project, m, off_map=scan.off_map)
    assert report.off_map == scan.off_map
    assert _report(project, m).off_map is None   # not walked is not "none found"


# ---------------------------------------------------------------- review fixes

def test_one_conform_pass_brings_the_section_its_template_and_its_card(drive):
    m = _load(drive)
    project = make_project(drive, "250101_One Pass House", sections=["01 Model"])
    apply_plan(drive, project, m, build_plan(_report(project, m), m, project))
    assert (project / PROGRAM).is_file()
    assert (project / "06 Research/README.md").is_file()
    assert _report(project, m).missing_control_plane == ()


def test_a_template_may_not_claim_a_filing_card_path(fixture_drive):
    data = copy.deepcopy(MAP)
    data["templates"].append({"path": "06 Research/README.md", "template": "PROGRAM.md"})
    write_map(fixture_drive, data)
    with pytest.raises(MapError, match="filing card"):
        _load(fixture_drive)


def test_revit_temp_is_not_drift(drive):
    m = _load(drive)
    project = make_project(drive, "250101_Revit House", sections=["01 Model"])
    (project / "01 Model/Revit_temp").mkdir()
    assert scan_deep(project, m).off_map == ()


def test_a_pipe_in_a_description_stays_in_its_cell(drive):
    data = copy.deepcopy(MAP)
    next(s for s in data["sections"] if s["id"] == "06 Research")["children"][0]["description"] = "Zoning | overlays"
    write_map(drive, data)
    lines = card_block_lines(_load(drive).section("06 Research"))
    assert "| Zoning \\| overlays | `Zoning` |" in lines


def test_a_missing_on_create_template_stops_the_add_before_any_folder(drive, monkeypatch, tmp_path):
    m = _load(drive)
    project = new_project(drive, m, make_intake(drive, "No Template House")).path
    monkeypatch.setenv("ATLAS_TEMPLATES", str(tmp_path / "nowhere"))
    with pytest.raises(Exception, match="CLIENT-ITEMS.md"):
        add_sections(drive, m, project, [ITEMS_DIR])
    assert not (project / ITEMS_DIR).exists()


def test_lint_warns_when_a_card_section_child_has_no_description(drive):
    codes = {f.code for f in lint_map(_load(drive))}
    assert "CARD-CHILD-UNDESCRIBED" in codes
