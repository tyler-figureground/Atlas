"""Ticket 12's Drive latency budgets, and a scoped Guard that is actually
scoped (#46). The drive's numbers cannot be taken locally, so these assert the
work done - enumerations and walks - rather than milliseconds."""

from __future__ import annotations

import pytest

import atlas.core.conform as conform
import atlas.core.scan as scan
from atlas.core.conform import Guard, build_repair_plan
from atlas.core.doctor import report_project
from atlas.core.scan import PARTIAL, READ, list_entries, scan_drive
from atlas.core.tree import (
    CONCURRENCY_CAP,
    COUNT_CAP,
    LOADING_DELAY,
    PREFETCH_CAP,
    open_project_tree,
)

from conftest import make_project


def test_the_budgets_are_the_measured_ones():
    """docs/research/atlas-drive-latency-measurement.md, ticket 12."""
    assert LOADING_DELAY == 0.120
    assert PREFETCH_CAP == 50
    assert CONCURRENCY_CAP == 4
    assert COUNT_CAP == 500


def _count_walks(monkeypatch) -> list[str]:
    calls: list[str] = []
    real = scan.walk

    def counting(top, *args, **kwargs):
        calls.append(str(top))
        return real(top, *args, **kwargs)

    monkeypatch.setattr(scan, "walk", counting)
    monkeypatch.setattr(conform, "walk", counting)
    return calls


def _busy_project(drive):
    """One Drifted node, plus a relocation source with a subtree the Guard of
    that node has no business walking."""
    files = {"Meetings/kickoff.md": "z"}
    files.update({f"08 OUT/Invoices/{y}/INV-{i}.pdf": "x" for y in ("2024", "2025") for i in range(5)})
    return make_project(drive, "260920_Busy",
                        sections=["01 Model", "Meetings", "08 OUT/Invoices", "10 Legal"],
                        files=files)


def _armed(drive):
    inventory = scan_drive(drive)
    m = inventory.map
    inv = next(p for p in inventory.projects if p.name == "260920_Busy")
    plan = build_repair_plan(report_project(inv, m), m, "Meetings", project=inv.path)
    return m, plan


def test_the_scoped_guard_walks_nothing(fixture_drive, monkeypatch):
    """ADR 0006 promised the map plus two parent listings. The guard rebuilt a
    whole ProjectReport and Plan, walking every relocation source on the UI
    thread - three more times on commit."""
    _busy_project(fixture_drive)
    m, plan = _armed(fixture_drive)
    guard = Guard.for_action(fixture_drive, "260920_Busy", m, plan)

    walks = _count_walks(monkeypatch)
    assert guard.check(fixture_drive) is None
    assert walks == [], walks


def test_the_scoped_guard_still_refuses_changed_work(fixture_drive):
    project = _busy_project(fixture_drive)
    m, plan = _armed(fixture_drive)
    guard = Guard.for_action(fixture_drive, "260920_Busy", m, plan)

    (project / "Meetings").rename(project / "Meetings Old")
    assert guard.check(fixture_drive) is not None


def test_a_repair_plan_measures_only_its_own_action(fixture_drive, monkeypatch):
    project = _busy_project(fixture_drive)
    inventory = scan_drive(fixture_drive)
    m = inventory.map
    inv = next(p for p in inventory.projects if p.name == "260920_Busy")
    report = report_project(inv, m)

    walks = _count_walks(monkeypatch)
    plan = build_repair_plan(report, m, "Meetings", project=inv.path)

    assert plan.actions[0].path_length > 0
    assert all("Invoices" not in w for w in walks), walks


def test_a_listing_past_the_count_cap_is_partial(tmp_path):
    for i in range(7):
        (tmp_path / f"f{i}.txt").write_text("x", encoding="utf-8")

    capped = list_entries(tmp_path, limit=5)
    assert capped.state == PARTIAL
    assert len(capped) == 5
    assert list_entries(tmp_path, limit=7).state == READ
    assert list_entries(tmp_path).state == READ


def test_the_tree_caps_a_huge_folder_and_says_so(fixture_drive):
    project = make_project(fixture_drive, "260921_Huge", sections=["01 Model", "Dump"])
    for i in range(6):
        (project / "Dump" / f"{i}.txt").write_text("x", encoding="utf-8")
    inventory = scan_drive(fixture_drive)
    inv = next(p for p in inventory.projects if p.name == "260921_Huge")
    tree = open_project_tree(inv, inventory.map, report_project(inv, inventory.map),
                             count_cap=5)

    assert len(tree.children("Dump")) == 5
    dump = next(n for n in tree.children("") if n.key == "Dump")
    assert dump.load == PARTIAL


def test_expectations_never_call_a_child_missing_from_a_partial_listing(fixture_drive):
    project = make_project(fixture_drive, "260922_Many",
                           sections=["01 Model/01 Site Model", "01 Model/02 Design"])
    for i in range(6):
        (project / "01 Model" / f"a{i}").mkdir()
    inventory = scan_drive(fixture_drive)
    inv = next(p for p in inventory.projects if p.name == "260922_Many")
    tree = open_project_tree(inv, inventory.map, report_project(inv, inventory.map),
                             count_cap=3)

    paths = [e.path for e in tree.expectations()]
    assert not any(p.startswith("01 Model/") for p in paths), paths


