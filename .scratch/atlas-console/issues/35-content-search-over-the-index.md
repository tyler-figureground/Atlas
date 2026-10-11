# Content search over the index

Type: task
Status: closed (2026-10-09)
Blocked by: 33, 34
Parent: ../map.md

## Work

Build ticket for the ticket 08 decision, phase B: content matches join the
Search Overlay and the CLI.

- The Search Overlay (ticket 33) gains content matches from the Content Index
  (ticket 34): name matches rank first, content matches carry the matched
  line or snippet. Result rows keep the colour-alone rule (ADR 0008).
- Freshness at query time: a file whose path+size+mtime no longer matches its
  index entry is re-extracted or flagged stale, never silently matched on old
  text. The Indexed-At Stamp is visible in the overlay.
- CLI parity in the same session (ADR 0008): `atlas search QUERY --content
  [--json]`, same seam, same freshness rule.
- Index absent or still building: the overlay says so in one honest line and
  serves name matches; it never blocks waiting for the background build.

## Done when

- Fixture drive: a PDF-text phrase and a Markdown phrase both match; a file
  edited after indexing re-extracts and matches its new text; a deleted
  file's match disappears.
- Cold-index and building-index states rendered headless at the measured
  widths (179, 153, 120, 87, 77, 46 columns; 51, 30, 24 rows).
- `atlas search --content --json` shape documented alongside ticket 33's.
- `cd tools/atlas && uv run pytest` green.

## Build summary (2026-10-09)

Built. 1093 tests pass, up from 1073 (`tests/test_content_search.py`, 20 new).

- `core/contentindex.py`: `ContentHit` gains the matched line as `snippet`
  (from the stored normalised text - a query never re-reads a file) plus the
  `name`/`node_key` NameHit parity the overlay's reveal/open act on.
- The Search Overlay (`tui/search.py`) merges content matches below name
  matches (never mixed), each row keeping its kind word
  (`pdf`/`markdown`/`text` vs `file`/`folder` - ADR 0008) and the snippet. A
  new `#search-content` line under the results carries the Indexed-At Stamp
  always, the stale count beside the match count after a query, and the three
  honest states - absent (`atlas index build` named), building (with
  progress), failed (the reason) - never a silent zero. `#search-status`
  strings from ticket 33 are unchanged.
- The console first-builds an absent index on a background worker at
  drive-open (ADR 0020 #5), throttled progress relayed to an open overlay,
  which warms in place when the build lands. A rescan reloads the stored
  index (a CLI top-up may have landed) but never rebuilds one: freshness is
  revalidation plus `atlas index build`, not a download at `r`.
- `atlas search QUERY --content [--json]`: same seam, same freshness rule.
  `--json` adds `content` - null when no index exists (never a silently empty
  list), else `indexed_at`, `total`, `shown`, `cap`, `stale`, `results` with
  `snippet`. Exit 0/1/2 unchanged; content-only matches exit 0.
- Headless renders at the measured widths: cold, building and warm states at
  179/153/120/87/77/46 columns and 51 rows, content rows at 120/87/46 x
  30/24 rows; every state line fitted to the dialog, never widget-clipped.

Deviations, recorded:

- The done-when's "a file edited after indexing re-extracts and matches its
  new text" is satisfied through the top-up build, not at query time: ADR
  0020 rejects query-time re-extraction (a download at keystroke time). The
  test pair shows the edit counted stale until `build_index` re-reads it,
  then matching its new text.
- The snippet comes from the stored normalised text, so it renders casefolded
  with whitespace collapsed; the index stores nothing else.
- The 500 cap applies per seam (500 name + at most 500 content); the combined
  list can exceed 500 rows. The cap's job - bounding a too-broad answer -
  holds per class, and the overflow is counted on each.
- `tests/conftest.py::_local_cache` now points `ATLAS_CACHE_DIR` at a tmp
  path instead of merely deleting it: the console first-builds at drive-open,
  so a deleted override would have every TUI test writing the machine's real
  cache.
- No ADR amendment was drafted on this ticket; none applied. ADR 0005's
  search amendment note now records the content half as landed.

README (`atlas search --content`, the `g` key row, the JSON shape), CHANGELOG
Unreleased, and CONTEXT.md (Search Overlay) updated.
