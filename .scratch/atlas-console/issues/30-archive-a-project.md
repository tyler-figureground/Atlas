# Archive a project, as an Atlas action

Type: grilling
Status: closed (2026-10-07)
Blocked by: -
Parent: ../map.md

## Question

Tyler ruled 2026-10-07 (docs/plans/2026-10-project-structure-robustness-plan.md,
Phase 0.3): dormant projects move under `_Archived Projects`; Coleman stays live and
conforms. Atlas today has no verb that moves a whole project - `project edit` edits
intake, conform's relocations move folders *within* a project, and `_Archived
Projects` is not a project root the map describes.

So: is archiving a project a new action kind, or a relocation whose destination the
map names?

What the ticket has to settle:

- **What archives.** The project folder alone, or also its rows in the drive index
  (`_Project Index.md`), its prompt-vault note, and its contacts? A project with a
  live `TYLER.md` open item should probably refuse, or warn.
- **What an archived project is to Atlas.** Invisible to `doctor` and the console
  project list? Listed greyed? A `projectStates` key in the map (`active` |
  `archived`) rather than a path rule?
- **The way back.** Un-archive must be the same plan inverted. A Move Manifest
  covers the folder move; index-row removal needs its own inverse.
- **Who holds the guard.** Nothing a Revit model references may move - the existing
  conform guard - but an archived project is dormant precisely because nothing
  references it. Is the guard still run, or is "no `.rvt` links resolve outside the
  project" a precondition check?

## Constraints

- Every mutation crosses a Plan with preview and confirmation (map.md standing
  constraint). A whole-project move is the largest single action Atlas would ever
  apply - confirmation weight follows plan size (ADR 0006), so this is the modal,
  never the inline confirm.
- `_Archived Projects` naming and whether it is one folder or per-year children is
  Tyler's, not this ticket's.
- Undo's precondition rule applies: re-pressing the archive key after undo is redo.

## Done when

A decision: action kind or relocation, what archives with the folder, what Atlas
shows afterward, and the guard. Then it becomes a task ticket with tests.

## Decision

**A new action kind, drive-scoped - not a relocation.** Archive is an operator
ruling (Tyler, 2026-10-07), not drift the map detects: no `report_project` fact
derives "this project is dormant", so it can never be a conform relocation,
which is a map rule. The conform `Plan` is project-scoped by construction -
`_safe_target` / `_inside` refuse any path outside the project, and that
refusal is the security property, not a limitation to relax. Archive therefore
gets a new action kind `ARCHIVE` (inverse `UNARCHIVE`) in a drive-scoped plan
that reuses the Action / Move Manifest / `invert_plan` / Guard primitives with
drive-root-relative path validation of the same shape. The destination is
map-named via a `controlPlane.archiveRoot` key (default `_Archived Projects`):
the map is the only folder-structure brain, but naming the archive root does
not map its contents - per the plan's Q3, `_Archived Projects` stays outside
the project list until search exists.

**What archives: the folder and the index row - stamped, not removed.** The
`_Project Index.md` row stays (the register is history); `update_project_index_row`
sets Status to `archived YYYY-MM-DD`, and the prior row text goes into the Plan
record so the inverse restores it verbatim. The prompt-vault note and contacts
are untouched: they live in `_tools`, are historical and shared, and deleting
them buys nothing - the preview notes that the vault note remains. A project
with open TYLER.md / TASKS.md items **warns, never refuses**: unchecked items
are counted and listed in the preview modal. Refusal would block exactly the
intended use - a dormant project with stale open items is the common case.

**An archived project is invisible to Atlas afterward.** `is_project_dir`
already excludes `_`-prefixed roots and `scan_drive` never descends, so archived
projects vanish from doctor and the console for free. Recommended over
greyed-listing: greyed costs an extra enumeration per drive scan and a new
project state for near-zero value. Un-archive takes a name (`atlas unarchive
"103 Mosco"` / console equivalent) and enumerates the archive root only on
demand.

**Un-archive is the inverse plan.** The Move Manifest covers the folder (one
Move, `is_dir`); the index-row inverse restores the recorded prior row; the
undo Guard is the ADR 0006 `for_undo` shape, drive-scoped - snapshot the two
watched parents (drive root, archive root). Re-invoking archive after undo is
redo, per the standing rule.

**The guard is two things, and the Revit check is honest about what the mount
cannot see.** The staleness Guard still runs between preview and apply (map
unchanged; the two watched directories unchanged; same abort semantics). "No
`.rvt` links resolve outside the project" becomes a **plan-build precondition
check**, because it is not fully knowable from the mount: Revit links live
inside binary models and local journals, and nothing on the drive enumerates
them. What the precondition does check, all cheap: project root readable;
destination name free at the archive root; project not already under the
archive root. What it surfaces as warnings in the modal: (a) a count of
Revit/CAD/linked-resource files in the project (`*.rvt .rfa .rte .dwg .ifc
.pcg .rcp` - one walk, paid once per archive, at preview), so the operator sees
"links into this project from live projects will break" before confirming; (b)
the open-task count. Cross-project link breakage is Tyler's call, made with the
warning in front of him - the tool records the ruling, it does not detect
dormancy. Confirmation is **always the modal**, even at one to three actions:
an explicit exception to ADR 0006's inline-for-one-action rule, because a
whole-project move is the largest single action Atlas applies.

Reasoning, three lines:

1. Relocation is map-derived repair of drift; archiving is neither map-derived
   nor repair, and wedging it into the project-scoped Plan would break the
   path-containment invariant that makes `plan_from_dict` safe.
2. Invisible-afterward is free (`is_project_dir` already excludes `_` roots),
   reversible by name, and matches Q3's ruling that the archive root stays
   outside the map - greyed-listing is cost with no operator asking for it.
3. Warn-not-refuse on open items and models is the only posture that fits the
   actual job: dormant projects are dormant *with* stale items and models, and
   the precondition check reports what Atlas can see rather than pretending to
   a link scan only Revit can run.

Consequences:

- Becomes build ticket **32** (archive verb). Vocabulary (Archive Root,
  Archive/Unarchive, Archive Precondition) lands in `/CONTEXT.md` with that
  build, and the full design wants a new ADR (0019), drafted there.
- **ADR 0006 needs a line.** Drafted amendment, to be added by ticket 32 (not
  created here):

  > **Amendment (ticket 30, 2026-10-07): the action set gains ARCHIVE and
  > UNARCHIVE, drive-scoped.** These move a whole project between the drive
  > root and the map's `controlPlane.archiveRoot`. They are not map-derived:
  > an operator names the project, and the plan carries the folder Move plus
  > the project-index row's before/after text so the inverse restores both.
  > Their Guard watches the two drive-level parents rather than project
  > folders. Confirmation is always the modal, an explicit exception to
  > inline-for-one-action: a whole-project move is the largest single action
  > Atlas applies.

- ADR 0007 is untouched: archive moves no node within a project tree, and the
  project disappears from the console rather than reconciling - the
  reconcile-by-manifest machinery never sees it.
- Phase 5 of `docs/plans/2026-10-project-structure-robustness-plan.md` (the
  five dormant projects, Coleman excepted) unblocks once ticket 32 ships: one
  Plan per project, Tyler approves each, undo restores.
- Recorded limit: a true cross-project Revit-link scan needs Revit (or Pyvoid)
  running; the model-file warning is what Atlas can honestly offer from the
  mount. If a real link breakage happens anyway, that is the unpark trigger for
  revisiting.
