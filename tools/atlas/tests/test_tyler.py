"""Tyler digest (ADR 0016): errands from TYLER.md, blockers from the DECISION lane."""

from __future__ import annotations

import json
from pathlib import Path

from atlas.cli import main
from atlas.core.scan import scan_drive
from atlas.core.tyler import collect, digest_path, render

TYLER_MD = """---
project: "261002_1 Main St-Test"
updated: 2026-10-05
---

# Tyler's list - Test

## Now

- [ ] Y-002 Call the structural engineer about the beam - from 261004 minutes.
- [ ] Y-003 Email the survey to the lender. ready: 08 OUT/Drafts/261005_survey.md
- [x] Y-001 Sent the fee proposal.

## Next

- [ ] Y-004 Sign the consultant agreement when it arrives.

## Done

- [x] Y-000 2026-09-30 kicked off.
"""

TASKS_MD = """# Tasks - Test

## In progress

- [ ] T-010 `MODEL` Repair the A501 schedules - claimed 2026-10-04 by pi

## Now

- [ ] T-011 `DECISION` Choose the stair nosing profile - done when picked.
- [ ] T-012 `AGENT` Research the egress width - done when cited.
- [ ] T-013 `WAIT` Structural engineer: beam size.

## Next

- [ ] T-014 `DECISION` Approve the allowance basis.

## Done

- [x] T-001 `DECISION` Old settled call.
"""


def _project(drive: Path, name: str, *, tyler: str | None, tasks: str | None) -> Path:
    tasks_dir = drive / name / "00 Tasks"
    tasks_dir.mkdir(parents=True)
    if tyler is not None:
        (tasks_dir / "TYLER.md").write_text(tyler, encoding="utf-8")
    if tasks is not None:
        (tasks_dir / "TASKS.md").write_text(tasks, encoding="utf-8")
    return drive / name


def test_collect_errands_and_decisions(fixture_drive):
    _project(fixture_drive, "261002_1 Main St-Test", tyler=TYLER_MD, tasks=TASKS_MD)
    _project(fixture_drive, "261003_2 Oak Ave-Empty", tyler=None, tasks=None)
    digest = collect(scan_drive(fixture_drive))
    assert digest.errand_count == 3  # Y-002, Y-003, Y-004; checked and Done excluded
    assert digest.decision_count == 2  # T-011, T-014; MODEL/AGENT/WAIT/Done excluded
    full, empty = digest.projects
    assert [i.id for i in full.errands] == ["Y-002", "Y-003", "Y-004"]
    assert full.errands[1].section == "Now" and full.errands[2].section == "Next"
    assert [i.id for i in full.decisions] == ["T-011", "T-014"]
    assert empty.tyler_missing and empty.tasks_missing


def test_render_marks_missing_lists_and_sections(fixture_drive):
    _project(fixture_drive, "261002_1 Main St-Test", tyler=TYLER_MD, tasks=TASKS_MD)
    _project(fixture_drive, "261003_2 Oak Ave-Empty", tyler=None, tasks=None)
    text = render(collect(scan_drive(fixture_drive)))
    assert "Never edit this file" in text
    assert "3 errands / 2 decisions" in text
    assert "Y-002 Call the structural engineer" in text
    assert "Blocked on your call:" in text and "T-011" in text
    assert "TYLER.md missing - run conform" in text
    assert "Y-001" not in text  # checked off


