"""The permit tracker (roadmap F3, ADR 0024): the AHJ register is the source,
the R<n>_YYMMDD round folders are evidence."""

from __future__ import annotations

import copy
import json
from datetime import date

import pytest

from atlas.cli import main
from atlas.core.lintmap import lint_map
from atlas.core.mapfile import MapError, PermitRule, load_map
from atlas.core.permits import (
    AHJ,
    CLOSED,
    FIELD,
    UNKNOWN,
    US,
    build_application,
    parse_register,
    scan_permits,
    status_word,
)
from atlas.core.scan import scan_drive
from atlas.core.tyler import collect, permit_lines, render
from atlas.tui.permitsview import permit_mode_lines

from conftest import FIXTURE_MAP, make_project, write_map

TODAY = date(2026, 10, 31)
PROJECT = "260717_2267 Monticello-Addition"
AHJ_DIR = "07 Correspondence/AHJ"
RULE = PermitRule(register=f"{AHJ_DIR}/AHJ-REGISTER.md",
                  submissions=f"{AHJ_DIR}/03 Submissions",
                  comments=f"{AHJ_DIR}/04 Comments & Responses")
PERMITS_KEY = {"register": RULE.register, "submissions": RULE.submissions,
               "comments": RULE.comments, "stuckDays": 30}

REGISTER = """# AHJ register - Test

Intro text.

## Applications

| Agency | Application / permit # | Type | Status | Submitted | Round | Next action | Owner |
|---|---|---|---|---|---|---|---|
| Napa County PBES (Building) | BR26-00109-ADD | Building permit | resubmitted (V4 filed per Tyler, chat 2026-10-04) | V4 set 2026-09-11 | 4 | Await County response | CODE360 |
| Napa County Fire | F26-00247 | Fire sprinkler permit | issued 2026-08-03 | - | - | Confirm scope | OutKast |
| Napa County PBES (Environmental Health) | E25-00435 | Septic evaluation | comments - EH letter 2026-10-20 | - | - | Answer EH \\| capacity | Still Water |

**Status:** researching - preparing - submitted - in review - comments - resubmitted -
approved - issued - inspections - finaled - withdrawn

## Contacts

| Agency | Role | Name | Email / phone | Portal |
|---|---|---|---|---|
| Napa County | Planner | A. Person | a@example.com | CODE360 |
"""

EMPTY_REGISTER = """# AHJ register

## Applications

| Agency | Application / permit # | Type | Status | Submitted | Round | Next action | Owner |
|---|---|---|---|---|---|---|---|

## Contacts
"""


def _map_with(**keys) -> dict:
    data = copy.deepcopy(FIXTURE_MAP)
    data["sections"] = data["sections"] + [{"id": "07 Correspondence", "seed": False}]
    data.update(keys)
    return data


def _project(root, register=REGISTER, folders=()):
    files = {RULE.register: register} if register is not None else {}
    for folder in folders:
        files[f"{AHJ_DIR}/{folder}/sheet.pdf"] = ""
    return make_project(root, PROJECT, sections=["07 Correspondence"], files=files)


THREE_ROUNDS = ("03 Submissions/R1_260115", "03 Submissions/R2_260710",
                "03 Submissions/R4_260911", "04 Comments & Responses/R1_260226",
                "04 Comments & Responses/R2_260728 (600807)")


# --- the register ---------------------------------------------------------------

def test_parse_register_reads_only_the_applications_table():
    rows = parse_register(REGISTER)
    assert [r["number"] for r in rows] == ["BR26-00109-ADD", "F26-00247", "E25-00435"]
    assert rows[2]["next_action"] == "Answer EH | capacity"   # escaped pipe kept
    assert parse_register(EMPTY_REGISTER) == []
    assert parse_register("# nothing here\n") == []


@pytest.mark.parametrize("cell, word", [
    ("resubmitted (V4 filed)", "resubmitted"),
    ("submitted (per V4 letter)", "submitted"),
    ("In review since 2026-10-01", "in review"),
    ("**comments** - intake review", "comments"),
    ("issued - job 9/30/26", "issued"),
    ("waiting on county", None),
    ("", None),
])
def test_status_word(cell, word):
    assert status_word(cell) == word


@pytest.mark.parametrize("status, court", [
    ("preparing", US), ("comments", US), ("approved", US), ("researching", US),
    ("submitted", AHJ), ("in review", AHJ), ("resubmitted", AHJ),
    ("inspections", FIELD), ("issued", CLOSED), ("finaled", CLOSED), ("withdrawn", CLOSED),
    ("on hold", UNKNOWN),
])
def test_ball_in_court(status, court):
    assert build_application({"status": status}, {}, {}).court == court


