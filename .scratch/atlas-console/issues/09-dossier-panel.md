# Dossier panel

Type: grilling
Status: open
Blocked by: -
Parent: ../map.md

## Question

Reading `PROJECT.md` inside Atlas is in scope. The machine contract stands: ADR
0001 covers the shared front matter, `core/projectmd.py` reads and writes it,
and `core/project_data.py::load_project_record` exposes the record.

What changed since this ticket opened - **the layout question is settled.** The
dossier is a Companion Mode: `MODES = (EXPECTATIONS, HEALTH, DOSSIER)` in
`tui/layout.py`, cycled on `d`. The slot is a stub today -
`_render_companion` in `tui/app.py` renders the literal string "The dossier
lands here." So the remaining questions are about content and behaviour, not
placement.

Resolve:

- Which facts surface: identity, site address, use case, billing and client
  contact snapshots, decisions index, code edition. All of them, or a chosen
  subset?
- Read-only, or editable in place? Atlas already has a full edit path behind
  `e` (`action_edit_project`) with rename preview and confirmation - does the
  dossier panel duplicate an entry point into that, or become a second way to
  write?
- What renders when `PROJECT.md` is missing, malformed, or legacy? Core
  deliberately refuses to silently rewrite malformed dossier data - the panel
  must say so usefully rather than showing blanks.
- Does the decisions index link through to `decisions/NNNN-slug.md`, and can
  those be read in Atlas too, or is that a different surface?
- CLI form: ADR 0008 obliges every fact-producing surface. `atlas dossier
  PROJECT [--json]` over `load_project_record`, or is `cat PROJECT.md` the
  answer? If the latter, record why.

## Acceptance

- Each question above answered; decision recorded in `docs/adr/` and one line
  on `../map.md`; new vocabulary in `/CONTEXT.md`.
- The stub string in `_render_companion` is gone - the mode renders real
  dossier facts or a deliberate decision not to build it is on record.
- Missing/malformed/legacy rendering verified headless at the measured widths
  (179, 153, 120, 87, 77, 46 columns; 51, 30, 24 rows).
