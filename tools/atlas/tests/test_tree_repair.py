"""The tree's write keys, end to end (ticket 23, ADR 0006 and 0007).

Real keys against a real widget through ``App.run_test``, on a fixture drive.
The rule these exercise lives in ``tui/repair.py`` and is tested purely there;
what is asserted here is that pressing a key on a node actually moves a folder,
that nothing moves before the confirm, and that the cursor follows what it
repaired.
"""

from __future__ import annotations

import pytest
from textual.widgets import Static

from atlas.tui.app import OPERATION_MARGIN, AtlasApp
from atlas.tui.treeview import ProjectTreeView

from conftest import make_project, write_map


async def settle(app: AtlasApp, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def drifted_project(drive):
    """One project with one thing wrong with it: a folder the map renames."""
    return make_project(drive, "260601_Drift", sections=["01 Model", "Meetings"],
                        files={"Meetings/kickoff.md": "z"})


async def open_tree_on(app, pilot, key: str):
    """Drill into the Tree Region and put the cursor on one Node Key."""
    await pilot.press("enter")
    await settle(app, pilot)
    app.query_one(ProjectTreeView).select_key(key)
    await settle(app, pilot)


def operation_text(app) -> str:
    return str(app.query_one("#operation", Static).content)


# ------------------------------------------------------------- the offer


async def test_the_repair_key_arms_a_confirm_and_writes_nothing_yet(fixture_drive):
    """Every write crosses a plan, previews, and confirms - no exceptions
    (ADR 0006). The preview is the point: arming must not touch the drive."""
    project = drifted_project(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await open_tree_on(app, pilot, "Meetings")
        await pilot.press("f")
        await settle(app, pilot)

        assert "Meetings" in operation_text(app)
        assert "11 Meetings" in operation_text(app)
        assert (project / "Meetings").is_dir(), "arming a repair must not write"
        assert not (project / "11 Meetings").exists()


async def test_confirming_the_repair_moves_the_folder(fixture_drive):
    project = drifted_project(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await open_tree_on(app, pilot, "Meetings")
        await pilot.press("f")
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)

        assert (project / "11 Meetings" / "kickoff.md").is_file()
        assert not (project / "Meetings").exists()


async def test_escape_abandons_an_armed_repair(fixture_drive):
    project = drifted_project(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await open_tree_on(app, pilot, "Meetings")
        await pilot.press("f")
        await settle(app, pilot)
        await pilot.press("escape")
        await settle(app, pilot)

        assert (project / "Meetings").is_dir()
        assert "Enter confirm" not in operation_text(app)


async def test_a_node_with_nothing_wrong_says_so_rather_than_going_quiet(fixture_drive):
    """A key that does nothing and says nothing is indistinguishable from a key
    that is broken."""
    drifted_project(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await open_tree_on(app, pilot, "01 Model")
        await pilot.press("f")
        await settle(app, pilot)

        assert "filed correctly" in operation_text(app)


# --------------------------------------------------------------- the undo


async def test_undo_puts_it_back(fixture_drive):
    project = drifted_project(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await open_tree_on(app, pilot, "Meetings")
        await pilot.press("f")
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        assert (project / "11 Meetings").is_dir()

        await pilot.press("u")
        await settle(app, pilot)

        assert (project / "Meetings" / "kickoff.md").is_file()
        assert not (project / "11 Meetings").exists()


async def test_undo_with_an_empty_stack_says_so(fixture_drive):
    drifted_project(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await open_tree_on(app, pilot, "Meetings")
        await pilot.press("u")
        await settle(app, pilot)

        assert "nothing to undo" in operation_text(app).lower()


async def test_the_confirm_is_not_clipped_by_the_operation_line_padding(fixture_drive):
    """Third time this repo has paid for the same arithmetic. `#operation` has
    `padding: 0 2`, so the line has four fewer columns than the terminal - the
    same correction ticket 17 needed for the wordmark. Passing the terminal width
    straight through clipped `Esc cancel` down to `Esc`, and a confirm whose
    cancel key is half-drawn is worse than no confirm at all."""
    drifted_project(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(46, 51)) as pilot:
        await settle(app, pilot)
        await open_tree_on(app, pilot, "Meetings")
        await pilot.press("f")
        await settle(app, pilot)

        line = operation_text(app)
        assert "Esc cancel" in line, line
        assert len(line) <= 46 - OPERATION_MARGIN, line


# ------------------------------------------- an armed repair and its context


def alpha_and_bravo(drive):
    """Two projects with the same drift, so a write to the wrong one is visible."""
    alpha = make_project(drive, "260601_Alpha", sections=["01 Model", "Meetings"],
                         files={"Meetings/a.md": "a"})
    bravo = make_project(drive, "260602_Bravo", sections=["01 Model", "Meetings"],
                         files={"Meetings/b.md": "b"})
    return alpha, bravo


async def arm_on_alpha(app, pilot):
    await settle(app, pilot)
    await open_tree_on(app, pilot, "Meetings")
    await pilot.press("f")
    await settle(app, pilot)
    assert "Enter confirm" in operation_text(app)


def untouched(*projects):
    return all((p / "Meetings").is_dir() and not (p / "11 Meetings").exists()
               for p in projects)


async def test_the_confirm_line_names_the_project(fixture_drive):
    """Issue #2. The confirm named a path, and every project has a Meetings."""
    alpha_and_bravo(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await arm_on_alpha(app, pilot)
        assert "260601_Alpha" in operation_text(app)


async def test_switching_project_disarms_the_repair(fixture_drive):
    """Issue #2. Arm in Alpha, move to Bravo, press Enter to open Bravo: that
    Enter renamed Alpha's folder."""
    alpha, bravo = alpha_and_bravo(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await arm_on_alpha(app, pilot)
        app._move_to_region("projects")
        await pilot.press("down")
        await settle(app, pilot)
        assert app._workspace_project == "260602_Bravo"
        assert "Enter confirm" not in operation_text(app)

        await pilot.press("enter")
        await settle(app, pilot)

        assert untouched(alpha, bravo)


async def test_a_refresh_disarms_the_repair(fixture_drive):
    alpha, bravo = alpha_and_bravo(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await arm_on_alpha(app, pilot)
        await pilot.press("r")
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)

        assert untouched(alpha, bravo)


async def test_opening_the_filter_disarms_the_repair(fixture_drive):
    alpha, bravo = alpha_and_bravo(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await arm_on_alpha(app, pilot)
        await pilot.press("slash")
        await pilot.press("B", "r", "a", "v", "o")
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)

        assert untouched(alpha, bravo)


async def test_a_modal_disarms_the_repair_behind_it(fixture_drive):
    alpha, bravo = alpha_and_bravo(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await arm_on_alpha(app, pilot)
        app.action_add_section()
        await settle(app, pilot)
        assert app.screen is not app.screen_stack[0], "the modal is up"
        app.action_drill()
        await settle(app, pilot)

        assert untouched(alpha, bravo)


async def test_escape_during_a_rescan_disarms_the_repair(fixture_drive):
    """Escape took the scan branch before the cancel, so the repair survived the
    trip to the drive picker and committed on the next Enter."""
    alpha, bravo = alpha_and_bravo(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await arm_on_alpha(app, pilot)
        app.action_refresh()
        app.action_back()
        await settle(app, pilot)
        app._open_drive(fixture_drive)
        await settle(app, pilot)
        await open_tree_on(app, pilot, "01 Model")
        await pilot.press("enter")
        await settle(app, pilot)

        assert app._armed is None
        assert untouched(alpha, bravo)


async def test_a_write_to_another_project_does_not_repaint_the_tree(fixture_drive):
    """Issue #3. Reconciling after a write pointed the widget at the written
    project's tree even when another project was on screen, so the Tree Region
    showed Alpha under Bravo's title and the next repair wrote to Bravo."""
    alpha, bravo = alpha_and_bravo(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await arm_on_alpha(app, pilot)
        armed = app._armed
        app._move_to_region("projects")
        await pilot.press("down")
        await settle(app, pilot)
        assert app._workspace_project == "260602_Bravo"

        app._apply_repair(armed.project, armed.plan, armed.guard, armed.node,
                          remember=True)
        await settle(app, pilot)

        assert (alpha / "11 Meetings").is_dir()
        view = app.query_one(ProjectTreeView)
        assert view.source.project == bravo, "Bravo's title, Bravo's tree"


async def test_the_repair_key_refuses_when_the_tree_is_not_the_selected_project(fixture_drive):
    """Issue #3's second half: the Plan is built for the list's project, the node
    comes from the widget. When they disagree, nothing is armed."""
    alpha, bravo = alpha_and_bravo(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await open_tree_on(app, pilot, "Meetings")
        alpha_tree = app._trees["260601_Alpha"]
        app._move_to_region("projects")
        await pilot.press("down")
        await settle(app, pilot)
        app._move_to_region("tree")
        view = app.query_one(ProjectTreeView)
        view.set_source(alpha_tree)
        await settle(app, pilot)
        view.select_key("Meetings")
        await settle(app, pilot)

        await pilot.press("f")
        await settle(app, pilot)

        assert app._armed is None
        await pilot.press("enter")
        await settle(app, pilot)
        assert untouched(alpha, bravo)


# ------------------------------------------------------ the drive switch


def two_drives(tmp_path):
    """The same project folder on two drives - an active and an archive copy."""
    drives = []
    for letter in ("A", "B"):
        drive = tmp_path / letter
        drive.mkdir()
        write_map(drive)
        drives.append(drive)
    make_project(drives[0], "260604_SameName", sections=["01 Model", "Meetings"],
                 files={"Meetings/a.md": "a"})
    make_project(drives[1], "260604_SameName", sections=["01 Model", "11 Meetings"],
                 files={"11 Meetings/b.md": "b"})
    return drives


async def test_undo_does_not_follow_the_operator_to_another_drive(tmp_path, monkeypatch):
    """Issue #8. The stack and the tree cache were keyed by project name and
    outlived a drive switch, so drive A's undo renamed drive B's folder."""
    drive_a, drive_b = two_drives(tmp_path)
    monkeypatch.setattr("atlas.tui.app.discover_drives", lambda: [drive_a, drive_b])
    app = AtlasApp(drive_a, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await open_tree_on(app, pilot, "Meetings")
        await pilot.press("f")
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        assert (drive_a / "260604_SameName" / "11 Meetings" / "a.md").is_file()

        app._show_drives(auto_open=False)
        await settle(app, pilot)
        app._open_drive(drive_b)
        await settle(app, pilot)

        view = app.query_one(ProjectTreeView)
        assert view.source is not None
        assert view.source.project == drive_b / "260604_SameName", "drive B's tree, not A's"

        await pilot.press("u")
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)

        assert "nothing to undo" in operation_text(app).lower()
        assert (drive_b / "260604_SameName" / "11 Meetings" / "b.md").is_file()
        assert not (drive_b / "260604_SameName" / "Meetings").exists()
