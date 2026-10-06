---
project: "{{project_folder}}"
updated: {{created}}
---

# Tasks - {{project_name}}

The production task list for this project: model work, sheets, documentation,
research, drafting - anything that moves the deliverable. Tyler and agents edit it
in place. Tyler's personal errands (calls, emails, sends, sign-offs) live in
`00 Tasks/TYLER.md`, never here. Facts -> `PROJECT.md`. Why -> `decisions/`.
A longer list for one scope -> `00 Tasks/Lists/`, copied from
`00 Tasks/_Task List Template.md` and linked below.

**Lanes:** `AGENT` can run unattended - `MODEL` needs a live Revit session -
`DECISION` only Tyler can call it; blocks production until he does - `WAIT`
someone outside, named in the task

**Rules**

- IDs run T-001, T-002 ... and are never reused.
- One line per task, verb first. Detail goes indented below it.
- Link the source (minutes, comment letter, decision). Do not paste it.
- Done only with evidence: a file, an export, a receipt. Move it to **Done** with the date.
- No other task lists anywhere in the project - only this file, `TYLER.md`, and
  linked scoped lists in `00 Tasks/Lists/`.

**Picking up work (agents)**

When told to work on this project without a specific task: read `BRIEF.md`, then
take the top unblocked `AGENT` or `MODEL` item from **Now**, then **Next**. Claim it
before starting - move the line to **In progress** and append `claimed YYYY-MM-DD by
<name>`. One task at a time. Never start a `DECISION` or `WAIT` item; if everything
actionable is blocked, say so and name the blockers. Close with evidence and a run
receipt in `.agent/runs/`. A claim stale more than 7 days with no run receipt may be
reclaimed - check `.agent/handoff/CURRENT.md` first.

## In progress

<!-- Claimed items. Format: - [ ] T-NNN `LANE` <task> - claimed YYYY-MM-DD by <name> -->

## Now

- [ ] T-001 `DECISION` Fill in `PROJECT.md` with `/project-dossier` - done when jurisdiction, occupancy and code edition are set.

## Next

## Waiting on others

| ID | Who | What | Asked | Chase by | Unblocks |
|---|---|---|---|---|---|

## Holds

| ID | Hold | Why | Evidence that clears it | Blocks |
|---|---|---|---|---|

## Parked - outside sheet scope

Research findings no sheet item needs. No further work; never on a sheet. Tyler reviews the list at issue-ready; a promoted item becomes a task with a requirement and a fresh time-box.

<!-- One line each: finding - source path - why it may matter -->

## Lists

<!-- One line per list in 00 Tasks/Lists/: [YYMMDD-slug](Lists/YYMMDD-slug.md) - what it covers - parent T-NNN -->

## Done

<!-- Newest first. Older than 30 days -> 00 Tasks/Archive/YYMM-done.md -->
