# 6. Tree writes are one-action Plans, revalidated at their own scope, and reversible from a per-project undo stack

Date: 2026-09-03

## Status

Accepted

## Context

Atlas's folder tree offers writes on the live studio drive from a single keystroke
on a node. Everything Atlas writes today goes through one path: `build_plan`
produces a `Plan` of typed `Action`s, the TUI previews it in a modal, and on
confirmation `apply_plan` executes it without ever clobbering a destination. That
contract was designed for `conform`, which a person invokes deliberately, once, on
a whole project.

Two properties of that path do not survive being invoked per node.

**The staleness guard is a full drive rescan.** `action_conform` re-runs
`scan_drive`, rebuilds the plan, and refuses to write unless the drive map, the
rebuilt actions, and `_project_token` all match what was previewed. Ticket 12
measured a full walk of the studio drive at 4.24 seconds over 7,956 folders. That
is a reasonable price for one deliberate operation and an unreasonable one for a
keystroke.

**`_project_token` only covers the project root.** It is the sorted `(name,
is_dir)` list of `project.root_entries`. A node three levels down is outside it
entirely, so the guard that protects `conform` would not protect a tree action even
if it were free.

Separately, the prior design critique scored user control 2/4 for having no undo at
all, and a per-node action makes that worse rather than better: it makes the
mistake cheap to commit while leaving it expensive to reverse.

## Decision

**The tree introduces no new action kinds.** The repairable Filing States from ADR
0004 - Drifted, Misplaced, Loose - map one-to-one onto the existing RENAME,
RELOCATE, and SWEEP. Creating a missing folder is the existing BACKFILL, and since
ADR 0004 rules that an unmet Expectation is not a node, that action belongs to the
Companion Region rather than the tree. Unfiled nodes offer no write, because only a
person can decide where they belong. Core therefore gains no new concepts - it
gains a way to build a `Plan` holding exactly one `Action`.

**Every write crosses a Plan, is previewed, and is confirmed - no exceptions**,
including creating an empty mapped folder. That looked cheap enough to exempt and
is not: the destination may already exist as a file, and the new path may exceed
MAX_PATH, which ticket 19 established is a live condition on this drive.

**Revalidation is scoped to what the action touches.** For a one-action Plan:
re-read the drive map file, re-enumerate the source's and destination's parents,
rebuild that single Action, compare. Tens of milliseconds against a measured
per-enumeration p99 of 91 ms, rather than 4.24 seconds. Project-wide `conform`
keeps the full rescan, which is already paid for and already correct. The abort
path is identical in both - nothing moves, and the operator is told what changed.

**A full undo stack, one per Project**, in memory, capped, discarded on drive
switch. Per project rather than per session because cross-project LIFO is a mental
model nobody holds; "undo my last change to the project I am looking at" is the one
everybody holds, and it eliminates every case where undo touches something off
screen. The stack is optimistic - entries are never eagerly invalidated, because
the same scoped guard runs on every pop and catches a stale entry at the moment it
would write.

**`Action` gains a `moved` manifest**, recording every `(src, dst)` pair actually
moved, empty until applied. `_apply_move` runs with `merge_into_existing=True`, and
after a merge Atlas cannot otherwise tell which files it moved in and which were
already there. Inverting a merge by inference is a guess, and a wrong guess here is
data loss. The manifest costs a field rather than a walk, because `_apply_move` is
already iterating the entries it moves.

**No redo.** Undo restores the precondition that offered the action - undo a
RENAME and the node is Drifted again, undo a SWEEP and the file is Loose again - so
the node is sitting there offering the same repair key. Re-pressing it is redo.

**Confirmation weight follows plan size:** more than one action gets the modal,
exactly one confirms inline on the operation line, which ADR 0005 already made the
persistent surface for reporting writes. Undo inherits the same rule, so the stack
needs no display of its own.

**Path length warns; it never refuses and never routes around.** The `\\?\` prefix
added by ticket 19 for reads works equally well for writes, which is precisely the
hazard - it would let Atlas create a path Explorer, Revit, and the PowerShell tools
cannot open. The check lives in `build_plan` as a field on the Action so the CLI and
`--json` inherit it. Because a RELOCATE moves a subtree, the length that matters is
the deepest path beneath the source after the move, which costs one walk per
previewed action.

**Tree actions ship without CLI equivalents.** Ticket 10 settles the parity rule for
the tree, search, and the dossier together rather than having this decision
pre-empt it.

## Consequences

`Action` is a frozen dataclass consumed by `conform`, the CLI, and `--json`. Adding
`moved` and a path-length warning changes a record that four surfaces read, which is
why this is an ADR rather than a ticket note.

Undo is the largest thing here and it is not free. It requires the manifest, a
per-project stack, and a guard that runs in both directions. The alternative
considered was one level of undo gated on invertibility, which is materially
cheaper and was rejected because a stack that stops at the first merged move is not
the thing it claims to be.

Two guard strengths now exist for the same concept. That is deliberate and the rule
is stated as such - guard strength scales with action scope - but it is a place
where a future change could plausibly apply the wrong one. The narrow guard is only
correct for a Plan whose actions all sit under one known neighbourhood.

Warning rather than refusing on path length means Atlas can be used to create a
path that other studio tools cannot open. That is the operator's call to make, and
it is only an honest call because Atlas does not apply the extended-length prefix
to hide the consequence.

## Corrections

Three claims in this ADR were wrong, all written before the code existed. The first
two were found by pressing the key rather than by reading the design; the third by
ADR 0007, reading what `_apply_backfill` actually creates.

**"The same guard runs on every undo pop."** It cannot. `Guard.for_action.check`
re-derives the Plan from the drive map and compares - which is the strongest check
available for a repair, because a repair *is* a slice of the Plan conform builds.
An undo's Plan is by construction not map-derived: the map wants
`Meetings -> 11 Meetings`, and the undo does the reverse. Guarding an inverse that
way refuses every time, on a drive nothing has changed on.

What an undo has to verify is not "does the map still want this work" - it never
did - but "are these folders still as they were when the repair applied". That is
the watched-directory snapshot, and the snapshot needed no change. `Guard.for_undo`
keeps the map check and the snapshot and drops the re-derivation, carrying a
`derived` flag that says which it is. Ticket 23, session 9.

**Ticket 10's parity question is settled and it reaches back here.** This ADR
deferred CLI equivalents for tree actions to that ticket. ADR 0008 answers it: a
capability that writes owes a CLI form, discharged in the same session. The tree's
repair key is `conform --node PATH`, and its undo is `conform --revert FILE`,
reading back the `--json` manifest a prior apply printed. The CLI has no session,
so it cannot hold the per-Project stack this ADR specifies; what it can do is take
back what it printed, which is what makes `invert_plan` reachable from outside.
That needed `plan_from_dict` - `action_to_dict` had no inverse, so the Move
Manifest was write-only.

**"Creating a missing folder is the existing BACKFILL."** Only for the control
plane. ADR 0007 corrects this: conform backfills `PROJECT.md`, `decisions`,
`AGENTS.md`, `CLAUDE.md` and the analysis directory, and has never created a mapped
section. An unmet Expectation therefore carries its kind, and only a control-plane
one offers a Repair - `f` in the Companion arms it (#42). A missing section keeps
the add-folders path, `a`. The Decision section above, and the "empty mapped
folder" example under it, should be read with that limit.
