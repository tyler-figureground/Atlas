"""The console under filesystem faults: it reports, it never shows a failure as
an empty or healthy drive, and it never exits. Fixture drives only."""

from __future__ import annotations

import os

from textual.widgets import Static

from atlas.tui.app import AtlasApp

from conftest import make_project


async def settle(app: AtlasApp, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def _deny_listing(monkeypatch, name: str) -> None:
    real = os.scandir

    def scandir(path="."):
        if os.path.basename(os.fspath(path).rstrip("\\/")) == name:
            raise PermissionError(13, "Access is denied", os.fspath(path))
        return real(path)

    monkeypatch.setattr(os, "scandir", scandir)


async def test_an_unreadable_drive_root_is_a_scan_failure_not_zero_projects(fixture_drive, monkeypatch):
    """#26: the console used to say "Scan complete - 0 project(s)"."""
    make_project(fixture_drive, "260301_Hidden", sections=["01 Model"])
    _deny_listing(monkeypatch, fixture_drive.name)
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        operation = str(app.query_one("#operation", Static).content)
        assert "0 project" not in operation
        assert "cannot read" in operation
        assert "Access is denied" in operation
