"""Archive and un-archive a project (ticket 32, ADR 0019).

Fixture drives only - the five real archive moves are a separate production
run. Covers the map key, the index-row stamp and its verbatim inverse, plan
preconditions (refuse) and warnings (never refuse), the drive-scoped Guard,
apply, undo via the manifest, and the invisibility of archived projects.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.archive import (
    ARCHIVE,
    UNARCHIVE,
    ArchiveGuard,
    apply_archive_plan,
    archive_plan_from_dict,
    archive_plan_to_dict,
    build_archive_plan,
    build_unarchive_plan,
    invert_archive_plan,
)
from atlas.core.conform import CONFLICT, DONE, FAILED, SKIPPED, NotInvertible
from atlas.core.mapfile import MapError, find_map, load_map
from atlas.core.ops import OpsError
from atlas.core.project_index import (
    ProjectIndexError,
    append_project_index_row,
    preflight_project_index,
    restore_project_index_row,
    stamp_project_index_status,
)
from atlas.core.scan import is_project_dir, scan_drive

from conftest import FIXTURE_MAP, make_intake, make_project, write_map


def _project(drive: Path, name: str = "260101_103 Mosco", **kwargs) -> Path:
    files = kwargs.pop("files", None) or {"01 Model/notes.md": "z"}
    return make_project(drive, name, sections=["01 Model", "00 Tasks"], files=files)


def _index_row(drive: Path, name: str, status: str = "Active") -> str:
    """A real expanded-format row for ``name`` in the drive's index."""
    m = load_map(find_map(drive))
    preflight_project_index(drive, m)
    append_project_index_row(drive, m, name, make_intake(drive, name))
    if status != "Active":
        stamp_project_index_status(drive, m, name, status)
    index = (drive / "_Project Index.md").read_text(encoding="utf-8")
    return next(line for line in index.splitlines() if name in line)


def _status_cell(row: str) -> str:
    return [cell.strip() for cell in row.strip().strip("|").split("|")][6]


def _map(drive: Path):
    return load_map(find_map(drive))


# ------------------------------------------------------------------ map key

def test_archive_root_defaults_when_absent(fixture_drive):
    assert _map(fixture_drive).archive_root == "_Archived Projects"


def test_archive_root_parses_explicit_value(fixture_drive):
    data = dict(FIXTURE_MAP, controlPlane={**FIXTURE_MAP["controlPlane"],
                                           "archiveRoot": "_Archived Projects/2026"})
    write_map(fixture_drive, data)
    assert _map(fixture_drive).archive_root == "_Archived Projects/2026"


@pytest.mark.parametrize("value", [
    42,
    "",
    "   ",
    "/absolute",
    "C:/elsewhere",
    "../up",
    "Archive",                  # no '_' prefix: would re-list archived projects
    "_Archived/../up",
])
def test_archive_root_refuses_a_malformed_value(fixture_drive, value):
    data = dict(FIXTURE_MAP, controlPlane={**FIXTURE_MAP["controlPlane"],
                                           "archiveRoot": value})
    write_map(fixture_drive, data)
    with pytest.raises(MapError):
        _map(fixture_drive)


# ------------------------------------------------------------ index stamping

def test_stamp_sets_only_the_status_cell_and_returns_the_prior_row(fixture_drive):
    _project(fixture_drive)
    prior = _index_row(fixture_drive, "260101_103 Mosco")

    returned = stamp_project_index_status(fixture_drive, _map(fixture_drive),
                                          "260101_103 Mosco", "archived 2026-10-08")

    assert returned == prior
    index = (fixture_drive / "_Project Index.md").read_text(encoding="utf-8")
    stamped = next(line for line in index.splitlines() if "260101_103 Mosco" in line)
    assert _status_cell(stamped) == "archived 2026-10-08"
    # Every other cell survives byte-for-byte.
    assert stamped.split("|")[1:-2] == prior.split("|")[1:-2]


