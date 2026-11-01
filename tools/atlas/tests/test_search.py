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


def _archive(drive, root="_Archived Projects"):
    """One archived project under the archive root, plus a loose file there."""
    archived = drive / root / "260101_Old"
    (archived / "01 Model").mkdir(parents=True)
    (archived / "01 Model" / "old model notes.md").write_text("x", encoding="utf-8")
    (drive / root / "README.txt").write_text("loose", encoding="utf-8")
    return archived


def test_the_index_skips_the_control_plane(fixture_drive):
    """`_tools` and every other `_`-root but the archive stay out: drive-root
    files are the control plane, not search results."""
    _drive(fixture_drive)
    (fixture_drive / "_scratch" / "x").mkdir(parents=True)
    index = build_name_index(fixture_drive)
    assert not any(e.path.startswith("_") for e in index.entries)


def test_archived_projects_are_indexed_and_tagged(fixture_drive):
    """Plan Q3 (2026-10-16): the archive is mapped read-only so search reaches
    it. Each child folder of the archive root is an archived project; a loose
    file at the archive root is not a result."""
    _drive(fixture_drive)
    _archive(fixture_drive)
    index = build_name_index(fixture_drive)
    by_path = {e.path: e for e in index.entries}

    root = by_path["_Archived Projects/260101_Old"]
    assert root.archived and root.is_dir and root.project == "260101_Old"
    assert root.node_key == ""
    deep = by_path["_Archived Projects/260101_Old/01 Model/old model notes.md"]
    assert deep.archived and deep.project == "260101_Old"
    assert deep.node_key == "01 Model/old model notes.md"
    assert "_Archived Projects" not in by_path, "the archive root is not a result"
    assert "_Archived Projects/README.txt" not in by_path
    # Live hits carry the flag too, false.
    assert not by_path["260813_Alpha"].archived


def test_the_archive_root_comes_from_the_map(fixture_drive):
    from conftest import FIXTURE_MAP

    write_map(fixture_drive, {**FIXTURE_MAP, "controlPlane": {
        **FIXTURE_MAP["controlPlane"], "archiveRoot": "_Old Jobs/2025"}})
    _drive(fixture_drive)
    _archive(fixture_drive, "_Old Jobs/2025")
    _archive(fixture_drive)        # the default root is not this drive's archive
    index = build_name_index(fixture_drive)
    archived = {e.path for e in index.entries if e.archived}

    assert "_Old Jobs/2025/260101_Old" in archived
    assert not any(p.startswith("_Archived Projects") for p in archived)


def test_a_drive_without_an_archive_is_not_unreadable(fixture_drive):
    """No archive root yet is the normal state, never a failure note."""
    _drive(fixture_drive)
    index = build_name_index(fixture_drive)
    assert index.unreadable == ()
    assert not any(e.archived for e in index.entries)


def test_the_archive_can_be_left_out(fixture_drive):
    _drive(fixture_drive)
    _archive(fixture_drive)
    index = build_name_index(fixture_drive, archived=False)
    assert not any(e.archived or e.path.startswith("_") for e in index.entries)


def test_live_hits_rank_before_archived_ones(fixture_drive):
    """The archive never buries current work: every live match comes first,
    and the cap fills with live hits before any archived one."""
    _archive(fixture_drive)
    # Sorts before the live projects by name: ordering must not be alphabetical.
    first = fixture_drive / "_Archived Projects" / "000_First"
    first.mkdir()
    (first / "model a.md").write_text("x", encoding="utf-8")
    _drive(fixture_drive)
    result = search_names(build_name_index(fixture_drive), "model")

    flags = [h.archived for h in result.hits]
    assert True in flags and False in flags
    assert flags == sorted(flags), "every live hit before any archived one"
    assert result.archived == flags.count(True)

    live = flags.count(False)
    capped = search_names(build_name_index(fixture_drive), "model", cap=live)
    assert not any(h.archived for h in capped.hits)
    assert capped.overflow == result.archived


def test_archived_projects_stay_out_of_the_project_list_and_doctor(fixture_drive):
    """Only search sees the archive (ADR 0019)."""
    from atlas.core.doctor import report_drive
    from atlas.core.scan import scan_drive

    _drive(fixture_drive)
    _archive(fixture_drive)
    inventory = scan_drive(fixture_drive)
    assert {p.name for p in inventory.projects} == {"260813_Alpha", "260901_Beta"}
    report = report_drive(inventory)
    assert len(report.projects) == 2
    assert "260101_Old" not in repr(report.projects)


def test_indexing_the_archive_writes_nothing(fixture_drive):
    _drive(fixture_drive)
    _archive(fixture_drive)
    archive = fixture_drive / "_Archived Projects"

    def snapshot():
        return sorted((os.fspath(p), p.stat().st_mtime_ns, p.stat().st_size)
                      for p in [archive, *archive.rglob("*")])

    before = snapshot()
    build_name_index(fixture_drive)
    assert snapshot() == before


@windows_only
def test_a_junction_in_the_archive_is_never_walked_through(fixture_drive, tmp_path):
    elsewhere = tmp_path / "ELSEWHERE"
    elsewhere.mkdir()
    (elsewhere / "secret.rvt").write_text("x", encoding="utf-8")
    archive = fixture_drive / "_Archived Projects"
    archive.mkdir()
    _junction(archive / "260101_Linked", elsewhere)

    index = build_name_index(fixture_drive)
    assert not any("secret" in e.path or "Linked" in e.path for e in index.entries)


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
                   "name": "01 Model", "kind": "folder", "archived": False,
                   "crm_id": None}
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


def test_search_tags_archived_hits_in_text_and_json(fixture_drive, capsys):
    _drive(fixture_drive)
    _archive(fixture_drive)
    status, payload = _search(fixture_drive, capsys, "model notes")
    assert status == 0
    assert [(r["path"], r["archived"]) for r in payload["results"]] == [
        ("260901_Beta/01 Model/model notes.txt", False),
        ("_Archived Projects/260101_Old/01 Model/old model notes.md", True)]
    assert payload["results"][1]["project"] == "260101_Old"
    assert payload["archived"] == 1

    status = main(["search", "model notes", "--drive", str(fixture_drive)])
    lines = capsys.readouterr().out.splitlines()
    assert "file  260901_Beta/01 Model/model notes.txt" in lines
    assert ("file  [archived] _Archived Projects/260101_Old/01 Model/old model notes.md"
            in lines)
    assert any("1 archived" in line for line in lines)


def test_search_no_archived_leaves_the_archive_out(fixture_drive, capsys):
    _drive(fixture_drive)
    _archive(fixture_drive)
    status, payload = _search(fixture_drive, capsys, "model notes", "--no-archived")
    assert status == 0
    assert [r["archived"] for r in payload["results"]] == [False]
    assert payload["archived"] == 0
