# 19. Archiving a project is a drive-scoped verb, not a relocation

Date: 2026-10-09

## Status

Accepted. Decided by Tyler 2026-10-07 (ticket 30), built under ticket 32
(`.scratch/atlas-console/issues/30-archive-a-project.md`,
`32-archive-a-project-verb.md`). Amends ADR 0006.

## Context

Tyler ruled 2026-10-07 that dormant projects move under `_Archived Projects`
(Coleman excepted). Atlas had no verb that moves a whole project: conform's
relocations move folders *within* a project, and its plan containment is
project-scoped on purpose - that containment is a security property
(`plan_from_dict` can refuse any path outside the project).

## Decision

1. **New action kinds, ARCHIVE and UNARCHIVE**, on a drive-scoped plan
   (`ArchivePlan`) that reuses the conform primitives - the Action record, the
   Move Manifest, inverse-plan and Guard shapes - with paths validated
   drive-root-relative (`_drive_relative`, the same shape as `_inside`, one
   level up). Conform's project-scoped containment is not relaxed to make room
   for this; archive manifests have their own door.
2. **The destination is map-named**: `controlPlane.archiveRoot`, default
   `_Archived Projects`, strictly parsed at load. The first segment must start
   with `_` - that prefix is the whole mechanism keeping archived projects out
   of the scan (`is_project_dir`), which is what makes an archived project
   invisible to doctor, `atlas tree`, and the console project list with no
   further work.
3. **One plan per project**: the folder Move plus the `_Project Index.md` row
   stamped `archived YYYY-MM-DD`. The row is stamped, not removed - the
   register is history - and its prior text rides the applied Action so the
   inverse restores it verbatim. The prompt-vault note and contacts are
   untouched (historical and shared); the preview says so even when there is
   nothing to warn about.
4. **Warn, never refuse**: Revit/CAD/linked-resource file count
   (`rvt rfa rte dwg ifc pcg rcp`, one walk paid at plan build) and open task
   items warn in the preview. A true cross-project Revit-link scan is not
   knowable from the mount - links live inside binary models - so the count is
   the honest substitute, not a placeholder for a real scan.
5. **Confirmation is always the modal**, even at one action - the explicit
   exception to ADR 0006's inline-for-one-action rule. A whole-project move is
   the largest single action Atlas applies. No `archive --all`: every archive
   is named and approved one project at a time.
6. **Guard and undo**: the Guard watches the map and the two drive-level
   parents (drive root, archive root), drive-scoped; there is no
   re-derivation, because an archive is an operator ruling, never map-derived.
   UNARCHIVE is the inverse plan through the same machinery; unarchive by name
   enumerates the archive root on demand. Re-invoking archive after undo is
   redo. On the CLI, undo is `unarchive --revert FILE` against the JSON
   manifest `archive --apply --json` printed - the CLI holds no undo stack
   (same shape as `conform --revert`).

## Consequences

- CLI: `atlas archive PROJECT` / `atlas unarchive NAME [--revert FILE]`, dry
  run by default, `--apply` to write, `--json` for the manifest. Exit codes
  keep the contract: 0 applied clean, 1 pending/dry run, 2 error or refusal.
- A missing `_Project Index.md` or a missing row is the no-row case, not a
  failure: the folder still moves, the note says the index was unchanged.
- An emptied archive root is pruned after an un-archive (rmdir-only).
- The five real archive moves (103 Mosco, 389 Bushwick Ave, ADNY LL97, 242924
  Dekalb, 250622 Huckleberry) are a separate Tyler-approved production run -
  plan Phase 5 of
  `docs/plans/2026-10-project-structure-robustness-plan.md`.
- `_Archived Projects` naming and any per-year structure under it are Tyler's;
  the verb reads `archiveRoot` and nothing else.
