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
