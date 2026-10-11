# Content search over the index

Type: task
Status: open
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
