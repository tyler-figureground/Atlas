"""The tree's non-writes: open, reveal, copy path (ticket 04's action set, #45).

`o` on a node opens it; an Unfiled node is revealed rather than opened, because
it is the one state that needs a person to look at it where it sits. `y` copies
a node's full path. None of these write, so none of them cross a Plan.
"""

from __future__ import annotations

import atlas.tui.app as tui_app
from atlas.tui.app import AtlasApp
from atlas.tui.layout import TREE
from atlas.tui.treeview import ProjectTreeView

from conftest import make_project


async def settle(app, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def project_with_files(drive):
    return make_project(drive, "260813_Files", sections=["01 Model", "Random Stuff"],
                        files={"CLAUDE.md": "x"})


def record(monkeypatch):
    calls = []
    monkeypatch.setattr(tui_app, "open_path", lambda path: calls.append(("open", path)))
    monkeypatch.setattr(tui_app, "reveal_path", lambda path: calls.append(("reveal", path)))
    return calls


async def in_tree_on(app, pilot, key):
    await settle(app, pilot)
    await pilot.press("enter")
    await settle(app, pilot)
    assert app._focus_region == TREE
    app.query_one(ProjectTreeView).select_key(key)
    await settle(app, pilot)


async def test_o_on_a_file_in_the_tree_opens_that_file(fixture_drive, monkeypatch):
    project = project_with_files(fixture_drive)
    calls = record(monkeypatch)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await in_tree_on(app, pilot, "CLAUDE.md")
        await pilot.press("o")
        await pilot.pause()

    assert calls == [("open", project / "CLAUDE.md")]


async def test_o_on_an_unfiled_node_reveals_it_rather_than_opening_it(fixture_drive, monkeypatch):
    project = project_with_files(fixture_drive)
    calls = record(monkeypatch)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await in_tree_on(app, pilot, "Random Stuff")
        await pilot.press("o")
        await pilot.pause()

    assert calls == [("reveal", project / "Random Stuff")]


async def test_y_copies_the_nodes_full_path(fixture_drive, monkeypatch):
    project = project_with_files(fixture_drive)
    record(monkeypatch)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await in_tree_on(app, pilot, "01 Model")
        await pilot.press("y")
        await pilot.pause()
        assert app.clipboard == str(project / "01 Model")
        assert "Copied" in app._operation_text


async def test_o_on_the_project_list_still_opens_the_project(fixture_drive, monkeypatch):
    project = project_with_files(fixture_drive)
    calls = record(monkeypatch)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("o")
        await pilot.pause()

    assert calls == [("open", project)]
