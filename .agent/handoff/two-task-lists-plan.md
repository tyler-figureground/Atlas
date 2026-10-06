# Two task lists - implementation plan

2026-10-05. Tyler's ask: split the single per-project task list into a **production
list** (Revit model, sheets, families, documentation - work Tyler, the team, or an
agent can pick up) and a **Tyler-only list** (PM errands from meeting minutes: emails,
calls, sends). Both written from meeting transcripts during closeout. Agents cd into a
project, read the dossier, and pick the top production task without triaging Tyler's
errands.

Decision record: `docs/adr/0016-production-and-tyler-errands-are-two-task-files.md`
(accepted 2026-10-05). Tyler's answers to the open questions:

- Tyler list lives per project at `00 Tasks/TYLER.md` (source of truth), plus a
  generated drive-level digest aggregating all projects.
- Decision blockers stay in `TASKS.md` as a `DECISION` lane. Not mirrored to `TYLER.md`.
- This round: templates + rules + ADR + plan. Skills and digest tooling later.

## Done this round (repo)

| # | Work | File |
|---|---|---|
| 1 | TASKS.md reframed as production list: lanes `AGENT`/`MODEL`/`DECISION`/`WAIT`, **In progress** section, claim protocol, agent pickup block | `tools/atlas/src/atlas/templates/project/TASKS.md` |
| 2 | New TYLER.md template: errands only, Y-NNN IDs, agents add but never check off, `ready:` links to pre-drafted artifacts, digest rule | `tools/atlas/src/atlas/templates/project/TYLER.md` |
| 3 | agents-rules.md: session-start pickup protocol; meeting closeout step 4 splits items across the two lists; filing rule names both files | `tools/atlas/src/atlas/templates/project/agents-rules.md` |
| 4 | Scoped-list template: lane wording `AGENT`/`MODEL`/`DECISION`/`WAIT`, errands excluded | `tools/atlas/src/atlas/templates/project/Task List Template.md` |
| 5 | ADR 0016 | `docs/adr/0016-production-and-tyler-errands-are-two-task-files.md` |
| 6 | CONTEXT.md terms: Task List rewritten; Tyler List, Decision Lane, Claim, Tyler Digest added | `CONTEXT.md` |
| 7 | Drive map v3.6: seeds `00 Tasks/TYLER.md` (conform backfills create-only; doctor flags missing) | `G:\Shared drives\ARCHITECTURE\_tools\architecture-map.json` |

## Remaining phases

### Phase A - Digest (the cross-project Tyler view) - DONE 2026-10-05

- `atlas tyler` (Atlas 0.10.0): walks every project, reads `00 Tasks/TYLER.md`
  (open errands) and the `DECISION` lane of `00 Tasks/TASKS.md`, prints the digest;
  `--write` regenerates `G:\Shared drives\ARCHITECTURE\_tools\TYLER-TODAY.md`.
  Read-only by default. Header says "never edit - edit the project list". Includes
  the read-only "Blocked on your call" section per project (open question 2: yes).
- Core: `tools/atlas/src/atlas/core/tyler.py`; CLI: `cmd_tyler`; tests:
  `tools/atlas/tests/test_tyler.py`.
- Not built: scheduled regeneration. Run `atlas tyler --write` after each meeting
  closeout (the /meeting-closeout skill already says to), or wire a scheduled task.

### Phase B - Skills - DONE 2026-10-05

- `plugins/09-project-dossier/skills/tasks/`: next/add/done/hold/prune across both
  lists; claim protocol; TYLER.md add-only for agents.
- `plugins/09-project-dossier/skills/meeting-closeout/`: the six-step closeout with
  the two-list split in step 4 and digest regeneration in step 6.
- Marketplace description, root README (47 skills), skills-menu updated; lint green.

### Phase C - Migrate live projects - DONE 2026-10-05

- Backfill: conform --all --apply backfilled `TYLER.md` and refreshed the AGENTS.md
  block (new rules text) on all 15 projects; no moves or deletes. Revert manifest:
  `.agent/handoff/conform-20261005-manifest.json`. 295 West Ln also got its missing
  control plane (TASKS.md, INTAKE, runs/backups, AHJ seed).
- Content migration, all 14 projects with lists, 2026-10-05. Every project backed
  up to `.agent/backups/TASKS.backup-20261005-two-list-split.md` before editing.
  Verified after: zero open `TYLER` tags anywhere, In progress section present in
  every TASKS.md, Y-IDs unique per project, no new lines over 1000 chars.
  - Six seed-state projects (Mosco, Hayes, Dekalb, Tahoe, Bushwick, ADNY): header
    swap + T-001 retag DECISION, scripted.
  - Monte Vista (pilot, by main session): 5 moved, 17 retagged.
  - Monticello, Pestoni, Beitz 315 (main session): 1 errand each moved; Pestoni
    T-010's six table references annotated `(now TYLER.md Y-001)`; Beitz T-004 refs
    annotated.
  - Coleman, 64th Lane, Silverado, 211 Centre (subagents): 12 / 8 / 11 / 4 errands
    moved; retags mostly DECISION. 211 Centre header customization preserved; only
    the Lanes line changed plus the pickup block and In progress section.
- Digest after migration: 45 errands / 39 decisions drive-wide.
- Judgment calls flagged for Tyler's review (all reversible):
  64th Lane T-028 (DECISION) and T-044 (AGENT); Silverado T-019 Veras rendering
  (MODEL - move to Y-012 if Veras is Tyler-only); 211 Centre T-015/T-016 moved to
  TYLER.md (Y-002/Y-003) though decision-flavored - reverse if you'd rather they
  stay DECISION; Coleman T-002 (DECISION) and T-006 (errand).

### Phase D - Keep clean

- Doctor finding: task-list-shaped files outside `00 Tasks/` (extends ADR 0009 file
  rules; ticket 26 territory).
- Monthly prune already specified: Done older than 30 days -> `00 Tasks/Archive/`,
  same rule now covers `TYLER.md`.
- Digest freshness: regenerate on meeting closeout and on `atlas tyler`; stale-digest
  warning if newer than the newest TYLER.md is false... simpler: digest prints its
  generation time.

## Open questions for later phases

| # | Question | Default |
|---|---|---|
| ~~1~~ | Digest as Atlas command or script first? | Answered: `atlas tyler`, Atlas 0.10.0 |
| ~~2~~ | Does the digest list `DECISION` blockers? | Answered: yes, read-only "Blocked on your call" section |
| 3 | Team members (office staff) claim via the same line format - any identity convention? | `claimed YYYY-MM-DD by <first name>`; agents use session slug |
| 4 | MODEL tasks and Revit: who opens the session - agent drives Revit directly, or queues for a person? | Agent opens Revit where the bridge exists on that machine; otherwise the task stays claimable but the agent reports the missing bridge instead of starting |
