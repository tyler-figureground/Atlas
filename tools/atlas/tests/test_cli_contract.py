"""The CLI's contract with a script: output encoding, exit codes, and inputs it
must refuse. Fixture drives only."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from atlas.cli import main

from conftest import FIXTURE_MAP, agent_files, make_project, write_map


def _run(*args: str, encoding: str = "cp1252") -> subprocess.CompletedProcess:
    """The CLI in a real subprocess, stdout piped - the way a script sees it."""
    env = {**os.environ, "PYTHONIOENCODING": encoding}
    env.pop("PYTHONUTF8", None)
    return subprocess.run(
        [sys.executable, "-m", "atlas.cli", *args],
        capture_output=True, env=env, timeout=120,
    )


# ------------------------------------------------------------ encoding (#28)


def test_json_output_survives_a_cp1252_pipe(fixture_drive):
    """A redirected stdout on Windows is cp1252. A Vietnamese name used to crash
    after the contact was already written, so a retry failed as a duplicate."""
    added = _run("contacts", "add", "--drive", str(fixture_drive),
                 "--first-name", "Thảo", "--last-name", "Nguyễn",
                 "--email", "thao@example.com", "--json")
    assert added.returncode == 0, added.stderr.decode("utf-8", "replace")
    assert json.loads(added.stdout.decode("utf-8"))["last_name"] == "Nguyễn"

    listed = _run("contacts", "list", "--drive", str(fixture_drive), "--json")
    assert listed.returncode == 0, listed.stderr.decode("utf-8", "replace")
    assert json.loads(listed.stdout.decode("utf-8"))[0]["first_name"] == "Thảo"


def test_text_output_survives_a_cp1252_pipe(fixture_drive):
    make_project(fixture_drive, "260903_Nguyễn House", sections=["01 Model"])
    doctor = _run("doctor", "--drive", str(fixture_drive))
    assert doctor.returncode in (0, 1), doctor.stderr.decode("utf-8", "replace")
    assert "260903_Nguyễn House" in doctor.stdout.decode("utf-8")


# ------------------------------------------------------------ exit codes (#27)
#
# 0 clean, 1 findings or pending work, 2 error. A script must be able to tell
# "the drive has drift" from "the command failed".

NEW_ARGS = ["--name", "Oak", "--street", "1 Oak Street", "--city", "Oakland",
            "--state", "CA", "--zip", "94612", "--use-case", "Renovation",
            "--billing-contact", "nobody@example.com"]

MAP_COMMANDS = {
    "lint": ["lint"],
    "doctor": ["doctor"],
    "conform": ["conform", "--all"],
    "clean": ["clean", "--project", "260101_P"],
    "add": ["add", "--project", "260101_P", "--section", "01 Model"],
    "new": ["new", *NEW_ARGS],
    "project edit": ["project", "edit", "260101_P", "--yes", "--name", "X"],
}


def _with_drive(argv: list[str], drive: Path) -> list[str]:
    # --drive belongs to the leaf subcommand, after any nested command word.
    split = 2 if argv[0] == "project" else 1
    return [*argv[:split], "--drive", str(drive), *argv[split:]]


@pytest.mark.parametrize("name", [*MAP_COMMANDS, "contacts list"])
def test_a_drive_without_a_map_is_an_error_not_a_finding(tmp_path, capsys, name):
    argv = MAP_COMMANDS.get(name, ["contacts", "list"])
    if name == "contacts list":
        argv = ["contacts", "list"]
        full = ["contacts", "list", "--drive", str(tmp_path)]
    else:
        full = _with_drive(argv, tmp_path)
    assert main(full) == 2
    assert "error" in capsys.readouterr().err


@pytest.mark.parametrize("name", list(MAP_COMMANDS))
def test_an_unparseable_map_is_an_error_everywhere(fixture_drive, capsys, name):
    make_project(fixture_drive, "260101_P", sections=["01 Model"])
    (fixture_drive / "_tools" / "testdrive-map.json").write_text("{not json", encoding="utf-8")
    assert main(_with_drive(MAP_COMMANDS[name], fixture_drive)) == 2
    captured = capsys.readouterr()
    assert "error" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("name", list(MAP_COMMANDS))
def test_a_map_of_the_wrong_shape_is_refused_as_a_map_error(fixture_drive, capsys, name):
    """`"relocations": []` used to reach lint as an AttributeError traceback."""
    make_project(fixture_drive, "260101_P", sections=["01 Model"])
    write_map(fixture_drive, {**FIXTURE_MAP, "relocations": []})
    assert main(_with_drive(MAP_COMMANDS[name], fixture_drive)) == 2
    assert "relocations" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [
    ["clean", "--project", "260199_Nope"],
    ["add", "--project", "260199_Nope", "--section", "01 Model"],
    ["project", "edit", "260199_Nope", "--yes", "--name", "X"],
    ["conform", "--project", "260199_Nope"],
])
def test_an_unknown_project_is_an_error(fixture_drive, capsys, argv):
    assert main(_with_drive(argv, fixture_drive)) == 2
    assert "260199_Nope" in capsys.readouterr().err


def test_an_os_error_is_an_error_not_a_traceback(fixture_drive, capsys, monkeypatch):
    import atlas.cli as cli

    def boom(*_args, **_kwargs):
        raise PermissionError(13, "Access is denied", "somewhere")

    monkeypatch.setattr(cli, "scan_drive", boom)
    assert main(["doctor", "--drive", str(fixture_drive), "--json"]) == 2
    assert "Access is denied" in capsys.readouterr().err


def _conformed_project(drive: Path, name: str, extra: dict[str, str] | None = None) -> Path:
    files = {
        "PROJECT.md": "---\nproject: x\n---\n# x\n",
        "decisions/README.md": "x",
        **agent_files(drive),
        **(extra or {}),
    }
    return make_project(drive, name,
                        sections=["01 Model", "06 Research/Code", "08 OUT", "11 Meetings"],
                        files=files)


def test_conform_does_not_call_a_project_with_unfiled_leftovers_ok(fixture_drive, capsys):
    """Nothing Atlas can repair is not the same as nothing wrong: doctor says
    UNFILED and exits 1, so conform must not print OK and exit 0."""
    _conformed_project(fixture_drive, "260102_Leftovers", {"Random Stuff/a.txt": "x"})

    assert main(["doctor", "--drive", str(fixture_drive)]) == 1
    capsys.readouterr()

    assert main(["conform", "--drive", str(fixture_drive),
                 "--project", "260102_Leftovers"]) == 1
    out = capsys.readouterr().out
    assert "[OK" not in out
    assert "need a person" in out


# ------------------------------------------------------- --project (#14)


def _escape_setup(tmp_path: Path) -> tuple[Path, Path]:
    """A drive beside another drive, each with an empty seeded skeleton."""
    drive = tmp_path / "drive2"
    drive.mkdir()
    write_map(drive)
    make_project(drive, "260101_ProjA", sections=["01 Model", "06 Research/Code"])
    other = tmp_path / "otherdrive"
    make_project(other, "ProjZ", sections=["01 Model"])
    return drive, other


@pytest.mark.parametrize("bad", ["..", ".", "260101_ProjA/01 Model",
                                 "260101_ProjA\\01 Model", "_tools", "ABSOLUTE"])
def test_clean_refuses_a_project_that_is_not_one_folder_on_this_drive(tmp_path, capsys, bad):
    drive, other = _escape_setup(tmp_path)
    if bad == "ABSOLUTE":
        bad = str(other / "ProjZ")

    assert main(["clean", "--drive", str(drive), "--project", bad, "--apply", "--json"]) == 2
    assert "error" in capsys.readouterr().err
    assert (drive / "260101_ProjA" / "01 Model").is_dir()
    assert (drive / "260101_ProjA" / "06 Research" / "Code").is_dir()
    assert (other / "ProjZ" / "01 Model").is_dir()


@pytest.mark.parametrize("bad", ["..", "."])
def test_add_refuses_the_drive_root_as_a_project(fixture_drive, capsys, bad):
    assert main(["add", "--drive", str(fixture_drive), "--project", bad,
                 "--section", "10 Legal"]) == 2
    assert not (fixture_drive / "10 Legal").exists()
    assert not (fixture_drive.parent / "10 Legal").exists()


def test_project_edit_refuses_a_path_for_a_folder(fixture_drive, capsys):
    assert main(["project", "edit", "--drive", str(fixture_drive), "..",
                 "--yes", "--name", "X"]) == 2


def test_a_real_project_still_resolves(fixture_drive, capsys):
    make_project(fixture_drive, "260101_Fine", sections=["01 Model", "Empty"])
    assert main(["clean", "--drive", str(fixture_drive), "--project", "260101_Fine",
                 "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["empty"] == ["Empty"]


# ------------------------------------------------------- --node (#29)


def _node_project(drive: Path) -> Path:
    return make_project(
        drive, "260201_Node",
        sections=["01 Model", "Meetings", "08 OUT/Invoices", "10 Legal"],
        files={"Meetings/kickoff.md": "z", "08 OUT/Invoices/INV-1.pdf": "z"},
    )


@pytest.mark.parametrize("spelling", ["08 OUT\\Invoices", "08 OUT/Invoices/", "/08 OUT/Invoices"])
def test_node_is_normalised_to_the_node_key_before_matching(fixture_drive, capsys, spelling):
    _node_project(fixture_drive)
    assert main(["conform", "--drive", str(fixture_drive), "--project", "260201_Node",
                 "--node", spelling, "--json"]) == 1
    actions = [a for p in json.loads(capsys.readouterr().out) for a in p["actions"]]
    assert [(a["kind"], a["src"]) for a in actions] == [("relocate", "08 OUT/Invoices")]


@pytest.mark.parametrize("missing", ["No Such Folder", "meetings"])
def test_a_node_that_is_not_there_is_an_error_not_ok(fixture_drive, capsys, missing):
    _node_project(fixture_drive)
    assert main(["conform", "--drive", str(fixture_drive), "--project", "260201_Node",
                 "--node", missing]) == 2
    captured = capsys.readouterr()
    assert "no such node" in captured.err
    assert "[OK" not in captured.out


def test_a_missing_expectation_is_still_a_node_conform_can_backfill(fixture_drive, capsys):
    """A backfill's node does not exist yet - that is the point of it."""
    _node_project(fixture_drive)
    assert main(["conform", "--drive", str(fixture_drive), "--project", "260201_Node",
                 "--node", "PROJECT.md", "--json"]) == 1
    actions = [a for p in json.loads(capsys.readouterr().out) for a in p["actions"]]
    assert [(a["kind"], a["dst"]) for a in actions] == [("backfill", "PROJECT.md")]


@pytest.mark.parametrize("extra", [["--project", "260201_Node"], ["--node", "Meetings"],
                                   ["--project", "260201_Node", "--node", "Meetings"]])
def test_all_cannot_be_combined_with_project_or_node(fixture_drive, capsys, extra):
    project = _node_project(fixture_drive)
    make_project(fixture_drive, "260202_Other", sections=["01 Model", "Meetings"])
    assert main(["conform", "--drive", str(fixture_drive), "--all", *extra, "--apply"]) == 2
    assert "--all" in capsys.readouterr().err
    assert (project / "Meetings").is_dir()
    assert (fixture_drive / "260202_Other" / "Meetings").is_dir()