async def test_the_loading_state_waits_for_a_slow_read(fixture_drive):
    """A warm read is ~0.5 ms; showing a spinner for it is a flicker. The state
    appears only once a load has run past LOADING_DELAY."""
    import threading

    from textual.app import App

    from atlas.tui.treeview import ProjectTreeView

    make_project(fixture_drive, "260923_Slow", sections=["01 Model"])
    inventory = scan_drive(fixture_drive)
    inv = next(p for p in inventory.projects if p.name == "260923_Slow")
    tree = open_project_tree(inv, inventory.map, report_project(inv, inventory.map))
    release = threading.Event()
    real_children = tree.children

    def slow_children(key=""):
        release.wait(5)
        return real_children(key)

    tree.children = slow_children

    class Host(App):
        def compose(self):
            yield ProjectTreeView()

    app = Host()
    async with app.run_test() as pilot:
        view = app.query_one(ProjectTreeView)
        view.set_source(tree)
        await pilot.pause()
        assert not view.loading, "not before the delay"
        await pilot.pause(LOADING_DELAY * 2)
        assert view.loading, "after the delay, a slow read says so"
        release.set()
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert not view.loading


def test_tree_loads_share_a_pool_capped_at_four():
    from atlas.tui import treeview

    assert treeview.LOAD_SLOTS._initial_value == CONCURRENCY_CAP


def test_the_project_guard_watches_the_root_the_preview_scanned(fixture_drive):
    """A change between the scan behind a preview and the confirm is caught,
    not only a change after the guard was built."""
    project = _busy_project(fixture_drive)
    inventory = scan_drive(fixture_drive)
    inv = next(p for p in inventory.projects if p.name == "260920_Busy")
    from atlas.core.conform import build_plan

    plan = build_plan(report_project(inv, inventory.map), inventory.map, project=inv.path)
    assert Guard.for_project(fixture_drive, inv.name, inventory.map, plan,
                             root_listing=inv.root_entries).check(fixture_drive) is None

    (project / "desktop.ini").write_text("x", encoding="utf-8")   # tolerated: no new work
    guard = Guard.for_project(fixture_drive, inv.name, inventory.map, plan,
                              root_listing=inv.root_entries)
    assert guard.check(fixture_drive) is not None


# ------------------------------------------ the UI thread stays free (#46)


async def _tree_app(drive, monkeypatch):
    import threading

    import atlas.tui.app as tui_app

    main_thread = threading.main_thread()
    seen: dict[str, bool] = {}

    def spy(name, real):
        def wrapped(*args, **kwargs):
            seen[name] = threading.current_thread() is main_thread
            return real(*args, **kwargs)
        return wrapped

    monkeypatch.setattr(tui_app, "build_repair_plan", spy("arm", tui_app.build_repair_plan))
    monkeypatch.setattr(tui_app, "apply_plan", spy("apply", tui_app.apply_plan))
    monkeypatch.setattr(Guard, "check", spy("check", Guard.check))
    return seen


async def test_arming_and_committing_a_repair_leave_the_ui_thread(fixture_drive, monkeypatch):
    from atlas.tui.app import AtlasApp
    from atlas.tui.treeview import ProjectTreeView

    project = make_project(fixture_drive, "260924_Thread", sections=["01 Model", "Meetings"],
                           files={"Meetings/kickoff.md": "z"})
    seen = await _tree_app(fixture_drive, monkeypatch)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async def settle(pilot):
        for _ in range(3):
            await app.workers.wait_for_complete()
            await pilot.pause()

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(pilot)
        await pilot.press("enter")
        await settle(pilot)
        app.query_one(ProjectTreeView).select_key("Meetings")
        await settle(pilot)
        await pilot.press("f")
        await settle(pilot)
        assert app._armed is not None
        await pilot.press("enter")
        await settle(pilot)

    assert (project / "11 Meetings" / "kickoff.md").is_file()
    assert seen == {"arm": False, "check": False, "apply": False}, seen


async def test_a_cancel_while_a_preview_is_building_drops_it(fixture_drive):
    from atlas.core.conform import Plan
    from atlas.tui.app import AtlasApp

    make_project(fixture_drive, "260925_Drop", sections=["01 Model", "Meetings"])
    app = AtlasApp(fixture_drive, follow_debounce=0)
    async with app.run_test(size=(120, 51)) as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        from atlas.core.conform import Action

        plan = Plan("260925_Drop", (Action(kind="rename", src="Meetings", dst="11 Meetings"),))
        generation = app._arm_generation
        app._cancel_repair()
        app._arm_ready(generation, app._workspace_project or "", plan, object(),
                       "Meetings", "Meetings", None)
        assert app._armed is None, "a stale preview never arms"