def test_since_prefers_the_matching_round_folder_then_status_then_submitted():
    folder = build_application({"status": "resubmitted, chat 2026-10-04", "round": "4"},
                               {4: date(2026, 9, 11)}, {})
    assert (folder.since, folder.since_source, folder.days(TODAY)) == (
        date(2026, 9, 11), "folder", 50)
    comments = build_application({"status": "comments", "round": "R2"},
                                 {}, {2: date(2026, 7, 28)})
    assert comments.since == date(2026, 7, 28)
    status = build_application({"status": "issued 2026-08-03", "round": "-"}, {}, {})
    assert (status.since, status.since_source) == (date(2026, 8, 3), "status")
    submitted = build_application({"status": "submitted", "submitted": "set 2026-09-11"}, {}, {})
    assert (submitted.since, submitted.since_source) == (date(2026, 9, 11), "submitted")
    unknown = build_application({"status": "submitted"}, {}, {})
    assert unknown.since is None and unknown.days(TODAY) is None
    future = build_application({"status": "submitted 2027-01-01"}, {}, {})
    assert future.days(TODAY) is None


# --- the scan --------------------------------------------------------------------

def test_three_rounds_two_agencies(tmp_path):
    scan = scan_permits(_project(tmp_path, folders=THREE_ROUNDS), RULE)
    courts = {a.number: (a.court, a.days(TODAY)) for a in scan.applications}
    assert courts == {
        "BR26-00109-ADD": (AHJ, 50),       # R4 folder, 2026-09-11
        "F26-00247": (CLOSED, 89),
        "E25-00435": (US, 11),             # no round: the status cell's date
    }
    assert [r.number for r in scan.submissions] == [1, 2, 4]
    assert scan.comments[1].folder.endswith("R2_260728 (600807)")
    assert scan.findings == () and scan.misnamed == () and scan.unreadable == ()


def test_folders_never_date_an_application_when_two_rows_have_rounds(tmp_path):
    # R1 folders carry no agency: with two rounded rows either could own them.
    two = REGISTER.replace("2026-10-20 | - | - |", "2026-10-20 | - | R1 |")
    assert two != REGISTER
    scan = scan_permits(_project(tmp_path, two, THREE_ROUNDS), RULE)
    building, _, health = scan.applications
    assert health.round == 1 and health.since_source == "status"
    assert building.since_source == "status" and building.since == date(2026, 10, 4)


def test_a_newer_folder_round_than_the_register_is_a_finding(tmp_path):
    scan = scan_permits(_project(tmp_path, folders=THREE_ROUNDS + (
        "03 Submissions/R5_261020",)), RULE)
    assert scan.findings == (
        f"{AHJ_DIR}/03 Submissions/R5_261020 is newer than the register (round 4) - "
        "update the register",)


def test_round_folders_beside_an_empty_register_is_a_finding(tmp_path):
    scan = scan_permits(_project(tmp_path, EMPTY_REGISTER, ("03 Submissions/R1_261001",)), RULE)
    assert "register has no applications" in scan.findings[0]
    loose = make_project(tmp_path / "b", PROJECT, files={
        RULE.register: EMPTY_REGISTER, f"{AHJ_DIR}/03 Submissions/set.pdf": ""})
    assert "submissions on file" in scan_permits(loose, RULE).findings[0]


def test_misnamed_round_folders_are_named_and_underscore_dot_skipped(tmp_path):
    scan = scan_permits(_project(tmp_path, folders=(
        "03 Submissions/V1 Submission", "03 Submissions/R2_261399",
        "03 Submissions/_Working", "04 Comments & Responses/V1")), RULE)
    assert scan.misnamed == (f"{AHJ_DIR}/03 Submissions/R2_261399",
                             f"{AHJ_DIR}/03 Submissions/V1 Submission",
                             f"{AHJ_DIR}/04 Comments & Responses/V1")


def test_missing_register_is_missing_not_empty(tmp_path):
    scan = scan_permits(_project(tmp_path, register=None), RULE)
    assert not scan.register_present and scan.applications == ()
    assert scan.findings == ()      # doctor's control-plane check names it


def test_unreadable_register_is_unreadable(tmp_path):
    project = make_project(tmp_path, PROJECT)
    (project / RULE.register).mkdir(parents=True)
    scan = scan_permits(project, RULE)
    assert scan.unreadable and scan.unreadable[0].startswith(RULE.register)


# --- map and lint ----------------------------------------------------------------

def test_map_parses_permits(tmp_path):
    m = load_map(write_map(tmp_path, _map_with(permits=PERMITS_KEY)))
    assert m.permits == RULE
    assert load_map(write_map(tmp_path, FIXTURE_MAP)).permits is None


@pytest.mark.parametrize("bad", [
    [],
    {**PERMITS_KEY, "stuckDays": 0},
    {**PERMITS_KEY, "register": "../x.md"},
    {**PERMITS_KEY, "issued": "x"},
    {k: v for k, v in PERMITS_KEY.items() if k != "comments"},
])
def test_a_malformed_permits_rule_refuses_the_map(tmp_path, bad):
    with pytest.raises(MapError):
        load_map(write_map(tmp_path, _map_with(permits=bad)))


def test_lint_warns_when_a_permits_path_is_not_under_a_section(tmp_path):
    m = load_map(write_map(tmp_path, _map_with(
        permits={**PERMITS_KEY, "comments": "13 AHJ/04 Comments"})))
    assert [f.code for f in lint_map(m)] == ["PERMITS-PATH"]


