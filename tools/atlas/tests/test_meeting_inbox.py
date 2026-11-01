"""The Meeting Inbox (roadmap F4): meetings with no minutes, by map rule."""

from __future__ import annotations

import copy
import json
from datetime import date

import pytest

from atlas.cli import main
from atlas.core.lintmap import lint_map
from atlas.core.mapfile import MapError, MeetingRule, load_map
from atlas.core.meetings import file_date, pair, scan_meetings, stem
from atlas.core.scan import scan_drive
from atlas.core.tyler import collect, meeting_line, render

from conftest import FIXTURE_MAP, make_project, write_map

RULE = MeetingRule(
    dir="11 Meetings",
    transcripts=("*transcript*.md",),
    recordings=("*.m4a",),
    minutes=("*minutes*.md", "*minutes*.docx", "*minutes*.pdf"),
)

MEETINGS_KEY = {
    "dir": "11 Meetings",
    "transcripts": ["*transcript*.md"],
    "recordings": ["*.m4a"],
    "minutes": ["*minutes*.md", "*minutes*.docx"],
}

PROJECT = "261002_1 Main St-Test"


def _map_with(**keys) -> dict:
    data = copy.deepcopy(FIXTURE_MAP)
    data.update(keys)
    return data


# --- names --------------------------------------------------------------------

@pytest.mark.parametrize("name, expected", [
    ("260813-64th Lane rebid site meeting.m4a", date(2026, 8, 13)),
    ("20261013 - Montez curtains.transcript.md", date(2026, 10, 13)),
    ("261399 - not a date.md", None),
    ("Kickoff.transcript.md", None),
    ("2610011 - seven digits.md", None),
])
def test_file_date(name, expected):
    assert file_date(name) == expected


def test_stems_group_the_spellings_the_drive_actually_uses():
    # Recording and transcript, differing by case and a Dicta hash.
    assert (stem("260927 - silverado material story.m4a")
            == stem("260927 - silverado material story-e2f109372d44.transcript.md"))
    assert (stem("260915 - Montez Meeting - storage.m4a")
            == stem("260915 - Montez Meeting - Storage.transcript.md"))
    # " - Transcript" and "_Transcript-Excerpt" suffixes.
    assert stem("261006 - Damian Ostertag - Transcript.md") == "damianostertag"
    assert stem("260914_Kitchen-Walkthrough_Transcript-Excerpt.md") == "kitchenwalkthrough"
    # Dicta's raw name and the renamed copy are one meeting.
    assert (stem("20261013 - Montez meeting curtains and electrical-e7591de7d34d.transcript.md")
            == stem("261013 - Montez Curtains and Electrical.transcript.md"))
    # Minutes in three formats are one document.
    assert (stem("260915 - Storage - Meeting Minutes.md")
            == stem("260915 - Storage - Meeting Minutes.docx") == "storage")


# --- pairing --------------------------------------------------------------------

def test_pairs_same_day_and_reports_exactly_the_unpaired():
    meetings = pair([
        "260913-site meeting.m4a",
        "260913-site meeting.transcript.md",
        "260913_Site-Walk_Meeting-Minutes.md",
        "260916 - owner.transcript.md",
        "261006 - cabling.m4a",
        "261006 - cabling.transcript.md",
        "261014 - weekly.m4a",
        "260920_Window-Audit.md",          # an audit memo: not part of any meeting
    ], RULE)
    assert [(m.date.isoformat(), m.closed, m.transcribed) for m in meetings] == [
        ("2026-09-13", True, True),
        ("2026-09-16", False, True),
        ("2026-10-06", False, True),
        ("2026-10-14", False, False),
    ]
    assert meetings[0].transcripts == ("260913-site meeting.transcript.md",)
    assert meetings[0].recordings == ("260913-site meeting.m4a",)


def test_minutes_up_to_the_window_later_close_a_meeting():
    # Silverado: recorded 9/27, minutes dated 9/29.
    meetings = pair(["Recordings/260927 - material story.m4a",
                     "Minutes/260929_Material-Story_Meeting-Minutes.md"], RULE)
    assert meetings[0].closed
    assert meetings[0].minutes == "Minutes/260929_Material-Story_Meeting-Minutes.md"
    # Past the window, or before the meeting, they do not.
    assert not pair(["260920 - a.m4a", "260924 - a - Meeting Minutes.md"], RULE)[0].closed
    assert not pair(["260920 - a.m4a", "260919 - a - Meeting Minutes.md"], RULE)[0].closed


