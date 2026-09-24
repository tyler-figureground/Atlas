---
title: "What the folder tree is allowed to write"
date: 2026-09-03
generated_by: skills-for-architects
---

# What the folder tree is allowed to write

Type: grilling
Status: resolved
Blocked by: -
Parent: ../map.md

## Question

File-level actions are in scope: creating a folder the map expects, renaming a
drifted folder, filing an unfiled item into its mapped home, revealing in Explorer.
Every one of those except reveal is a mutation on the live studio drive, triggered
from a tree node by a single keystroke.

Atlas today puts a core-built plan, an exact preview, and a confirmation in front of
every write, and never overwrites a destination.

Resolve:

- Does every tree action build a core plan and confirm, with no exceptions? The
  proposed answer is yes - the same contract conform already meets.
- If yes, what does confirmation look like for a single-node action, where a modal
  listing one line is heavier than the action itself? Is there a lighter confirm
  that is still honest?
- Is there any action cheap and reversible enough to skip confirmation - creating an
  empty mapped folder, for instance - and if so what makes it safe?
- Is there undo, or is preview-then-confirm the whole safety story? The prior
  critique scored user control 2/4 specifically for having no undo.
- What happens when the drive changed underneath a displayed tree? The existing code
  uses stale-plan fingerprints; does the tree carry the same guarantee?
- Do tree actions get CLI equivalents, or is this the first TUI-only capability?
  Interacts with the CLI-parity ticket.

## Answer

### What the existing contract actually is

Read before deciding, because two details change the shape of the answer.

`core/conform.py` has `Action(kind, src, dst, file_count, status, note)` in four
kinds - BACKFILL, RENAME, RELOCATE, SWEEP - and `Plan(project, actions)`.
`apply_plan` sorts by kind, never clobbers, returns DONE / CONFLICT / SKIPPED per
action, and appends an audit line via `append_log`.

`tui/app.py:1732` `action_conform` builds the plan from the cached report, previews
it in `ConfirmListModal`, and on confirm **rescans the whole drive**, rebuilds the
plan, and aborts unless `fresh_map`, `fresh_plan.actions`, and
`_project_token(fresh_project)` all match the preview.

The two details:

1. **The staleness guard costs a full `scan_drive`** - 4.24 seconds over 7,956
   folders, per ticket 12's measurement. Fine once for a deliberate project-wide
   conform. Not viable per keystroke on a node.
2. **`_project_token` is the project root's entries only** (`app.py:73`). A node
   three levels down is not covered by it at all.

### The action set

**The tree invents no new action kinds.** Every write it offers is a one-action
slice of the Plan conform would already build.

The repairable Filing States in `CONTEXT.md` are exactly Drifted, Misplaced, and
Loose, and those map one-to-one onto RENAME, RELOCATE, and SWEEP. Unfiled can
never be repaired by Atlas by definition. Creating a missing folder is BACKFILL,
and it acts on an unmet Expectation - which ADR 0004 says is not a node - so it
lives in the Companion Region, not the tree.

- **Tree, writes:** repair this node. One key, because a node has at most one
  Repair.
