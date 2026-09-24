"""The one recursive walk Atlas does: never through a link (#49), never silent
about a folder it could not read (#24). Fixture drives only."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.conform import apply_plan, build_repair_plan
from atlas.core.doctor import report_project
from atlas.core.ops import find_empty_dirs
from atlas.core.scan import count_files, scan_drive

from conftest import make_project

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="NTFS junctions")


def _junction(link: Path, target: Path) -> None:
    import _winapi

    _winapi.CreateJunction(str(target), str(link))


def _inv(drive: Path, name: str):
    inventory = scan_drive(drive)
    return inventory, next(p for p in inventory.projects if p.name == name)


# ------------------------------------------------------------ junctions (#49)


@windows_only
def test_clean_never_descends_into_a_junction(fixture_drive, tmp_path, capsys):
    elsewhere = tmp_path / "elsewhere" / "Keep"
    (elsewhere / "EmptyA" / "EmptyB").mkdir(parents=True)
    project = make_project(fixture_drive, "260501_ProjJ", sections=["01 Model"])
    _junction(project / "Linked", elsewhere)

    assert main(["clean", "--drive", str(fixture_drive), "--project", "260501_ProjJ",
                 "--apply", "--json"]) == 0

    assert (elsewhere / "EmptyA" / "EmptyB").is_dir(), "an empty folder outside the project"
    assert (project / "Linked").exists(), "the link is not empty; it is never removed"


@windows_only
def test_find_empty_dirs_treats_a_link_as_content(fixture_drive, tmp_path):
    from atlas.core.mapfile import find_map, load_map

    elsewhere = tmp_path / "elsewhere"
    (elsewhere / "Empty").mkdir(parents=True)
    project = make_project(fixture_drive, "260502_Holder", sections=["01 Model", "Holder"])
    _junction(project / "Holder" / "Link", elsewhere)

    empties = find_empty_dirs(project, load_map(find_map(fixture_drive)))
    assert not any(rel.startswith("Holder") for rel in empties), empties


@windows_only
def test_count_files_never_counts_through_a_junction(fixture_drive, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "outside.txt").write_text("x", encoding="utf-8")
    project = make_project(fixture_drive, "260503_Count", sections=["01 Model"],
                           files={"inside.txt": "y"})
    _junction(project / "Linked", elsewhere)

    assert count_files(project) == 1


@windows_only
def test_a_repair_never_removes_empty_folders_behind_a_junction(fixture_drive, tmp_path):
    """Repairing an empty Meetings that held a junction removed a template
    skeleton that lived somewhere else entirely."""
    skeleton = tmp_path / "ELSEWHERE" / "Template Skeleton" / "01 Agendas" / "2026"
    skeleton.mkdir(parents=True)
    project = make_project(fixture_drive, "260504_Skel",
                           sections=["01 Model", "11 Meetings", "Meetings"])
    _junction(project / "Meetings" / "Link", tmp_path / "ELSEWHERE" / "Template Skeleton")

    inventory, inv = _inv(fixture_drive, "260504_Skel")
    plan = build_repair_plan(report_project(inv, inventory.map), inventory.map,
                             "Meetings", project=inv.path)
    apply_plan(fixture_drive, inv.path, inventory.map, plan)

    assert skeleton.is_dir()


# ------------------------------------------------- unreadable subfolders (#24)


def _deny(monkeypatch, *names: str) -> None:
    """Make any folder with one of these names refuse to list, as an icacls
    deny or an over-long path on a machine without LongPathsEnabled does."""
    real = os.scandir

    def scandir(path="."):
        if os.path.basename(os.fspath(path).rstrip("\\/")) in names:
            raise PermissionError(13, "Access is denied", os.fspath(path))
        return real(path)

    monkeypatch.setattr(os, "scandir", scandir)


def _invoices_project(drive: Path) -> Path:
    return make_project(
        drive, "260601_Locked",
        sections=["01 Model", "08 OUT/Invoices/Denied", "10 Legal"],
        files={"08 OUT/Invoices/Denied/INV-1.pdf": "x",
               "08 OUT/Invoices/Denied/INV-2.pdf": "y"},
    )


def test_doctor_never_counts_an_unreadable_subfolder_as_zero_files(fixture_drive, capsys, monkeypatch):
    import json

    _invoices_project(fixture_drive)
    _deny(monkeypatch, "Denied")

    assert main(["doctor", "--drive", str(fixture_drive), "--json"]) == 1
    project = json.loads(capsys.readouterr().out)["projects"][0]
    assert project["relocations"][0]["files"] is None
    assert any("Denied" in line for line in project["unreadable"]), project["unreadable"]

    assert main(["doctor", "--drive", str(fixture_drive)]) == 1
    out = capsys.readouterr().out
    assert "(0 files)" not in out
    assert "Denied" in out, "text output names what it could not read"


def test_conform_refuses_to_move_or_remove_a_source_it_cannot_fully_read(fixture_drive, capsys, monkeypatch):
    """The empty-duplicate branch believed the source empty and rmdir'd it;
    only rmdir refusing a non-empty folder stopped it, as a traceback."""
    import json

    project = _invoices_project(fixture_drive)
    (project / "10 Legal" / "Invoices").mkdir()
    _deny(monkeypatch, "Denied")

    status = main(["conform", "--drive", str(fixture_drive), "--project", "260601_Locked",
                   "--only", "relocate", "--apply", "--json"])
    monkeypatch.undo()

    assert status == 1
    actions = [a for p in json.loads(capsys.readouterr().out) for a in p["actions"]]
    relocate = next(a for a in actions if a["kind"] == "relocate")
    assert relocate["status"] == "conflict"
    assert "cannot read" in relocate["note"]
    assert (project / "08 OUT" / "Invoices" / "Denied" / "INV-1.pdf").is_file()


def test_walk_reports_what_it_could_not_read(tmp_path, monkeypatch):
    from atlas.core.scan import tally_files

    (tmp_path / "ok").mkdir()
    (tmp_path / "ok" / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "Denied").mkdir()
    (tmp_path / "Denied" / "b.txt").write_text("b", encoding="utf-8")
    _deny(monkeypatch, "Denied")

    tally = tally_files(tmp_path)
    assert tally.files == 1
    assert [rel for rel, _error in tally.unreadable] == ["Denied"]
    assert not tally.known
