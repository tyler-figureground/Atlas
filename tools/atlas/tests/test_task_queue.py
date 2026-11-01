"""The cross-project production queue (roadmap F5): states, the next task,
and the parser's prompt detection."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date

import pytest

from atlas.cli import main
from atlas.core.scan import scan_drive
from atlas.core.taskqueue import (
    BLOCKED,
    CLAIMED,
    DECISION,
    PARKED,
    PICKABLE,
    STALE,
    WAITING,
    classify,
    collect,
    next_task,
    revit_ready,
)
from atlas.core.tasks import parse_open

from conftest import make_project

TODAY = date(2026, 10, 31)

TASKS = """# Tasks

## In progress

- [ ] T-010 `AGENT` Draft the window schedule - claimed 2026-10-29 by pi
- [ ] T-011 `AGENT` Old claim nobody worked - claimed 2026-10-01 by codex

## Now

- [ ] T-001 `DECISION` Pick the siding.
- [ ] T-002 `AGENT` Price the siding options after:T-001 added:2026-10-01
- [ ] T-003 `AGENT` Collect the survey added:2026-10-20
- [ ] T-004 `AGENT` Write the parking memo added:2026-10-25
  ```text
  Read BRIEF.md, then:
  - [ ] not a task - quoted inside the prompt
  ```
- [ ] T-005 `MODEL` Tag the sections added:2026-09-01
- [ ] T-006 `WAIT` Engineer's calcs (Smith)

## Next

- [ ] T-007 `AGENT` Older but Next added:2026-01-01
- [ ] T-008 `AGENT` Waits on a closed task after:T-099

## Holds

- [ ] T-009 `AGENT` Held until the client signs

## Done

