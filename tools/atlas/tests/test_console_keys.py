"""Keys and focus in the console, pressed rather than clicked.

Every test here presses the key an operator would press. The audit that found
these (2026-09) noted that modals were only ever confirmed with
``pilot.click("#ok")``, so no test had pressed Enter or Tab inside one - and the
App's priority bindings had been taking both keys away from every modal, the
filter box and the command palette.
"""

from __future__ import annotations

from textual.command import CommandPalette
from textual.widgets import Button, DataTable, Input

from atlas.tui.app import AtlasApp, ConfirmListModal, NewProjectModal
from atlas.tui.layout import HEALTH, PROJECT_LIST, TREE
from atlas.tui.treeview import ProjectTreeView

from conftest import make_project


async def settle(app: AtlasApp, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def drifted(drive):
    make_project(drive, "260813_Fixit", sections=["01 Model", "Meetings"],
                 files={"Meetings/kickoff.md": "x"})


def two_projects(drive):
    make_project(drive, "260501_Alpha", sections=["01 Model", "Meetings"],
                 files={"Meetings/k.md": "z"})
    make_project(drive, "260502_Bravo", sections=["01 Model"])


# ------------------------------------------------ priority keys and modals (#10)


async def test_tab_moves_focus_inside_the_conform_modal_not_behind_it(fixture_drive):
    drifted(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("f")
        await settle(app, pilot)
        assert isinstance(app.screen, ConfirmListModal)
        before = app.screen.focused

        await pilot.press("tab")
        await pilot.pause()
        assert app._focus_region == PROJECT_LIST, "Tab cycled the Regions behind the modal"
        assert app.screen.focused is not before
        assert isinstance(app.screen.focused, Button)


async def test_enter_on_the_focused_ok_button_applies_the_conform(fixture_drive):
    drifted(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("f")
        await settle(app, pilot)
        app.screen.query_one("#ok", Button).focus()
        await pilot.press("enter")
        await settle(app, pilot)

    assert (fixture_drive / "260813_Fixit" / "11 Meetings" / "kickoff.md").is_file()


async def test_tab_leaves_the_new_project_name_field(fixture_drive):
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("n")
        await settle(app, pilot)
        assert isinstance(app.screen, NewProjectModal)
        await pilot.press("tab")
        await pilot.press("1", "2")
        await pilot.pause()
        assert app.screen.query_one("#name", Input).value == ""
        assert app.screen.query_one("#street", Input).value == "12"


async def test_enter_in_the_filter_submits_rather_than_drills(fixture_drive):
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("slash", "b", "r", "a")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app._focus_region == PROJECT_LIST, "Enter drilled instead of submitting"
        assert isinstance(app.focused, DataTable)
        assert app.query_one("#projects", DataTable).row_count == 1


async def test_enter_in_the_command_palette_runs_the_command(fixture_drive):
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("ctrl+p")
        await settle(app, pilot)
        assert isinstance(app.screen, CommandPalette)
        await pilot.press(*"Project health")
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        assert not isinstance(app.screen, CommandPalette), "the palette stayed open"
        assert app._companion_mode == HEALTH
        assert app._focus_region == PROJECT_LIST, "Enter drilled the Region behind it"


async def test_enter_in_a_modal_never_commits_an_armed_repair(fixture_drive):
    drifted(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")          # into the tree
        await settle(app, pilot)
        tree = app.query_one(ProjectTreeView)
        tree.select_key("Meetings")
        await settle(app, pilot)
        await pilot.press("f")
        await pilot.pause()
        assert app._armed is not None
        await pilot.press("n")
        await settle(app, pilot)
        assert isinstance(app.screen, NewProjectModal)
        await pilot.press("enter")
        await settle(app, pilot)

    assert (fixture_drive / "260813_Fixit" / "Meetings").is_dir(), "the repair behind the modal ran"


# ------------------------------------------------ focus never lands hidden (#11)


async def test_refresh_from_the_tree_keeps_focus_on_the_tree(fixture_drive):
    """87 columns is Single-Region: the list is hidden while the tree is drawn.
    A rescan used to hand focus to the hidden list, and the next Down moved its
    cursor - silently swapping the tree on screen to another project."""
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(87, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        assert app._focus_region == TREE
        project = app._workspace_project

        await pilot.press("r")
        await settle(app, pilot)
        assert isinstance(app.focused, ProjectTreeView)
        await pilot.press("down")
        await settle(app, pilot)
        assert app._workspace_project == project


async def test_escape_out_of_the_filter_focuses_a_drawn_region(fixture_drive):
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(87, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        await pilot.press("slash")
        await pilot.pause()
        await pilot.press("escape")
        await settle(app, pilot)
        assert isinstance(app.focused, ProjectTreeView)
        assert app.query_one("#tree").display


async def test_collapse_and_zoom_are_inert_on_the_drive_picker(fixture_drive, monkeypatch):
    other = fixture_drive.parent / "OTHER"
    other.mkdir()
    monkeypatch.setattr("atlas.tui.app.discover_drives", lambda: [fixture_drive, other])
    app = AtlasApp(follow_debounce=0)

    async with app.run_test(size=(87, 51)) as pilot:
        await settle(app, pilot)
        drives = app.query_one("#drives")
        assert app.focused is drives
        for key in ("left_square_bracket", "right_square_bracket", "z"):
            await pilot.press(key)
            await pilot.pause()
            assert app.focused is drives, key
        before = drives.index
        await pilot.press("down")
        await pilot.pause()
        assert drives.index != before, "arrow keys stopped moving the drive list"
