"""The Companion Region's unmet Expectations: what they say, and what `f` does
with one (ADR 0004, 0006, 0007)."""

from __future__ import annotations

from textual.widgets import OptionList, Static

from atlas.core.doctor import report_project
from atlas.core.scan import scan_drive
from atlas.core.tree import CONTRACT, open_project_tree
from atlas.tui.app import AtlasApp
from atlas.tui.layout import COMPANION
from atlas.tui.repair import repair_offer

from conftest import agent_files, make_project


async def settle(app: AtlasApp, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def tree_for(drive, name):
    inventory = scan_drive(drive)
    inv = next(p for p in inventory.projects if p.name == name)
    return open_project_tree(inv, inventory.map, report_project(inv, inventory.map))


# ------------------------------------ present but without the contract (#58)


def test_a_project_md_without_front_matter_is_not_listed_as_missing(fixture_drive):
    """ADR 0004: an unmet Expectation is something absent from disk. A
    PROJECT.md that is there but lacks its front matter is a different fact,
    and backfill leaves it unchanged as a conflict - so no repair is offered."""
    make_project(fixture_drive, "260813_Prose", sections=["01 Model"],
                 files={"PROJECT.md": "# Just prose\n", **agent_files(fixture_drive)})
    tree = tree_for(fixture_drive, "260813_Prose")

    by_path = {e.path: e for e in tree.expectations()}
    project_md = by_path["PROJECT.md"]
    assert project_md.kind == CONTRACT
    assert not project_md.repairable
    offer = repair_offer(project_md)
    assert not offer.repairable
    assert "front matter" in offer.reason


def test_an_absent_project_md_is_still_a_backfill(fixture_drive):
    make_project(fixture_drive, "260813_Bare", sections=["01 Model"])
    tree = tree_for(fixture_drive, "260813_Bare")

    by_path = {e.path: e for e in tree.expectations()}
    assert by_path["PROJECT.md"].repairable


async def test_the_companion_names_the_contract_not_an_absence(fixture_drive):
    make_project(fixture_drive, "260813_Prose", sections=["01 Model"],
                 files={"PROJECT.md": "# Just prose\n", **agent_files(fixture_drive)})
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(179, 51)) as pilot:
        await settle(app, pilot)
        body = companion_text(app)
        assert "PROJECT.md - no front matter" in body, body


def companion_text(app: AtlasApp) -> str:
    return str(app.query_one("#companion-body", Static).content)


# ------------------------------------------ repairing from the Companion (#42)


async def open_companion(app: AtlasApp, pilot) -> OptionList:
    await settle(app, pilot)
    await pilot.press("enter", "enter")
    await settle(app, pilot)
    assert app._focus_region == COMPANION
    choices = app.query_one("#expectations", OptionList)
    assert choices.display and app.focused is choices
    return choices


def highlight(app: AtlasApp, choices: OptionList, path: str) -> None:
    choices.highlighted = next(i for i, e in enumerate(app._unmet) if e.path == path)


async def test_f_on_a_control_plane_expectation_arms_a_backfill_and_enter_applies_it(
        fixture_drive):
    """ADR 0006: an unmet Expectation earns BACKFILL from the Companion. It was
    only ever reachable from tests; `f` with the Companion focused conformed
    the whole project."""
    project = make_project(fixture_drive, "260813_Sparse", sections=["01 Model", "Meetings"],
                           files={"Meetings/k.md": "x"})
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        choices = await open_companion(app, pilot)
        highlight(app, choices, "decisions")
        await pilot.press("f")
        await pilot.pause()
        assert app.screen is app.screen_stack[0], "a one-action repair opened the modal"
        assert app._armed is not None
        assert "decisions" in app._operation_text
        assert "Enter confirm" in app._operation_text
        assert not (project / "decisions").exists(), "nothing written before Enter"

        await pilot.press("enter")
        await settle(app, pilot)
        assert (project / "decisions").is_dir()
        assert (project / "Meetings").is_dir(), "only the one action ran"
        assert "decisions" not in {e.path for e in app._unmet}


async def test_f_on_a_section_expectation_says_to_add_folders(fixture_drive):
    project = make_project(fixture_drive, "260813_Sparse", sections=["01 Model"])
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        choices = await open_companion(app, pilot)
        highlight(app, choices, "08 OUT")
        await pilot.press("f")
        await pilot.pause()
        assert app._armed is None
        assert app.screen is app.screen_stack[0]
        assert "add it with a" in app._operation_text
        assert not (project / "08 OUT").exists()


async def test_escape_cancels_a_backfill_armed_from_the_companion(fixture_drive):
    project = make_project(fixture_drive, "260813_Sparse", sections=["01 Model"])
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        choices = await open_companion(app, pilot)
        highlight(app, choices, "decisions")
        await pilot.press("f")
        await pilot.pause()
        await pilot.press("escape")
        await settle(app, pilot)
        assert app._armed is None
        assert not (project / "decisions").exists()
