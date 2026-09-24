# Atlas: four tickets driven test-first

Session 8. Effort: `atlas-console`. Tickets 21, 07, 15, 20, in that order.

Baseline at start: 261 tests pass, lint green, `main` clean and ahead of
`origin/main` by 21 commits, unpushed.

## Why this order

21 is core-only and testable without a TUI; it settles what core hands over, which
is what 07 needs to decide the seam. 15 is a consequence of 07 - what the tree does
after a plan applies - and cannot be answered before the structure exists. 20 is
independent of all three and goes last so the shell is built once, against a seam
that is already settled.

## Phase plan

- [x] **P0 - survey.** Fetch, baseline suite, read ADR 0004/0005/0006, `core/conform.py`,
  `core/doctor.py`, `core/scan.py`, the full-rescan guard at `app.py:1732`.
- [x] **P1 - ticket 21, seams agreed.** Move Manifest carries `is_dir`. A Plan holding
  a Backfill or a file-empty removal is not invertible and `invert_plan` refuses the
  whole Plan.
- [x] **P2 - ticket 21, built.** `Move`, `Action.moved`, `build_repair_plan`,
  `invert_plan`, `Guard` at two scopes, path-length warning, `action_to_dict` for
  the CLI. 281 tests pass, up from 261. Repo lint green.
- [x] **P3 - ticket 07.** The seam. `core/tree.py` built test-first alongside the
  decision: lazily-expanding handle, containment below the root, Node Key, unmet
  Expectations with a repairable kind, 60-second shelf life. ADR 0007, CONTEXT.md.
- [x] **P4 - ticket 15.** Reconcile by Move Manifest, cursor follows the repair, no
  new state for a conflict. Folded into ADR 0007. 294 tests pass, up from 281.
- [x] **P5 - ticket 20.** The console shell. `tui/layout.py` pure and test-first,
  `app.py` applying it. Three Regions, two Compositions, collapse, navigation,
  Companion Modes, narrow chrome, cursor-follow with cancellation. 339 tests pass,
  up from 294. Rendered headless at 179/120/87/46/39 columns and 51/24 rows.

## Decisions taken this session

- **Move Manifest is `Move(src, dst, is_dir)`**, not a bare pair. Inverting a merge
  has to send a file back as a Sweep and a folder back as a Relocate, and inferring
  which at undo time is one more read and a race. One stat per moved child, paid
  only on the write path.
- **Filing State below the root is containment.** A node at or under a canonical
  path is Mapped, one under an Unfiled node is Unfiled, and a path the map names
  explicitly keeps its own verdict at any depth. Needs no amendment to ADR 0004,
  and never renders something nobody can explain as accounted for.
- **The tree reconciles by Move Manifest.** Forget the two folders the scoped Guard
  already watched, take the fresh report, move the cursor to where the node went.
  A project-wide conform forgets the project instead.
- **Invertibility is uniform or refused.** Backfill creates and the file-empty
  removal deletes; neither has a move to reverse. `invert_plan` raises on a Plan
  containing one rather than performing a partial undo, which would leave a third
  state that is neither before nor after.

## Constraints carried in

- ADR 0006 is ticket 21's contract; ADR 0005 is ticket 20's. Deviating from either
  is a decision and goes back on tickets 04 and 03 respectively.
- Fixture drives only. Never a shared drive, never a production drive.
- Colour comes from `tui/tokens.py`; the app CSS block is geometry only.
- Ticket 13 stands: no recursive counts. The path-length walk is per previewed
  action, never per render.

## Two things the next session should know

- **The published design sheet is gone.** The artifact at
  `claude.ai/code/artifact/4a9756ec-...`, cited by the wayfinder handoff and by
  tickets 02 and 03, no longer resolves for this account. Anything that needs those
  renders has to re-render them. It was already out of date in two ways.
- **One intermittent TUI test.** `test_edit_project_prepopulates_and_confirms_folder_rename`
  failed once with a Textual `NoMatches` during a full run, then passed alone and in
  two consecutive full runs. Timing, not the tree work - nothing in this session
  touches that path. Worth a look if it recurs.

- [x] **P6 - ticket 22, charted and built.** The tree widget. `tui/treeview.py`
  over `core.tree`, wired into the Tree Region in place of ticket 20's
  placeholder. 360 tests pass, up from 339.

## The mistake worth keeping

Ticket 20's footer rule was first implemented through `check_action`, returning
`None` for any binding too wide to name. In Textual that return value hides a
binding **and disables it**, so at 80 columns every action key stopped working and
twenty-three tests went red in one run. The narrow chrome is now its own widget
and `check_action` is back to being only about state. Hiding and disabling share a
return value there and are not the same thing.

## And one the tests did not catch

Ticket 22's widget passed sixteen tests while every closed folder on screen drew
an open disclosure triangle. The Companion's unmet-Expectations pass reads every
mapped section before the operator touches one, so those folders really were Read
- and the token layer had one glyph standing for two different facts. Readness is
what Atlas knows; expansion is what the widget is doing. `tokens.disclosure` picks
between them now.

Nothing in the test suite could have found it, because every test asserted on the
label of a node whose expansion state it had chosen deliberately. Rendering the
screen found it in one look.