- [x] T-099 Closed earlier.
"""


def _states(text=TASKS, newest_run=None):
    return {i.id: (s, b) for i, s, b in classify(parse_open(text), TODAY, newest_run)}


# --- the parser ------------------------------------------------------------------

def test_prompt_detected_and_fenced_checkboxes_are_not_tasks():
    items = {i.id: i for i in parse_open(TASKS)}
    assert items["T-004"].prompt and not items["T-003"].prompt
    assert not any("quoted inside the prompt" in i.text for i in items.values())
    assert len(items) == 11
    assert items["T-010"].claimed_on == date(2026, 10, 29)
    assert items["T-003"].claimed_on is None


def test_a_prompt_belongs_to_the_line_above_it_only():
    text = "## Now\n\n- [ ] T-1 a\n\nSome note.\n  ```text\n  x\n  ```\n- [ ] T-2 b\n"
    assert [i.prompt for i in parse_open(text)] == [False, False]


@pytest.mark.parametrize("middle", [
    "```x``` is inline code, not a fence",                       # inline triple ticks
    "1. ```text\n   - [ ] q quoted\n   ```",                      # numbered-list fence
    "> ```\n> - [ ] q quoted\n```",                               # blockquote fence
    "  ```text\n  - [ ] T-9 unclosed fence, so this is a task",   # never closed
    "````text\n- [ ] q quoted\n```\nstill inside\n````",          # four ticks, inner ```
    "~~~\n- [ ] q quoted\n~~~",                                   # tildes
])
def test_no_fence_shape_can_swallow_the_tasks_after_it(middle):
    text = f"## Now\n\n- [ ] T-1 a\n{middle}\n- [ ] T-2 b\n\n## Next\n\n- [ ] T-3 c\n"
    ids = [i.id for i in parse_open(text)]
    assert ids[0] == "T-1" and ids[-2:] == ["T-2", "T-3"]
    assert not any("quoted" in i.text for i in parse_open(text))


def test_a_stray_indented_fence_ends_with_its_list_item():
    text = ("## Now\n- [ ] T-1 a\n  ```\n- [ ] T-2 b\n- [ ] T-3 c\n"
            "  ```text\n  p\n  ```\n- [ ] T-4 d\n")
    items = parse_open(text)
    assert [i.id for i in items] == ["T-1", "T-2", "T-3", "T-4"]
    assert [i.prompt for i in items] == [False, False, True, False]


def test_list_marker_closer_tilde_backticks_and_many_unclosed_openers():
    marker = "## Now\n- [ ] T-1 a\n  - ```text\n    - [ ] q\n  - ```\n- [ ] T-2 b\n"
    assert [(i.id, i.prompt) for i in parse_open(marker)] == [("T-1", True), ("T-2", False)]
    tilde = "## Now\n- [ ] T-1 a\n~~~text `x`\n- [ ] q\n~~~\n- [ ] T-2 b\n"
    assert [i.id for i in parse_open(tilde)] == ["T-1", "T-2"]
    many = "## Now\n" + "```\n" * 1 + "".join(f"```lang{i}\n" for i in range(5000)) + "- [ ] T-1 a\n"
    import time
    started = time.perf_counter()
    parse_open(many)
    assert time.perf_counter() - started < 2


def test_an_unclosed_fence_is_not_a_prompt():
    text = "## Now\n\n- [ ] T-1 a\n  ```text\n  do it\n\n## Next\n\n- [ ] T-2 b\n"
    items = parse_open(text)
    assert [i.id for i in items] == ["T-1", "T-2"] and not items[0].prompt


# --- states ----------------------------------------------------------------------

def test_every_state():
    states = _states()
    assert states["T-010"] == (CLAIMED, ())
    assert states["T-011"] == (STALE, ())
    assert states["T-001"] == (DECISION, ())
    assert states["T-002"] == (BLOCKED, ("T-001",))
    assert states["T-003"][0] == PICKABLE
    assert states["T-005"][0] == PICKABLE
    assert states["T-006"][0] == WAITING
    assert states["T-007"][0] == PICKABLE
    assert states["T-008"] == (PICKABLE, ())          # T-099 is done
    assert states["T-009"][0] == PARKED


def test_a_run_since_the_claim_keeps_it_fresh():
    assert _states(newest_run=date(2026, 10, 2))["T-011"][0] == CLAIMED
    assert _states(newest_run=date(2026, 9, 30))["T-011"][0] == STALE


def test_an_unreadable_runs_folder_never_makes_a_claim_stale():
    states = {i.id: s for i, s, _ in classify(parse_open(TASKS), TODAY, None, runs_known=False)}
    assert states["T-011"] == CLAIMED


def test_archived_run_zips_count_as_receipts(tmp_path):
    from atlas.core.taskqueue import project_queue
    project = make_project(tmp_path, "261001_A", files={
        "00 Tasks/TASKS.md": TASKS, ".agent/archive/261005-old-run.zip": "z"})
    (project / ".agent" / "runs").mkdir(parents=True)
    queue = project_queue("261001_A", project, ".agent/runs", "PROJECT.md", TODAY,
                          ".agent/archive")
    assert queue.newest_run == date(2026, 10, 5)
    assert {t.item.id: t.state for t in queue.tasks}["T-011"] == CLAIMED


def test_revit_ready_reads_only_a_named_model():
    blank = "---\nproject: x\nrevit:\n  model:\n  local:\n---\n# P\n"
    named = "---\nproject: x\nrevit:\n  model: 'C:/Models/x.rvt'  # central\n---\n"
    other = "---\nother:\n  model: x.rvt\nrevit:\n  model: null\n---\n"
    assert not revit_ready(blank) and revit_ready(named) and not revit_ready(other)
    assert not revit_ready("no front matter\nrevit:\n  model: x\n") and not revit_ready(None)
    assert revit_ready("---\nrevit:\n\n  model: a.rvt\n---\n")          # blank line inside
    assert not revit_ready("---\nrevit:\n  local: x\n    model: a.rvt\n---\n")   # nested
    assert not revit_ready("---\nrevit:\n  model: |\n    a.rvt\n---\n")  # block scalar
    assert revit_ready("---\r\nrevit:\r\n  model: a.rvt\r\n---\r\n")     # CRLF


# --- the next task -----------------------------------------------------------------

def _drive(tmp_path, *, revit=False, extra=None):
    drive = tmp_path / "TESTDRIVE"
    drive.mkdir(parents=True)
    from conftest import write_map
    write_map(drive)
    model = "'x.rvt'" if revit else ""
    make_project(drive, "261001_A", sections=["01 Model"], files={
        "00 Tasks/TASKS.md": TASKS,
        "PROJECT.md": f"---\nproject: a\nrevit:\n  model: {model}\n---\n",
    })
    for name, text in (extra or {}).items():
        make_project(drive, name, sections=["01 Model"], files={"00 Tasks/TASKS.md": text})
    return drive


def test_next_never_returns_blocked_claimed_decision_or_parked(tmp_path):
    queues = collect(scan_drive(_drive(tmp_path)), TODAY)
    task = next_task(queues, "AGENT", TODAY)
    # Now before Next; among Now, a prompt beats age: T-004 over older T-003.
    assert task.item.id == "T-004"
    assert next_task(queues, "AGENT", TODAY, with_prompt=True).item.id == "T-004"
    picked = []
    while (task := next_task(queues, "AGENT", TODAY)) is not None:
        picked.append(task.item.id)
        queues = tuple(replace(q, tasks=tuple(t for t in q.tasks if t is not task))
                       for q in queues)
    assert picked == ["T-004", "T-003", "T-007", "T-008"]


def test_due_beats_everything_but_section(tmp_path):
    other = "## Now\n\n- [ ] T-050 `AGENT` Due soon due:2026-11-02\n"
    queues = collect(scan_drive(_drive(tmp_path, extra={"261002_B": other})), TODAY)
    assert next_task(queues, "AGENT", TODAY).item.id == "T-050"


def test_model_work_only_where_the_dossier_names_a_model(tmp_path):
    assert next_task(collect(scan_drive(_drive(tmp_path)), TODAY), "MODEL", TODAY) is None
    ready = collect(scan_drive(_drive(tmp_path / "r", revit=True)), TODAY)
    assert next_task(ready, "MODEL", TODAY).item.id == "T-005"


# --- CLI -------------------------------------------------------------------------

def test_cli_lists_states_and_hides_parked_unless_all(tmp_path, capsys):
    drive = _drive(tmp_path)
    assert main(["tasks", "--drive", str(drive)]) == 0
    out = capsys.readouterr().out
    assert "[blocked    ] T-002 `AGENT` Price the siding options" in out
    assert "after T-001" in out and "(prompt)" in out
    assert "claimed 2026-10-01 by codex" in out and "T-009" not in out
    assert main(["tasks", "--drive", str(drive), "--all", "--lane", "AGENT"]) == 0
    out = capsys.readouterr().out
    assert "[parked     ] T-009" in out and "DECISION" not in out


def test_cli_next_json_and_exit_codes(tmp_path, capsys):
    drive = _drive(tmp_path)
    assert main(["tasks", "--drive", str(drive), "--next", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["id"] == "T-004" and data["state"] == PICKABLE and data["prompt"] is True
    assert data["tasks_file"].endswith("TASKS.md")
    assert main(["tasks", "--drive", str(drive), "--next", "--lane", "MODEL"]) == 1
    assert "no pickable MODEL task" in capsys.readouterr().out


def test_cli_json_names_missing_and_unreadable(tmp_path, capsys):
    drive = _drive(tmp_path)
    make_project(drive, "261003_C", sections=["01 Model"])
    broken = make_project(drive, "261004_D", sections=["01 Model"])
    (broken / "00 Tasks" / "TASKS.md").mkdir(parents=True)
    assert main(["tasks", "--drive", str(drive), "--json"]) == 0
    rows = {r["project"]: r for r in json.loads(capsys.readouterr().out)}
    assert rows["261003_C"]["tasks_present"] is False and rows["261003_C"]["tasks"] == []
    assert rows["261004_D"]["tasks_readable"] is False and rows["261004_D"]["error"]
    assert main(["tasks", "--drive", str(drive)]) == 0
    out, err = capsys.readouterr()
    assert "cannot read 00 Tasks/TASKS.md" in out and "1 project(s) unreadable" in out
    assert main(["tasks", "--drive", str(drive), "--next"]) == 0
    assert "warning: cannot read 261004_D" in capsys.readouterr().err


@pytest.mark.parametrize("args", [["--with-prompt"], ["--next", "--lane", "DECISION"],
                                  ["--next", "--lane", "WAIT"]])
def test_cli_refuses_flag_combinations_that_mean_nothing(tmp_path, capsys, args):
    assert main(["tasks", "--drive", str(_drive(tmp_path)), *args]) == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize("lane", ["AGENT", "MODEL"])
def test_next_with_no_drive_work_is_none(tmp_path, lane):
    drive = tmp_path / "EMPTY"
    drive.mkdir()
    from conftest import write_map
    write_map(drive)
    assert next_task(collect(scan_drive(drive), TODAY), lane, TODAY) is None
