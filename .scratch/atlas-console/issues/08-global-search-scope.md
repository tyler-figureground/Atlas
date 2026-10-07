# Global search scope

Type: grilling
Status: open
Blocked by: -
Parent: ../map.md

## Question

Global search is in scope: one keystroke, search across the drive, jump to the
result. What it searches is undecided. Nothing is built - there is no search
overlay anywhere in `tools/atlas/src/atlas/tui/`.

What changed since this ticket opened:

- **The cost objection is gone.** Ticket 12 measured the live drive: 7,956
  folders, 18,536 files, walked in 4.24 s, cold p99 91 ms per folder. A
  drive-wide index is affordable; enumeration over the mount is no longer a
  reason to narrow the scope by fiat. `Path.rglob` remains banned (ticket 06:
  it suppresses every `OSError`).
- **The `/` filter grew.** Per ADR 0005 and the 2026-09 audit (#62), `/`
  filters the focused Region - the project list and, per project, the tree
  (`tui/app.py` `#filter` / `#tree-filter` inputs,
  `tui/treeview.py::set_filter`). It never leaves the selected project. The
  "existing `/` filter" this ticket asks about is that pair.

Resolve:

- What is searchable: project names only, project names plus dossier facts,
  folder and file names across all projects, or file contents?
- Drive-wide, or scoped to the selected project with a widen key?
- Live-as-you-type or submit-then-results? Live search over a network mount is
  a different engineering problem than a submitted query, even at 4.24 s.
- Does it need an index? If so, where does it live, when is it built, and how
  does it go stale? An index file on the drive is shared state that other
  studio machines will also read.
- What does a result look like, and what does selecting one do - reveal in the
  tree, open the project, open the file?
- Is the Region filter subsumed, kept alongside, or promoted into this?
- What happens with no results, with too many results, and while a slow search
  runs?

## Acceptance

- Each question above answered with the measured numbers from ticket 12, not
  assumed ones.
- Decision recorded in `docs/adr/` and one line on `../map.md`; new vocabulary
  in `/CONTEXT.md`.
- If the answer builds a fact-producing surface, ADR 0008 applies: it owes a
  CLI form with a `--json` shape in the same session.
