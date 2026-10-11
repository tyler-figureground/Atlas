# The dossier Companion Mode and `atlas dossier`

Type: task
Status: open
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
