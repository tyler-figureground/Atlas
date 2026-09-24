"""The Companion Region's unmet Expectations: what they say, and what `f` does
with one (ADR 0004, 0006, 0007)."""

from __future__ import annotations

from textual.widgets import Static

from atlas.core.doctor import report_project
from atlas.core.scan import scan_drive
from atlas.core.tree import CONTRACT, open_project_tree
from atlas.tui.app import AtlasApp
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
