"""The session Name Index and `atlas search` (ticket 33, ticket 08, ADR 0008).

One bounded walk of the drive - folders, files, and the project roots - matched
by case-folded substring, capped at ticket 12's count cap. Zero content reads.
Fixture drives only.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

from atlas.cli import main
from atlas.core.search import RESULT_CAP, build_name_index, search_names

from conftest import make_project, write_map

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="NTFS junctions")


def _junction(link, target) -> None:
    """Same shell junction the walk tests use - admin-free on NTFS."""
    import subprocess

    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                   check=True, capture_output=True)


def _drive(drive):
    make_project(drive, "260813_Alpha",
                 sections=["01 Model", "06 Research/Code"],
                 files={"01 Model/site model.rvt": "x",
                        "06 Research/Code/zoning notes.md": "z",
                        "PERMIT-set.pdf": "p"})
    make_project(drive, "260901_Beta",
                 sections=["01 Model"],
                 files={"01 Model/model notes.txt": "n"})


# ------------------------------------------------------------- the index


def test_the_index_covers_projects_folders_and_files(fixture_drive):
    _drive(fixture_drive)
    index = build_name_index(fixture_drive)
    paths = {e.path for e in index.entries}

    # The project roots are entries themselves, so a project name is findable.
    assert "260813_Alpha" in paths and "260901_Beta" in paths
    assert "260813_Alpha/01 Model" in paths
    assert "260813_Alpha/06 Research/Code/zoning notes.md" in paths
    assert "260813_Alpha/PERMIT-set.pdf" in paths
    root = next(e for e in index.entries if e.path == "260813_Alpha")
    assert root.is_dir and root.node_key == ""
    deep = next(e for e in index.entries if e.path.endswith("zoning notes.md"))
    assert not deep.is_dir and deep.node_key == "06 Research/Code/zoning notes.md"
    assert deep.project == "260813_Alpha"


def test_the_index_walks_project_roots_only(fixture_drive):
    """`_`-roots are out: archived projects and the control plane are invisible
    to the console (ADR 0019), and the overlay is a console surface."""
    _drive(fixture_drive)
    archived = fixture_drive / "_Archived Projects" / "260101_Old"
    archived.mkdir(parents=True)
    (archived / "keep.md").write_text("x", encoding="utf-8")
    index = build_name_index(fixture_drive)
    paths = {e.path for e in index.entries}

    assert not any("_Archived Projects" in p or "_tools" in p for p in paths)
    assert all(not e.name.startswith("_") for e in index.entries)


def test_unreadable_folders_are_recorded_never_swallowed(fixture_drive, monkeypatch):
    """A folder the walk cannot open is on the index as a failure; the rest of
    the drive is still indexed. `Path.rglob` would have hidden it (ticket 06)."""
    _drive(fixture_drive)
    target = str(fixture_drive / "260813_Alpha" / "01 Model")
    real_scandir = os.scandir

    def denying(path, *args, **kwargs):
        if os.fspath(path) == target:
            raise PermissionError(5, "Access is denied", target)
        return real_scandir(path, *args, **kwargs)

    monkeypatch.setattr(os, "scandir", denying)
    index = build_name_index(fixture_drive)

    unreadable = dict(index.unreadable)
    assert "260813_Alpha/01 Model" in unreadable
    assert "Access is denied" in unreadable["260813_Alpha/01 Model"]
    # The rest of the drive survived.
    assert any(e.path == "260901_Beta/01 Model/model notes.txt" for e in index.entries)
    # The folder itself is an entry; its children are simply absent, and the
    # unreadable record is what keeps that from reading as empty (ADR 0004).
    assert any(e.path == "260813_Alpha/01 Model" for e in index.entries)
    assert not any(e.path == "260813_Alpha/01 Model/site model.rvt"
                   for e in index.entries)


@windows_only
def test_a_junction_is_never_walked_through(fixture_drive, tmp_path):
    elsewhere = tmp_path / "ELSEWHERE"
    elsewhere.mkdir()
    (elsewhere / "secret.rvt").write_text("x", encoding="utf-8")
    project = make_project(fixture_drive, "260813_Alpha", sections=["01 Model"])
    _junction(project / "Linked", elsewhere)

    index = build_name_index(fixture_drive)
    assert not any("secret" in e.path or "Linked" in e.path for e in index.entries)


# ------------------------------------------------------------- matching


def test_matching_is_a_case_folded_substring_on_name_and_path(fixture_drive):
    _drive(fixture_drive)
    index = build_name_index(fixture_drive)

    by_name = search_names(index, "ZONING")
    assert [h.path for h in by_name.hits] == ["260813_Alpha/06 Research/Code/zoning notes.md"]

    # The path is searchable too, so "code zoning" narrows by where a thing sits.
    by_path = search_names(index, "code/zoning")
    assert [h.path for h in by_path.hits] == ["260813_Alpha/06 Research/Code/zoning notes.md"]

    # Straussian fold: a case-folded query finds a case-folded name.
    assert search_names(index, "permit").total == 1


def test_a_blank_query_matches_nothing(fixture_drive):
    _drive(fixture_drive)
    result = search_names(build_name_index(fixture_drive), "   ")
    assert result.hits == () and result.total == 0


def test_results_cap_at_the_count_cap_and_count_the_overflow(fixture_drive):
    project = make_project(fixture_drive, "260813_Full", sections=["01 Model"])
    for i in range(RESULT_CAP + 25):
        (project / "01 Model" / f"sheet {i:03}.pdf").write_text("x", encoding="utf-8")

    result = search_names(build_name_index(fixture_drive), "sheet")
    assert len(result.hits) == RESULT_CAP
    assert result.total == RESULT_CAP + 25
    assert result.overflow == 25

    cheap = search_names(build_name_index(fixture_drive), "sheet", cap=3)
    assert len(cheap.hits) == 3 and cheap.total == RESULT_CAP + 25


def test_a_query_matching_everything_still_caps(fixture_drive):
    _drive(fixture_drive)
    result = search_names(build_name_index(fixture_drive), "model")
    assert result.total > 1
    assert all("model" in (h.name + h.path).casefold() for h in result.hits)


# ------------------------------------------------------------- the CLI


def _search(drive, capsys, *args):
    status = main(["search", *args, "--drive", str(drive), "--json"])
    return status, json.loads(capsys.readouterr().out)


def test_search_json_names_its_fields(fixture_drive, capsys):
    _drive(fixture_drive)
    status, payload = _search(fixture_drive, capsys, "model")

    assert status == 0
    assert payload["query"] == "model"
    assert payload["drive"] == "TESTDRIVE"
    assert payload["total"] == payload["shown"] == len(payload["results"])
    assert payload["cap"] == RESULT_CAP
    assert payload["unreadable"] == []
    hit = next(r for r in payload["results"] if r["path"] == "260813_Alpha/01 Model")
    assert hit == {"project": "260813_Alpha", "path": "260813_Alpha/01 Model",
                   "name": "01 Model", "kind": "folder"}
    kinds = {r["kind"] for r in payload["results"]}
    assert kinds <= {"folder", "file"}


def test_search_text_names_the_kind_and_the_overflow(fixture_drive, capsys):
    project = make_project(fixture_drive, "260813_Full", sections=["01 Model"])
    for i in range(5):
        (project / "01 Model" / f"sheet {i}.pdf").write_text("x", encoding="utf-8")

    status = main(["search", "sheet", "--drive", str(fixture_drive)])
    out = capsys.readouterr().out
    assert status == 0
    assert "file  260813_Full/01 Model/sheet 0.pdf" in out
    assert "5 matches" in out


def test_search_no_matches_exits_1(fixture_drive, capsys):
    _drive(fixture_drive)
    status = main(["search", "no-such-thing", "--drive", str(fixture_drive)])
    out = capsys.readouterr().out
    assert status == 1
    assert "no matches" in out.casefold()


def test_search_errors_exit_2(fixture_drive, capsys, tmp_path):
    _drive(fixture_drive)
    # A blank query is a usage error, not a match-everything.
    assert main(["search", "  ", "--drive", str(fixture_drive)]) == 2
    capsys.readouterr()
    # An unmapped drive is an error, never "no matches".
    stray = tmp_path / "STRAY"
    stray.mkdir()
    assert main(["search", "x", "--drive", str(stray)]) == 2
