---
name: meeting-closeout
description: Close out a recorded meeting - turn the transcript into minutes, decision records, dossier facts, tasks in both lists (production TASKS.md and Tyler's TYLER.md), and a rebuilt BRIEF.md. Use after any project meeting once the transcript exists in 11 Meetings/, or when the user says "process the meeting", "meeting notes", or drops a transcript. Not done until all six steps are done.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Bash
  - AskUserQuestion
---

# /meeting-closeout — Transcript to Minutes, Decisions, Tasks, Brief

A meeting that produced minutes but stale tasks and a stale brief is the leak that
makes the next agent re-ask settled questions. This skill is the whole closeout, in
order, every time. Do not stop between steps.

## Input

The transcript lands in `11 Meetings/` (Dicta or similar). If several transcripts
are unprocessed, process oldest first, one run each. Read the current
`decisions/REGISTER.md` (or `decisions/` index) before judging what is new.

## The six steps, in order

1. **Minutes.** Write `YYMMDD - <Name> - Meeting Minutes.md` beside the transcript.
   Decisions made (each linked to the register), action items with owner, open
   questions; every item in the transcript, walked end to end.
   `Prepared by: Tyler`. A bare `[mm:ss]` timestamp on every decision and action,
   never explained. Mark doubt inline with `(confirm)`. Never name file paths, the
   transcript, the recording or the transcription tool; no limits paragraph, no
   internal-draft label. Everything filed for a person gets a PDF beside it
   (`atlas pdf "<file>"`, re-run after every edit).

2. **Decisions.** One record per decision made or changed - `/decision`, or the
   project's own register if its AGENTS.md says it keeps one. Supersede; never
   overwrite a rationale.

3. **Facts.** Update `PROJECT.md` front matter and its mirror rows, each with
   source and date. Facts only - no session narrative.

4. **Tasks.** Every action item goes to exactly one list, linked to the minutes
   (ADR 0016):
   - Production work (model, sheets, research, drafting) → `00 Tasks/TASKS.md`,
     lane `AGENT` or `MODEL`.
   - A decision only Tyler can make that blocks production → `TASKS.md`, lane
     `DECISION`.
   - Tyler's personal errand (call, email, send, sign-off) → `00 Tasks/TYLER.md`,
     next Y-NNN. If the artifact can be prepared now, draft it to
     `08 OUT/Drafts/` and link it with `ready:`. Never send.
   - Someone outside → `WAIT` in `TASKS.md`, naming who.

   Close tasks the meeting finished - in both files. If either file does not exist,
   create it from the Atlas template (`00 Tasks/TASKS.md`, `00 Tasks/TYLER.md`)
   first. Back up both files to `.agent/backups/` before rewriting.

5. **Brief.** Rebuild `BRIEF.md`: answered questions move to Settled, new ones to
   Open, update Now and Latest meeting, bump `updated:`. Under 150 lines.

6. **Report.** Tell Tyler: minutes path, decisions added/changed (numbers), tasks
   added/closed per list (IDs), brief updated. If `atlas` is available, regenerate
   his digest: `atlas tyler --drive "G:\Shared drives\ARCHITECTURE" --write`.

## Hard rules

1. **All six or not done.** Partial closeout is worse than none - it looks finished.
2. **Every task links its minutes.** A task without a source is a rumor.
3. **IDs never reused** in either list (T-NNN, Y-NNN independent).
4. **Newest source wins** when the meeting contradicts older files - record the
   contradiction in the decision record, do not silently edit history.
5. **Doubt is marked, not resolved by guessing.** `(confirm)` in the minutes; an
   open question in the brief; never an invented fact in `PROJECT.md`.
