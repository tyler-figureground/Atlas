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