def test_stamp_without_a_matching_row_changes_nothing(fixture_drive):
    _project(fixture_drive)
    m = _map(fixture_drive)
    preflight_project_index(fixture_drive, m)
    before = (fixture_drive / "_Project Index.md").read_bytes()

    assert stamp_project_index_status(fixture_drive, m, "260101_Ghost",
                                      "archived 2026-10-08") is None
    assert (fixture_drive / "_Project Index.md").read_bytes() == before


def test_restore_puts_the_row_back_verbatim(fixture_drive):
    _project(fixture_drive)
    prior = _index_row(fixture_drive, "260101_103 Mosco", status="On hold")
    m = _map(fixture_drive)
    stamp_project_index_status(fixture_drive, m, "260101_103 Mosco", "archived 2026-10-08")

    replaced = restore_project_index_row(fixture_drive, m, "260101_103 Mosco", prior)

    assert _status_cell(replaced) == "archived 2026-10-08"
    index = (fixture_drive / "_Project Index.md").read_text(encoding="utf-8")
    assert prior in index.splitlines()


def test_restore_refuses_a_non_row(fixture_drive):
    _project(fixture_drive)
    _index_row(fixture_drive, "260101_103 Mosco")
    with pytest.raises(ProjectIndexError):
        restore_project_index_row(fixture_drive, _map(fixture_drive),
                                  "260101_103 Mosco", "not a table row")


def test_stamp_refuses_duplicate_rows(fixture_drive):
    _project(fixture_drive)
    m = _map(fixture_drive)
    row = _index_row(fixture_drive, "260101_103 Mosco")
    index = fixture_drive / "_Project Index.md"
    index.write_text(index.read_text(encoding="utf-8") + row + "\r\n", encoding="utf-8")

    with pytest.raises(ProjectIndexError, match="duplicate"):
        stamp_project_index_status(fixture_drive, m, "260101_103 Mosco",
                                   "archived 2026-10-08")


# ------------------------------------------------------------- plan building

def test_archive_plan_moves_the_folder_and_stamps_the_row(fixture_drive):
    _project(fixture_drive)
    _index_row(fixture_drive, "260101_103 Mosco")

    plan = build_archive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco",
                              today=date(2026, 10, 8))

    action = plan.actions[0]
    assert action.kind == ARCHIVE
    assert action.src == "260101_103 Mosco"
    assert action.dst == "_Archived Projects/260101_103 Mosco"
    assert action.file_count == 1
    assert "archived 2026-10-08" in action.note
    assert plan.warnings == ()
    assert any("prompt-vault" in note for note in plan.notes)


def test_archive_plan_warns_on_model_files_without_refusing(fixture_drive):
    _project(fixture_drive, files={
        "01 Model/103 Mosco.rvt": "z",
        "01 Model/details.dwg": "z",
        "01 Model/render.png": "z",
    })

    plan = build_archive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco")

    assert any("2 Revit/CAD" in w for w in plan.warnings)


def test_archive_plan_counts_and_lists_open_task_items(fixture_drive):
    _project(fixture_drive, files={
        "00 Tasks/TASKS.md": "# Tasks\n\n## Now\n\n- [ ] T-001 file the permit\n"
                             "- [x] done thing\n\n## Done\n\n- [ ] closed\n",
        "00 Tasks/TYLER.md": "# Tyler\n\n- [ ] Y-001 call the expediter\n",
    })

    plan = build_archive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco")

    assert any("2 open task item(s)" in w for w in plan.warnings)
    assert any("T-001 file the permit" in w for w in plan.warnings)
    assert any("Y-001 call the expediter" in w for w in plan.warnings)
    assert not any("closed" in w for w in plan.warnings)


def test_archive_refuses_a_missing_project(fixture_drive):
    with pytest.raises(OpsError, match="no project folder"):
        build_archive_plan(fixture_drive, _map(fixture_drive), "260101_Ghost")


def test_archive_refuses_a_name_that_is_not_one_folder(fixture_drive):
    with pytest.raises(OpsError):
        build_archive_plan(fixture_drive, _map(fixture_drive), "../_tools")
    with pytest.raises(OpsError):
        build_archive_plan(fixture_drive, _map(fixture_drive), "a/b")


