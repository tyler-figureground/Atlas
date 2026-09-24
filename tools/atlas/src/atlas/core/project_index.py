"""Safe drive-wide project index creation, migration, and append."""

from __future__ import annotations

import hashlib
import os
import re
from contextlib import contextmanager
from pathlib import Path
import tempfile
import time
from uuid import uuid4

from .intake import ProjectIntake
from .mapfile import DriveMap


__all__ = [
    "ProjectIndexError",
    "append_project_index_row",
    "preflight_project_index",
    "update_project_index_row",
]


INDEX_NAME = "_Project Index.md"
LEGACY_HEADER = "| Project folder | Created | Descriptor | Status |"
LEGACY_SEPARATOR = "|---|---|---|---|"
EXPANDED_HEADER = (
    "| Project folder | Project name | Full project address | Project use case | "
    "Created | Description | Status |"
)
EXPANDED_SEPARATOR = "|---|---|---|---|---|---|---|"


class ProjectIndexError(Exception):
    """Project index shape or persistence is unsafe to change."""


def _crlf_bytes(lines: list[str]) -> bytes:
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


_STALE_LOCK_SECONDS = 600


@contextmanager
def _index_lock(path: Path):
    lock = path.with_suffix(path.suffix + ".lock")
    descriptor: int | None = None
    for attempt in range(2):
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                stale = time.time() - lock.stat().st_mtime > _STALE_LOCK_SECONDS
            except FileNotFoundError:
                continue
            except OSError as error:
                raise ProjectIndexError(f"cannot inspect project-index lock {lock}: {error}") from error
            if stale and attempt == 0:
                try:
                    lock.unlink()
                except FileNotFoundError:
                    pass
                except OSError as error:
                    raise ProjectIndexError(
                        f"stale project-index lock must be removed manually: {lock}: {error}"
                    ) from error
                continue
            raise ProjectIndexError(
                f"project index is being updated. Wait a moment and retry. "
                f"If no Atlas operation is running after 10 minutes, remove {lock}."
            ) from None
        except OSError as error:
            raise ProjectIndexError(f"cannot lock project index {path}: {error}") from error
    if descriptor is None:
        raise ProjectIndexError(f"cannot acquire project-index lock {lock}")
    try:
        os.write(descriptor, f"pid={os.getpid()} created={time.time()}\n".encode("ascii"))
        os.close(descriptor)
        descriptor = None
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            lock.unlink(missing_ok=True)
        except OSError:
            pass


def _atomic_write(path: Path, contents: bytes, expected: bytes | None) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            current = path.read_bytes()
        except FileNotFoundError:
            current = None
        except OSError as error:
            raise ProjectIndexError(
                f"cannot verify project index {path}: {error}; index unchanged"
            ) from error
        if current != expected:
            raise ProjectIndexError(
                f"project index changed while preparing update: {path}; external change preserved"
            )
        os.replace(temporary, path)
        temporary = None
    except OSError as error:
        raise ProjectIndexError(
            f"cannot atomically write {path}: {error}; index unchanged"
        ) from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _split_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in stripped[1:-1]:
        if character == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        if character == "\\":
            escaped = not escaped
        else:
            escaped = False
    cells.append("".join(current).strip())
    return cells


def _move_legacy_to_backup(path: Path) -> Path:
    """Move, rather than copy, so concurrent writers can never be overwritten."""

    logs = path.parent / "_tools" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    backup = logs / f"Project-Index-pre-migration-{uuid4().hex}.md"
    try:
        os.replace(path, backup)
    except OSError as error:
        raise ProjectIndexError(
            f"cannot move legacy project index to backup {backup}: {error}; index unchanged"
        ) from error
    return backup


def _validate_table(
    path: Path,
    lines: list[str],
    header_index: int,
    separator: str,
    column_count: int,
) -> None:
    if header_index + 1 >= len(lines) or lines[header_index + 1].strip() != separator:
        raise ProjectIndexError(
            f"{path} has an unknown project-index table shape; index unchanged"
        )
    for line in lines[header_index + 2 :]:
        cells = _split_table_row(line)
        if cells is None:
            break
        if len(cells) != column_count:
            raise ProjectIndexError(
                f"{path} has an unknown project-index table shape; index unchanged"
            )


def _migrate_legacy(
    path: Path, contents: bytes, lines: list[str], header_index: int
) -> None:
    _validate_table(path, lines, header_index, LEGACY_SEPARATOR, 4)
    backup = _move_legacy_to_backup(path)
    try:
        moved_contents = backup.read_bytes()
        moved_lines = moved_contents.decode("utf-8").splitlines()
        moved_header = next(
            index for index, line in enumerate(moved_lines) if line.strip() == LEGACY_HEADER
        )
        _validate_table(backup, moved_lines, moved_header, LEGACY_SEPARATOR, 4)
        migrated = moved_lines[:moved_header] + [EXPANDED_HEADER, EXPANDED_SEPARATOR]
        row_index = moved_header + 2
        while row_index < len(moved_lines):
            cells = _split_table_row(moved_lines[row_index])
            if cells is None:
                break
            if len(cells) != 4:
                raise ProjectIndexError(
                    f"{backup} has an unknown project-index table shape; migration stopped"
                )
            folder, created, description, status = cells
            migrated.append(f"| {folder} |  |  |  | {created} | {description} | {status} |")
            row_index += 1
        migrated.extend(moved_lines[row_index:])
        with path.open("xb") as stream:
            stream.write(_crlf_bytes(migrated))
            stream.flush()
            os.fsync(stream.fileno())
    except (OSError, UnicodeDecodeError, StopIteration, ProjectIndexError) as error:
        if not path.exists():
            try:
                os.replace(backup, path)
            except OSError:
                pass
        if isinstance(error, ProjectIndexError):
            raise
        raise ProjectIndexError(
            f"cannot create expanded project index {path}: {error}; legacy data preserved"
        ) from error