def test_a_later_meetings_minutes_never_close_an_earlier_one_that_lacks_its_own():
    meetings = pair(["260915 - storage.m4a", "260916 - walk.m4a",
                     "260916 - walk - Meeting Minutes.md"], RULE)
    assert {m.date.day: m.closed for m in meetings} == {15: False, 16: True}


def test_one_document_in_three_formats_closes_one_meeting_only():
    meetings = pair(["260914 - a.m4a", "260915 - b.m4a",
                     "260915 - b - Meeting Minutes.md",
                     "260915 - b - Meeting Minutes.docx",
                     "260915 - b - Meeting Minutes.pdf"], RULE)
    assert {m.date.day: m.closed for m in meetings} == {14: False, 15: True}


def test_two_meetings_one_day_the_named_one_claims_the_minutes():
    meetings = pair(["261001 - alpha.m4a", "261001 - zulu.m4a",
                     "261001 - zulu - Meeting Minutes.md"], RULE)
    assert {m.stem: m.closed for m in meetings} == {"alpha": False, "zulu": True}


def test_undated_meetings_pair_by_stem_only_and_never_guess_a_date():
    meetings = pair(["Kickoff.transcript.md", "Kickoff - Meeting Minutes.md",
                     "Walkthrough.transcript.md"], RULE)
    assert [(m.stem, m.date, m.closed) for m in meetings] == [
        ("kickoff", None, True), ("walkthrough", None, False)]


# --- the walk --------------------------------------------------------------------

def test_scan_walks_subfolders_skips_dot_folders(tmp_path):
    project = make_project(tmp_path, PROJECT, files={
        "11 Meetings/Recordings/261014 - weekly.m4a": "",
        "11 Meetings/.dicta/abc/261020 - hidden.transcript.md": "",
        "11 Meetings/Minutes/261006 - kickoff - Meeting Minutes.md": "",
        "11 Meetings/261006 - kickoff.transcript.md": "",
    })
    scan = scan_meetings(project, RULE)
    assert scan.present and not scan.unreadable
    assert [m.label for m in scan.pending] == ["Recordings/261014 - weekly.m4a"]
    assert scan.oldest_pending() == date(2026, 10, 14)


def test_scan_without_a_meetings_folder_is_absent_not_empty(tmp_path):
    project = make_project(tmp_path, PROJECT, sections=["01 Model"])
    scan = scan_meetings(project, RULE)
    assert not scan.present and scan.meetings == ()


# --- the map --------------------------------------------------------------------

def test_map_parses_meetings_with_defaults(tmp_path):
    m = load_map(write_map(tmp_path, _map_with(meetings=MEETINGS_KEY)))
    assert m.meetings == MeetingRule(
        dir="11 Meetings", transcripts=("*transcript*.md",), recordings=("*.m4a",),
        minutes=("*minutes*.md", "*minutes*.docx"), window_days=3, max_depth=3)
    assert load_map(write_map(tmp_path, FIXTURE_MAP)).meetings is None


@pytest.mark.parametrize("bad", [
    "11 Meetings",
    {**MEETINGS_KEY, "minutes": []},
    {**MEETINGS_KEY, "windowDays": 0},
    {**MEETINGS_KEY, "windowDays": True},
    {**MEETINGS_KEY, "dir": "../elsewhere"},
    {**MEETINGS_KEY, "minute": ["*"]},
    {k: v for k, v in MEETINGS_KEY.items() if k != "transcripts"},
])
def test_a_malformed_meetings_rule_refuses_the_map(tmp_path, bad):
    with pytest.raises(MapError):
        load_map(write_map(tmp_path, _map_with(meetings=bad)))


