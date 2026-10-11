"""The per-machine Content Index: PDF text and Markdown, cached off the drive.

Ticket 08 settled the mechanics on the measured cost classes (ticket 12): every
content read over the Drive mount is a download - the studio's datum is 1,386
files zipped in 48 minutes - so content search needs an index, and the index
belongs to this machine. It lives in the platformdirs user cache, keyed per
drive root, **never on the shared drive**: an index file there is shared
mutable state with no locking story across studio machines, and a bulk derived
artifact on the drive is the anti-preload finding
(``docs/research/atlas-tui-ux-evidence.md``) in reverse. Filesystem-only reads,
per ticket 11: no Drive API, no credential story.

Keying is path+size+mtime - the cache key ADR 0009's File Rules already use for
``pdfText``. An unchanged file is never re-read; a changed one re-extracts; a
skipped file (damaged, locked, oversized) keeps its key so a top-up does not
retry it every run, and is retried when it changes. Filesystem watching stays
banned (ticket 06).

Extraction is ADR 0009's machinery, not a second PDF dependency: ``pdfText``
for PDFs (metadata plus page one), the 64 MB Read Limit - one number for every
kind, no size surprise - and silence on damaged or locked files. Markdown and
plain text are the same extractor class. The walk is ``core.scan.walk`` scoped
to the project roots, so junctions are never followed, every level takes
``long_path``, and an unreadable folder is recorded, never swallowed.

Freshness is rebuild and revalidate, never watching (ticket 08). Builds are
incremental top-ups and resumable by key: an interrupted build saves what it
extracted, and the next run re-reads only the remainder. Queries revalidate
each matching candidate's key against the disk before trusting it; a match
whose file changed or vanished is stale - excluded and counted, never silently
served. The **Indexed-At Stamp** rides every save; consumers show it rather
than implying freshness.

A damaged index file rebuilds, never crashes: ``load_index`` returns None on
any corruption, schema drift, or root mismatch, and the next build starts
clean.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from platformdirs import user_cache_path

from . import content
from .mapfile import find_map, load_map
from .scan import is_project_dir, long_path, walk
from .search import RESULT_CAP

SCHEMA = 1

# The ADR 0009 Read Limit, one number for every kind: a 900 MB scan is never
# pulled down to answer a search, and neither is a 900 MB log.
READ_LIMIT = content.PDF_READ_LIMIT

CONTENT_EXTENSIONS = frozenset({".pdf", ".md", ".markdown", ".txt"})
_KIND = {".pdf": "pdf", ".md": "markdown", ".markdown": "markdown", ".txt": "text"}

TOO_LARGE = "too large"
UNREADABLE = "unreadable"

# Tests and unusual machines point the cache elsewhere; the suite must never
# touch the machine's real one.
CACHE_ENV_VAR = "ATLAS_CACHE_DIR"


@dataclass(frozen=True)
class IndexedFile:
    """One extracted file. ``text`` is normalised (casefolded, whitespace
    collapsed), ready for substring matching."""

    path: str       # drive-relative, forward-slashed
    kind: str       # pdf | markdown | text
    size: int
    mtime_ns: int
    text: str


@dataclass(frozen=True)
class SkippedFile:
    """A candidate the build would not read, with the key it was skipped at.

    The key is what makes a top-up cheap: an unchanged damaged file is not
    retried every run. It is retried when it changes - the fix might be a
    re-export.
    """

    path: str
    size: int
    mtime_ns: int
    reason: str     # TOO_LARGE | UNREADABLE


@dataclass(frozen=True)
class ContentIndex:
    """The index on disk. ``indexed_at`` is the Indexed-At Stamp: when the
    build that wrote this ran, shown by consumers rather than implied fresh."""

    root: Path
    drive: str
    indexed_at: str
    files: tuple[IndexedFile, ...]
    skipped: tuple[SkippedFile, ...] = ()
    unreadable: tuple[tuple[str, str], ...] = ()


# ------------------------------------------------------------- location


def default_cache_dir() -> Path:
    override = os.environ.get(CACHE_ENV_VAR)
    if override:
        return Path(override)
    return user_cache_path("studio-atlas", appauthor=False) / "content-index"


def index_path(root: Path | str, cache_dir: Path | str | None = None) -> Path:
    """The one cache file per drive root, named so a human can tell drives
    apart and keyed so two roots never share a file."""
    base = os.path.abspath(os.fspath(root))
    digest = hashlib.sha1(base.casefold().encode("utf-8")).hexdigest()[:12]
    # The root's own name ("TESTDRIVE", "G") is the human label; the digest
    # is the key, so two roots that share a name never share a file.
    name = Path(base).name or base.rstrip("\\/").rstrip(":")
    label = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").casefold()[:40] or "drive"
    directory = Path(cache_dir) if cache_dir is not None else default_cache_dir()
    return directory / f"{label}-{digest}.json"


# ------------------------------------------------------------- persistence


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _save(path: Path, index: ContentIndex) -> None:
    """Atomic: a reader never meets a half-written index."""
    payload = {
        "schema": SCHEMA,
        "drive": index.drive,
        "root": os.fspath(index.root),
        "indexed_at": index.indexed_at,
        "files": [vars(f) for f in index.files],
        "skipped": [vars(s) for s in index.skipped],
        "unreadable": [list(u) for u in index.unreadable],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, path)


def load_index(root: Path | str, *,
               cache_dir: Path | str | None = None) -> ContentIndex | None:
    """The stored index for this drive root, or None.

    None covers absent, unreadable, corrupt, wrong schema, and written for a
    different root alike - a damaged index rebuilds, never crashes.
    """
    path = index_path(root, cache_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["schema"] != SCHEMA:
            return None
        if payload["root"].casefold() != os.path.abspath(os.fspath(root)).casefold():
            return None
        files = tuple(IndexedFile(**f) for f in payload["files"])
        skipped = tuple(SkippedFile(**s) for s in payload["skipped"])
        unreadable = tuple((where, why) for where, why in payload["unreadable"])
        return ContentIndex(root=Path(payload["root"]), drive=payload["drive"],
                            indexed_at=payload["indexed_at"], files=files,
                            skipped=skipped, unreadable=unreadable)
    except (OSError, ValueError, KeyError, TypeError):
        return None


# ------------------------------------------------------------- extraction


def _extract(path: str, kind: str) -> str | None:
    """One file's searchable text, or None when it cannot be read.

    The single chokepoint the build loops over - tests count calls here the
    way ticket 05's probes count syscalls. Silence is the contract (ADR 0009):
    a damaged or locked file returns None and never raises, never prints.
    """
    if kind == "pdf":
        return content.pdf_text(Path(path))
    try:
        with open(long_path(path), "rb") as handle:
            data = handle.read(READ_LIMIT + 1)
    except OSError:
        return None
    return content.normalise(data.decode("utf-8", errors="replace"))


def _drive_label(root: str) -> str:
    try:
        map_path = find_map(Path(root))
        if map_path is not None:
            return load_map(map_path).drive
    except Exception:  # noqa: BLE001 - the label is cosmetic; the build is not
        pass
    return Path(root).name or root


# ------------------------------------------------------------- the build


def build_index(root: Path | str, *,
                cache_dir: Path | str | None = None,
                progress: Callable[[int, int], None] | None = None,
                save_every: int | None = None) -> ContentIndex:
    """Build or top up the index for one drive root. Incremental by key.

    One bounded walk of the project roots finds the candidates; anything whose
    path+size+mtime matches the stored index - extracted or skipped - is
    carried without a read. The rest are extracted with ``progress(done,
    total)`` after each. A long build persists every ``save_every``
    extractions, and an interrupted build saves what it has before re-raising:
    the next run re-reads only the remainder.
    """
    base = os.path.abspath(os.fspath(root))
    prior = load_index(base, cache_dir=cache_dir)
    prior_files = {f.path: f for f in prior.files} if prior else {}
    prior_skipped = {s.path: s for s in prior.skipped} if prior else {}

    errors: list[tuple[str, str]] = []
    candidates: list[tuple[str, str, str]] = []
    for folder, dirs, files, _links in walk(base, errors=errors):
        rel = os.path.relpath(folder, base).replace("\\", "/")
        if rel == ".":
            # As the Name Index: project roots only. `_`-roots stay invisible
            # (ADR 0019), and drive-root files are the control plane.
            dirs[:] = [d for d in dirs if is_project_dir(d)]
            continue
        for name in files:
            kind = _KIND.get(os.path.splitext(name)[1].casefold())
            if kind:
                candidates.append((f"{rel}/{name}", os.path.join(folder, name), kind))

    kept: list[IndexedFile] = []
    skipped: list[SkippedFile] = []
    to_read: list[tuple[str, str, str, int, int]] = []
    for rel, absolute, kind in candidates:
        try:
            stat = os.stat(long_path(absolute))
        except OSError:
            # Vanished mid-walk or unreadable. Unkeyable, so not recorded:
            # the next build retries the stat, which costs nothing.
            continue
        prev = prior_files.get(rel)
        if prev and prev.size == stat.st_size and prev.mtime_ns == stat.st_mtime_ns:
            kept.append(prev)
            continue
        prev_skip = prior_skipped.get(rel)
        if (prev_skip and prev_skip.size == stat.st_size
                and prev_skip.mtime_ns == stat.st_mtime_ns):
            skipped.append(prev_skip)
            continue
        if stat.st_size > READ_LIMIT:
            skipped.append(SkippedFile(rel, stat.st_size, stat.st_mtime_ns, TOO_LARGE))
            continue
        to_read.append((rel, absolute, kind, stat.st_size, stat.st_mtime_ns))

    unreadable = tuple(
        (os.path.relpath(where, base).replace("\\", "/"), why) for where, why in errors
    )
    path = index_path(base, cache_dir)

    def snapshot() -> ContentIndex:
        return ContentIndex(
            root=Path(base), drive=_drive_label(base), indexed_at=_stamp(),
            files=tuple(sorted(kept, key=lambda f: f.path.casefold())),
            skipped=tuple(sorted(skipped, key=lambda s: s.path.casefold())),
            unreadable=unreadable)

    total = len(to_read)
    try:
        for done, (rel, absolute, kind, size, mtime_ns) in enumerate(to_read, 1):
            text = _extract(absolute, kind)
            if text is None:
                skipped.append(SkippedFile(rel, size, mtime_ns, UNREADABLE))
            else:
                kept.append(IndexedFile(rel, kind, size, mtime_ns, text))
            if progress is not None:
                progress(done, total)
            if save_every and done % save_every == 0:
                _save(path, snapshot())
    except BaseException:
        # Resumable by key: what was extracted is kept, and the next run
        # re-reads only the remainder. The stamp stays honest - this save is
        # a partial build, stamped when it ran.
        _save(path, snapshot())
        raise
    index = snapshot()
    _save(path, index)
    return index


# ------------------------------------------------------------- the query


@dataclass(frozen=True)
class ContentHit:
    """One file whose indexed text matched and whose key still holds on disk."""

    project: str
    path: str
    kind: str


@dataclass(frozen=True)
class ContentResult:
    """One query against the index. ``hits`` is capped; ``total`` is not.

    ``stale`` counts matches whose key no longer holds on disk - changed or
    vanished since the build. They are excluded, never silently trusted, and
    the count is what a consumer shows beside the Indexed-At Stamp.
    """

    query: str
    hits: tuple[ContentHit, ...]
    total: int
    stale: int
    index: ContentIndex

    @property
    def overflow(self) -> int:
        return self.total - len(self.hits)


def query_index(index: ContentIndex, query: str, *,
                cap: int = RESULT_CAP) -> ContentResult:
    """Case-folded substring over the indexed text, revalidated against disk.

    Never reads content: the revalidation is one stat per matching candidate,
    and a match whose key changed is stale - a top-up's job, not a query-time
    download (ticket 08).
    """
    needle = content.normalise(query)
    if not needle:
        return ContentResult(query=query, hits=(), total=0, stale=0, index=index)
    hits: list[ContentHit] = []
    stale = 0
    for entry in index.files:
        if needle not in entry.text:
            continue
        try:
            stat = os.stat(long_path(index.root / entry.path))
        except OSError:
            stale += 1
            continue
        if stat.st_size != entry.size or stat.st_mtime_ns != entry.mtime_ns:
            stale += 1
            continue
        hits.append(ContentHit(project=entry.path.split("/", 1)[0],
                               path=entry.path, kind=entry.kind))
    total = len(hits)
    return ContentResult(query=query, hits=tuple(hits[:cap]), total=total,
                         stale=stale, index=index)