def test_archive_refuses_the_tools_folder(fixture_drive):
    with pytest.raises(OpsError, match="not a project"):
        build_archive_plan(fixture_drive, _map(fixture_drive), "_tools")


def test_archive_refuses_a_destination_collision(fixture_drive):
    _project(fixture_drive)
    make_project(fixture_drive / "_Archived Projects", "260101_103 Mosco")

    with pytest.raises(OpsError, match="already taken"):
        build_archive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco")


def test_archive_refuses_an_unreadable_project_root(fixture_drive, monkeypatch):
    _project(fixture_drive)
    real = os.scandir

    def scandir(path="."):
        if os.path.basename(os.fspath(path).rstrip("\\/")) == "260101_103 Mosco":
            raise PermissionError(13, "Access is denied", os.fspath(path))
        return real(path)

    monkeypatch.setattr(os, "scandir", scandir)
    with pytest.raises(OpsError, match="cannot read"):
        build_archive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco")


def test_unarchive_plan_finds_the_project_by_name(fixture_drive):
    _project(fixture_drive)
    _index_row(fixture_drive, "260101_103 Mosco")
    plan = apply_archive_plan(fixture_drive, _map(fixture_drive),
                              build_archive_plan(fixture_drive, _map(fixture_drive),
                                                 "260101_103 Mosco"))
    assert plan.actions[0].status == DONE

    back = build_unarchive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco")

    action = back.actions[0]
    assert action.kind == UNARCHIVE
    assert action.src == "_Archived Projects/260101_103 Mosco"
    assert action.dst == "260101_103 Mosco"


def test_unarchive_refuses_when_nothing_is_archived(fixture_drive):
    with pytest.raises(OpsError, match="nothing is archived"):
        build_unarchive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco")


def test_unarchive_refuses_a_name_not_under_the_archive_root(fixture_drive):
    _project(fixture_drive)
    (fixture_drive / "_Archived Projects").mkdir()

    with pytest.raises(OpsError, match="no archived project"):
        build_unarchive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco")


def test_unarchive_refuses_a_drive_root_collision(fixture_drive):
    _project(fixture_drive)
    make_project(fixture_drive / "_Archived Projects", "260101_103 Mosco")
    # Same name at the drive root too: bringing it back would collide.
    with pytest.raises(OpsError, match="already taken"):
        build_unarchive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco")


# ------------------------------------------------------------------- apply

def test_apply_moves_stamps_and_logs(fixture_drive):
    project = _project(fixture_drive)
    prior = _index_row(fixture_drive, "260101_103 Mosco")
    m = _map(fixture_drive)
    plan = build_archive_plan(fixture_drive, m, "260101_103 Mosco",
                              today=date(2026, 10, 8))

    applied = apply_archive_plan(fixture_drive, m, plan, today=date(2026, 10, 8))

    action = applied.actions[0]
    assert action.status == DONE
    assert action.moved[0].src == "260101_103 Mosco"
    assert action.moved[0].dst == "_Archived Projects/260101_103 Mosco"
    assert action.moved[0].is_dir
    assert action.index_row == prior
    assert action.created == ("_Archived Projects",)
    archived = fixture_drive / "_Archived Projects" / "260101_103 Mosco"
    assert (archived / "01 Model" / "notes.md").is_file()
    assert not project.exists()
    index = (fixture_drive / "_Project Index.md").read_text(encoding="utf-8")
    row = next(line for line in index.splitlines() if "260101_103 Mosco" in line)
    assert _status_cell(row) == "archived 2026-10-08"
    log = next((fixture_drive / "_tools" / "logs").glob("atlas-*.log"))
    assert "archive 260101_103 Mosco -> _Archived Projects/260101_103 Mosco" \
        in log.read_text(encoding="utf-8")


def test_apply_with_an_existing_archive_root_creates_nothing(fixture_drive):
    _project(fixture_drive)
    (fixture_drive / "_Archived Projects").mkdir()

    applied = apply_archive_plan(fixture_drive, _map(fixture_drive),
                                 build_archive_plan(fixture_drive, _map(fixture_drive),
                                                    "260101_103 Mosco"))

    assert applied.actions[0].created == ()


