"""The deep pass beyond receipts (robustness plan 1.4-1.6).

One opt-in walk below a project root now gathers, in the same enumeration:
Receipt Rule hits (ticket 31), folders it could not open (1.5), paths already
over the length Win32 opens without the extended-length prefix (1.4), and the
project's item count against the shared-drive cap (1.6). The default doctor
pass stays root-only and reports none of it.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core import deep as deep_mod
from atlas.core.deep import OverlongPath, scan_deep
from atlas.core.doctor import report_drive
from atlas.core.mapfile import find_map, load_map
from atlas.core.scan import long_path, scan_drive

from conftest import agent_files, make_project

SECTIONS = ["01 Model", "06 Research", "08 OUT", "11 Meetings"]
CONTROL_PLANE = {
    "PROJECT.md": "---\nproject: x\n---\n",
    "decisions/README.md": "# Decisions\n",
    "06 Research/Code/.keep": "",
}


def conforming(drive: Path, name: str, files: dict[str, str] | None = None) -> Path:
    """A project doctor calls conform, so an exit code or status in a test
    comes from what the test added and nothing else."""
    return make_project(drive, name, sections=SECTIONS,
                        files={**CONTROL_PLANE, **agent_files(drive), **(files or {})})


def _long_tree(project: Path, *, floor: int) -> tuple[Path, int]:
    """Nest 60-char folder names until the absolute path crosses ``floor``,
    then add one more folder and a file inside it. Returns (deepest, length
    of the crossing folder's path). 60 keeps every component under the
    255-byte name limit on any platform."""
    current = project
    name = "backup-" + "x" * 52
    while len(os.path.abspath(str(current))) < floor:
        current = current / name
    crossing = current
    current = current / name
    os.makedirs(long_path(current))
    (current if sys.platform != "win32" else Path(long_path(current))).joinpath(
        "leaf.rvt").write_text("m", encoding="utf-8")
    return current, len(os.path.abspath(str(crossing)))


def _rm(path: Path) -> None:
    """rmtree that survives the over-long paths these tests create."""
    shutil.rmtree(long_path(path) if sys.platform == "win32" else path,
                  ignore_errors=True)


def _report(drive: Path, *, deep: frozenset[str] | None = None):
    return report_drive(scan_drive(drive), deep=deep)


# ---- 1.4: over-long paths -------------------------------------------------


def test_overlong_paths_are_found_and_named_with_their_length(fixture_drive):
    project = conforming(fixture_drive, "260950_Long")
    deepest, crossing_len = _long_tree(project / "01 Model", floor=259)
    try:
        scan = scan_deep(project, load_map(find_map(fixture_drive)))
        assert scan.overlong, "the crossing folder must be flagged"
        first = scan.overlong[0]
        assert isinstance(first, OverlongPath)
        assert first.length == crossing_len
        assert first.path.startswith("01 Model/backup-")
        # Only the first crossing per branch is named: everything below an
        # over-long folder is over-long by inheritance, and listing each child
        # is noise on the finding, not information.
        assert len(scan.overlong) == 1
    finally:
        _rm(project)


def test_the_dir_threshold_matches_the_measured_failure(fixture_drive):
    """A directory needs room for the enumeration suffix: the latency report's
    live failure is 259 chars, so 259 is flagged and 258 is not. Files warn
    past 260, the same bar conform's Path Length Warning uses."""
    project = conforming(fixture_drive, "260951_Boundary")
    base = len(os.path.abspath(str(project / "01 Model"))) + 1  # plus separator
    over = "d" * (259 - base)
    under = "s" * (258 - base)
    os.mkdir(long_path(project / "01 Model" / over))
    os.mkdir(long_path(project / "01 Model" / under))
    scan = scan_deep(project, load_map(find_map(fixture_drive)))
    flagged = {entry.path for entry in scan.overlong}
    assert f"01 Model/{over}" in flagged and f"01 Model/{under}" not in flagged


def test_overlong_is_a_warning_finding_that_never_changes_status(
        fixture_drive, capsys):
    project = conforming(fixture_drive, "260952_LongDoc")
    _deepest, crossing_len = _long_tree(project / "01 Model", floor=259)
    try:
        assert main(["doctor", "--drive", str(fixture_drive), "--deep",
                     "260952_LongDoc"]) == 1
        out = capsys.readouterr().out
        [line] = [ln for ln in out.splitlines() if "over-long path" in ln]
        assert "backup-" in line and str(crossing_len) in line
        # Atlas cannot shorten a path for a person: the project stays conform
        # beside the finding, the way it does next to an unreadable folder.
        report = _report(fixture_drive, deep=frozenset({"260952_LongDoc"}))
        assert report.projects[0].status == "conform"
        assert report.projects[0].overlong
    finally:
        _rm(project)


def test_overlong_reaches_json_and_the_default_pass_stays_root_only(
        fixture_drive, capsys):
    project = conforming(fixture_drive, "260953_LongJson")
    _long_tree(project / "01 Model", floor=259)
    try:
        assert main(["doctor", "--drive", str(fixture_drive), "--deep",
                     "260953_LongJson", "--json"]) == 1
        (proj,) = json.loads(capsys.readouterr().out)["projects"]
        assert proj["overlong"][0]["length"] >= 259
        assert proj["overlong"][0]["path"].startswith("01 Model/backup-")

        assert main(["doctor", "--drive", str(fixture_drive), "--json"]) == 0
        (proj,) = json.loads(capsys.readouterr().out)["projects"]
        assert proj["overlong"] == []
    finally:
        _rm(project)


# ---- 1.5: deep unreadable folders -----------------------------------------


def _deny_scandir(monkeypatch, suffix: str):
    real = os.scandir

    def scandir(path):
        if str(path).endswith(suffix):
            raise PermissionError(13, "Access is denied", str(path))
        return real(path)

    monkeypatch.setattr(os, "scandir", scandir)


def test_deep_unreadable_is_its_own_finding_without_receipt_rules(
        fixture_drive, monkeypatch, capsys):
    """The walk runs with no receiptRules in the map: a deep unreadable folder
    surfaces even on a map that never opted into Receipt Rules."""
    conforming(fixture_drive, "260954_Denied",
               files={"06 Research/Vault/secret.txt": "s"})
    _deny_scandir(monkeypatch, "Vault")

    assert main(["doctor", "--drive", str(fixture_drive), "--deep",
                 "260954_Denied"]) == 1
    out = capsys.readouterr().out
    assert "cannot read (deep): 06 Research/Vault" in out
    # Its own line, never bundled into the sweep counts.
    assert "sweep" not in out


def test_deep_unreadable_reaches_json_separately(fixture_drive, monkeypatch, capsys):
    conforming(fixture_drive, "260955_DeniedJson",
               files={"06 Research/Vault/secret.txt": "s"})
    _deny_scandir(monkeypatch, "Vault")

    assert main(["doctor", "--drive", str(fixture_drive), "--deep",
                 "260955_DeniedJson", "--json"]) == 1
    (proj,) = json.loads(capsys.readouterr().out)["projects"]
    assert any("06 Research/Vault" in line for line in proj["unreadable_deep"])
    assert proj["unreadable"] == []  # the root itself read fine
    assert proj["sweeps"] == [] and proj["receipts"] == []


# ---- 1.6: the drive item budget -------------------------------------------

# A conforming fixture project holds, exactly: folders 01 Model, 06 Research,
# 06 Research/Code, 08 OUT, 11 Meetings, decisions (6); files PROJECT.md,
# AGENTS.md, CLAUDE.md, decisions/README.md, 06 Research/Code/.keep (5).
CONFORMING_ITEMS = {"files": 5, "folders": 6, "total": 11}


def test_items_count_files_and_folders_and_ride_the_deep_flag(
        fixture_drive, capsys):
    conforming(fixture_drive, "260956_Items")

    assert main(["doctor", "--drive", str(fixture_drive), "--deep", "--all",
                 "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    (proj,) = out["projects"]
    assert proj["items"] == CONFORMING_ITEMS
    budget = out["budget"]
    assert budget["cap"] == 400_000
    assert budget["counted"] is True
    assert budget["total_items"] == 11
    assert budget["percent_of_cap"] == pytest.approx(11 / 400_000 * 100)

    # The default pass never pays the walk: items are null, never a zero.
    assert main(["doctor", "--drive", str(fixture_drive), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["projects"][0]["items"] is None
    assert out["budget"]["counted"] is False
    assert out["budget"]["total_items"] is None
    assert out["budget"]["cap"] == 400_000  # the cap itself is a fact either way


def test_the_agent_workspace_is_counted(fixture_drive, capsys):
    """Run volume is what eats the cap (ADR 0011); pruning the workspace out
    of the count would hide exactly what the budget watches."""
    conforming(fixture_drive, "260957_Workspace",
               files={".agent/runs/251001-a/notes.zip": "z",
                      ".agent/runs/251002-b/run.md": "r"})

    assert main(["doctor", "--drive", str(fixture_drive), "--deep", "--all",
                 "--json"]) == 0
    (proj,) = json.loads(capsys.readouterr().out)["projects"]
    # .agent, runs and the two run folders join the conforming six.
    assert proj["items"] == {"files": 7, "folders": 10, "total": 17}


def test_budget_text_line_prints_only_over_half_the_cap(
        fixture_drive, monkeypatch, capsys):
    conforming(fixture_drive, "260958_Budget")
    monkeypatch.setattr(deep_mod, "DRIVE_ITEM_CAP", 20)  # 11 items = 55% of 20

    assert main(["doctor", "--drive", str(fixture_drive), "--deep", "--all"]) == 0
    out = capsys.readouterr().out
    [line] = [ln for ln in out.splitlines() if "shared-drive item cap" in ln]
    assert "11" in line and "20" in line and "55%" in line

    monkeypatch.setattr(deep_mod, "DRIVE_ITEM_CAP", 400_000)
    assert main(["doctor", "--drive", str(fixture_drive), "--deep", "--all"]) == 0
    assert "item cap" not in capsys.readouterr().out

    # Never in the default pass, whatever the count would be.
    monkeypatch.setattr(deep_mod, "DRIVE_ITEM_CAP", 20)
    assert main(["doctor", "--drive", str(fixture_drive)]) == 0
    assert "item cap" not in capsys.readouterr().out


# ---- the depth guard -------------------------------------------------------


def test_the_depth_guard_bounds_the_walk_and_says_so(
        fixture_drive, monkeypatch, capsys):
    project = conforming(fixture_drive, "260959_Deep",
                         files={"01 Model/a/b/c/d/leaf.txt": "x"})
    monkeypatch.setattr(deep_mod, "DEEP_MAX_DEPTH", 2)

    scan = scan_deep(project, load_map(find_map(fixture_drive)))
    # Root is depth 0: 01 Model is 1, a is 2 - the boundary, never descended.
    # The conforming project's own depth-2 folder (06 Research/Code) trips the
    # same guard.
    assert set(scan.depth_capped) == {"01 Model/a", "06 Research/Code"}
    # The six conforming folders plus "a"; b/c/d are never seen.
    assert scan.items.folders == 7

    assert main(["doctor", "--drive", str(fixture_drive), "--deep",
                 "260959_Deep", "--json"]) == 1
    (proj,) = json.loads(capsys.readouterr().out)["projects"]
    assert sorted(proj["depth_capped"]) == ["01 Model/a", "06 Research/Code"]
