# The dossier Companion Mode and `atlas dossier`

Type: task
Status: closed (2026-10-09)
Blocked by: -
Parent: ../map.md

## Work

Build ticket for the ticket 09 decision: the DOSSIER Companion Mode renders
real facts, and the stub string in `_render_companion` goes away.

- The mode draws a **Dossier Facts Table** from
  `core/project_data.py::load_project_record`: identity (name, address, use
  case, description, created), the billing/client Contact Snapshots, and the
  decisions summary (count and latest titles) the digest already computes.
  Not raw Markdown; `o` opens the file. No in-Atlas decision reading -
  recorded scope cut.
- Read-only. The footer line advertises `e` (`project edit`); the panel is
  never a third write path beside `project edit` and conform.
- Missing, malformed, and legacy PROJECT.md render the reason -
  `ProjectDataError`'s message, or the unmet control-plane Expectation
  pointer - never blanks. Blank means unknown (ADR 0001).
- CLI parity in the same session (ADR 0008): `atlas dossier PROJECT
  [--json]` over `load_project_record`, surfacing the validation error with
  the CLI's exit-2 error convention.
- Adds the drafted ADR 0005 amendment from ticket 09 verbatim.

## Done when

- DOSSIER mode renders the facts table on a fixture project; the stub string
  is gone from `_render_companion`.
- Missing, malformed, and legacy dossiers each render their reason, verified
  headless at the measured widths (179, 153, 120, 87, 77, 46 columns; 51, 30,
  24 rows) - the ticket 09 acceptance.
- `atlas dossier PROJECT --json` emits a documented shape; a malformed
  dossier exits 2 with the reason.
- ADR 0005 amendment line added; vocabulary (Dossier Facts Table) lands in
  `/CONTEXT.md`.
- `cd tools/atlas && uv run pytest` green.

## Build summary (2026-10-09)

Built. 1107 tests pass, up from 1093 (`tests/test_dossier.py`, 14 new).

- `core/project_data.py`: `DecisionsSummary` (count plus the latest three
  titles, newest first - `/decision` appends chronologically) parsed from the
  dossier's `## Decisions` table, exposed as `ProjectRecord.decisions`. No
  section is zero decisions, not an error. Titles only - decisions do not
  link through (ticket 09's recorded scope cut).
- `tui/dossier.py`, pure like `tui.layout`/`tui.repair` (the CLI imports it
  without Textual): `dossier_lines` (identity, the billing/client Contact
  Snapshots, the decisions summary, the `e edit   o open` line),
  `dossier_error_lines` (the `ProjectDataError` reason, the absolute path
  replaced by the file name), `dossier_missing_lines` (the unmet
  control-plane Expectation pointer, offering nothing - backfill lives one
  `d` away).
- `_render_companion`'s stub string is gone; the DOSSIER branch renders
  through `load_project_record`, never raw Markdown. An unreadable project
  root says "cannot read - unknown, not absent" rather than reporting the
  dossier missing (ADR 0004).
- `atlas dossier PROJECT [--json]`: exit 0 with the record; missing,
  malformed, legacy or unknown project exit 2 with the reason (the CLI's
  error convention). The `--json` shape (`drive`, `project`, `path`, `name`,
  `address`, `use_case`, `use_case_category`, `description`, `created`,
  `billing_contact`/`client_contact`, `decisions` `{count, latest}`,
  `source_digest`) is documented in `tools/atlas/README.md`.
- The ticket 09 ADR 0005 amendment is applied verbatim, with an as-built
  note. Dossier Facts Table is in `/CONTEXT.md`.
- Headless renders at the measured widths: missing/malformed/legacy at
  179/153/120/87/77/46 columns x 51/30/24 rows (the ticket 09 acceptance),
  plus the facts table at the same grid.

Deviations, recorded:

- "The decisions summary the digest already computes" (ticket 09) named no
  existing seam - nothing in core computed one. `DecisionsSummary` is that
  computation, new in `core/project_data.py`, parsing the table `/decision`
  maintains. Read-only; ADR 0001 untouched.
- The footer line lives as the facts table's last line (`e edit   o open`),
  not as separate chrome - the Companion's body is the surface every other
  mode uses. What the keys do is the console's own: `e` is `project edit`,
  `o` opens the project folder.

README (the CLI row, the `d` key row), CHANGELOG Unreleased, CONTEXT.md and
ADR 0005 updated.
