# The local content index

Type: task
Status: closed (2026-10-09)
Blocked by: -
Parent: ../map.md

## Work

Build ticket for the ticket 08 and 11 decisions: the per-machine **Content
Index** that makes PDF-text and Markdown search possible without a Drive API
credential story.

- Location: the local machine's user cache via `platformdirs`, keyed per
  drive. **Never on the shared drive** - an index file there is shared
  mutable state with no locking story across studio machines, and a bulk
  derived artifact on the drive is the anti-preload finding
  (`docs/research/atlas-tui-ux-evidence.md`) in reverse.
- Keying: path+size+mtime per file - the cache key ADR 0009's File Rules
  already use. Changed or new files re-extract; unchanged files never
  re-read. Filesystem watching stays banned (ticket 06).
- Extraction reuses ADR 0009's machinery: `pdfText` for PDFs, the 64 MB Read
  Limit, silence on damaged or locked files. Markdown and plain text are the
  same extractor class with no size surprise.
- The first build is a background job with progress, never an interactive
  block: content reads are downloads on the mount, and the studio's datum is
  1,386 files zipped in 48 minutes. Subsequent runs are incremental top-ups.
- The index carries an **Indexed-At Stamp**; consumers show it rather than
  implying freshness.
- Drafts and adds ADR 0020 (index location, keying, freshness, mount-only
  read path per ticket 11) - the ticket-30 convention: the build ticket owns
  the ADR.

## Build summary

**Built.** `core/contentindex.py`: `build_index` (one project-root walk,
incremental by path+size+mtime, progress callback, `save_every` periodic
persistence, partial save-and-re-raise on interruption so a stopped build
resumes by key), `load_index` (None on absent/corrupt/wrong-schema/wrong-root
- rebuilds, never crashes; atomic write-then-replace saves), `query_index`
(case-folded substring over normalised text, query-time key revalidation per
matching candidate by stat only, changed/vanished matches counted `stale` and
excluded, capped with overflow like the Name Index). `atlas index build` /
`atlas index status` with `--json`, exit 0/1/2 (status exits 1 with no index).
Cache: platformdirs user cache `studio-atlas/content-index/<root-label>-<sha1>.json`,
`ATLAS_CACHE_DIR` override. platformdirs promoted to a direct dependency.

Done-when evidence: first build indexes every PDF/Markdown/txt under the
project roots (`_`-roots out); second build re-reads only touched files,
asserted on extraction-call counts (probe style); a damaged PDF and a 65 MB
PDF are skipped silently with their keys, never opened past the limit,
excluded from matches, retried on change; nothing written to the drive
(snapshot asserted); corrupt-index rebuild tested; fixture probe at 4,000
content files: first build 58.9 s local (14.7 ms/file, pypdf-bound; the mount
adds the download per file - local timings are not a latency claim), no-op
top-up 0.23 s, 4-changed top-up 0.32 s, index 2.1 MB. ADR 0020 added;
Content Index and Indexed-At Stamp in `/CONTEXT.md`; CHANGELOG, README.
1073 tests, up from 1049. No console wiring - ticket 35 owns content matches.

Deviations: PDF text scope is metadata + page one (the `pdfText` machinery the
ticket named) - recorded in ADR 0020 as a named limit with a reversal path,
since a phrase from page two onward is not findable. Query-time revalidation
excludes and counts stale matches rather than re-extracting them: a query-time
download is what the index exists to prevent; re-extraction is a top-up's job.

## Done when

- Fixture drive: first build indexes every PDF and Markdown file; a second
  run re-reads only touched files (assert on read counts, per the ticket 05
  probe-script style).
- A damaged PDF and a 65 MB PDF are skipped silently and excluded from
  matches, per ADR 0009.
- Nothing is written to the drive under test; cache-dir override works for
  tests.
- ADR 0020 added; vocabulary (Content Index, Indexed-At Stamp) lands in
  `/CONTEXT.md`.
- `cd tools/atlas && uv run pytest` green.
