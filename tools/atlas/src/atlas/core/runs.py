"""Archive closed agent runs: `atlas runs`.

An agent run keeps its scratch in one folder under the map's ``runsDir``
(ADR 0011). A run is closed once nothing in it has changed for
``runRetentionDays`` and no task list or handoff names it. Closed runs are
zipped into ``archiveDir`` as one file each - one Drive item instead of
hundreds - and the folder is removed only after the zip has been read back
and found to hold every file.

Preview by default, like clean and conform. The zip is the undo: extracting it
where it came from restores the run.
"""

from __future__ import annotations

import os
import shutil
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .mapfile import DriveMap
from .ops import OpsError, append_log
from .scan import long_path

DAY = 86400


@dataclass(frozen=True)
class Run:
    name: str
    files: int
    bytes: int
    idle_days: int
    referenced_by: tuple[str, ...]   # project-relative files that name this run
    unreadable: tuple[str, ...]

    def closed(self, retention_days: int) -> bool:
        return self.idle_days >= retention_days and not self.referenced_by and not self.unreadable


@dataclass(frozen=True)
class RunResult:
    name: str
    status: str      # archived / skipped / failed
    note: str = ""
    archive: str = ""


def _walk_files(folder: Path):
    """(relative path, size, mtime) for every file below ``folder``, plus what
    could not be read. A folder Atlas cannot read is never called empty."""
    files: list[tuple[str, int, float]] = []
    unreadable: list[str] = []

    def onerror(error: OSError) -> None:
        unreadable.append(f"{error.filename}: {error.strerror or error}")

    for root, _dirs, names in os.walk(long_path(folder), onerror=onerror):
        for name in names:
            full = os.path.join(root, name)
            try:
                st = os.stat(full)
            except OSError as error:
                unreadable.append(f"{name}: {error.strerror or error}")
                continue
            rel = os.path.relpath(full, long_path(folder)).replace("\\", "/")
            files.append((rel, st.st_size, st.st_mtime))
    return files, unreadable


def _reference_texts(project: Path, m: DriveMap) -> list[tuple[str, str]]:
    """The task lists and handoffs a live run would be named in."""
    texts: list[tuple[str, str]] = []
    folders = {t.path.split("/")[0] for t in m.templates if t.path.lower().endswith("tasks.md")}
    if m.handoffs_dir:
        folders.add(m.handoffs_dir)
    for folder in sorted(folders):
        base = project / folder
        if not base.is_dir():
            continue
        for root, _dirs, names in os.walk(long_path(base)):
            for name in names:
                if not name.lower().endswith(".md"):
                    continue
                full = os.path.join(root, name)
                try:
                    with open(full, encoding="utf-8", errors="replace") as fh:
                        text = fh.read()
                except OSError:
                    continue
                rel = os.path.relpath(full, long_path(project)).replace("\\", "/")
                texts.append((rel, text))
    return texts


def list_runs(project: Path, m: DriveMap, now: float | None = None) -> list[Run]:
    if not m.runs_dir:
        raise OpsError("the drive map names no runsDir; nothing to archive")
    base = project / m.runs_dir
    if not base.is_dir():
        return []
    now = time.time() if now is None else now
    texts = _reference_texts(project, m)
    runs: list[Run] = []
    for entry in sorted(os.scandir(long_path(base)), key=lambda e: e.name):
        if not entry.is_dir(follow_symlinks=False):
            continue    # the run template and stray files are not runs
        files, unreadable = _walk_files(base / entry.name)
        newest = max((mtime for _rel, _size, mtime in files),
                     default=entry.stat(follow_symlinks=False).st_mtime)
        runs.append(Run(
            name=entry.name,
            files=len(files),
            bytes=sum(size for _rel, size, _mtime in files),
            idle_days=int((now - newest) // DAY),
            referenced_by=tuple(rel for rel, text in texts if entry.name in text),
            unreadable=tuple(unreadable),
        ))
    return runs


def archive_run(drive_root: Path, project: Path, m: DriveMap, run: Run) -> RunResult:
    """Zip one run, verify the zip, then remove the folder. Never overwrites."""
    if not m.archive_dir:
        raise OpsError("the drive map names no archiveDir; nowhere to put closed runs")
    source = project / m.runs_dir / run.name
    archive_root = project / m.archive_dir
    archive = archive_root / f"{run.name}.zip"
    if archive.exists():
        return RunResult(run.name, "skipped", f"{archive.name} already exists; left both alone")
    files, unreadable = _walk_files(source)
    if unreadable:
        return RunResult(run.name, "skipped", "part of the run could not be read")
    archive_root.mkdir(parents=True, exist_ok=True)
    partial = archive.with_suffix(".zip.partial")
    try:
        with zipfile.ZipFile(long_path(partial), "x", compression=zipfile.ZIP_DEFLATED) as zf:
            for rel, _size, _mtime in files:
                zf.write(long_path(source / rel), arcname=f"{run.name}/{rel}")
        with zipfile.ZipFile(long_path(partial)) as zf:
            if zf.testzip() is not None:
                raise OpsError("zip failed its CRC check")
            sizes = {info.filename: info.file_size for info in zf.infolist()}
        expected = {f"{run.name}/{rel}": size for rel, size, _mtime in files}
        if sizes != expected:
            raise OpsError("zip does not hold every file of the run")
        os.replace(long_path(partial), long_path(archive))
    except (OSError, OpsError, zipfile.BadZipFile) as error:
        try:
            os.remove(long_path(partial))
        except OSError:
            pass
        return RunResult(run.name, "failed", str(error))
    # Everything is in the verified zip; only now does the folder go.
    try:
        shutil.rmtree(long_path(source))
    except OSError as error:
        return RunResult(run.name, "failed", f"zipped to {archive.name}, folder not removed: {error}",
                         archive=archive.relative_to(project).as_posix())
    append_log(drive_root, f"[{project.name}] runs: archived {run.name} "
                           f"({run.files} files) -> {archive.relative_to(project).as_posix()}")
    return RunResult(run.name, "archived", f"{run.files} files", archive=archive.relative_to(project).as_posix())
