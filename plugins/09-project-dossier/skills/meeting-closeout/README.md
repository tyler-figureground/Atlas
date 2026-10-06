# /meeting-closeout

Turns a meeting transcript into the full closeout, six steps in one run:

1. **Minutes** beside the transcript in `11 Meetings/` (+ PDF)
2. **Decision records** in `decisions/` - supersede, never overwrite
3. **Facts** in `PROJECT.md`, sourced and dated
4. **Tasks** split across both lists - production to `TASKS.md`
   (`AGENT`/`MODEL`/`DECISION`/`WAIT`), Tyler's errands to `TYLER.md` with
   pre-drafted artifacts linked `ready:`
5. **Brief** rebuilt - Settled/Open/Now/Latest meeting
6. **Report** - what changed, with IDs, plus a regenerated Tyler digest

## Usage

```
/meeting-closeout                     → process the newest unprocessed transcript
/meeting-closeout 261004              → a specific meeting
```

Not done until all six. A meeting whose minutes exist but whose brief and tasks are
stale is the leak that makes agents re-ask settled questions.

Writes both task lists per ADR 0016; see [`/tasks`](../tasks) for the list contract.
