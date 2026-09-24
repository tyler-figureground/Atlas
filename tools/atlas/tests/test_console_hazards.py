"""Concurrency and control-flow hazards in the console, traced by the 2026-09
audit rather than reproduced by an operator (#52). Each test forces the
interleaving the code used to be unsafe under."""

from __future__ import annotations

from textual.app import App

import atlas.tui.app as tui_app
from atlas.core.doctor import report_project
from atlas.core.scan import scan_drive
from atlas.core.tree import open_project_tree
from atlas.tui.app import AtlasApp, ConfirmListModal
from atlas.tui.layout import TREE
from atlas.tui.treeview import ProjectTreeView

from conftest import make_project


async def settle(app, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def tree_for(drive, name):
    inventory = scan_drive(drive)
    inv = next(p for p in inventory.projects if p.name == name)
    return open_project_tree(inv, inventory.map, report_project(inv, inventory.map))


def test_invalidate_survives_a_listing_written_mid_iteration(fixture_drive):
    """Tree-load workers write the cache from a worker thread while the UI
    thread's invalidate iterates it. Simulated deterministically: a cached key
    whose comparison writes a new listing, as the worker would, mid-loop."""
    make_project(fixture_drive, "260813_Race", sections=["01 Model", "06 Research"])
    tree = tree_for(fixture_drive, "260813_Race")
    tree.children("")

    class Intruder(str):
        def startswith(self, prefix, *args):
            tree._listings["06 Research/late"] = tree._listings[""]
            return str.startswith(self, prefix, *args)

    tree._listings[Intruder("01 Model/x")] = tree._listings[""]
    tree.invalidate(["01 Model"])      # used to raise: dictionary changed size


class Harness(App):
    def __init__(self, source):
        super().__init__()
        self._source = source

    def compose(self):
        yield ProjectTreeView(id="tree")

    def on_mount(self):
        self.query_one(ProjectTreeView).set_source(self._source)


async def test_a_load_finished_for_the_previous_project_is_dropped(fixture_drive):
    make_project(fixture_drive, "260813_Old", sections=["01 Model"])
    make_project(fixture_drive, "260813_New", sections=["06 Research", "08 OUT"])
    old = tree_for(fixture_drive, "260813_Old")
    new = tree_for(fixture_drive, "260813_New")
    app = Harness(old)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        view = app.query_one(ProjectTreeView)
        view.set_source(new)
        # Loading shows after a short delay; the timer is the pending state.
        assert view.loading or view._loading_timer is not None
        view._loaded("", old)          # the old project's root read, landing late
        assert view.loading or view._loading_timer is not None, \
            "a stale load cleared the new project's loading state"
        assert [n.data for n in view.root.children] == []
        await settle(app, pilot)
        assert [n.data for n in view.root.children] == ["06 Research", "08 OUT"]


def drifted(drive):
    make_project(drive, "260813_Fixit", sections=["01 Model", "Meetings"],
                 files={"Meetings/kickoff.md": "x"})


async def test_a_multi_action_node_plan_opens_the_modal_instead_of_recursing(
        fixture_drive, monkeypatch):
    """Unreachable today - a node plan has one action - but the fallback to
    action_conform called _arm_repair again with the tree focused."""
    drifted(fixture_drive)
    monkeypatch.setattr(tui_app, "confirms_inline", lambda plan: False)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        app.query_one(ProjectTreeView).select_key("Meetings")
        await settle(app, pilot)
        await pilot.press("f")
        await settle(app, pilot)
        assert isinstance(app.screen, ConfirmListModal)


async def test_the_repair_key_says_the_tree_is_still_loading(fixture_drive):
    drifted(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        assert app._focus_region == TREE
        app._trees.clear()             # as while the debounced follow is pending
        await pilot.press("f")
        await pilot.pause()
        assert "loading" in app._operation_text.casefold()
