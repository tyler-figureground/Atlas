"""Drive-wide name search: the session Name Index (ticket 33).

Ticket 08 settled the mechanics on the measured cost classes (ticket 12): one
4.24 s walk of the whole drive, run once per session on a background worker,
buys a drive-wide name search with **zero content reads**. This module is that
walk plus the matcher over it. Names only - content search waits for the
per-machine index (tickets 34, 35), and Markdown waits with the PDFs.

The walk is ``core.scan.walk``, so the standing rules come with it: junctions
are never followed, every level takes ``long_path``, and a folder that cannot
be opened is recorded on the index rather than vanishing the way
``Path.rglob`` would vanish it (ticket 06).

Two scopes are walked: the live project roots at the drive root, and the
**Archived Projects** - each folder directly under the map's
``controlPlane.archiveRoot`` (plan Q3, ruled 2026-10-16: the archive is mapped
read-only so search reaches it). Every other ``_``-root stays out: drive-root
files and the control plane are not search results. Search is the only
surface that sees the archive - the project list, doctor, conform, runs and
the console tree still never do (ADR 0019) - and nothing here writes. Every
hit carries ``archived``; live hits always rank first, so the archive never
buries current work.

The dossier facts ticket 08 names are not read here - "zero content reads" is
taken literally, and a ``PROJECT.md`` per project is a content read. The
project folder name already carries the short address and description by
naming convention; dossier fields join when an in-session parse exists
(ticket 36), through this same matcher.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .mapfile import DEFAULT_ARCHIVE_ROOT, find_map, load_map
from .scan import is_project_dir, long_path, walk

# Ticket 12's count cap, reused: a query broader than this is answered with
# the first page and the count of what it is not showing.
RESULT_CAP = 500


@dataclass(frozen=True)
class NameHit:
    """One folder or file whose name or path matched."""

    project: str  # the project folder the hit sits in (its own name, live or archived)
    path: str     # drive-relative, forward-slashed; archived hits keep the archive prefix
    name: str     # the entry's own name
    is_dir: bool
    archived: bool = False
    # The project folder's drive-relative path when it is not the project
    # name itself - "_Archived Projects/<project>" for an archived hit.
    root: str = ""

    @property
    def kind(self) -> str:
        return "folder" if self.is_dir else "file"

    @property
    def node_key(self) -> str:
        """The hit as a Node Key inside its project; "" for the project itself."""
        prefix = f"{self.root or self.project}/"
        return self.path[len(prefix):] if self.path.startswith(prefix) else ""


@dataclass(frozen=True)
class ProjectRoot:
    """One project folder search walks: drive-relative path, name, scope."""

    path: str
    project: str
    archived: bool = False


def resolve_archive_root(root: Path | str) -> str:
    """The drive map's archive root, or the default where there is no map.

    Search is read-only and never refuses over the archive: a map that will
    not load falls back to the default the rest of Atlas uses (ADR 0019).
    """
    try:
        map_path = find_map(Path(root))
        if map_path is not None:
            return load_map(map_path).archive_root
    except Exception:  # noqa: BLE001 - the map's own commands report it
        pass
    return DEFAULT_ARCHIVE_ROOT


def _is_link(path: str) -> bool:
    try:
        return os.path.islink(path) or os.path.isjunction(path)
    except OSError:
        return True     # cannot tell: never descend


def project_roots(root: Path | str, *, archive_root: str | None = None,
                  archived: bool = True,
                  errors: list[tuple[str, str]] | None = None) -> list[ProjectRoot]:
    """The project folders search walks, live first, each scope name-sorted.

    Two enumerations: the drive root, and the archive root when it exists. A
    drive with no archive yet is the normal state, not an unreadable folder;
    an archive root that exists but cannot be opened is recorded in
    ``errors``. Links are never roots, live or archived.
    """
    base = os.fspath(root)
    top = next(walk(base, errors=errors), None)
    if top is None:
        return []
    roots = [ProjectRoot(d, d) for d in sorted(top[1], key=str.casefold)
             if is_project_dir(d)]
    if not archived:
        return roots
    archive_root = archive_root if archive_root is not None else resolve_archive_root(base)
    archive = os.path.join(base, *archive_root.split("/"))
    if _is_link(archive) or not os.path.isdir(long_path(archive)):
        return roots
    listed = next(walk(archive, errors=errors), None)
    if listed is not None:
        roots.extend(ProjectRoot(f"{archive_root}/{d}", d, True)
                     for d in sorted(listed[1], key=str.casefold) if is_project_dir(d))
    return roots


def walk_project(base: str, project_root: ProjectRoot,
                 errors: list[tuple[str, str]] | None = None):
    """``core.scan.walk`` over one project folder, yielding ``(folder,
    drive-relative folder, dirs, files)``. Links are leaves and dropped."""
    for folder, dirs, files, _links in walk(os.path.join(base, project_root.path),
                                            errors=errors):
        yield folder, os.path.relpath(folder, base).replace("\\", "/"), dirs, files


@dataclass(frozen=True)
class NameIndex:
    """Every folder and file name below the drive's project roots and the
    Archived Projects.

    ``unreadable`` holds ``(drive-relative path, reason)`` for each folder the
    walk could not open. A folder absent from ``entries`` because Atlas could
    not read it must never be indistinguishable from one that matched nothing
    (ADR 0004).
    """

    root: Path
    entries: tuple[NameHit, ...]
    unreadable: tuple[tuple[str, str], ...] = ()


def build_name_index(root: Path, *, archive_root: str | None = None,
                     archived: bool = True) -> NameIndex:
    """One bounded walk of the drive. Never reads a file's content.

    Links are leaves in ``walk`` and stay out of the index entirely: indexing
    a junction as a folder would invite a reveal into a tree Atlas never
    walks. ``archive_root`` defaults to the drive map's; ``archived=False``
    leaves the archive unwalked.
    """
    base = os.fspath(root)
    errors: list[tuple[str, str]] = []
    entries: list[NameHit] = []
    roots = project_roots(base, archive_root=archive_root, archived=archived,
                          errors=errors)
    for scope in (False, True):
        group = [r for r in roots if r.archived is scope]
        # The roots themselves first, so a project name is findable and ranks
        # ahead of what sits inside it.
        entries.extend(NameHit(r.project, r.path, r.project, True, r.archived,
                               r.path if r.archived else "") for r in group)
        for r in group:
            tag = r.path if r.archived else ""
            for _folder, rel, dirs, files in walk_project(base, r, errors):
                for name in sorted(dirs, key=str.casefold):
                    entries.append(NameHit(r.project, f"{rel}/{name}", name, True,
                                           r.archived, tag))
                for name in sorted(files, key=str.casefold):
                    entries.append(NameHit(r.project, f"{rel}/{name}", name, False,
                                           r.archived, tag))
    unreadable = tuple(
        (os.path.relpath(where, base).replace("\\", "/"), why) for where, why in errors
    )
    return NameIndex(root=Path(base), entries=tuple(entries), unreadable=unreadable)


@dataclass(frozen=True)
class SearchResult:
    """One query against the index. ``hits`` is capped; ``total`` is not.
    ``archived`` counts the matches in archived projects, shown or not."""

    query: str
    hits: tuple[NameHit, ...]
    total: int
    index: NameIndex
    archived: int = 0

    @property
    def overflow(self) -> int:
        """How many matches the cap is not showing."""
        return self.total - len(self.hits)


def live_first(hits):
    """Stable partition: every live hit, then every archived one."""
    hits = tuple(hits)
    return (tuple(h for h in hits if not h.archived)
            + tuple(h for h in hits if h.archived))


def search_names(index: NameIndex, query: str, *, cap: int = RESULT_CAP) -> SearchResult:
    """Case-folded substring over each entry's name and drive-relative path.

    Matching the path as well as the name costs nothing - both are already in
    memory - and lets "code zoning" narrow by where a thing sits. A blank
    query matches nothing: "everything on the drive" is a walk, not a search.
    Live hits rank before archived ones, so the cap fills with current work.
    """
    needle = query.strip().casefold()
    if not needle:
        return SearchResult(query=query, hits=(), total=0, index=index)
    matches = live_first(
        entry for entry in index.entries
        if needle in entry.name.casefold() or needle in entry.path.casefold()
    )
    return SearchResult(query=query, hits=matches[:cap], total=len(matches), index=index,
                        archived=sum(1 for m in matches if m.archived))
