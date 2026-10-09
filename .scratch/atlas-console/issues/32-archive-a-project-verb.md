# Archive and un-archive a project, as Atlas verbs

Type: task
Status: open
Blocked by: -
Parent: ../map.md

Graduated from [ticket 30](30-archive-a-project.md), which decided the design.
Build it. Unblocks Phase 5 of
`docs/plans/2026-10-project-structure-robustness-plan.md` (103 Mosco, 389
Bushwick Ave, ADNY LL97, 242924 Dekalb, 250622 Huckleberry; Coleman excepted).

## What to build

`atlas archive PROJECT` / `atlas unarchive NAME`, drive-scoped plans with new
action kinds `ARCHIVE` / `UNARCHIVE`. Decision and reasoning on ticket 30; the
shape:

- **Map schema.** `controlPlane.archiveRoot`, default `_Archived Projects`. The
  key names the destination folder only; the archive root stays outside the
  project list (plan Q3) - `is_project_dir` already excludes `_`-prefixed
  roots, so archived projects are invisible to doctor and the console with no
  further work.
- **The plan.** One plan per project: the folder Move (drive root to archive
  root, one manifest entry) plus the `_Project Index.md` row stamped
  `archived YYYY-MM-DD` via `update_project_index_row`, with the row's prior
  text recorded so the inverse restores it verbatim. Drive-root-relative path
  validation of the same shape as `_inside` - the project-scoped containment
  invariant in `plan_from_dict` is not relaxed to make room for this.
- **Precondition check at plan-build.** Refuse: project root unreadable,
  destination name already taken at the archive root, project already archived
  (for un-archive: not under the archive root). Warn in the preview, never
  refuse: count of Revit/CAD/linked-resource files in the project
  (`*.rvt .rfa .rte .dwg .ifc .pcg .rcp`, one walk, paid once at preview);
  count of unchecked task items (TASKS.md, and PROJECT.md open items where
  readable); a note that the prompt-vault note and contacts stay untouched.
- **Confirmation is always the modal**, even at one to three actions - the
  explicit exception to ADR 0006's inline-for-one-action rule that ticket 30
  recorded. No `archive --all` inference: every archive is named and approved
  one project at a time.
- **Guard and undo.** Staleness Guard between preview and apply, drive-scoped:
  map unchanged, the two watched parents (drive root, archive root) unchanged.
  `UNARCHIVE` is the inverse plan through the existing `invert_plan` /
  `conform --revert`-shaped machinery, with the `for_undo` guard shape.
  Re-invoking archive after undo is redo.
- **CLI parity (ADR 0008).** The verbs ship on the CLI and the console in the
  same session; console archive is invoked per project from the list, unarchive
  by typed name (the archive root is enumerated only on demand).
- **ADR work.** Add the ticket 30 amendment text to ADR 0006 (drafted on the
  ticket) and author the new ADR (0019) carrying the full design. Vocabulary -
  Archive Root, Archive Precondition - lands in `/CONTEXT.md`.

## Constraints

- Never touch the production drive. Fixture drives only, per the map's standing
  constraints. The five real archive moves are a separate, Tyler-approved
  production run after this ships (plan Phase 5).
- Every mutation crosses the plan with preview and confirmation; the drive log
  gets its line per applied archive, as conform does.
- No Revit-link scanning is promised: the mount cannot enumerate links, and the
  model-file count warning is the honest substitute (ticket 30, recorded
  limit).
- `_Archived Projects` naming and per-year structure are Tyler's (ticket 30
  constraint); the verb reads `archiveRoot` and nothing else.

## Done when

- `atlas archive PROJECT` on a fixture drive moves the folder under the archive
  root, stamps the index row, logs it, and prints the manifest as JSON;
  `atlas unarchive NAME` restores folder and row exactly.
- Precondition refusals and both warning lists are covered by tests, including:
  destination collision, already-archived, unreadable project root, and a
  project containing `.rvt` files warning without refusing.
- Undo after archive restores the index row text verbatim; re-archiving after
  undo works (redo by precondition).
- Archived projects do not appear in `doctor`, `atlas tree`, or the console
  project list; `unarchive` finds them by name anyway.
- Tests green (`uv run pytest`); ADR 0006 amendment applied, ADR 0019 authored,
  `/CONTEXT.md` terms landed.