def test_apply_never_clobbers_a_destination(fixture_drive):
    _project(fixture_drive)
    m = _map(fixture_drive)
    # Built before the collision appeared (the Guard's job in the console); the
    # apply itself still refuses to merge two projects.
    plan = build_archive_plan(fixture_drive, m, "260101_103 Mosco")
    make_project(fixture_drive / "_Archived Projects", "260101_103 Mosco",
                 files={"keep.md": "z"})

    applied = apply_archive_plan(fixture_drive, m, plan)

    assert applied.actions[0].status == CONFLICT
    assert (fixture_drive / "260101_103 Mosco").is_dir()
    assert (fixture_drive / "_Archived Projects" / "260101_103 Mosco" / "keep.md").is_file()
    assert (fixture_drive / "_Archived Projects" / "260101_103 Mosco" / "keep.md").is_file()


def test_apply_skips_a_vanished_source(fixture_drive):
    plan = build_archive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco") \
        if False else None
    _project(fixture_drive)
    plan = build_archive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco")
    for child in (fixture_drive / "260101_103 Mosco").iterdir():
        pass
    import shutil
    shutil.rmtree(fixture_drive / "260101_103 Mosco")

    applied = apply_archive_plan(fixture_drive, _map(fixture_drive), plan)

    assert applied.actions[0].status == SKIPPED


def test_a_failed_stamp_still_records_the_move(fixture_drive, monkeypatch):
    _project(fixture_drive)
    _index_row(fixture_drive, "260101_103 Mosco")

    import atlas.core.archive as archive_module

    def boom(*args, **kwargs):
        raise ProjectIndexError("index is being updated")

    monkeypatch.setattr(archive_module, "stamp_project_index_status", boom)
    plan = build_archive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco")
    applied = apply_archive_plan(fixture_drive, _map(fixture_drive), plan)

    action = applied.actions[0]
    assert action.status == FAILED
    assert action.moved, "the moved folder is recorded so the revert can put it back"
    assert "stamp failed" in action.note
    assert (fixture_drive / "_Archived Projects" / "260101_103 Mosco").is_dir()


# -------------------------------------------------------------- guard

def test_guard_passes_on_an_unchanged_drive(fixture_drive):
    _project(fixture_drive)
    m = _map(fixture_drive)
    plan = build_archive_plan(fixture_drive, m, "260101_103 Mosco")
    guard = ArchiveGuard.for_plan(fixture_drive, m, plan)

    assert guard.check(fixture_drive) is None


def test_guard_refuses_a_map_change(fixture_drive):
    _project(fixture_drive)
    m = _map(fixture_drive)
    plan = build_archive_plan(fixture_drive, m, "260101_103 Mosco")
    guard = ArchiveGuard.for_plan(fixture_drive, m, plan)
    write_map(fixture_drive, dict(FIXTURE_MAP, version="2.1"))

    assert guard.check(fixture_drive) == "the drive map changed"


def test_guard_refuses_a_drive_root_change(fixture_drive):
    _project(fixture_drive)
    m = _map(fixture_drive)
    plan = build_archive_plan(fixture_drive, m, "260101_103 Mosco")
    guard = ArchiveGuard.for_plan(fixture_drive, m, plan)
    make_project(fixture_drive, "260102_Other")

    assert guard.check(fixture_drive) == "the drive changed since the preview"


def test_guard_refuses_an_archive_root_change(fixture_drive):
    _project(fixture_drive)
    (fixture_drive / "_Archived Projects").mkdir()
    m = _map(fixture_drive)
    plan = build_archive_plan(fixture_drive, m, "260101_103 Mosco")
    guard = ArchiveGuard.for_plan(fixture_drive, m, plan)
    make_project(fixture_drive / "_Archived Projects", "260103_Third")

    assert guard.check(fixture_drive) == "the drive changed since the preview"


# ------------------------------------------------------------------- undo

