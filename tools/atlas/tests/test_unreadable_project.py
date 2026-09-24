"""An unreadable project, or an unreadable file in one, never reads as an empty
or missing one (#13, ADR 0004). Fixture drives only; denial is simulated at the
listing and read calls, as icacls or a Drive permission change produces it."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.doctor import report_project
from atlas.core.scan import scan_drive
from atlas.core.tree import open_project_tree
from atlas.tui.model import project_rows

from conftest import agent_files, make_project


def _deny_listing(monkeypatch, *names: str) -> None:
    real = os.scandir

    def scandir(path="."):
        if os.path.basename(os.fspath(path).rstrip("\\/")) in names:
            raise PermissionError(13, "Access is denied", os.fspath(path))
        return real(path)

    monkeypatch.setattr(os, "scandir", scandir)


def _deny_reading(monkeypatch, name: str) -> None:
    real_bytes, real_text = Path.read_bytes, Path.read_text

    def read_bytes(self):
        if self.name == name:
            raise PermissionError(13, "Access is denied", str(self))
        return real_bytes(self)

    def read_text(self, *args, **kwargs):
        if self.name == name:
            raise PermissionError(13, "Access is denied", str(self))
        return real_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setattr(Path, "read_text", read_text)


def _locked(drive: Path) -> Path:
    """A project whose control plane is all present, so any 'missing' is false."""
    return make_project(
        drive, "260902_Locked",
        sections=["01 Model", "06 Research/Code", "06 Research/Zoning", "11 Meetings"],
        files={"PROJECT.md": "---\nproject: x\n---\n# x\n", "decisions/README.md": "x",
               **agent_files(drive)},
    )


def _report(drive: Path, name: str):
    inventory = scan_drive(drive)
    inv = next(p for p in inventory.projects if p.name == name)
    return inventory, inv, report_project(inv, inventory.map)


def test_an_unreadable_root_reports_only_that_it_is_unreadable(fixture_drive, monkeypatch):
    _locked(fixture_drive)
    _deny_listing(monkeypatch, "260902_Locked")
    _inventory, _inv, report = _report(fixture_drive, "260902_Locked")

    assert report.unreadable
    assert not report.root_readable
    assert report.missing_control_plane == ()
    assert not report.actionable
    assert report.unfiled == ()


def test_doctor_says_it_cannot_read_rather_than_missing(fixture_drive, capsys, monkeypatch):
    _locked(fixture_drive)
    _deny_listing(monkeypatch, "260902_Locked")

    assert main(["doctor", "--drive", str(fixture_drive)]) == 1
    out = capsys.readouterr().out
    assert "control-plane missing" not in out
    assert "(0 sections)" not in out
    assert "cannot read" in out

    assert main(["doctor", "--drive", str(fixture_drive), "--json"]) == 1
    project = json.loads(capsys.readouterr().out)["projects"][0]
    assert project["sections_present"] is None
    assert project["missing_control_plane"] == []


def test_conform_skips_an_unreadable_project_and_changes_nothing(fixture_drive, capsys, monkeypatch):
    _locked(fixture_drive)
    _deny_listing(monkeypatch, "260902_Locked")

    status = main(["conform", "--drive", str(fixture_drive), "--project", "260902_Locked",
                   "--apply", "--json"])
    assert status == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["actions"] == []

    assert main(["conform", "--drive", str(fixture_drive), "--project", "260902_Locked"]) == 1
    out = capsys.readouterr().out
    assert "[OK" not in out
    assert "cannot read" in out


def test_an_unreadable_control_file_is_unreadable_not_missing(fixture_drive, capsys, monkeypatch):
    _locked(fixture_drive)
    _deny_reading(monkeypatch, "PROJECT.md")
    _inventory, _inv, report = _report(fixture_drive, "260902_Locked")

    assert "PROJECT.md" not in report.missing_control_plane
    assert any("PROJECT.md" in line for line in report.unreadable), report.unreadable

    # conform --only backfill used to crash reading it back.
    assert main(["conform", "--drive", str(fixture_drive), "--project", "260902_Locked",
                 "--only", "backfill", "--apply", "--json"]) == 1


def test_the_project_row_never_shows_a_zero_for_a_folder_it_could_not_read(fixture_drive, monkeypatch):
    _locked(fixture_drive)
    _deny_listing(monkeypatch, "260902_Locked")
    inventory, _inv, report = _report(fixture_drive, "260902_Locked")

    row = project_rows((report,), inventory.map)[0]
    assert row.sections.startswith("?")


def test_expectations_never_list_what_sits_under_an_unreadable_folder(fixture_drive, monkeypatch):
    _locked(fixture_drive)
    inventory, inv, report = _report(fixture_drive, "260902_Locked")
    _deny_listing(monkeypatch, "06 Research")
    tree = open_project_tree(inv, inventory.map, report)

    paths = [e.path for e in tree.expectations()]
    assert not any(p.startswith("06 Research/") for p in paths), paths


def test_expectations_of_an_unreadable_root_list_no_sections(fixture_drive, monkeypatch):
    _locked(fixture_drive)
    _deny_listing(monkeypatch, "260902_Locked")
    inventory, inv, report = _report(fixture_drive, "260902_Locked")
    tree = open_project_tree(inv, inventory.map, report)

    assert tree.expectations() == ()
