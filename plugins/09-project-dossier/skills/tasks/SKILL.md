---
name: tasks
description: Work the project's two task lists - 00 Tasks/TASKS.md (production: model, sheets, research, drafting) and 00 Tasks/TYLER.md (Tyler's personal errands). Use to add, claim, complete, hold or prune tasks; to pick the next task when the user says "work on this project" or "what's next"; or when meeting closeout needs action items filed. Tyler errands are add-only for agents - never check one off.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Bash
  - AskUserQuestion
---

# /tasks — Two Lists, One Contract

Every project carries two task files (ADR 0016), and they are not interchangeable:

| File | Holds | Lanes / IDs | Who checks off |
|---|---|---|---|
| `00 Tasks/TASKS.md` | Production: model, sheets, families, documentation, research | `AGENT` `MODEL` `DECISION` `WAIT`, T-NNN | Whoever did it, with evidence |
| `00 Tasks/TYLER.md` | Tyler's errands: calls, emails, sends, sign-offs | Y-NNN | Tyler only |

Facts go in `PROJECT.md`. Reasons go in `decisions/`. Neither holds tasks. No other
task lists exist anywhere in the project - a longer list for one scope is a scoped
list in `00 Tasks/Lists/`, copied from `_Task List Template.md` and linked from
`TASKS.md`.

## Usage

```
/tasks next             → pick and claim the top unblocked AGENT/MODEL task
/tasks add <item>       → file an item to the right list and lane
/tasks done T-NNN       → close with evidence
/tasks hold T-NNN       → move to Holds with what clears it
/tasks prune            → Done older than 30 days to 00 Tasks/Archive/YYMM-done.md
/tasks                  → show both lists' open state
```

## Hard rules

1. **IDs are never reused.** T-NNN and Y-NNN are independent series. Take max + 1
   across the file and its archive.
2. **One line per task, verb first.** Detail indents below. Link the source
   (minutes, decision, comment letter); never paste it.
3. **Done needs evidence** - a file, an export, a receipt. Move to **Done** with the
   date and the evidence link. "Should be done" is not done.
4. **TYLER.md is add-only for agents.** Never check off, never reorder Tyler's
   items, never send anything. Where the artifact can be prepared, prepare it
   (draft to `08 OUT/Drafts/`, package staged) and link it with `ready:`.
5. **DECISION and WAIT are never started.** They block; they are not work. If every
   actionable item is blocked, report the blockers instead of inventing work.
6. **Edit in place, back up first:** copy the file to `.agent/backups/` before
   rewriting a list. Never leave the backup at the project root.

## Picking up work (`/tasks next`)

1. Read `BRIEF.md`, then `00 Tasks/TASKS.md`, then `.agent/handoff/CURRENT.md`.
2. Take the top unblocked `AGENT` or `MODEL` item from **Now**, then **Next**.
   Respect the Holds table and the project's own priority bands if it declares them.
3. Claim before starting: move the line to **In progress** and append
   `claimed YYYY-MM-DD by <name>`. One task at a time.
4. A claim stale more than 7 days with no run receipt in `.agent/runs/` may be
   reclaimed - check `.agent/handoff/CURRENT.md` first so you are not colliding
   with a live session.
5. `MODEL` work needs a live Revit session. If no Revit bridge is available on this
   machine, do not start the task - report that it needs a session instead.
6. Work it. Scratch goes in `.agent/runs/YYMMDD-<slug>/` from the run template.
7. Close with evidence: move to **Done** with date + receipt link, update
   `.agent/handoff/CURRENT.md`, bump the file's `updated:`.

## Adding from meeting minutes

Each action item goes to exactly one list, linked to the minutes:

- Production work an agent or the team does → `TASKS.md` as `AGENT` or `MODEL`.
- A call only Tyler can make that blocks production → `TASKS.md` as `DECISION`.
- Tyler's own errand (call, email, send, sign-off) → `TYLER.md`; pre-draft the
  artifact if possible and link `ready:`.
- Someone outside → `WAIT`, naming who.

Also close whatever the meeting finished, in both files.
