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