def test_undo_restores_the_folder_and_the_row_verbatim(fixture_drive):
    _project(fixture_drive, files={
        "01 Model/notes.md": "z",
        "00 Tasks/TASKS.md": "# Tasks\n\n- [ ] T-001 open item\n",
    })
    prior = _index_row(fixture_drive, "260101_103 Mosco", status="On hold")
    m = _map(fixture_drive)
    applied = apply_archive_plan(fixture_drive, m,
                                 build_archive_plan(fixture_drive, m, "260101_103 Mosco"),
                                 today=date(2026, 10, 8))

    inverse = invert_archive_plan(applied)
    assert inverse.inverse
    assert inverse.actions[0].kind == UNARCHIVE
    undone = apply_archive_plan(fixture_drive, m, inverse)

    assert undone.actions[0].status == DONE
    assert (fixture_drive / "260101_103 Mosco" / "01 Model" / "notes.md").is_file()
    index = (fixture_drive / "_Project Index.md").read_text(encoding="utf-8")
    assert prior in index.splitlines(), "the register says what it said before"
    # The archive root the apply created is pruned once empty.
    assert not (fixture_drive / "_Archived Projects").exists()


def test_rearchive_after_undo_is_redo(fixture_drive):
    _project(fixture_drive)
    _index_row(fixture_drive, "260101_103 Mosco")
    m = _map(fixture_drive)
    applied = apply_archive_plan(fixture_drive, m,
                                 build_archive_plan(fixture_drive, m, "260101_103 Mosco"))
    apply_archive_plan(fixture_drive, m, invert_archive_plan(applied))

    again = apply_archive_plan(fixture_drive, m,
                               build_archive_plan(fixture_drive, m, "260101_103 Mosco"))

    assert again.actions[0].status == DONE
    assert (fixture_drive / "_Archived Projects" / "260101_103 Mosco").is_dir()


def test_invert_refuses_an_unapplied_plan(fixture_drive):
    _project(fixture_drive)
    plan = build_archive_plan(fixture_drive, _map(fixture_drive), "260101_103 Mosco")

    with pytest.raises(NotInvertible):
        invert_archive_plan(plan)


def test_unarchive_by_name_marks_the_row_active(fixture_drive):
    _project(fixture_drive)
    _index_row(fixture_drive, "260101_103 Mosco")
    m = _map(fixture_drive)
    apply_archive_plan(fixture_drive, m,
                       build_archive_plan(fixture_drive, m, "260101_103 Mosco"),
                       today=date(2026, 10, 8))

    back = apply_archive_plan(fixture_drive, m,
                              build_unarchive_plan(fixture_drive, m, "260101_103 Mosco"))

    assert back.actions[0].status == DONE
    assert back.actions[0].index_row, "the archived row text is recorded for its own inverse"
    index = (fixture_drive / "_Project Index.md").read_text(encoding="utf-8")
    row = next(line for line in index.splitlines() if "260101_103 Mosco" in line)
    assert _status_cell(row) == "Active"
    assert not (fixture_drive / "_Archived Projects").exists()


# --------------------------------------------------------------- manifests

def test_manifest_round_trips(fixture_drive):
    _project(fixture_drive)
    prior = _index_row(fixture_drive, "260101_103 Mosco")
    m = _map(fixture_drive)
    applied = apply_archive_plan(fixture_drive, m,
                                 build_archive_plan(fixture_drive, m, "260101_103 Mosco"))

    payload = archive_plan_to_dict(applied, m.drive)
    back = archive_plan_from_dict(json.loads(json.dumps(payload)))

    assert back.project == "260101_103 Mosco"
    assert back.archive_root == "_Archived Projects"
    assert back.actions[0].kind == ARCHIVE
    assert back.actions[0].index_row == prior
    assert back.actions[0].moved == applied.actions[0].moved


