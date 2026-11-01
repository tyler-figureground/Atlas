"""Control-file budgets (roadmap F6): oversize control files and a Done
section due for pruning, as report-only deep-pass warnings."""

from __future__ import annotations

import copy
import json
from datetime import date

import pytest

from atlas.cli import main
from atlas.core.filebudget import check, line_count, scan_budgets, stale_done
from atlas.core.lintmap import lint_map
from atlas.core.mapfile import FileBudget, MapError, load_map

from conftest import FIXTURE_MAP, make_project, write_map

TODAY = date(2026, 10, 31)
PROJECT = "261002_1 Main St-Test"
BUDGETS = [
    {"file": "PROJECT.md", "maxLines": 5, "fix": "/project-dossier"},
    {"file": "BRIEF.md", "maxLines": 10, "fix": "rebuild the brief"},
    {"file": "00 Tasks/TASKS.md", "doneMaxAgeDays": 30, "fix": "/tasks prune"},
]

TASKS = """# Tasks

## Now

- [ ] T-009 `AGENT` Open item from 2026-08-01 - added:2026-08-01

## Done

<!-- Newest first. -->

- [x] T-008 Recent - done 2026-10-20.
- [x] 2026-09-29 - T-007 Exactly 32 days old.
- [x] T-006 Old one - done 2026-08-17. Evidence from 2026-10-30.
  - detail line dated 2026-01-01 is not an item
- [x] T-005 No date at all.

### Archived group

- [x] T-004 Older - closed 2026-07-04.

## Holds

- [x] T-003 Not in Done - 2026-01-01.
"""


def _map_with(**keys) -> dict:
    data = copy.deepcopy(FIXTURE_MAP)
    data.update(keys)
    return data


def test_line_count():
    assert line_count("") == 0
    assert line_count("a") == 1
    assert line_count("a\nb\n") == 2
    assert line_count("a\r\nb") == 2


def test_stale_done_reads_only_top_level_done_items_by_their_first_date():
    assert stale_done(TASKS, TODAY, 30) == [date(2026, 9, 29), date(2026, 8, 17),
                                            date(2026, 7, 4)]
    assert stale_done(TASKS, TODAY, 100) == [date(2026, 7, 4)]
    assert stale_done("# no done section\n- [x] 2020-01-01 x\n", TODAY, 30) == []
    # An H1 after Done ends it.
    assert stale_done("## Done\n- [x] 2026-01-01 a\n# Appendix\n- [x] 2026-01-02 b\n",
                      TODAY, 30) == [date(2026, 1, 1)]


def test_check_names_the_breach_and_the_fix():
    budget = FileBudget(file="00 Tasks/TASKS.md", fix="/tasks prune", done_max_age_days=30)
    [breach] = check(budget, TASKS, TODAY)
    assert breach.message == ("00 Tasks/TASKS.md Done holds 3 items older than 30 days, "
                              "oldest 2026-07-04 - /tasks prune")
    lines = FileBudget(file="PROJECT.md", fix="/project-dossier", max_lines=3)
    assert check(lines, "1\n2\n3\n", TODAY) == []
    [breach] = check(lines, "1\n2\n3\n4\n", TODAY)
    assert breach.message == "PROJECT.md is 4 lines (budget 3) - /project-dossier"


def test_scan_skips_absent_files_and_flags_only_the_oversize_one(tmp_path):
    project = make_project(tmp_path, PROJECT, files={
        "PROJECT.md": "\n".join(f"line {i}" for i in range(9)),
        "BRIEF.md": "short\n",
        # No TASKS.md: a missing control file is doctor's other finding.
    })
    m = load_map(write_map(tmp_path, _map_with(fileBudgets=BUDGETS)))
    scan = scan_budgets(project, m.file_budgets, TODAY)
    assert [(b.file, b.kind, b.value) for b in scan.breaches] == [("PROJECT.md", "lines", 9)]
    assert scan.unreadable == ()


def test_unreadable_file_is_reported_not_skipped(tmp_path):
    project = make_project(tmp_path, PROJECT)
    (project / "PROJECT.md").mkdir()   # a folder where the file should be
    budgets = (FileBudget(file="PROJECT.md", fix="x", max_lines=1),)
    scan = scan_budgets(project, budgets, TODAY)
    assert scan.breaches == () and len(scan.unreadable) == 1
    assert scan.unreadable[0].startswith("PROJECT.md  ")


@pytest.mark.parametrize("bad", [
    {"fileBudgets": {"file": "PROJECT.md"}},
    {"fileBudgets": [{"file": "PROJECT.md", "fix": "x"}]},
    {"fileBudgets": [{"file": "PROJECT.md", "maxLines": 400}]},
    {"fileBudgets": [{"file": "PROJECT.md", "fix": "x", "maxLines": -1}]},
    {"fileBudgets": [{"file": "C:/PROJECT.md", "fix": "x", "maxLines": 1}]},
    {"fileBudgets": [{"file": "PROJECT.md", "fix": "x", "maxLine": 1}]},
])
def test_a_malformed_budget_refuses_the_map(tmp_path, bad):
    with pytest.raises(MapError):
        load_map(write_map(tmp_path, _map_with(**bad)))


def test_lint_warns_on_a_duplicate_budget(tmp_path):
    twice = BUDGETS + [{"file": "project.md", "maxLines": 9, "fix": "x"}]
    m = load_map(write_map(tmp_path, _map_with(fileBudgets=twice)))
    assert [f.code for f in lint_map(m)] == ["DUP-BUDGET"]


def test_doctor_deep_warns_without_touching_status_or_exit(tmp_path, capsys):
    def drive(where, budgets):
        root = where / "TESTDRIVE"
        root.mkdir(parents=True)
        write_map(root, _map_with(fileBudgets=budgets) if budgets else FIXTURE_MAP)
        make_project(root, PROJECT, sections=["01 Model"], files={
            "PROJECT.md": "\n".join(f"line {i}" for i in range(9)),
            "00 Tasks/TASKS.md": TASKS,
        })
        return root

    with_budgets = drive(tmp_path / "a", BUDGETS)
    code = main(["doctor", "--drive", str(with_budgets), "--deep", PROJECT])
    out = capsys.readouterr().out
    assert "warning: PROJECT.md is 9 lines (budget 5) - /project-dossier" in out
    assert "warning: 00 Tasks/TASKS.md Done holds" in out
    assert main(["doctor", "--drive", str(with_budgets), "--deep", PROJECT, "--json"]) == code
    project = json.loads(capsys.readouterr().out)["projects"][0]
    assert [b["kind"] for b in project["budgets"]["breaches"]] == ["lines", "done"]

    plain = drive(tmp_path / "b", None)
    assert main(["doctor", "--drive", str(plain), "--deep", PROJECT, "--json"]) == code
    other = json.loads(capsys.readouterr().out)["projects"][0]
    assert other["status"] == project["status"] and other["budgets"] is None
