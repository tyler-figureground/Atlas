# Atlas session 9: ticket 10, then ticket 23

Effort: `atlas-console`. Two tickets, in this order, on the user's instruction.

Baseline at start: **360 tests pass**, repo lint green, `main` clean and ahead of
`origin/main` by 26 commits, unpushed. `git fetch` run; behind 0.

## Why this order

Ticket 10 has slipped three sessions (6, 7, 8) and each one added surface that
inherits its unanswered question. Ticket 23 adds two more - a repair keybinding on
a node and an inline confirm on the operation line. Settling 10 first means 23
lands already conformant instead of adding a fourth session of debt.

## Phase plan

- [x] **P0 - survey.** Read ticket 10, CONTEXT.md, the CLI surface and its
  `--json` contract, the TUI-only capabilities added in sessions 6-8, and the
  narrow-width render where colour carries Filing State alone.
- [x] **P1 - ticket 10, grilled.** Resolve the five questions on the ticket. The
  live one is colour-carries-meaning at narrow widths. Output: Resolution section,
  map line, ADR if the decision earns one, CONTEXT.md vocabulary.
- [x] **P2 - ticket 10, whatever it obliges.** Only if the decision requires code
  to stop the debt growing. Scope stated before starting.
- [x] **P3 - ticket 23, charted.** The tree's writes. Repair keys on a node, the
  inline confirm on the operation line, the per-project undo stack. Write the
  ticket before building it.
- [x] **P4 - ticket 23, built.** Test-first through `/tdd` against
  `build_repair_plan`, `invert_plan`, `Guard.for_action` - all built and tested in
  session 8.
- [x] **P5 - verify and close.** Full suite, repo lint, headless render at the
  measured widths. Resolution sections, map lines, commits, wayfinder update.

## Constraints carried in

- ADR 0006 is ticket 23's contract; deviating is a decision and goes back on
  ticket 04.
- Fixture drives only. Never the studio drive, never a shared drive.
- Colour comes from `tui/tokens.py`; the app CSS block is geometry only.
- Verification widths are the measured ones: 179, 153, 120, 87, 77, 46 columns;
  51, 30, 24 rows.
- Tracker is local Markdown under `.scratch/atlas-console/issues/`. This repo has
  GitHub issues disabled.

## Log

**P0 done.** Fetched, baseline 360 green, read ticket 10, `tokens.py`,
`treeview.py`, `layout.py`, the CLI parser, `report_to_dict`, `cmd_conform`.

**P1 + P2 done, committed.** Ticket 10 grilled through three rounds and resolved.
ADR 0008, CONTEXT.md under Atlas Interface Contract, README accessibility section,
map line, fog note. Code: `FilingStyle.short`, `_fault_word`,
`layout.ABBREVIATE_COLUMNS = 60`, `app.py` keying `narrow` on it. **364 tests**,
up from 360. Repo lint green.

Two findings worth carrying:

- The defect was worse than the ticket described. Dropping the word collapsed
  Drifted, Misplaced and Loose into one appearance **for everyone**, not only for
  a colour-blind operator - ADR 0004 has them share a glyph and a colour by
  design. What was left measured 1.82:1, vermilion against ochre.
- **Rendering found the second half of the same bug and the suite did not.**
  `node_label` returned early for a file, before the word was appended, so a Loose
  file and an Unfiled file were separated by hue alone at *every* width. Second
  session running that a headless render found what a green suite could not.

Tickets 23 and 24 charted. 24 is ticket 22's retroactive parity debt under ADR
0008 and is deliberately its own ticket, not folded into 23's commit.

**P3 + P4 + P5 done, committed.** Ticket 23 built test-first through `/tdd`.
**405 tests**, up from 364 at the ticket's start and 360 at session start. Repo
lint green. Rendered headless at 120 / 87 / 46 columns and driven end to end with
keys only.

Five bugs. Two were design errors in ADRs shipped in earlier sessions; three were
shipped code that a green suite could not have caught, and all three came out of
rendering the screen.

- **`Guard.for_action` cannot guard an undo.** It re-derives the Plan from the map
  and compares; an undo reverses the map. It refused every undo on an unchanged
  drive. ADR 0006 had claimed one guard served both. `Guard.for_undo` now exists.
- **`reconcile` missed the folder a merge consumed.** Every Move in a merge names
  a child, so their parents are the two merged folders, never the folder that lost
  the source from its own listing. The tree drew a row for a directory that no
  longer existed, as Mapped. `follow` already knew this in a comment.
- **The Tree Region could not take keyboard focus at all.** `#tree` is a
  `Vertical`; `Vertical.focus()` is a no-op. The tree widget shipped in session 8
  **entirely unreachable by keyboard** while sixteen widget tests and a console
  shell suite passed - nothing had asserted which widget the keyboard was talking
  to. Fixing it exposed Textual's `Tree` taking Atlas's Enter, and a drilled tree
  having no cursor at all until an arrow key moved it.

Corrections recorded on ADR 0006 and ADR 0007 rather than left to be discovered.

## What the next session should know

- **Rendering has now found a real bug in three consecutive sessions**, and in
  this one it found three the suite structurally could not. The pattern is
  specific: tests assert on state the app *believes* (`_focus_region`, `display`,
  a Filing State) and not on what the screen or the keyboard actually does. Two
  render scripts are in the session scratchpad and worth rebuilding: one that
  drills and dumps the tree rows, one that drives the whole repair flow with keys
  only and prints the operation line after each step.
- **Ticket 24 is the outstanding debt.** `atlas tree PROJECT [--json] [--depth N]`
  - ticket 22's retroactive parity obligation under ADR 0008. Charted, unblocked,
  and deliberately not folded into ticket 23's commit so it could not be silently
  dropped. It is also the cheapest real test of whether the ticket 07 seam is a
  seam: a second consumer that is not a Textual widget.
- **Also unclaimed and unblocked:** 08 (global search scope), 09 (dossier
  Companion Mode), 11 (Drive API read path).
- **Load State labels still do not abbreviate.** `not opened yet` runs past the
  viewport at 46 columns. In the map's fog, deliberately out of scope at ticket 10.
- The `space` key now toggles a folder when the tree has focus and marks a project
  when the list does. That fell out of the focus fix and is the right answer, but
  it was never explicitly decided - worth a look if it feels wrong in use.