@pytest.mark.parametrize("field,value", [
    ("src", "../outside"),
    ("dst", "/absolute"),
    ("dst", "C:/elsewhere"),
])
def test_manifest_paths_cannot_leave_the_drive(fixture_drive, field, value):
    action = {"kind": "archive", "src": "260101_X", "dst": "_Archived Projects/260101_X",
              "status": "done", "note": "", "moved": [], "index_row": "",
              "created": [], "prune": []}
    action[field] = value
    payload = {"drive": "TESTDRIVE", "scope": "drive", "project": "260101_X",
               "archive_root": "_Archived Projects", "actions": [action]}
    with pytest.raises(OpsError, match="not a path inside the drive"):
        archive_plan_from_dict(payload)


def test_manifest_refuses_a_conform_plan(fixture_drive):
    payload = {"drive": "TESTDRIVE", "project": "260101_X",
               "actions": [{"kind": "rename", "src": "a", "dst": "b", "status": "done",
                            "note": "", "moved": []}]}
    with pytest.raises(OpsError, match="not a drive-scoped"):
        archive_plan_from_dict(payload)


def test_manifest_refuses_a_conform_action_kind(fixture_drive):
    payload = {"drive": "TESTDRIVE", "scope": "drive", "project": "260101_X",
               "archive_root": "_Archived Projects",
               "actions": [{"kind": "rename", "src": "a", "dst": "b", "status": "done",
                            "note": "", "moved": []}]}
    with pytest.raises(OpsError, match="unknown action kind"):
        archive_plan_from_dict(payload)


# ------------------------------------------------------------- invisibility

def test_archived_projects_are_invisible_to_the_scan(fixture_drive):
    _project(fixture_drive, "260101_Live")
    make_project(fixture_drive / "_Archived Projects", "260099_Dormant")

    inventory = scan_drive(fixture_drive)

    assert [p.name for p in inventory.projects] == ["260101_Live"]
    assert not is_project_dir("_Archived Projects")


def test_archived_projects_are_invisible_to_doctor(fixture_drive, capsys):
    _project(fixture_drive, "260101_Live")
    make_project(fixture_drive / "_Archived Projects", "260099_Dormant")

    assert main(["doctor", "--drive", str(fixture_drive)]) in (0, 1)
    out = capsys.readouterr().out
    assert "260099_Dormant" not in out


def test_tree_cannot_open_an_archived_project(fixture_drive, capsys):
    _project(fixture_drive)
    m = _map(fixture_drive)
    apply_archive_plan(fixture_drive, m,
                       build_archive_plan(fixture_drive, m, "260101_103 Mosco"))

    assert main(["tree", "260101_103 Mosco", "--drive", str(fixture_drive)]) == 2


# --------------------------------------------------------------------- CLI

def _archive_cli(drive: Path, *extra: str) -> int:
    return main(["archive", "260101_103 Mosco", "--drive", str(drive), *extra])


def test_archive_cli_is_a_dry_run_unless_applied(fixture_drive, capsys):
    _project(fixture_drive)
    _index_row(fixture_drive, "260101_103 Mosco")

    assert _archive_cli(fixture_drive) == 1
    out = capsys.readouterr().out
    assert "archive" in out
    assert "_Archived Projects/260101_103 Mosco" in out
    assert "dry run" in out
    assert (fixture_drive / "260101_103 Mosco").is_dir(), "a preview writes nothing"