def test_lint_warns_when_the_meetings_dir_is_not_a_section(tmp_path):
    m = load_map(write_map(tmp_path, _map_with(meetings={**MEETINGS_KEY, "dir": "12 Meetngs"})))
    assert [f.code for f in lint_map(m)] == ["MEETINGS-DIR"]
    m = load_map(write_map(tmp_path, _map_with(meetings=MEETINGS_KEY)))
    assert "MEETINGS-DIR" not in [f.code for f in lint_map(m)]


# --- doctor, CLI, digest ------------------------------------------------------------

def _drive(tmp_path, *, rule=True):
    drive = tmp_path / "TESTDRIVE"
    drive.mkdir(parents=True)
    write_map(drive, _map_with(meetings=MEETINGS_KEY) if rule else FIXTURE_MAP)
    make_project(drive, PROJECT, sections=["11 Meetings"], files={
        "11 Meetings/261006 - kickoff.transcript.md": "",
        "11 Meetings/261006 - kickoff - Meeting Minutes.md": "",
        "11 Meetings/261014 - weekly.m4a": "",
        "11 Meetings/261014 - weekly.transcript.md": "",
        "11 Meetings/261021 - site.m4a": "",
    })
    return drive


def test_doctor_deep_warns_without_touching_status_or_exit(tmp_path, capsys):
    drive = _drive(tmp_path)
    args = ["doctor", "--drive", str(drive), "--deep", PROJECT]
    code = main(args)
    out = capsys.readouterr().out
    assert "warning: meeting not closed out (2026-10-14): 11 Meetings/261014 - weekly.transcript.md" in out
    assert "warning: meeting not closed out (2026-10-21) (not transcribed): 11 Meetings/261021 - site.m4a" in out
    assert main(args + ["--json"]) == code
    project = json.loads(capsys.readouterr().out)["projects"][0]
    # Same exit code and status as the same drive without the rule.
    without = _drive(tmp_path / "plain", rule=False)
    assert main(["doctor", "--drive", str(without), "--deep", PROJECT, "--json"]) == code
    assert json.loads(capsys.readouterr().out)["projects"][0]["status"] == project["status"]
    assert project["meetings"]["closed"] == 1
    assert [p["date"] for p in project["meetings"]["pending"]] == ["2026-10-14", "2026-10-21"]


def test_doctor_default_pass_never_walks_meetings(tmp_path, capsys):
    drive = _drive(tmp_path)
    main(["doctor", "--drive", str(drive), "--json"])
    assert json.loads(capsys.readouterr().out)["projects"][0]["meetings"] is None


def test_meetings_cli_lists_pending_and_all(tmp_path, capsys):
    drive = _drive(tmp_path)
    assert main(["meetings", "--drive", str(drive), "--pending"]) == 0
    out = capsys.readouterr().out
    assert "261014 - weekly.transcript.md  [PENDING]" in out
    assert "261021 - site.m4a  [PENDING, not transcribed]" in out
    assert "kickoff" not in out and "2 pending meetings" in out
    assert main(["meetings", "--drive", str(drive), PROJECT, "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [m["closed"] for m in data[0]["meetings"]] == [True, False, False]


def test_meetings_cli_without_a_rule_says_so(tmp_path, capsys):
    drive = _drive(tmp_path, rule=False)
    assert main(["meetings", "--drive", str(drive)]) == 2
    assert "no 'meetings' rule" in capsys.readouterr().err


def test_digest_names_meetings_not_closed_out(tmp_path, capsys):
    drive = _drive(tmp_path)
    digest = collect(scan_drive(drive))
    assert meeting_line(digest.projects[0]) == (
        "**1 Main St**: 2 meetings not closed out (1 not transcribed) - oldest 2026-10-14")
    text = render(digest, generated=date(2026, 10, 31))
    assert "## Meetings not closed out" in text
    assert text.index("## Meetings not closed out") < text.index(f"## {PROJECT}")
    assert main(["tyler", "--drive", str(drive), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["projects"][0]["meetings_pending"]) == 2


def test_digest_without_a_rule_has_no_meetings_block(tmp_path):
    drive = _drive(tmp_path, rule=False)
    digest = collect(scan_drive(drive))
    assert "Meetings not closed out" not in render(digest)
    assert meeting_line(digest.projects[0]) is None
