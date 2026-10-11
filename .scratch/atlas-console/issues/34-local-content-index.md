# The local content index

Type: task
Status: open
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