def test_archive_cli_apply_moves_stamps_and_prints_a_manifest(fixture_drive, capsys):
    _project(fixture_drive)
    prior = _index_row(fixture_drive, "260101_103 Mosco")

    assert _archive_cli(fixture_drive, "--apply", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["drive"] == "TESTDRIVE"
    assert payload[0]["scope"] == "drive"
    action = payload[0]["actions"][0]
    assert action["kind"] == "archive"
    assert action["status"] == "done"
    assert action["index_row"] == prior
    assert (fixture_drive / "_Archived Projects" / "260101_103 Mosco").is_dir()
    row = next(line for line in (fixture_drive / "_Project Index.md")
               .read_text(encoding="utf-8").splitlines() if "260101_103 Mosco" in line)
    assert _status_cell(row).startswith("archived ")


def test_archive_cli_warns_and_still_applies(fixture_drive, capsys):
    _project(fixture_drive, files={
        "01 Model/model.rvt": "z",
        "00 Tasks/TASKS.md": "# Tasks\n\n- [ ] T-001 file the permit\n",
    })

    assert _archive_cli(fixture_drive) == 1
    out = capsys.readouterr().out
    assert "1 Revit/CAD" in out
    assert "1 open task item(s)" in out
    assert "prompt-vault" in out

    assert _archive_cli(fixture_drive, "--apply") == 0
    assert (fixture_drive / "_Archived Projects" / "260101_103 Mosco").is_dir()


def test_archive_cli_refuses_a_collision(fixture_drive, capsys):
    _project(fixture_drive)
    make_project(fixture_drive / "_Archived Projects", "260101_103 Mosco")

    assert _archive_cli(fixture_drive, "--apply") == 2
    assert "already taken" in capsys.readouterr().err
    assert (fixture_drive / "260101_103 Mosco").is_dir()


def test_unarchive_cli_round_trip_by_name(fixture_drive, capsys):
    _project(fixture_drive)
    prior = _index_row(fixture_drive, "260101_103 Mosco", status="On hold")
    assert _archive_cli(fixture_drive, "--apply") == 0
    capsys.readouterr()

    assert main(["unarchive", "260101_103 Mosco", "--drive", str(fixture_drive)]) == 1
    assert "dry run" in capsys.readouterr().out
    assert not (fixture_drive / "260101_103 Mosco").exists()

    assert main(["unarchive", "260101_103 Mosco", "--drive", str(fixture_drive),
                 "--apply"]) == 0
    assert (fixture_drive / "260101_103 Mosco" / "01 Model" / "notes.md").is_file()
    row = next(line for line in (fixture_drive / "_Project Index.md")
               .read_text(encoding="utf-8").splitlines() if "260101_103 Mosco" in line)
    assert _status_cell(row) == "Active"


def test_unarchive_revert_restores_the_row_verbatim(fixture_drive, capsys, tmp_path):
    _project(fixture_drive)
    prior = _index_row(fixture_drive, "260101_103 Mosco", status="On hold")
    assert _archive_cli(fixture_drive, "--apply", "--json") == 0
    manifest = tmp_path / "archived.json"
    manifest.write_text(capsys.readouterr().out, encoding="utf-8")

    assert main(["unarchive", "--drive", str(fixture_drive), "--revert",
                 str(manifest)]) == 1, "a revert previews unless --apply"
    assert not (fixture_drive / "260101_103 Mosco").exists()

    assert main(["unarchive", "--drive", str(fixture_drive), "--revert",
                 str(manifest), "--apply"]) == 0
    assert (fixture_drive / "260101_103 Mosco").is_dir()
    index = (fixture_drive / "_Project Index.md").read_text(encoding="utf-8")
    assert prior in index.splitlines()


def test_unarchive_revert_refuses_another_drives_manifest(fixture_drive, capsys, tmp_path):
    _project(fixture_drive)
    assert _archive_cli(fixture_drive, "--apply", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    payload[0]["drive"] = "OTHERDRIVE"
    manifest = tmp_path / "foreign.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["unarchive", "--drive", str(fixture_drive), "--revert",
                 str(manifest), "--apply"]) == 2
    assert "not TESTDRIVE" in capsys.readouterr().err
    assert (fixture_drive / "_Archived Projects" / "260101_103 Mosco").is_dir()


def test_unarchive_revert_refuses_an_unapplied_manifest(fixture_drive, capsys, tmp_path):
    _project(fixture_drive)
    assert _archive_cli(fixture_drive, "--json") == 1   # dry run: nothing applied
    manifest = tmp_path / "preview.json"
    manifest.write_text(capsys.readouterr().out, encoding="utf-8")

    assert main(["unarchive", "--drive", str(fixture_drive), "--revert",
                 str(manifest), "--apply"]) == 2
    assert (fixture_drive / "260101_103 Mosco").is_dir()


def test_unarchive_cli_errors_when_nothing_is_archived(fixture_drive, capsys):
    assert main(["unarchive", "260101_103 Mosco", "--drive", str(fixture_drive)]) == 2
    assert "nothing is archived" in capsys.readouterr().err
