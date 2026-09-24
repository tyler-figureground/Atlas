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
