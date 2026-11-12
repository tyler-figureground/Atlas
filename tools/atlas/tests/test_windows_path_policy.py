"""#95: public Plan/apply behavior at the legacy Windows boundaries."""
import os
import sys
from pathlib import Path

import pytest

from atlas.core.conform import Action, Plan, RELOCATE, SWEEP, apply_plan, measure_plan
from atlas.core.mapfile import load_map
from atlas.core.scan import long_path
from conftest import write_map

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="native Windows filesystem")


def target_at(project, length, suffix):
    parent = project / ("p" * 40)
    name = "n" * (length - len(str(parent)) - 1 - len(suffix)) + suffix
    assert 1 < len(name) <= 255
    return parent / name


@windows_only
@pytest.mark.parametrize("length,allowed", [(247, True), (248, False), (259, False), (260, False)])
@pytest.mark.parametrize("suffix", [" ", "."])
@pytest.mark.parametrize("prefixed", [False, True])
def test_exact_directory_destination_never_bypasses_legacy_limit(tmp_path, length, allowed, suffix, prefixed):
    drive = tmp_path
    m = load_map(write_map(drive))
    project = drive / "project"
    source = project / "source"
    source.mkdir(parents=True)
    (source / "proof.txt").write_text("retained", encoding="utf-8")
    target = target_at(project, length, suffix)
    action = Action(RELOCATE, "source", target.relative_to(project).as_posix())
    if prefixed:
        project = Path("\\\\?\\" + str(project))
    result = apply_plan(drive, project, m, Plan(project.name, (action,))).actions[0]
    assert result.status == ("done" if allowed else "failed"), result.note
    assert os.path.isdir(long_path(target)) is allowed
    assert source.exists() is not allowed
    if allowed:
        assert Path(long_path(target / "proof.txt")).read_text(encoding="utf-8") == "retained"
        assert target.name in os.listdir(long_path(target.parent))
    else:
        assert not result.moved
        assert (source / "proof.txt").read_text(encoding="utf-8") == "retained"


@windows_only
@pytest.mark.parametrize("length,allowed", [(247, True), (248, False), (259, False)])
def test_native_legacy_directory_creation_boundary(tmp_path, length, allowed):
    # ANSI API deliberately tests the legacy limit even on a longPathAware Python.
    import ctypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateDirectoryA
    create.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
    create.restype = ctypes.c_int
    target = target_at(tmp_path, length, "")
    target.parent.mkdir()
    assert bool(create(os.fsencode(target), None)) is allowed
    if not allowed:
        assert ctypes.get_last_error() == 206  # ERROR_FILENAME_EXCED_RANGE


@pytest.mark.parametrize("length,warning", [(259, False), (260, True), (261, True)])
def test_file_warning_includes_the_refusal_boundary(length, warning):
    assert Action(SWEEP, "a", "b", path_length=length).path_warning is warning


@windows_only
@pytest.mark.parametrize("length,allowed", [(259, True), (260, False)])
@pytest.mark.parametrize("suffix", [" ", "."])
def test_exact_file_destination_boundary(tmp_path, length, allowed, suffix):
    m = load_map(write_map(tmp_path))
    project = tmp_path / "project"
    project.mkdir()
    target = target_at(project, length, suffix)
    source = project / target.name
    Path(long_path(source)).write_text("retained", encoding="utf-8")
    action = Action(SWEEP, source.name, target.parent.relative_to(project).as_posix())
    measured = measure_plan(Plan(project.name, (action,)), project)
    assert measured.actions[0].path_length == length
    assert measured.actions[0].path_warning is not allowed
    result = apply_plan(tmp_path, project, m, measured).actions[0]
    assert result.status == ("done" if allowed else "failed"), result.note
    assert os.path.isfile(long_path(target)) is allowed
    assert os.path.isfile(long_path(source)) is not allowed
    if allowed:
        assert target.name in os.listdir(long_path(target.parent))


@windows_only
@pytest.mark.parametrize("length", [258, 259, 260])
def test_extended_unc_preview_counts_the_two_leading_slashes_not_unc_marker(length):
    # No network access: SWEEP measurement is lexical, not a share probe.
    project = Path("\\\\?\\UNC\\server\\share\\project")
    leaf = "x" * (length - len("\\\\server\\share\\project\\") - 1) + "."
    action = Action(SWEEP, leaf, "")
    measured = measure_plan(Plan("project", (action,)), project).actions[0]
    assert measured.path_length == length
    assert measured.path_warning is (length >= 260)


@windows_only
@pytest.mark.parametrize("suffix", [" ", "."])
def test_preview_preserves_exact_project_root_name(tmp_path, suffix):
    project = tmp_path / ("project" + suffix)
    os.makedirs(long_path(project))
    target = target_at(project, 260, "")
    source = project / target.name
    source_path = Path(long_path(source))
    source_path.write_text("retained", encoding="utf-8")
    action = Action(SWEEP, source.name, target.parent.relative_to(project).as_posix())
    measured = measure_plan(Plan(project.name, (action,)), project).actions[0]
    assert measured.path_length == 260
    assert measured.path_warning
    assert source_path.read_text(encoding="utf-8") == "retained"


@pytest.mark.parametrize("directory,limit", [(False, 260), (True, 248)])
@pytest.mark.parametrize("delta", [-2, -1, 0])
def test_unc_write_adapter_uses_normal_unc_length(monkeypatch, directory, limit, delta):
    import ntpath
    from types import SimpleNamespace
    from atlas.core import scan
    from atlas.core.conform import _dest

    # Filesystem adapter seam: no live share or platform-global patching.
    monkeypatch.setattr(scan, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(scan, "os", SimpleNamespace(fspath=os.fspath, path=ntpath))
    raw = "\\\\server\\share\\" + "x" * (limit + delta - len("\\\\server\\share\\") - 1) + "."
    if delta < 0:
        assert _dest(raw, directory=directory) == "\\\\?\\UNC\\" + raw[2:]
    else:
        with pytest.raises(OSError):
            _dest(raw, directory=directory)
