"""Read-only drive/project inventory.

Scans are dirent-driven (names + is_dir), never mtime-heavy: enumeration is the
unit of cost on the Google Drive mount, and the dirent already carries the type,
so is_dir is free. File counts recurse only into relocation-source folders, which
are small by construction.

Enumeration reports whether it succeeded. A folder Atlas could not open and a
folder with nothing in it both yield zero entries, and for a tool whose product is
"what is filed and what is missing" those must never render alike - a false
negative here reads as fact. See ADR 0004 for the Load State model.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .mapfile import DriveMap, find_map, load_map

DEFAULT_MOUNT_ROOT = Path(os.environ.get("ATLAS_MOUNT_ROOT", r"G:\Shared drives"))

# Load State, per ADR 0004. UNREAD is the state of every folder Atlas has not
# opened yet - it belongs to the tree rather than to a Listing, since a Listing
# only exists once a folder has been read. PARTIAL is modelled but not yet
# produced: no reliable way to detect a short enumeration has been found (see the
# drive-cost research).
UNREAD = "unread"
READ = "read"
UNREADABLE = "unreadable"
PARTIAL = "partial"

# Windows refuses paths over MAX_PATH unless they carry the extended-length
# prefix. The studio drive has real folders past the limit - project names repeat
# inside their own Revit backup folders - and they fail to open while their
# parents list them happily. Prefix only when close to the limit: the prefix also
# disables all path normalisation, so it is not safe to apply blindly.
_MAX_PATH = 240
_LONG_PREFIX = "\\\\?\\"


def long_path(path: Path | str) -> str:
    """Path as a string Windows will accept, even past MAX_PATH."""
    raw = os.fspath(path)
    if sys.platform != "win32" or len(raw) < _MAX_PATH or raw.startswith(_LONG_PREFIX):
        return raw
    absolute = os.path.abspath(raw)
    if absolute.startswith("\\\\"):  # UNC
        return _LONG_PREFIX + "UNC" + absolute[1:]
    return _LONG_PREFIX + absolute


@dataclass(frozen=True)
class Entry:
    name: str
    is_dir: bool


@dataclass(frozen=True)
class Listing:
    """One directory enumeration and whether it can be trusted.

    Iterates and measures as the plain tuple it replaced, so callers that only
    want the names are unchanged. Deliberately always truthy: ``if listing:``
    must not silently collapse back into ``if listing.entries:``, which is the
    exact bug this type exists to prevent.
    """

    state: str
    entries: tuple[Entry, ...] = ()
    error: str | None = None

    def __iter__(self):
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __bool__(self) -> bool:
        return True

    @property
    def readable(self) -> bool:
        return self.state != UNREADABLE


@dataclass(frozen=True)
class ProjectInventory:
    path: Path
    name: str
    root_entries: Listing = field(default_factory=lambda: Listing(state=READ))


@dataclass(frozen=True)
class DriveInventory:
    root: Path
    map: DriveMap
    projects: tuple[ProjectInventory, ...]


def discover_drives(mount_root: Path = DEFAULT_MOUNT_ROOT) -> list[Path]:
    """Drives under the mount that carry a map file."""
    if not mount_root.is_dir():
        return []
    return [d for d in sorted(mount_root.iterdir()) if d.is_dir() and find_map(d)]


def is_project_dir(name: str) -> bool:
    """Same exclusion rule the PS1 tools use: no '_' prefix, no '00 ' prefix."""
    return not (name.startswith("_") or name.startswith("00 ") or name.startswith("."))


def list_entries(path: Path) -> Listing:
    """Enumerate one directory, reporting failure rather than hiding it."""
    try:
        with os.scandir(long_path(path)) as it:
            return Listing(
                state=READ,
                entries=tuple(
                    Entry(name=e.name, is_dir=e.is_dir(follow_symlinks=False))
                    for e in it
                ),
            )
    except OSError as exc:
        return Listing(state=UNREADABLE, error=f"{type(exc).__name__}: {exc.strerror or exc}")


def exists_exact(base: Path, rel: str) -> bool:
    """Whether ``rel`` exists under ``base`` with exactly that spelling.

    ``Path.exists`` is case-insensitive on the Windows and Drive mounts, so it
    would call "meetings" present when only "Meetings" is. One listing per
    segment, which for a Node Key is a handful of enumerations.
    """
    current = base
    for segment in rel.replace("\\", "/").split("/"):
        if not segment:
            continue
        if not any(e.name == segment for e in list_entries(current)):
            return False
        current = current / segment
    return True


def scan_drive(drive_root: Path) -> DriveInventory:
    map_path = find_map(drive_root)
    if map_path is None:
        raise FileNotFoundError(f"no _tools/*-map.json under {drive_root}")
    drive_map = load_map(map_path)

    projects: list[ProjectInventory] = []
    for entry in list_entries(drive_root):
        if not entry.is_dir or not is_project_dir(entry.name):
            continue
        project_path = drive_root / entry.name
        projects.append(
            ProjectInventory(
                path=project_path,
                name=entry.name,
                root_entries=list_entries(project_path),
            )
        )
    return DriveInventory(root=drive_root, map=drive_map, projects=tuple(projects))


def count_files(path: Path) -> int:
    """Recursive file count; never follows junctions/symlinks."""
    total = 0
    for _root, _dirs, files in os.walk(long_path(path), followlinks=False):
        total += len(files)
    return total
