# 20. A per-machine Content Index, keyed by path+size+mtime

Date: 2026-10-09

## Status

Accepted. Decided by Tyler 2026-10-07/08 (tickets 08, 11), built under ticket
34 (`.scratch/atlas-console/issues/08-global-search-scope.md`,
`11-drive-api-read-path.md`, `34-local-content-index.md`). Constrained by ADR
0006's cost discipline, ADR 0008 (a fact owes a CLI form), ADR 0009 (the
extraction machinery and its cache key), and ADR 0019 ( `_`-roots are
invisible). Research behind it: `docs/research/atlas-drive-tree-read-cost.md`,
`docs/research/atlas-tui-ux-evidence.md`.

## Context

Ticket 08 settled scope: the one-keystroke search searches everything,
including PDF text. The mechanics split on the measured cost classes (ticket
12). Names are free - one 4.24 s walk of the whole drive. Content is not: on
the Drive mount every content read is a download, and the studio's datum is
1,386 files zipped in 48 minutes. Markdown is exactly as content-bound as PDF,
so the split is names versus content, never file type. Ticket 11 declined the
Drive API read path: PDF indexing is byte-bound either way, and the auth story
is the true price. What remained is where a content index lives, how it keys
files, and how it goes stale.

## Decision

**A local Content Index, per machine, makes PDF-text and Markdown search
possible without a Drive API credential story.**

1. **Location: the local machine's user cache via `platformdirs`, keyed per
   drive root, never on the shared drive.** An index file on the drive is
   shared mutable state with no locking story across studio machines, and a
   bulk derived artifact pushed onto the drive is the anti-preload finding
   (`atlas-tui-ux-evidence.md`: do not preload files on the shared drive) in
   reverse. The drive map stays the only folder-structure brain; the index is
   a cache of disk truth, not a structure opinion. `ATLAS_CACHE_DIR` overrides
   the location for tests and unusual machines.
2. **Keying: path+size+mtime per file - the cache key ADR 0009's File Rules
   already use.** Changed or new files re-extract; unchanged files never
   re-read. Skipped files keep their key too, so a damaged file is not
   re-downloaded every run; it is retried when it changes, because the fix
   might be a re-export. Filesystem watching stays banned (ticket 06).
3. **Scope: every PDF, Markdown and plain-text file under the project roots,
   over the mount.** Filesystem-only reads per ticket 11. The walk is
   `core.scan.walk` with the Name Index's scope: project roots only -
   `_`-roots (the archive, the control plane) stay invisible - junctions never
   followed, `long_path` at every level, an unreadable folder recorded on the
   index rather than swallowed.
4. **Extraction reuses ADR 0009's machinery; there is no second PDF
   dependency.** `pdfText` for PDFs - metadata plus page one - the 64 MB Read
   Limit as one number for every kind (no size surprise on Markdown), and
   silence on damaged or locked files: they are skipped with their key,
   excluded from matches, and never raise or print. PDF text scope is a named
   limit: a phrase that appears only from page two onward is not findable.
   Broadening extraction is a future ticket if search misses prove it, not a
   default - full-text extraction multiplies the one cost class this index
   exists to pay once.
5. **The first build is a background job with progress, never an interactive
   block.** Thousands of files at the zip datum's cost class. Builds are
   incremental top-ups by key, and resumable: an interrupted build saves what
   it extracted, and the next run re-reads only the remainder. Progress is a
   callback (`done, total`); the CLI reports it, and the console's first-build
   worker (ticket 35) rides the same seam.
6. **Freshness is rebuild and revalidate, never watching.** The index carries
   an **Indexed-At Stamp** on every save; consumers show it rather than
   implying freshness. Queries revalidate each matching candidate's key
   against the disk - one stat per candidate, never a content read - and a
   match whose file changed or vanished is stale: excluded from hits and
   counted, never silently trusted. Re-extraction is a top-up's job, not a
   query-time download.
7. **A damaged index rebuilds, never crashes.** Absent, corrupt, wrong-schema
   or wrong-root index files all load as None, and the next build starts
   clean. Writes are atomic (write-then-replace), so a reader never meets a
   half-written index.
8. **CLI parity in the same session (ADR 0008):** `atlas index build` and
   `atlas index status`, both `--json`, exit 0/1/2 - status exits 1 when no
   index exists yet, because the build is the pending work. Both write only to
   the local cache; nothing is written to the drive.

## Consequences

`platformdirs` becomes a direct dependency (it was already transitive).

The index duplicates content the drive already holds - machine-local disk
spent so the mount is never re-downloaded per query. Cache eviction is the
OS's business; a deleted cache is a rebuild, not data loss.

Content search itself - matches joining the Search Overlay and `atlas search
--content` - is ticket 35, served by this index's query seam. The console
wires nothing here.

Two studio machines hold two indexes that drift independently. That is the
design, not a bug: freshness is per-machine by stamp and revalidation, and the
reversal trigger for a shared story is ticket 11's, not this ADR's.

Rejected alternatives, recorded: index on the drive (shared mutable state, no
locking, anti-preload in reverse); full-text PDF extraction (multiplies the
byte-bound cost; page one plus metadata matches the `pdfText` evidence bar);
query-time re-extraction of stale candidates (a download at keystroke time,
the thing the index exists to prevent); filesystem watching for freshness
(ticket 06: not a dependable staleness signal over the redirector).
