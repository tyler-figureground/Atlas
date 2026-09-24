"""An OS error mid-apply fails one action, not the process (#4).

What moved before the failure is recorded, logged, reported and undoable. The
Windows tests hold a real open handle - the studio's most common trigger is a
Revit, Excel or Word file left open inside the folder.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.conform import (
    DONE,
    FAILED,
    apply_plan,
    build_plan,
    build_repair_plan,
    invert_plan,
)
from atlas.core.doctor import report_project
from atlas.core.scan import scan_drive
from atlas.tui.app import AtlasApp

from conftest import make_project

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="Windows refuses to move an open file")


def _merge_project(drive: Path) -> Path:
    """Meetings merges into an existing 11 Meetings: two children, moved one by
    one, the second of which will be held open."""
    return make_project(
        drive, "260701_Open", sections=["01 Model", "11 Meetings", "Meetings"],
        files={"Meetings/a-agenda.md": "a", "Meetings/b-kickoff.md": "b"},
    )


def _log_text(drive: Path) -> str:
    logs = drive / "_tools" / "logs"
    return "".join(p.read_text(encoding="utf-8") for p in logs.glob("*.log")) if logs.is_dir() else ""


def _plan(drive: Path, name: str, node: str | None = None):
    inventory = scan_drive(drive)
    m = inventory.map
    inv = next(p for p in inventory.projects if p.name == name)
    report = report_project(inv, m)
    if node:
        return build_repair_plan(report, m, node, project=inv.path), inv, m
    return build_plan(report, m, project=inv.path), inv, m


@windows_only
def test_a_file_held_open_fails_that_action_and_keeps_what_moved(fixture_drive):
    project = _merge_project(fixture_drive)
    plan, inv, m = _plan(fixture_drive, "260701_Open", "Meetings")

    with open(project / "Meetings" / "b-kickoff.md", encoding="utf-8"):
        result = apply_plan(fixture_drive, inv.path, m, plan)

    action = result.actions[0]
    assert action.status == FAILED
    assert "b-kickoff.md" in action.note
    assert [(mv.src, mv.dst) for mv in action.moved] == [
        ("Meetings/a-agenda.md", "11 Meetings/a-agenda.md")]
    assert (project / "11 Meetings" / "a-agenda.md").is_file()
    assert "a-agenda.md" in _log_text(fixture_drive), "what moved is logged"

    # ...and undoable, once the file is closed.
    back = apply_plan(fixture_drive, inv.path, m, invert_plan(result))
    assert all(a.status == DONE for a in back.actions)
    assert (project / "Meetings" / "a-agenda.md").is_file()


def test_one_failed_action_does_not_stop_the_others(fixture_drive, monkeypatch):
    project = make_project(
        fixture_drive, "260702_Two", sections=["01 Model", "Meetings", "08 OUT/Invoices", "10 Legal"],
        files={"Meetings/kickoff.md": "z", "08 OUT/Invoices/INV-1.pdf": "z"},
    )
    plan, inv, m = _plan(fixture_drive, "260702_Two")
    real_rename = Path.rename

    def rename(self, target):
        if self.name == "Meetings":
            raise PermissionError(32, "The process cannot access the file", str(self))
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", rename)
    result = apply_plan(fixture_drive, inv.path, m, plan, only={"rename", "relocate"})

    by_kind = {a.kind: a for a in result.actions}
    assert by_kind["rename"].status == FAILED
    assert by_kind["relocate"].status == DONE
    assert (project / "10 Legal" / "Invoices" / "INV-1.pdf").is_file()
    assert "relocate 08 OUT/Invoices" in _log_text(fixture_drive)


@windows_only
def test_cli_reports_the_failure_as_json_and_exits_2(fixture_drive, capsys):
    project = _merge_project(fixture_drive)

    with open(project / "Meetings" / "b-kickoff.md", encoding="utf-8"):
        status = main(["conform", "--drive", str(fixture_drive), "--project", "260701_Open",
                       "--node", "Meetings", "--apply", "--json"])

    assert status == 2
    payload = json.loads(capsys.readouterr().out)
    action = payload[0]["actions"][0]
    assert action["status"] == "failed"
    assert action["moved"] == [{"src": "Meetings/a-agenda.md",
                                "dst": "11 Meetings/a-agenda.md", "is_dir": False}]


async def _settle(app, pilot):
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


async def _arm(app, pilot, key):
    from atlas.tui.treeview import ProjectTreeView

    await pilot.press("enter")
    await _settle(app, pilot)
    app.query_one(ProjectTreeView).select_key(key)
    await _settle(app, pilot)
    await pilot.press("f")
    await _settle(app, pilot)


def _operation(app) -> str:
    from textual.widgets import Static

    return str(app.query_one("#operation", Static).content)


@windows_only
async def test_the_console_reports_an_open_file_and_keeps_running(fixture_drive):
    project = _merge_project(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await _settle(app, pilot)
        await _arm(app, pilot, "Meetings")
        with open(project / "Meetings" / "b-kickoff.md", encoding="utf-8"):
            await pilot.press("enter")
            await _settle(app, pilot)
        assert app.is_running
        assert "b-kickoff.md" in _operation(app)
        assert (project / "11 Meetings" / "a-agenda.md").is_file()


async def test_a_map_caught_mid_save_does_not_crash_the_console(fixture_drive):
    """guard.check ran outside any handler, so invalid JSON on confirm exited
    the app."""
    make_project(fixture_drive, "260703_Drift", sections=["01 Model", "Meetings"],
                 files={"Meetings/kickoff.md": "z"})
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await _settle(app, pilot)
        await _arm(app, pilot, "Meetings")
        (fixture_drive / "_tools" / "testdrive-map.json").write_text("{half", encoding="utf-8")
        await pilot.press("enter")
        await _settle(app, pilot)
        assert app.is_running
        assert "Nothing moved" in _operation(app) or "stopped" in _operation(app)
        assert (fixture_drive / "260703_Drift" / "Meetings").is_dir()