- **Companion, writes:** create this Expectation.
- **Both, non-writes:** reveal in Explorer, open file, copy path.
- **Not offered:** delete, rename-to-arbitrary, create-arbitrary. An Unfiled node
  offers reveal and nothing else, which is what `CONTEXT.md` already says about it.

  *Note, 2026-09-23 (#45, built):* `o` opens the node under the cursor, and on an
  Unfiled node reveals it in Explorer instead. `y` copies the node's path on every
  node, Unfiled included. "Reveal and nothing else" was written against the writes
  above it; copying a path is not a write, touches nothing on the drive, and is
  what a person deciding where an Unfiled thing belongs reaches for first.

Core gains no new concepts. It gains a way to build a Plan holding one Action.

### Plan and confirm, with no exceptions

Every write crosses a Plan, is previewed, and is confirmed - including the empty
mapped folder that looked cheap enough to skip. It is not: the map's target may
already exist as a file, and it can push a path past MAX_PATH, which ticket 19
proved is a live condition on the studio drive rather than a theoretical one.

### Undo

**A full undo stack**, one per Project, in memory, capped at 50, discarded on drive
switch, surviving `r` refresh - a rescan changes what Atlas knows, not what the
drive contains.

Per Project rather than per session because cross-project LIFO is a mental model
nobody holds. "Undo my last change to the project I am looking at" is the one
everybody holds, and it removes every case where undo touches something off screen.

**No redo.** It is free without being built. Undo restores the precondition that
offered the action: undo a RENAME and the node is Drifted again, undo a SWEEP and
the file is Loose again, undo a BACKFILL and the Expectation is unmet again. The
node is sitting there offering the same repair key, so re-pressing it *is* redo.
The tree is stateful in a way a text editor is not, and this is the one place that
pays off.

**Undo is a write like any other.** It builds a Plan, previews, confirms, and
revalidates. Bound to `u`.

### The move manifest

`_apply_move` runs with `merge_into_existing=True`. After a merge Atlas cannot
tell which files it moved in and which were already there, so the inverse is a
guess - and a wrong guess here is data loss. A full stack cannot dodge this.

**`Action` gains a `moved` field**: every `(src, dst)` pair actually moved,
including inside a merge, empty until applied. Undo replays it in reverse.

The cost is a field, not a walk - `_apply_move` is already iterating the entries it
moves, so the manifest is the list it has in hand. The rejected alternative was
marking merged actions non-invertible and letting the stack stop at the first one,
which makes "full undo stack" a claim that stops being true at the third entry.

Side benefit: the result modal can report exactly what moved rather than only the
action kind.

### Revalidation

**Guard strength scales with action scope.** A one-node action can only be
invalidated by its own neighbourhood, and the existing guard's three checks narrow
cleanly onto it:

- re-read the drive map file,
- re-enumerate the source's parent and the destination's parent,
- rebuild that single Action and compare.

Tens of milliseconds against ticket 12's measured p99 of 91 ms per enumeration,
instead of 4.24 seconds. The full rescan stays for project-wide conform, where it
is already paid for and already correct.

The abort path is unchanged: same "changed since preview - nothing moved" outcome,
same refusal to write. **The same guard runs on every undo pop**, which is what
lets the stack be optimistic - entries are never eagerly invalidated, because a
stale one is caught at the moment it would write.

### Confirmation

**More than one action, modal. Exactly one, inline.**

A `ConfirmListModal` listing a single line is heavier than the action it guards.
Ticket 03 made the operation line the persistent surface that reports writes;
making it also the surface that *asks* about a one-line write is coherent, since it
is the same row on the same subject before and after.

It is still an explicit second keystroke, so the standing constraint holds. Undo is
a safety net, not a substitute for consent.

Undo inherits this rule, so the stack needs no display of its own: you see what you
are about to reverse in the same place you saw what you were about to do. No fourth
Companion Mode.

### Path length

Atlas **warns and obeys**. It does not refuse.

Two things make the warning meaningful:

**`long_path()` must not be applied blindly on the write side.** Ticket 19 added
the `\\?\` prefix for reads, and it works just as well for writes - which is the
danger. It would let Atlas successfully create a path that Explorer, Revit, and the
PowerShell tools cannot open. A warning is only honest if Atlas does not silently
route around the limit.

**A RELOCATE moves a whole subtree**, so the path that breaks is not the
destination folder, it is the deepest file beneath it after the move.

The check lives in `build_plan`, in core, as a field on the Action - not in the
TUI - so the CLI and `--json` inherit it. At preview time only, walk the source
subtree once for its deepest relative path, add the destination prefix, and if the
result exceeds 260 the Action carries the warning. Preview shows it, confirm still
offers to proceed, the operation line repeats it afterward.

That walk is per-previewed-action, not per-render, so it does not conflict with
ticket 13's ban on recursive counts in labels.

### CLI

**Tree actions ship without CLI equivalents.** No `atlas conform --path` is added
here. Ticket 10 decides the parity rule for the tree, search, and the dossier
together, rather than having this ticket pre-empt it.

### What this does to the map

- The **long paths on the write side** fog patch is cleared - it is answered above
  for the tree's actions and for `conform`'s plan-building generally.
- Tickets 07 and 15 are unblocked.
- Ticket 21 graduates: the core write surface, as Atlas code.

Vocabulary in `/CONTEXT.md`. Decision in `docs/adr/0006`.
