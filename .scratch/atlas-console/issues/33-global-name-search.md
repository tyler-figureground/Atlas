# Global name search: the walk, the overlay, and the CLI

Type: task
Status: open
Blocked by: -
Parent: ../map.md

## Work

Build ticket for the ticket 08 decision, phase A: drive-wide name search.

- A session **Name Index**: one drive walk (measured 4.24 s, ticket 12) on a
  background worker at session start and on `r`, never blocking; folders,
  files, and the project dossier facts Atlas already parses. `Path.rglob`
  stays banned (ticket 06).
- The **Search Overlay**: one keystroke opens it, live-as-you-type against the
  warm in-memory index, Escape dismisses without disturbing Region focus or
  collapse state. Not a Region - ADR 0005's three stand. A result row reveals
  the node in the tree, selects the project in the list, or opens the file on
  `o`.
- Edge states: no results renders one honest line; results cap at 500 with
  the overflow counted (ticket 12's count cap); the loading state appears past
  the 120 ms budget, never on a warm read.
- CLI parity in the same session (ADR 0008): `atlas search QUERY [--json]`
  over the same core seam.
- Adds the drafted ADR 0005 amendment from ticket 08 verbatim.

## Done when

- Overlay opens, narrows live, and all three result actions work against a
  synthetic fixture drive; never touches a production drive.
- Empty, overflow-cap, and slow-loading states each rendered headless at the
  measured widths (179, 153, 120, 87, 77, 46 columns; 51, 30, 24 rows).
- `atlas search QUERY --json` emits a documented shape; the colour-alone rule
  holds on result rows (ADR 0008).
- ADR 0005 amendment line added; vocabulary (Search Overlay, Name Index)
  lands in `/CONTEXT.md`.
- `cd tools/atlas && uv run pytest` green.
