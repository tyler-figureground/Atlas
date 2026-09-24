"""The MAX_PATH warning is ADR 0006's only safeguard, so it must never
under-report (#23): relative --drive, deep subtrees on a machine without
LongPathsEnabled, and undo were all measured short or not at all."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.conform import WINDOWS_MAX_PATH, build_plan, measure_plan
from atlas.core.doctor import report_project
from atlas.core.scan import long_path, scan_drive

from conftest import FIXTURE_MAP, make_project, write_map

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="MAX_PATH is a Windows limit")

LONG_A, LONG_B = "L" * 60, "M" * 60


def _refuse_unprefixed_long_paths(monkeypatch) -> None:
    """Studio machines without LongPathsEnabled refuse an unprefixed path at or
    past 260 characters (ticket 19). The dev machine has it enabled, so without
    this the prefix code is never exercised."""
    real = os.scandir

    def scandir(path="."):
        raw = os.fspath(path)
        if not raw.startswith("\\\\?\\") and len(os.path.abspath(raw)) >= WINDOWS_MAX_PATH:
            raise FileNotFoundError(3, "The system cannot find the path specified", raw)
        return real(path)

    monkeypatch.setattr(os, "scandir", scandir)


def _deep_project(drive: Path, name: str) -> tuple[Path, Path]:
    project = make_project(drive, name, sections=["01 Model", "08 OUT/Invoices", "10 Legal"])
    deep = project / "08 OUT" / "Invoices"
    for part in ("d" * 60, "e" * 60, "f" * 60):
        deep = deep / part
    os.makedirs(long_path(deep), exist_ok=True)
    leaf = deep / "invoice-for-the-client.pdf"
    Path(long_path(leaf)).write_text("x", encoding="utf-8")
    return project, leaf


@windows_only
def test_a_deep_subtree_is_measured_on_a_machine_without_long_paths(fixture_drive, monkeypatch):
    project, leaf = _deep_project(fixture_drive, "260901_Deep")
    assert len(str(project / "08 OUT" / "Invoices")) < 240, "the source itself is short"
    assert len(str(leaf)) > WINDOWS_MAX_PATH
    _refuse_unprefixed_long_paths(monkeypatch)

    inventory = scan_drive(fixture_drive)
    inv = next(p for p in inventory.projects if p.name == "260901_Deep")
    plan = build_plan(report_project(inv, inventory.map), inventory.map, project=inv.path)
    relocate = next(a for a in plan.actions if a.kind == "relocate")

    assert relocate.path_length >= len(str(leaf)) - len("08 OUT/Invoices") + len("10 Legal/Invoices")
    assert relocate.path_warning
    assert relocate.file_count == 1, "the file past 260 is counted, not skipped"


@windows_only
def test_long_path_measures_the_absolute_path_not_the_relative_string(tmp_path, monkeypatch):
    base = tmp_path / ("a" * 100) / ("b" * 100)
    os.makedirs(long_path(base), exist_ok=True)
    monkeypatch.chdir(long_path(base))
    relative = "c" * 41

    assert long_path(relative).startswith("\\\\?\\")


@windows_only
def test_long_path_leaves_device_paths_alone():
    assert long_path("\\\\.\\C:\\" + "x" * 250) == "\\\\.\\C:\\" + "x" * 250
    assert long_path("//?/C:/" + "x" * 250) == "//?/C:/" + "x" * 250


def test_a_relative_drive_is_measured_as_the_absolute_path(fixture_drive, capsys, monkeypatch):
    make_project(fixture_drive, "260902_Rel", sections=["01 Model", "Meetings"],
                 files={"Meetings/kickoff.md": "z"})
    monkeypatch.chdir(fixture_drive.parent)

    assert main(["conform", "--drive", fixture_drive.name, "--project", "260902_Rel",
                 "--json"]) == 1
    action = json.loads(capsys.readouterr().out)[0]["actions"]
    rename = next(a for a in action if a["kind"] == "rename")
    absolute = len(str(fixture_drive.resolve() / "260902_Rel" / "11 Meetings" / "kickoff.md"))
    assert rename["path_length"] >= absolute


def test_an_inverse_plan_is_measured(fixture_drive, tmp_path, capsys):
    """Undo moves things too, and can push them past the limit just as well."""
    project = make_project(fixture_drive, "260903_Undo", sections=["01 Model", "Meetings"],
                           files={"Meetings/kickoff.md": "z"})
    assert main(["conform", "--drive", str(fixture_drive), "--project", "260903_Undo",
                 "--node", "Meetings", "--apply", "--json"]) == 0
    manifest = tmp_path / "m.json"
    manifest.write_text(capsys.readouterr().out, encoding="utf-8")

    assert main(["conform", "--drive", str(fixture_drive), "--revert", str(manifest),
                 "--json"]) == 1
    action = json.loads(capsys.readouterr().out)[0]["actions"][0]
    assert action["path_length"] >= len(str(project / "Meetings" / "kickoff.md"))


def test_measure_plan_fills_every_length(fixture_drive):
    from atlas.core.conform import Action, Plan

    project = make_project(fixture_drive, "260904_M", sections=["Meetings"],
                           files={"Meetings/a.md": "z"})
    plan = Plan(project="260904_M", actions=(Action(kind="relocate", src="Meetings", dst="X/Y"),))
    measured = measure_plan(plan, project)
    assert measured.actions[0].path_length == len(str(project / "X/Y")) + len("/a.md")


def test_the_multi_action_preview_carries_the_warning():
    from atlas.core.conform import Action
    from atlas.tui.app import _path_warning

    assert _path_warning(Action(kind="relocate", src="a", dst="b", path_length=300)) == \
        "  [path 300 > 260]"
    assert _path_warning(Action(kind="relocate", src="a", dst="b", path_length=100)) == ""
