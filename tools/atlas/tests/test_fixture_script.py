"""scripts/build_fixture_drive.py deletes only what it built itself (#44)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_fixture_drive.py"


def _script():
    spec = importlib.util.spec_from_file_location("build_fixture_drive", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_refuses_an_existing_folder_it_did_not_build(tmp_path):
    victim = tmp_path / "Shared drives" / "ARCHITECTURE"
    (victim / "260101_Real Project").mkdir(parents=True)
    (victim / "260101_Real Project" / "model.rvt").write_text("irreplaceable", encoding="utf-8")

    with pytest.raises(SystemExit):
        _script().build(victim)

    assert (victim / "260101_Real Project" / "model.rvt").read_text(encoding="utf-8") == "irreplaceable"


def test_builds_into_a_missing_or_empty_folder_and_rebuilds_its_own(tmp_path):
    script = _script()
    fresh = tmp_path / "fresh"
    script.build(fresh)
    assert (fresh / script.MARKER).is_file()
    assert (fresh / "_tools" / "testdrive-map.json").is_file()

    empty = tmp_path / "empty"
    empty.mkdir()
    script.build(empty)
    assert (empty / script.MARKER).is_file()

    (fresh / "leftover.txt").write_text("from a previous run", encoding="utf-8")
    script.build(fresh)
    assert not (fresh / "leftover.txt").exists()
    assert (fresh / script.MARKER).is_file()


def test_refuses_a_file(tmp_path):
    target = tmp_path / "notes.txt"
    target.write_text("keep", encoding="utf-8")
    with pytest.raises(SystemExit):
        _script().build(target)
    assert target.read_text(encoding="utf-8") == "keep"
