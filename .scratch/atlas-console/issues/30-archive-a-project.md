# Archive a project, as an Atlas action

Type: grilling
Status: open
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
