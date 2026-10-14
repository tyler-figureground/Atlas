"""The console keys for the archive verbs (ADR 0019).

Ticket 32 shipped `atlas archive` / `atlas unarchive` CLI-only; these are the
console surfaces. `A` archives the focused project; `U` enumerates the archive
root - on demand, never before - and un-archives a picked name. Confirmation is
ALWAYS the modal, even at one action: the recorded exception to ADR 0006's
inline-for-one-action rule. Applied plans go through ArchiveGuard.for_plan and
apply_archive_plan, and the rescan after apply is what drops (or restores) the
project-list row.

The per-Project undo stack (ticket 23) does not carry archives: it is keyed by
the selected list row and holds conform Plans inverted by conform's
invert_plan, and an applied archive removes its row on the rescan, so `u` has
nothing to select. ADR 0019's undo is the verb's own inverse - `U` runs the
inverse-shaped plan through the same Guard and apply machinery.
"""

from __future__ import annotations

from textual.widgets import Button, OptionList

from atlas.tui.app import ArchivePickerModal, AtlasApp, ConfirmListModal

from conftest import make_project


async def settle(app: AtlasApp, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def archivable(drive, name="260501_Alpha"):
    """A project carrying the two warnings the modal must show: a model file
    and an open task item."""
    return make_project(
        drive, name, sections=["01 Model", "00 Tasks"],
        files={
            "01 Model/house.rvt": "x",
            "00 Tasks/TASKS.md": "# Tasks\n\n- [ ] T-001 file the permit\n",
        },
    )


def modal_lines(app) -> str:
    assert isinstance(app.screen, ConfirmListModal)
    return "\n".join(app.screen._lines)


# ------------------------------------------------------------------ archive


async def test_A_archives_the_focused_project_after_the_modal(fixture_drive):
    archivable(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("A")
        await settle(app, pilot)

        assert isinstance(app.screen, ConfirmListModal)
        assert app._armed is None, "archive never arms the inline confirm (ADR 0019)"
        lines = modal_lines(app)
        assert "260501_Alpha -> _Archived Projects/260501_Alpha" in lines
        assert "Revit/CAD" in lines, "the model-file warning rides the modal"
        assert "open task item" in lines, "the open task items ride the modal"
        assert "prompt-vault" in lines, "the untouched note shows even with nothing to warn"

        app.screen.query_one("#ok", Button).focus()
        await pilot.press("enter")
        await settle(app, pilot)
        await settle(app, pilot)

    assert (fixture_drive / "_Archived Projects" / "260501_Alpha" / "01 Model" / "house.rvt").is_file()
    assert not (fixture_drive / "260501_Alpha").exists()
    assert [row.key for row in app._rows] == [], "the list drops the archived project"


async def test_escape_from_the_archive_modal_writes_nothing(fixture_drive):
    archivable(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("A")
        await settle(app, pilot)
        assert isinstance(app.screen, ConfirmListModal)
        await pilot.press("escape")
        await settle(app, pilot)

    assert (fixture_drive / "260501_Alpha").is_dir()
    assert not (fixture_drive / "_Archived Projects").exists()


async def test_a_taken_destination_refuses_on_the_operation_line(fixture_drive):
    archivable(fixture_drive)
    (fixture_drive / "_Archived Projects" / "260501_Alpha").mkdir(parents=True)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("A")
        await settle(app, pilot)
        assert not isinstance(app.screen, ConfirmListModal)
        assert "already taken" in app._operation_text

    assert (fixture_drive / "260501_Alpha").is_dir(), "a refused archive moves nothing"


async def test_A_is_inert_over_a_modal(fixture_drive):
    archivable(fixture_drive)
    make_project(fixture_drive, "260502_Bravo", sections=["Meetings"])
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("f")          # the conform modal for the focused project
        await settle(app, pilot)
        assert isinstance(app.screen, ConfirmListModal)
        await pilot.press("A")
        await settle(app, pilot)
        assert isinstance(app.screen, ConfirmListModal)
        assert "Archive" not in modal_lines(app), "A archived behind the modal"
    assert not (fixture_drive / "_Archived Projects").exists()


# ---------------------------------------------------------------- unarchive


async def test_U_lists_the_archive_root_on_demand_and_brings_one_back(fixture_drive):
    archivable(fixture_drive)
    archived = make_project(fixture_drive / "_Archived Projects", "260402_Old",
                            sections=["01 Model"], files={"01 Model/old.rvt": "y"})
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        assert [row.key for row in app._rows] == ["260501_Alpha"], \
            "archived projects never join the list"
        await pilot.press("U")
        await settle(app, pilot)
        assert isinstance(app.screen, ArchivePickerModal)
        options = app.screen.query_one(OptionList)
        assert options.option_count == 1

        await pilot.press("enter")      # pick the only archived project
        await settle(app, pilot)
        assert isinstance(app.screen, ConfirmListModal)
        lines = modal_lines(app)
        assert "_Archived Projects/260402_Old -> 260402_Old" in lines
        assert "prompt-vault" in lines

        app.screen.query_one("#ok", Button).focus()
        await pilot.press("enter")
        await settle(app, pilot)
        await settle(app, pilot)

    assert not archived.exists()
    assert (fixture_drive / "260402_Old" / "01 Model" / "old.rvt").is_file()
    assert not (fixture_drive / "_Archived Projects").exists(), \
        "an emptied archive root is pruned"
    assert {row.key for row in app._rows} == {"260501_Alpha", "260402_Old"}, \
        "the restored project rejoins the list"


async def test_U_with_nothing_archived_says_so(fixture_drive):
    archivable(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("U")
        await settle(app, pilot)
        assert not isinstance(app.screen, ArchivePickerModal)
        assert "Nothing is archived" in app._operation_text


async def test_escape_from_the_picker_writes_nothing(fixture_drive):
    make_project(fixture_drive / "_Archived Projects", "260402_Old", sections=["01 Model"])
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("U")
        await settle(app, pilot)
        assert isinstance(app.screen, ArchivePickerModal)
        await pilot.press("escape")
        await settle(app, pilot)

    assert (fixture_drive / "_Archived Projects" / "260402_Old").is_dir()
