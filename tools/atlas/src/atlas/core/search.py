"""Drive-wide name search: the session Name Index (ticket 33).

Ticket 08 settled the mechanics on the measured cost classes (ticket 12): one
4.24 s walk of the whole drive, run once per session on a background worker,
buys a drive-wide name search with **zero content reads**. This module is that
walk plus the matcher over it. Names only - content search waits for the
per-machine index (tickets 34, 35), and Markdown waits with the PDFs.

The walk is ``core.scan.walk``, so the standing rules come with it: junctions
are never followed, every level takes ``long_path``, and a folder that cannot
be opened is recorded on the index rather than vanishing the way
``Path.rglob`` would vanish it (ticket 06). Only project roots are descended:
``_``-roots are invisible to the console on purpose (ADR 0019), and the
overlay is a console surface.

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

from .scan import is_project_dir, walk

# Ticket 12's count cap, reused: a query broader than this is answered with
# the first page and the count of what it is not showing.
RESULT_CAP = 500


@dataclass(frozen=True)
class NameHit:
    """One folder or file whose name or path matched."""

    project: str  # the top-level project folder the hit sits in
    path: str     # drive-relative, forward-slashed
    name: str     # the entry's own name
    is_dir: bool

    @property
    def kind(self) -> str:
        return "folder" if self.is_dir else "file"

    @property
    def node_key(self) -> str:
        """The hit as a Node Key inside its project; "" for the project itself."""
        prefix = f"{self.project}/"
        return self.path[len(prefix):] if self.path.startswith(prefix) else ""


@dataclass(frozen=True)
class NameIndex:
    """Every folder and file name below the drive's project roots.

    ``unreadable`` holds ``(drive-relative path, reason)`` for each folder the
    walk could not open. A folder absent from ``entries`` because Atlas could
    not read it must never be indistinguishable from one that matched nothing
    (ADR 0004).
    """

    root: Path
    entries: tuple[NameHit, ...]
    unreadable: tuple[tuple[str, str], ...] = ()


def build_name_index(root: Path) -> NameIndex:
    """One bounded walk of the drive. Never reads a file's content.

    Links are leaves in ``walk`` and stay out of the index entirely: indexing
    a junction as a folder would invite a reveal into a tree Atlas never
    walks.
    """
    base = os.fspath(root)
    errors: list[tuple[str, str]] = []
    entries: list[NameHit] = []
    for folder, dirs, files, _links in walk(base, errors=errors):
        rel = os.path.relpath(folder, base).replace("\\", "/")
        if rel == ".":
            # The drive root: descend only into project folders, and index the
            # roots themselves so a project name is findable. Root files are
            # the control plane, not search results.
            dirs[:] = sorted((d for d in dirs if is_project_dir(d)), key=str.casefold)
            entries.extend(NameHit(project=d, path=d, name=d, is_dir=True) for d in dirs)
            continue
        project = rel.split("/", 1)[0]
        for name in sorted(dirs, key=str.casefold):
            entries.append(NameHit(project, f"{rel}/{name}", name, True))
        for name in sorted(files, key=str.casefold):
            entries.append(NameHit(project, f"{rel}/{name}", name, False))
    unreadable = tuple(
        (os.path.relpath(where, base).replace("\\", "/"), why) for where, why in errors
    )
    return NameIndex(root=Path(base), entries=tuple(entries), unreadable=unreadable)


@dataclass(frozen=True)
class SearchResult:
    """One query against the index. ``hits`` is capped; ``total`` is not."""

    query: str
    hits: tuple[NameHit, ...]
    total: int
    index: NameIndex

    @property
    def overflow(self) -> int:
        """How many matches the cap is not showing."""
        return self.total - len(self.hits)


def search_names(index: NameIndex, query: str, *, cap: int = RESULT_CAP) -> SearchResult:
    """Case-folded substring over each entry's name and drive-relative path.

    Matching the path as well as the name costs nothing - both are already in
    memory - and lets "code zoning" narrow by where a thing sits. A blank
    query matches nothing: "everything on the drive" is a walk, not a search.
    """
    needle = query.strip().casefold()
    if not needle:
        return SearchResult(query=query, hits=(), total=0, index=index)
    matches = tuple(
        entry for entry in index.entries
        if needle in entry.name.casefold() or needle in entry.path.casefold()
    )
    return SearchResult(query=query, hits=matches[:cap], total=len(matches), index=index)
