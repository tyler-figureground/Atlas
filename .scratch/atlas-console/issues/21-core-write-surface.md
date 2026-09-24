# The core write surface for the tree, as Atlas code

Type: task
Status: resolved
Blocked by: -
Parent: ../map.md

## Question

Ticket 04 decided the tree's write contract and ADR 0006 records it. None of it
exists in `atlas.core` yet.

Build the core side, ahead of and independent of the tree widget. Everything here
is testable without a TUI, and `conform` gains from it whether the tree ships or
not.

Do, test-first per the map's `/tdd` note:

- **`Action.moved`** - the move manifest. Every `(src, dst)` pair `_apply_move`
  actually moved, including inside a merge. Empty until applied. `_apply_sweep`
  and `_apply_backfill` fill it too, so a Plan is uniformly invertible or
  uniformly not.
- **A one-action plan builder.** `build_plan` currently takes a whole
  `ProjectReport`. The tree needs the Plan for one node's Repair - Drifted to
  RENAME, Misplaced to RELOCATE, Loose to SWEEP - and the Companion needs the Plan
  for one unmet Expectation as BACKFILL. Same `Action` values `build_plan` would
  have produced for the same node; a test should assert exactly that rather than
  trusting it.
- **The inverse plan.** Given an applied Plan, produce the Plan that reverses it
  from the manifests. Undo then flows through `apply_plan` like anything else.
- **The scoped guard.** Revalidate a one-action Plan by re-reading the drive map,
  re-enumerating the source's and destination's parents, and rebuilding the single
  Action. Same abort semantics as the full-rescan guard in `action_conform`. Both
  guards must produce the same verdict on the same divergence - worth a test that
  runs them side by side on a fixture drive.
- **Path-length warning on the Action.** Computed in `build_plan` at preview time:
  walk the source subtree once for its deepest relative path, add the destination
  prefix, warn above 260. Surfaces in `--json`. **`long_path()` is not applied on
  the write side** - the warning is only honest if Atlas cannot silently exceed the
  limit.

Explicitly not here: the undo stack itself, the inline confirm, and the keybindings.
Those are TUI and belong with ticket 20's shell or with the tree.

Verification: `cd tools/atlas && uv run pytest`, green, with new tests for each
bullet. Fixture drives only - never a shared drive. State what ran.

## Constraints already fixed

- ADR 0006 is the contract. Deviating is a decision, not an implementation detail,
  and belongs back on ticket 04.
- `Action` is frozen and read by `conform`, the CLI, and `--json`. Adding fields
  must not break the six existing consumers; the `Listing` change in ticket 16 is
  the precedent for how to widen a core record safely.
- `apply_plan` never clobbers. CONFLICT stays a real outcome, and a Plan
  containing one is not invertible.
- Ticket 13's ban on recursive counts stands. The path-length walk is per previewed
  action, never per render.

## Resolution

Built test-first, one slice at a time, in `atlas.core.conform`. 281 tests pass, up
from 261; repo lint green; `atlas conform --json` checked by hand on a scratch
fixture drive.

- **`Move(src, dst, is_dir)` and `Action.moved`.** Every apply path fills it:
  a whole-folder rename, the case-only two-step, each child of a merge, and a
  sweep. `is_dir` is recorded rather than re-read at undo time, because sending a
  merged child back needs a Sweep for a file and a Relocate for a folder, and
  asking the filesystem later is both an extra read and a race.
- **`build_repair_plan(report, m, path)`** returns the one Action for a node, or an
  empty Plan for Mapped, Unfiled, and paths the report has never heard of. It takes
  the Action out of the full Plan rather than deriving it a second way, and the
  test asserts equality against `build_plan` for a Drift, a Relocate, a Sweep and a
  Backfill in one project.
- **`invert_plan`** builds the reverse Plan from the manifests, and undo then flows
  through `apply_plan` like any other write. Inverting a merge is the case that
  justifies the manifest: moving the folder back would drag along whatever was
  already living at the destination, and the test proves it does not.
- **`NotInvertible`.** Invertibility is all-or-nothing. A Backfill creates and the
  file-empty-source branch deletes; neither has a move to reverse, and a Conflict
  leaves the drive in a state neither side owns. All three refuse the whole Plan
  rather than performing a partial undo.
- **`Guard`, at two scopes.** `for_project` keeps conform's rescan; `for_action`
  re-reads the map and only the directories the action touches - a move watches the
  parents it leaves and arrives in, a sweep watches the folder it files into. Three
  side-by-side tests: both call an in-scope divergence stale, both notice the work
  itself changed, and the scoped guard deliberately ignores a folder appearing at
  the project root that the action cannot touch. That asymmetry is the point of
  scoping, and it is asserted rather than left implied.
- **`Action.path_length` and `path_warning`.** One walk per previewed action for
  the deepest path under the source, re-hung under the destination. `long_path()`
  is still absent from every write path. It reaches `--json` and the plan line a
  person reads.
- **`action_to_dict`.** `--json` used `a.__dict__`, which stopped serialising the
  moment the manifest held records. The JSON surface now names its own fields.

### Not done here, deliberately

`app.py` still carries its own copy of the full-rescan guard in both
`action_conform` and `action_conform_marked`. Adopting `Guard` there is a TUI
change and belongs with the shell work, not with the core surface. Every
`build_plan` call in the TUI now passes `project=` so preview and guard measure
path length identically - passing it at only some call sites would have made every
conform abort as stale.
