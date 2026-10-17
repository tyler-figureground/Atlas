# Global name search: the walk, the overlay, and the CLI

Type: task
Status: closed (2026-10-09)
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

## Build summary (2026-10-09)

Built as specified, three surfaces over one seam:

- **Core** (`src/atlas/core/search.py`): `build_name_index` - one bounded
  `scan.walk` of the drive (junctions never followed, `long_path` at every
  level, unreadable folders recorded on the index, never swallowed), project
  roots only, links not indexed. `search_names` - case-folded substring over
  name and drive-relative path, capped at `RESULT_CAP = 500` with the overflow
  counted.
- **CLI**: `atlas search QUERY [--drive D] [--json]`, exit 0 matches / 1 none /
  2 error. `--json` fields: `drive`, `query`, `total`, `shown`, `cap`,
  `results` (`project`, `path`, `name`, `kind`), `unreadable`.
- **TUI** (`src/atlas/tui/search.py`): the Search Overlay on `g` - a ModalScreen,
  not a Region. Live narrowing on every keystroke against the warm index;
  Enter reveals (project in the list, or the node in the tree via
  `ProjectTreeView.reveal`, which chains expansions through `_fill` and lands
  the cursor by Node Key); `o` opens from the results list; Escape dismisses
  with focus, collapse and cursors untouched. Loading, empty and
  overflow-cap states are each one honest line. Geometry rules in
  `tui/layout.py` (`search_overlay_width` / `search_overlay_cells`), colours
  in `tokens.stylesheet()`.

Decisions taken where the ticket was silent:

- **The key is `g`** (global). `/` is the Region filter and stays it; nothing
  named the search key in 08 or 33.
- **The index walks project roots only** (`is_project_dir`): `_`-roots are
  invisible to the console on purpose (ADR 0019), and the overlay is a
  console surface. `_Archived Projects` and `_tools` are not findable.
  **Superseded 2026-10-16 (plan Q3: map read-only, search reaches the
  archive):** the index also walks each folder under the map's
  `archiveRoot`, read-only; hits carry `archived` and rank after every live
  hit; Enter on one names it on the operation line instead of revealing
  (the archive is still outside the list and tree, ADR 0019). `_tools` and
  other `_`-roots stay out.
- **Dossier facts are not read this ticket.** Ticket 08 lists "the project
  dossier facts Atlas already parses" and "zero content reads" in the same
  sentence; nothing parses dossiers in a session today (the dossier mode is
  ticket 36), so the bound was taken literally. The project folder name
  already carries short address and description by naming convention; the
  matcher takes dossier fields when an in-session parse exists.
- **`o` lives on the results list, not the input** - in the input it is a
  letter. The overlay says so on its keys line.

Done-when evidence: overlay opens / narrows / all three actions tested against
fixture drives (`tests/test_search_overlay.py`, 13 tests); empty, overflow-cap
and loading states rendered headless at 179, 153, 120, 87, 77, 46 columns and
51, 30, 24 rows; `--json` shape asserted field-by-field
(`tests/test_search.py`, 12 tests); result rows carry the kind as a word at
every width (ADR 0008). `uv run pytest`: 1049 passed (baseline this session:
1021; +25 new, +3 stylesheet-scan tests the new overlay selectors earn in
test_tokens.py). Repo lint clean. Not committed.

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
