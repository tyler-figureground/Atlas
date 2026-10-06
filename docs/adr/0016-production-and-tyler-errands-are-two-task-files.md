# Production work and Tyler's errands are two task files

Date: 2026-10-05

## Status

Accepted

Map v3.6. Decided by Tyler on 2026-10-05.

## Context

`00 Tasks/TASKS.md` (ADR 0013) holds everything in one file, laned `TYLER`, `AGENT`,
`MODEL`, `WAIT`. Two different kinds of work are conflated:

- **Production** - model updates, sheet sets, families, documentation, research. Work a
  team member or an agent can pick up and execute. An agent told "work on this project"
  should read the dossier, take the top unblocked item, and do it.
- **Tyler's errands** - the project manager's own list from meeting minutes: send that
  email, make that call, issue those drawings. Nobody else does these; agents at most
  pre-draft the artifact.

One list makes both worse: agents picking production work must triage Tyler's personal
items, and Tyler scanning for his errands wades through production detail (211 Centre's
TASKS.md runs to pages of audit findings). Meeting closeout also had no rule for where a
Tyler errand goes versus a production task.

The `TYLER` lane itself mixed two meanings: Tyler's personal errands, and decisions only
Tyler can make that block production (211 Centre T-040/T-041/T-045). Those are different -
the second is production state, not an errand.

## Decision

Two files in `00 Tasks/`, per project:

**`TASKS.md` - the production task list.** Lanes are now `AGENT` (runs unattended),
`MODEL` (needs a live Revit session), `DECISION` (only Tyler can call it; blocks
production until he does), `WAIT` (named outside party). Adds an **In progress** section
and a claim protocol: an agent taking a task moves it there with
`claimed YYYY-MM-DD by <name>` before starting, works one task at a time, and closes with
evidence plus a run receipt. A claim stale over 7 days with no run receipt may be
reclaimed after checking the handoff. Decision blockers stay in this file - they are
production state - and are not copied to Tyler's list; agents surface them when blocked.

**`TYLER.md` - Tyler's list.** Personal errands only: calls, emails, sends, sign-offs.
Own ID series (Y-NNN). Agents add items from meeting minutes but never check one off.
Where the artifact can be prepared, the agent prepares it (draft to `08 OUT/Drafts/`,
package staged) and the item links it with `ready:`; Tyler sends. This file is the source
of truth; a drive-level digest (planned, not yet built) aggregates open items across
projects and is never edited.

Meeting closeout writes each action item to exactly one list: production to `TASKS.md`,
Tyler errand to `TYLER.md`, Tyler decision blocking production to the `DECISION` lane,
outside party to `WAIT` - each linked to the minutes.

## Consequences

- Templates: `TASKS.md` reframed (lanes, In progress, pickup rules), new `TYLER.md`,
  `agents-rules.md` updated (session start, meeting step 4, filing rules), scoped-list
  template lane wording. Map v3.6 seeds `00 Tasks/TYLER.md`; conform backfills it
  create-only, doctor reports it missing until then.
- Migration (separate, per project, Tyler-approved): personal errands move from each
  project's `TASKS.md` to `TYLER.md`; `TYLER`-lane decision blockers are retagged
  `DECISION` and stay.
- Not built yet: the cross-project Tyler digest (an Atlas command or scheduled script),
  and `/tasks` / `/meeting-closeout` skills (research report phase 3). The updated
  AGENTS.md contract carries the workflow until then.
- Tyler's team members use the same claim line as agents, so office and agent work do
  not collide.
