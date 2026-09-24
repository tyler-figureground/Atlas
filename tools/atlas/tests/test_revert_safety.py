"""conform --revert FILE gets every safety every other conform write has (#9):
a dry run unless --apply, validated paths, drive identity, a precondition
check before anything moves, --json, and an honest exit code."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.conform import OpsError, plan_from_dict

from conftest import make_project


def _applied_manifest(drive: Path, capsys, tmp_path: Path, name: str = "260801_Rev") -> tuple[Path, Path]:
    project = make_project(drive, name, sections=["01 Model", "Meetings"],
                           files={"Meetings/kickoff.md": "z"})
    assert main(["conform", "--drive", str(drive), "--project", name,
                 "--node", "Meetings", "--apply", "--json"]) == 0
    tmp_path.mkdir(parents=True, exist_ok=True)
    manifest = tmp_path / "applied.json"
    manifest.write_text(capsys.readouterr().out, encoding="utf-8")
    return project, manifest


def _revert(drive: Path, manifest: Path, *extra: str) -> int:
    return main(["conform", "--drive", str(drive), "--revert", str(manifest), *extra])


def test_conform_json_names_the_drive(fixture_drive, capsys, tmp_path):
    _project, manifest = _applied_manifest(fixture_drive, capsys, tmp_path)
    assert json.loads(manifest.read_text(encoding="utf-8"))[0]["drive"] == "TESTDRIVE"


def test_revert_is_a_dry_run_unless_applied(fixture_drive, capsys, tmp_path):
    project, manifest = _applied_manifest(fixture_drive, capsys, tmp_path)

    assert _revert(fixture_drive, manifest) == 1
    out = capsys.readouterr().out
    assert "11 Meetings -> Meetings" in out
    assert "dry run" in out
    assert (project / "11 Meetings").is_dir(), "a preview writes nothing"

    assert _revert(fixture_drive, manifest, "--apply") == 0
    assert (project / "Meetings" / "kickoff.md").is_file()


def test_revert_honours_json(fixture_drive, capsys, tmp_path):
    _project, manifest = _applied_manifest(fixture_drive, capsys, tmp_path)

    assert _revert(fixture_drive, manifest, "--apply", "--json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["drive"] == "TESTDRIVE"
    assert [(a["kind"], a["src"], a["dst"], a["status"]) for a in payload[0]["actions"]] == [
        ("relocate", "11 Meetings", "Meetings", "done")]


def _crafted(tmp_path: Path, drive: str, project: str, moved: list[dict]) -> Path:
    manifest = tmp_path / "crafted.json"
    manifest.write_text(json.dumps([{
        "drive": drive, "project": project,
        "actions": [{"kind": "rename", "src": "x", "dst": "y", "file_count": 0,
                     "status": "done", "note": "", "moved": moved, "path_length": 0}],
    }]), encoding="utf-8")
    return manifest


@pytest.mark.parametrize("moved", [
    {"src": "../outside/Keep", "dst": "Keep", "is_dir": True},
    {"src": "Keep", "dst": "../../outside/Keep", "is_dir": True},
    {"src": "C:/Windows/Temp/x", "dst": "Keep", "is_dir": True},
    {"src": "/etc/x", "dst": "Keep", "is_dir": True},
    {"src": "Keep", "dst": "", "is_dir": True},
])
def test_a_manifest_path_that_leaves_the_project_is_refused(fixture_drive, tmp_path, capsys, moved):
    """Verified in the audit: a crafted manifest moved a file from beside the
    drive root into the project, without --apply, rc 0."""
    make_project(fixture_drive, "260802_Target", sections=["01 Model"])
    outside = tmp_path / "outside" / "Keep"
    outside.mkdir(parents=True)
    (outside / "precious.txt").write_text("x", encoding="utf-8")

    manifest = _crafted(tmp_path, "TESTDRIVE", "260802_Target", [moved])
    assert _revert(fixture_drive, manifest, "--apply") == 2
    assert (outside / "precious.txt").is_file()


@pytest.mark.parametrize("project", ["..", ".", "a/b", "C:\\x", ""])
def test_a_manifest_project_that_is_not_one_folder_is_refused(fixture_drive, tmp_path, capsys, project):
    manifest = _crafted(tmp_path, "TESTDRIVE", project,
                        [{"src": "Meetings", "dst": "11 Meetings", "is_dir": True}])
    assert _revert(fixture_drive, manifest, "--apply") == 2


def test_plan_from_dict_refuses_an_escaping_path():
    with pytest.raises(OpsError):
        plan_from_dict({"project": "P", "actions": [{
            "kind": "sweep", "src": "../a.txt", "dst": "", "file_count": 0, "status": "done",
            "note": "", "moved": [], "path_length": 0}]})


@pytest.mark.parametrize("field", ["created", "prune"])
@pytest.mark.parametrize("bad", ["../../outside", "C:/Windows", "/etc", ""])
def test_plan_from_dict_refuses_an_escaping_created_or_prune(field, bad):
    """Both name folders an undo will rmdir; they obey the same path rule."""
    with pytest.raises(OpsError):
        plan_from_dict({"project": "P", "actions": [{
            "kind": "rename", "src": "a", "dst": "b", "file_count": 0, "status": "done",
            "note": "", "moved": [], "path_length": 0, field: [bad]}]})


def test_node_key_normalises_and_joins_as_one_function():
    from atlas.core.conform import child_key, node_key

    assert node_key("08 OUT\\Invoices/") == "08 OUT/Invoices"
    assert node_key("", "Meetings") == "Meetings" == child_key("", "Meetings")
    assert child_key("11 Meetings", "a.md") == "11 Meetings/a.md"


def test_a_manifest_from_another_drive_is_refused(fixture_drive, capsys, tmp_path):
    project, manifest = _applied_manifest(fixture_drive, capsys, tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload[0]["drive"] = "OTHERDRIVE"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    assert _revert(fixture_drive, manifest, "--apply") == 2
    assert "OTHERDRIVE" in capsys.readouterr().err
    assert (project / "11 Meetings").is_dir()


def test_a_manifest_with_no_drive_is_refused(fixture_drive, capsys, tmp_path):
    _project, manifest = _applied_manifest(fixture_drive, capsys, tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    del payload[0]["drive"]
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    assert _revert(fixture_drive, manifest, "--apply") == 2


def test_revert_checks_every_project_before_moving_anything(fixture_drive, capsys, tmp_path):
    """A multi-project manifest used to stop halfway with no summary."""
    first, manifest_a = _applied_manifest(fixture_drive, capsys, tmp_path / "a", "260803_A")
    second, manifest_b = _applied_manifest(fixture_drive, capsys, tmp_path / "b", "260804_B")
    both = json.loads(manifest_a.read_text(encoding="utf-8")) + \
        json.loads(manifest_b.read_text(encoding="utf-8"))
    (second / "11 Meetings").rename(second / "Somewhere Else")
    manifest = tmp_path / "both.json"
    manifest.write_text(json.dumps(both), encoding="utf-8")

    assert _revert(fixture_drive, manifest, "--apply") == 2
    assert "11 Meetings" in capsys.readouterr().err
    assert (first / "11 Meetings").is_dir(), "nothing moved in the first project either"


def test_a_revert_that_leaves_work_undone_exits_1(fixture_drive, capsys, tmp_path):
    """Forward --apply exits 1 on a conflict; --revert returned 0 and left a
    half-undone project."""
    project, manifest = _applied_manifest(fixture_drive, capsys, tmp_path)
    (project / "Meetings").mkdir()
    (project / "Meetings" / "kickoff.md").write_text("someone else's", encoding="utf-8")

    assert _revert(fixture_drive, manifest, "--apply") == 1