# --- doctor, CLI, digest, console -----------------------------------------------------

def _drive(tmp_path, *, rule=True, folders=THREE_ROUNDS):
    drive = tmp_path / "TESTDRIVE"
    drive.mkdir(parents=True)
    write_map(drive, _map_with(permits=PERMITS_KEY) if rule else _map_with())
    _project(drive, folders=folders)
    return drive


def test_doctor_deep_warns_without_touching_status_or_exit(tmp_path, capsys):
    drive = _drive(tmp_path, folders=THREE_ROUNDS + ("03 Submissions/V5",))
    args = ["doctor", "--drive", str(drive), "--deep", PROJECT]
    code = main(args)
    out = capsys.readouterr().out
    assert f"warning: round folder not R<n>_YYMMDD: {AHJ_DIR}/03 Submissions/V5" in out
    assert main(args + ["--json"]) == code
    project = json.loads(capsys.readouterr().out)["projects"][0]
    assert project["permits"]["misnamed"] == [f"{AHJ_DIR}/03 Submissions/V5"]
    plain = _drive(tmp_path / "plain", rule=False, folders=THREE_ROUNDS + ("03 Submissions/V5",))
    assert main(["doctor", "--drive", str(plain), "--deep", PROJECT, "--json"]) == code
    other = json.loads(capsys.readouterr().out)["projects"][0]
    assert other["status"] == project["status"] and other["permits"] is None


def test_permits_cli_text_and_json(tmp_path, capsys):
    drive = _drive(tmp_path)
    assert main(["permits", "--drive", str(drive)]) == 0
    out = capsys.readouterr().out
    assert "[AHJ   ] Napa County PBES (Building) BR26-00109-ADD: at AHJ" in out
    assert "next: Await County response" in out and "3 applications" in out
    assert main(["permits", "--drive", str(drive), PROJECT, "--json"]) == 0
    (row,) = json.loads(capsys.readouterr().out)
    assert row["register_present"] is True
    assert [a["court"] for a in row["applications"]] == [AHJ, CLOSED, US]
    assert row["applications"][0]["since"] == "2026-09-11"


def test_permits_cli_without_a_rule_says_so(tmp_path, capsys):
    assert main(["permits", "--drive", str(_drive(tmp_path, rule=False))]) == 2
    assert "no 'permits' rule" in capsys.readouterr().err


def test_digest_lists_what_we_owe_and_what_is_stuck(tmp_path, capsys):
    digest = collect(scan_drive(_drive(tmp_path)))
    lines = permit_lines(digest, TODAY)
    assert lines == [
        "**2267 Monticello** BR26-00109-ADD: at AHJ 50d (resubmitted, round 4)",
        "**2267 Monticello** E25-00435: we owe 11d (comments) - "
        "next: Answer EH | capacity",
    ]
    text = render(digest, generated=TODAY)
    assert "## Permits" in text and "3 applications in the AHJ registers: 1 we owe, " \
        "1 at the agency, 0 in inspections, 1 closed" in text
    assert main(["tyler", "--drive", str(tmp_path / "TESTDRIVE"), "--json"]) == 0
    permits = json.loads(capsys.readouterr().out)["projects"][0]["permits"]
    assert len(permits["applications"]) == 3


def test_digest_without_a_rule_has_no_permits_block(tmp_path):
    digest = collect(scan_drive(_drive(tmp_path, rule=False)))
    assert "## Permits" not in render(digest)


@pytest.mark.parametrize("size", [(120, 51), (80, 30)])
async def test_console_cycles_to_the_permits_mode(tmp_path, size):
    from textual.widgets import Static

    from atlas.tui.app import AtlasApp
    from atlas.tui.layout import PERMITS

    drive = _drive(tmp_path)
    app = AtlasApp(drive, follow_debounce=0)
    async with app.run_test(size=size) as pilot:
        for _ in range(3):
            await app.workers.wait_for_complete()
            await pilot.pause()
        while app._companion_mode != PERMITS:
            await pilot.press("d")
            await pilot.pause()
        body = str(app.query_one("#companion-body", Static).content)
        assert "[AHJ] Napa County PBES (Building) BR26-00109-ADD" in body
        assert "Edit the register:" in body


def test_console_mode_lines(tmp_path):
    scan = scan_permits(_project(tmp_path, folders=THREE_ROUNDS + ("03 Submissions/V5",)), RULE)
    lines = permit_mode_lines(scan, TODAY)
    assert lines[0] == "[AHJ] Napa County PBES (Building) BR26-00109-ADD"
    assert "  at AHJ 50d (resubmitted, round 4)" in lines
    assert f"  {AHJ_DIR}/03 Submissions/V5" in lines
    assert lines[-1] == f"Edit the register: {RULE.register}"
    missing = scan_permits(_project(tmp_path / "m", register=None), RULE)
    assert permit_mode_lines(missing, TODAY)[0] == f"No register at {RULE.register}."