def test_cli_prints_and_writes(fixture_drive, capsys):
    _project(fixture_drive, "261002_1 Main St-Test", tyler=TYLER_MD, tasks=TASKS_MD)
    assert main(["tyler", "--drive", str(fixture_drive)]) == 0
    out = capsys.readouterr().out
    assert "Tyler today" in out and "Y-002" in out
    assert not digest_path(fixture_drive).exists()  # read-only by default
    assert main(["tyler", "--drive", str(fixture_drive), "--write"]) == 0
    digest = digest_path(fixture_drive)
    assert digest.exists() and "Y-002" in digest.read_text(encoding="utf-8")
    capsys.readouterr()
    assert main(["tyler", "--drive", str(fixture_drive), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["errands"] == 3 and data["decisions"] == 2


# --- Action Queue (roadmap F1) and Blocks (F2) --------------------------------

from datetime import date  # noqa: E402

from atlas.core.tyler import QUEUE_CAPS, build_queue  # noqa: E402

TODAY = date(2026, 10, 31)

QUEUE_TYLER = """## Now

- [ ] Y-001 Send the fee letter. ready: 07 Correspondence/_Outbox/261020_fee.md
- [ ] Y-002 Call the engineer - added:2026-09-01
- [ ] Y-003 Sign the permit form - due:2026-10-28 added:2026-10-25
- [ ] Y-004 Book the survey - due:2026-11-20
- [ ] Y-005 Undated errand.
- [ ] Y-006 Send the lender pack - due:2026-11-02 ready: 07 Correspondence/_Outbox/x.md
"""

QUEUE_TASKS = """## Now

- [ ] T-011 `DECISION` Pick the window supplier - added:2026-10-10
- [ ] T-012 `AGENT` Draft the window schedule - after:T-011
- [ ] T-013 `MODEL` Place the windows - after:T-011
- [ ] T-014 `DECISION` Approve the allowance basis.
- [ ] T-015 `MODEL` Price the allowance - after:T-014
- [ ] T-016 `DECISION` Choose the nosing profile.
"""

BARE_TASKS = """## Now

- [ ] T-021 `DECISION` Confirm the wind speed.
- [ ] T-022 `MODEL` Print G000.
"""


def _queue(fixture_drive):
    _project(fixture_drive, "261002_1 Main St-Test", tyler=QUEUE_TYLER, tasks=QUEUE_TASKS)
    _project(fixture_drive, "261003_2 Oak Ave-Bare", tyler="## Now\n", tasks=BARE_TASKS)
    return collect(scan_drive(fixture_drive))


def test_queue_send_now_first_and_no_item_twice(fixture_drive):
    queue = build_queue(_queue(fixture_drive), TODAY)
    assert [e.item.id for e in queue.send_now.entries] == ["Y-001", "Y-006"]
    shown = [(e.project, e.item.id) for s in queue.sections for e in s.entries]
    assert len(shown) == len(set(shown))  # Y-006 is ready and due: listed once, under Send now


def test_queue_decisions_ranked_by_what_they_block(fixture_drive):
    queue = build_queue(_queue(fixture_drive), TODAY)
    decide = [(e.item.id, e.blocks) for e in queue.decide.entries]
    # Main St uses after:, so a decision nothing names blocks 0 there. Oak Ave never
    # writes after:, so its decision blocks an unknown number - never a made-up 0.
    assert decide == [("T-011", 2), ("T-014", 1), ("T-021", None), ("T-016", 0)]


def test_queue_due_soonest_first_with_overdue_flag(fixture_drive):
    queue = build_queue(_queue(fixture_drive), TODAY)
    assert [e.item.id for e in queue.due.entries] == ["Y-003", "Y-004"]
    assert queue.due.entries[0].overdue and not queue.due.entries[1].overdue


def test_queue_oldest_only_dated_items(fixture_drive):
    queue = build_queue(_queue(fixture_drive), TODAY)
    assert [(e.item.id, e.age) for e in queue.oldest.entries] == [("Y-002", 60)]


def test_queue_caps_and_overflow(fixture_drive):
    many = "## Now\n" + "".join(
        f"- [ ] Y-{n:03d} Send item {n}. ready: 07 Correspondence/_Outbox/2610{n:02d}_x.md\n"
        for n in range(1, 10))
    _project(fixture_drive, "261002_1 Main St-Test", tyler=many, tasks="## Now\n")
    queue = build_queue(collect(scan_drive(fixture_drive)), TODAY)
    assert len(queue.send_now.entries) == QUEUE_CAPS["send_now"]
    assert queue.send_now.total == 9
    assert queue.send_now.entries[0].item.id == "Y-001"  # oldest source first
    assert sum(QUEUE_CAPS.values()) == 15


def test_render_puts_the_queue_on_top(fixture_drive):
    text = render(_queue(fixture_drive), generated=TODAY)
    queue_at = text.index("## Action queue")
    assert queue_at < text.index("## 261002_1 Main St-Test")
    assert "**Send now** (2)" in text
    assert "T-011" in text and "blocks 2" in text and "blocks ?" in text
    assert "OVERDUE 3d" in text
    assert "Age known for 3 of 6 errands" in text
    assert "Errands by project: 1 Main St 6" in text
    assert "- [ ] **1 Main St** (blocks 2, 21d old) T-011" in text
    # Per-project detail stays below, unchanged in shape.
    assert "**Blocked on your call:**" in text


def test_render_empty_queue_says_so(fixture_drive):
    _project(fixture_drive, "261002_1 Main St-Test", tyler="## Now\n", tasks="## Now\n")
    text = render(collect(scan_drive(fixture_drive)), generated=TODAY)
    assert "Nothing queued" in text


def test_cli_json_carries_the_queue(fixture_drive, capsys):
    _queue(fixture_drive)
    assert main(["tyler", "--drive", str(fixture_drive), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    sections = {s["name"]: s for s in data["queue"]}
    assert [e["id"] for e in sections["send_now"]["entries"]] == ["Y-001", "Y-006"]
    assert sections["decide"]["entries"][0]["blocks"] == 2
    assert sections["decide"]["entries"][2]["blocks"] is None
    first = data["projects"][0]["errands"][0]
    assert first["ready"] and first["added"] is None  # dates as ISO strings or null


def test_short_name_keeps_street_numbers():
    from atlas.core.tyler import short_name
    assert short_name("260301_80-23 64th Lane-Refactored Design") == "80-23 64th Lane"
    assert short_name("260717_2267 Monticello - Mkean Residence-Addition") == "2267 Monticello"
    assert short_name("260527_211 centre street ny-Montez Radio (MPR)") == "211 centre street ny"
    assert short_name("21042 Entrada Rd") == "21042 Entrada Rd"


def test_queue_item_belongs_to_one_section_and_overdue_everywhere(fixture_drive):
    tyler = "## Now\n" + "".join(
        f"- [ ] Y-{n:03d} Send item {n}. ready: 07 Correspondence/_Outbox/2610{n:02d}_x.md\n"
        for n in range(1, 7)) + "- [ ] Y-020 Overdue send - due:2026-10-20 ready: 07 Correspondence/_Outbox/x.md\n"
    tasks = "## Now\n- [ ] T-007 `DECISION` Pick it - due:2026-10-29\n- [ ] T-008 `MODEL` Do it - after:T-7\n"
    _project(fixture_drive, "261002_1 Main St-Test", tyler=tyler, tasks=tasks)
    queue = build_queue(collect(scan_drive(fixture_drive)), TODAY)
    assert queue.send_now.total == 7 and queue.oldest.total == 0  # ready errands never fall into Oldest
    assert queue.due.total == 0  # due items already claimed by Send now / Decide
    assert all(e.overdue for e in queue.send_now.entries if e.item.id == "Y-020")
    assert queue.decide.entries[0].overdue and queue.decide.entries[0].blocks == 1
