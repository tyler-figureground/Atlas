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
    OpsError,
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
    import os

    real_rename = os.rename

    def rename(src, dst):
        if os.path.basename(os.fspath(src)) == "Meetings":
            raise PermissionError(32, "The process cannot access the file", os.fspath(src))
        return real_rename(src, dst)

    monkeypatch.setattr(os, "rename", rename)
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


def test_broken_claude_markers_are_a_conflict_not_a_crash(fixture_drive):
    """#54: a hand-made CLAUDE.md with half an Atlas block and no AGENTS.md
    raised AgentsBlockError out of apply_plan."""
    from atlas.core.conform import CONFLICT
    from atlas.core.projectmd import AGENTS_BEGIN

    broken = "# House rules\n\n" + AGENTS_BEGIN + "\nhalf a block\n"
    project = make_project(fixture_drive, "260704_Broken", sections=["01 Model"],
                           files={"CLAUDE.md": broken})
    plan, inv, m = _plan(fixture_drive, "260704_Broken")
    result = apply_plan(fixture_drive, inv.path, m, plan)

    action = next(a for a in result.actions if a.dst == "AGENTS.md")
    assert action.status == CONFLICT
    assert "CLAUDE.md" in action.note
    assert not (project / "AGENTS.md").exists()
    assert (project / "CLAUDE.md").read_text(encoding="utf-8") == broken


def test_a_non_os_error_fails_that_action_and_the_rest_still_apply(fixture_drive, monkeypatch):
    """#54: OpsError (a file where a seeded folder belongs) escaped apply_plan."""
    import atlas.core.conform as conform
    from atlas.core.ops import OpsError

    project = make_project(fixture_drive, "260705_Ops", sections=["01 Model", "Meetings"],
                           files={"Meetings/kickoff.md": "z"})
    plan, inv, m = _plan(fixture_drive, "260705_Ops")
    real = conform._apply_backfill

    def backfill(project_path, m_, action):
        if action.dst == m_.decisions_dir:
            raise OpsError("cannot create folder; a file exists at decisions")
        return real(project_path, m_, action)

    monkeypatch.setattr(conform, "_apply_backfill", backfill)
    result = apply_plan(fixture_drive, inv.path, m, plan)

    from atlas.core.conform import CONFLICT

    stuck = [a for a in result.actions if a.status in (FAILED, CONFLICT)]
    assert [(a.dst, a.status) for a in stuck] == [(m.decisions_dir, CONFLICT)]
    assert "a file exists" in stuck[0].note
    assert (project / "11 Meetings" / "kickoff.md").is_file()


def test_cli_all_keeps_the_manifest_when_a_later_project_conflicts(fixture_drive, capsys):
    """#54: project A moved, project B crashed the loop, A's manifest was lost."""
    from atlas.core.projectmd import AGENTS_BEGIN

    make_project(fixture_drive, "260706_A", sections=["01 Model", "Meetings"],
                 files={"Meetings/kickoff.md": "z"})
    make_project(fixture_drive, "260707_B", sections=["01 Model"],
                 files={"CLAUDE.md": "# Rules\n\n" + AGENTS_BEGIN + "\nhalf\n"})

    status = main(["conform", "--drive", str(fixture_drive), "--all", "--apply", "--json"])

    payload = {p["project"]: p for p in json.loads(capsys.readouterr().out)}
    moved = [mv for a in payload["260706_A"]["actions"] for mv in a.get("moved", [])]
    assert any(mv["src"].startswith("Meetings") for mv in moved)
    b = next(a for a in payload["260707_B"]["actions"] if a["dst"] == "AGENTS.md")
    assert b["status"] == "conflict"
    assert status == 1


def test_unexpected_apply_error_propagates_and_logs_completed_actions(fixture_drive, monkeypatch):
    from atlas.core.conform import Action, Plan

    project = make_project(fixture_drive, "260713_Bug", sections=["Meetings"],
                           files={"Meetings/a.md": "keep"})
    m = scan_drive(fixture_drive).map
    plan = Plan(project=project.name, actions=(
        Action(kind="rename", src="Meetings", dst="11 Meetings"),
        Action(kind="sweep", src="a.txt", dst="target"),
    ))
    import os

    real = os.makedirs

    def mkdir(path, *args, **kwargs):
        if Path(path) == project / "target":
            raise RuntimeError("programming defect")
        return real(path, *args, **kwargs)

    (project / "a.txt").write_text("source", encoding="utf-8")
    monkeypatch.setattr(os, "makedirs", mkdir)
    with pytest.raises(RuntimeError, match="programming defect"):
        apply_plan(fixture_drive, project, m, plan)
    assert (project / "11 Meetings/a.md").read_text(encoding="utf-8") == "keep"
    assert "rename Meetings -> 11 Meetings" in _log_text(fixture_drive)


@pytest.mark.parametrize("error_type", [PermissionError, OpsError])
def test_failed_parent_creation_keeps_created_manifest(fixture_drive, monkeypatch, error_type):
    from atlas.core.conform import Action, Plan, action_to_dict, plan_from_dict

    project = make_project(fixture_drive, "260710_Parents")
    m = scan_drive(fixture_drive).map
    plan = Plan(project=project.name, actions=(
        Action(kind="backfill", src="", dst=m.analysis_dir),
        Action(kind="backfill", src="", dst=m.decisions_dir),
    ))
    real = Path.mkdir

    def mkdir(path, *args, **kwargs):
        if path == project / m.analysis_dir:
            real(path.parent, parents=True, exist_ok=True)
            raise error_type("injected child creation failure")
        return real(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", mkdir)
    result = apply_plan(fixture_drive, project, m, plan)
    assert result.actions[0].created == ("06 Research",)
    assert result.actions[0].status == (FAILED if error_type is PermissionError else "conflict")
    assert result.actions[1].status == DONE
    restored = plan_from_dict({"project": project.name,
                               "actions": [action_to_dict(a) for a in result.actions]})
    assert restored.actions[0].created == ("06 Research",)
    assert (project / "06 Research").is_dir()


@pytest.mark.parametrize("only", [None, "rename"])
def test_cli_all_records_a_vanished_project_and_keeps_going(fixture_drive, capsys, monkeypatch, only):
    """#54: apply_plan's 'project folder is no longer available' OpsError
    stopped the --all loop."""
    import atlas.cli as cli
    from atlas.core.ops import OpsError

    make_project(fixture_drive, "260708_A", sections=["01 Model", "Meetings"],
                 files={"Meetings/kickoff.md": "z"})
    make_project(fixture_drive, "260709_Gone", sections=["01 Model", "Meetings"],
                 files={"Meetings/kickoff.md": "z"})
    real = cli.apply_plan

    def apply(root, project, m, plan, only=None):
        if project.name == "260709_Gone":
            raise OpsError(f"project folder is no longer available: {project}")
        return real(root, project, m, plan, only=only)

    monkeypatch.setattr(cli, "apply_plan", apply)
    status = main(["conform", "--drive", str(fixture_drive), "--all", "--apply", "--json"]
                  + (["--only", only] if only else []))

    payload = {p["project"]: p for p in json.loads(capsys.readouterr().out)}
    assert any(a["status"] == "done" for a in payload["260708_A"]["actions"])
    gone = payload["260709_Gone"]["actions"]
    assert gone
    for action in gone:
        filtered = only and action["kind"] != only
        assert action["status"] == ("skipped" if filtered else "failed")
        if filtered:
            assert action["note"] == "filtered by --only"
    assert status == 2