def _prepare_locked(path: Path, drive_map: DriveMap) -> Path:
    if not path.exists():
        _atomic_write(
            path,
            _crlf_bytes(
                [
                    f"# {drive_map.drive} - Project Index",
                    "",
                    "Auto-maintained by Atlas. One row per project (searchable table of contents).",
                    "",
                    EXPANDED_HEADER,
                    EXPANDED_SEPARATOR,
                ]
            ),
            None,
        )
        return path
    try:
        contents = path.read_bytes()
        lines = contents.decode("utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise ProjectIndexError(
            f"cannot read UTF-8 project index {path}: {error}; index unchanged"
        ) from error
    expanded_indexes = [
        index for index, line in enumerate(lines) if line.strip() == EXPANDED_HEADER
    ]
    if expanded_indexes:
        _validate_table(path, lines, expanded_indexes[0], EXPANDED_SEPARATOR, 7)
        return path
    try:
        header_index = next(
            index for index, line in enumerate(lines) if line.strip() == LEGACY_HEADER
        )
    except StopIteration:
        raise ProjectIndexError(
            f"{path} has an unknown project-index table shape; index unchanged"
        ) from None
    _migrate_legacy(path, contents, lines, header_index)
    return path


def preflight_project_index(drive_root: Path, drive_map: DriveMap) -> Path:
    """Create or migrate a safe project index and return its path."""

    path = Path(drive_root) / INDEX_NAME
    with _index_lock(path):
        return _prepare_locked(path, drive_map)


def _table(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("|", r"\|")
    return " ".join(escaped.splitlines()).strip()


_CELL_ESCAPE = re.compile(r"\\([\\|])")


def _untable(cell: str) -> str:
    """The inverse of ``_table``: a parsed cell's text, so escaping it again
    reproduces the cell rather than doubling its backslashes."""
    return _CELL_ESCAPE.sub(r"\1", cell)


def _project_row(folder_name: str, intake: ProjectIntake, status: str = "Active") -> str:
    values = (
        folder_name,
        intake.project_name,
        intake.project_address.formatted,
        intake.project_use_case.display,
        intake.created.strftime("%Y-%m-%d"),
        intake.description,
        status,
    )
    return "| " + " | ".join(_table(value) for value in values) + " |"


def _expanded_table_bounds(path: Path, lines: list[str]) -> tuple[int, int]:
    try:
        header_index = next(
            index for index, line in enumerate(lines) if line.strip() == EXPANDED_HEADER
        )
    except StopIteration:
        raise ProjectIndexError(
            f"{path} has an unknown project-index table shape; index unchanged"
        ) from None
    _validate_table(path, lines, header_index, EXPANDED_SEPARATOR, 7)
    row_end = header_index + 2
    while row_end < len(lines) and _split_table_row(lines[row_end]) is not None:
        row_end += 1
    return header_index, row_end


def append_project_index_row(
    drive_root: Path,
    drive_map: DriveMap,
    folder_name: str,
    intake: ProjectIntake,
) -> None:
    """Append one expanded, non-sensitive row rendered from project intake."""

    path = Path(drive_root) / INDEX_NAME
    with _index_lock(path):
        _prepare_locked(path, drive_map)
        row = _project_row(folder_name, intake)
        try:
            existing_contents = path.read_bytes()
            lines = existing_contents.decode("utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as error:
            raise ProjectIndexError(
                f"cannot read UTF-8 project index {path}: {error}; index unchanged"
            ) from error
        _, row_end = _expanded_table_bounds(path, lines)
        lines.insert(row_end, row)
        updated = _crlf_bytes(lines)
        _atomic_write(path, updated, existing_contents)


def update_project_index_row(
    drive_root: Path,
    drive_map: DriveMap,
    old_folder_name: str,
    new_folder_name: str,
    intake: ProjectIntake,
    *,
    expected_digest: str,
) -> None:
    """Replace one row or append a missing row, refusing stale or ambiguous state."""

    path = Path(drive_root) / INDEX_NAME
    with _index_lock(path):
        try:
            contents = path.read_bytes()
            lines = contents.decode("utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as error:
            raise ProjectIndexError(
                f"cannot read UTF-8 project index {path}: {error}; index unchanged"
            ) from error
        if hashlib.sha256(contents).hexdigest() != expected_digest:
            raise ProjectIndexError(
                f"project index changed since preview: {path}; review changes and retry"
            )
        header_index, row_end = _expanded_table_bounds(path, lines)
        matches: list[int] = []
        for index in range(header_index + 2, row_end):
            cells = _split_table_row(lines[index])
            assert cells is not None
            if _untable(cells[0]) == old_folder_name:
                matches.append(index)
        if len(matches) > 1:
            raise ProjectIndexError(
                f"project index has duplicate matching rows for '{old_folder_name}'; index unchanged"
            )
        if not matches:
            lines.insert(row_end, _project_row(new_folder_name, intake))
        else:
            existing_cells = _split_table_row(lines[matches[0]])
            assert existing_cells is not None
            lines[matches[0]] = _project_row(
                new_folder_name, intake, _untable(existing_cells[6])
            )
        _atomic_write(path, _crlf_bytes(lines), contents)
