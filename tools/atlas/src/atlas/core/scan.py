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
# Already-extended or device paths, in either slash form. Prefixing one again
# would turn it into a bogus UNC path.
_DEVICE_PREFIXES = (_LONG_PREFIX, "\\\\.\\", "//?/", "//./")


def long_path(path: Path | str) -> str:
    """Path as a string Windows will accept, even past MAX_PATH."""
    raw = os.fspath(path)
    if sys.platform != "win32" or raw.startswith(_DEVICE_PREFIXES):
        return raw
    # Measure what Windows will see, not the string given: a 41-character
    # relative path can be 308 once the working directory is in front of it.
    absolute = os.path.abspath(raw)
    if len(absolute) < _MAX_PATH:
        return raw
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
    # The drive root's own Load State. An unreadable root yields no projects,
    # and "no projects" must never read as a healthy empty drive (ADR 0004).
    root_listing: Listing = field(default_factory=lambda: Listing(state=READ))

    @property
    def readable(self) -> bool:
        return self.root_listing.readable

    @property
    def error(self) -> str | None:
        return self.root_listing.error


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
    root_listing = list_entries(drive_root)
    for entry in root_listing:
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
    return DriveInventory(root=drive_root, map=drive_map, projects=tuple(projects),
                          root_listing=root_listing)


def _is_link(entry: os.DirEntry) -> bool:
    """A symlink or an NTFS junction. ``os.walk(followlinks=False)`` only skips
    the first: a junction answers ``islink()`` False and ``isjunction()`` True,
    so it was walked into, counted through and emptied."""
    try:
        return entry.is_symlink() or entry.is_junction()
    except OSError:
        return True     # cannot tell: never descend


def walk(top: Path | str, *, topdown: bool = True,
         errors: list[tuple[str, str]] | None = None):
    """The one recursive walk. ``os.walk``'s shape plus a fourth list, links.

    Yields ``(root, dirs, files, links)`` with ``root`` unprefixed. Differs
    from ``os.walk`` in the two ways every caller needs:

    - **Links are leaves.** Symlinks and junctions are listed in ``links`` and
      never descended into, so nothing outside the tree is counted or removed.
      A caller deciding "empty" must treat a link as content.
    - **Every level is prefixed** with ``long_path``, not only the top, so a
      short source with a deep subtree is read rather than skipped.

    A folder that cannot be listed is not yielded; with ``errors`` given, its
    path and reason are appended there instead of vanishing as ``os.walk``
    makes them vanish. An unreadable folder never reads as empty (ADR 0004).
    """
    top = os.fspath(top)
    try:
        with os.scandir(long_path(top)) as it:
            entries = list(it)
    except OSError as exc:
        if errors is not None:
            errors.append((top, f"{type(exc).__name__}: {exc.strerror or exc}"))
        return
    dirs: list[str] = []
    files: list[str] = []
    links: list[str] = []
    for entry in entries:
        if _is_link(entry):
            links.append(entry.name)
        elif entry.is_dir(follow_symlinks=False):
            dirs.append(entry.name)
        else:
            files.append(entry.name)
    if topdown:
        yield top, dirs, files, links
    for name in dirs:
        yield from walk(os.path.join(top, name), topdown=topdown, errors=errors)
    if not topdown:
        yield top, dirs, files, links


def count_files(path: Path) -> int:
    """Recursive file count; never follows junctions/symlinks."""
    return sum(len(files) for _root, _dirs, files, _links in walk(path))


@dataclass(frozen=True)
class FileTally:
    """A recursive file count and every folder it could not read on the way.

    A count with a failure in it is a lower bound, not a number: "(0 files)"
    over a folder Atlas could not list is the false negative ADR 0004 forbids.
    ``unreadable`` holds ``(path relative to the tallied folder, reason)``.
    """

    files: int
    unreadable: tuple[tuple[str, str], ...] = ()

    @property
    def known(self) -> bool:
        return not self.unreadable


def tally_files(path: Path) -> FileTally:
    """``count_files``, reporting what it could not read instead of hiding it."""
    errors: list[tuple[str, str]] = []
    total = sum(len(files) for _root, _dirs, files, _links in walk(path, errors=errors))
    base = os.fspath(path)
    return FileTally(files=total, unreadable=tuple(
        (os.path.relpath(where, base).replace("\\", "/"), why) for where, why in errors
    ))
