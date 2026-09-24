"""atlas tree - the tree's facts on the CLI (ticket 24, ADR 0008, #30).

A thin wrapper over core.tree: Filing State and Load State below the project
root, child counts only where a folder was read, unmet Expectations as their own
list. Fixture drives only.
"""

from __future__ import annotations

import json
import os

import pytest

from atlas.cli import main

from conftest import make_project


def _project(drive):
    return make_project(
        drive, "260910_Tree",
        sections=["01 Model/01 Site Model", "08 OUT/Invoices", "Meetings", "Random"],
        files={"Meetings/kickoff.md": "z", "08 OUT/Invoices/INV-1.pdf": "z",
               "HANDOFF-1.md": "h", "Random/a.txt": "x"},
    )


def _tree(drive, capsys, *extra):
    status = main(["tree", "260910_Tree", "--drive", str(drive), "--json", *extra])
    return status, json.loads(capsys.readouterr().out)


def test_json_carries_filing_and_load_state_keyed_by_node_key(fixture_drive, capsys):
    _project(fixture_drive)
    status, payload = _tree(fixture_drive, capsys, "--depth", "2")

    assert status == 1, "the project has findings"
    nodes = payload["nodes"]
    assert nodes["Meetings"]["filing"] == "drifted"
    assert nodes["08 OUT/Invoices"]["filing"] == "misplaced"
    assert nodes["HANDOFF-1.md"]["filing"] == "loose"
    assert nodes["Random"]["filing"] == "unfiled"
    assert nodes["01 Model"]["filing"] == "mapped"
    assert nodes["01 Model"]["load"] == "read"
    assert nodes["01 Model"]["folders"] == 1 and nodes["01 Model"]["files"] == 0
    assert nodes["HANDOFF-1.md"]["is_dir"] is False
    assert "load" not in nodes["HANDOFF-1.md"]


def test_depth_bounds_the_reads_and_never_counts_an_unread_folder(fixture_drive, capsys):
    _project(fixture_drive)
    _status, payload = _tree(fixture_drive, capsys)       # default depth 1

    nodes = payload["nodes"]
    assert "01 Model/01 Site Model" not in nodes
    assert nodes["01 Model"]["load"] == "unread"
    assert "folders" not in nodes["01 Model"], "never a zero count on an Unread folder"
    assert "files" not in nodes["01 Model"]


def test_unmet_expectations_are_a_separate_list_never_nodes(fixture_drive, capsys):
    _project(fixture_drive)
    _status, payload = _tree(fixture_drive, capsys)

    paths = {e["path"]: e for e in payload["expectations"]}
    assert "11 Meetings" in paths and paths["11 Meetings"]["kind"] == "section"
    assert paths["PROJECT.md"]["kind"] == "control-plane"
    assert paths["PROJECT.md"]["repairable"] is True
    assert not set(paths) & set(payload["nodes"])


def test_an_unreadable_folder_reads_as_unreadable(fixture_drive, capsys, monkeypatch):
    _project(fixture_drive)
    real = os.scandir

    def scandir(path="."):
        if os.path.basename(os.fspath(path).rstrip("\\/")) == "Random":
            raise PermissionError(13, "Access is denied", os.fspath(path))
        return real(path)

    monkeypatch.setattr(os, "scandir", scandir)
    _status, payload = _tree(fixture_drive, capsys, "--depth", "2")

    assert payload["nodes"]["Random"]["load"] == "unreadable"
    assert "files" not in payload["nodes"]["Random"]


def test_text_is_an_outline_that_spells_the_fault_out(fixture_drive, capsys):
    _project(fixture_drive)
    assert main(["tree", "260910_Tree", "--drive", str(fixture_drive), "--depth", "2"]) == 1
    out = capsys.readouterr().out

    assert "Meetings/" in out and "wrong name" in out
    assert "wrong place" in out and "not filed yet" in out and "not in the map" in out
    assert "  01 Site Model/" in out, "children are indented under their folder"
    assert "11 Meetings" in out and "missing" in out.lower()


def test_a_conforming_project_is_clean(fixture_drive, capsys):
    from conftest import agent_files

    make_project(
        fixture_drive, "260911_Clean",
        sections=["01 Model/01 Site Model", "01 Model/02 Design", "06 Research/Zoning",
                  "06 Research/Code", "08 OUT/Transmittals", "08 OUT/RFI",
                  "10 Legal/Invoices", "10 Legal/Proposals-Contracts",
                  "11 Meetings/Agendas", "11 Meetings/Minutes"],
        files={"PROJECT.md": "---\nx: y\n---\n", "decisions/README.md": "x",
               **agent_files(fixture_drive)},
    )
    assert main(["tree", "260911_Clean", "--drive", str(fixture_drive), "--json"]) == 0


@pytest.mark.parametrize("argv", [["tree", "260999_Nope"], ["tree", ".."],
                                  ["tree", "260910_Tree", "--depth", "0"]])
def test_errors_exit_2(fixture_drive, capsys, argv):
    _project(fixture_drive)
    assert main([*argv, "--drive", str(fixture_drive)]) == 2
