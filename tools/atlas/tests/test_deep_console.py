"""The console key for the deep pass (ticket 31 shipped it CLI-only).

`D` runs the opt-in walk below the focused project's root, off the UI thread -
one enumeration per folder gathering Receipt Rule hits, deep unreadables,
over-long paths and the item count (core.deep.scan_deep). Findings render in
the Companion's DEEP mode, which `d` also cycles to. Receipt sweeps earn no
inline repair key (ticket 26): the mode lists them and points at
`conform --deep --apply` on the CLI.
"""

from __future__ import annotations

import copy

from textual.widgets import Static

from atlas.tui.app import AtlasApp, ConfirmListModal
from atlas.tui.layout import DEEP, DOSSIER, EXPECTATIONS, HEALTH

from conftest import FIXTURE_MAP, make_project, write_map


async def settle(app: AtlasApp, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


ZIPS = {"name": "Run zips", "target": ".agent/runs", "match": {"extensions": ["zip"]}}


def deep_drive(drive):
    """A fixture drive whose map carries one Receipt Rule, and a project with a
    matching file below the root."""
    data = copy.deepcopy(FIXTURE_MAP)
    data["controlPlane"].update({"runsDir": ".agent/runs", "backupsDir": ".agent/backups"})
    data["receiptRules"] = [ZIPS]
    write_map(drive, data)
    make_project(drive, "260501_Alpha", sections=["01 Model", "06 Research"],
                 files={"06 Research/run-260501.zip": "x"})


def companion_text(app) -> str:
    return str(app.query_one("#companion-body", Static).content)


async def test_D_walks_the_project_and_the_companion_renders_the_findings(fixture_drive):
    deep_drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        assert app._companion_mode == EXPECTATIONS
        await pilot.press("D")
        await settle(app, pilot)

        assert app._companion_mode == DEEP, "findings land where the operator can read them"
        body = companion_text(app)
        assert "06 Research/run-260501.zip -> .agent/runs" in body
        assert "rule: Run zips" in body
        assert "conform --deep" in body, "receipt sweeps point at the CLI, never an inline key"
        assert "items" in body, "the item count rides every deep pass"
        assert "Deep pass on 260501_Alpha: 1 finding" in app._operation_text


async def test_the_deep_mode_before_a_run_says_how_to_run_one(fixture_drive):
    deep_drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        for expected in (HEALTH, DOSSIER, DEEP):
            await pilot.press("d")
            await settle(app, pilot)
            assert app._companion_mode == expected
        body = companion_text(app)
        assert "D" in body and "deep pass" in body.lower(), body


async def test_D_is_inert_over_a_modal(fixture_drive):
    deep_drive(fixture_drive)
    make_project(fixture_drive, "260502_Bravo", sections=["Meetings"],
                 files={"Meetings/k.md": "z"})
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        table_row = next(i for i, row in enumerate(app._visible_rows)
                         if row.key == "260502_Bravo")
        app.query_one("#projects").move_cursor(row=table_row)
        await settle(app, pilot)
        await pilot.press("f")          # the conform modal
        await settle(app, pilot)
        assert isinstance(app.screen, ConfirmListModal)
        await pilot.press("D")
        await settle(app, pilot)
        assert isinstance(app.screen, ConfirmListModal), "D walked behind the modal"
        assert app._deep == {}
