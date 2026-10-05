## Read first, ask last

- Start every session with `BRIEF.md`, then `00 Tasks/TASKS.md`, then `.agent/handoff/CURRENT.md`. `PROJECT.md`, `decisions/` and the latest minutes in `11 Meetings/` for detail.
- Before asking Tyler anything, search `BRIEF.md`, `decisions/`, `PROJECT.md`, `00 Tasks/TASKS.md` and the latest minutes. Answered in any of them = answered; act on it.
- Every question to Tyler names what you checked and why it does not answer it: "Checked BRIEF Settled + DR-061: covers paint colour, not touch-up scope." No citation, no question.
- Newest source wins: latest minutes > `BRIEF.md` > `PROJECT.md` narrative > older handoffs. An old open question is not open unless `BRIEF.md` lists it under Open.
- Tyler answers in chat: record it before the session ends - decision record, fact in `PROJECT.md`, line moved to Settled in `BRIEF.md`. An answer left only in chat is lost to the next agent.
- Never re-ask settled scope to be safe. Asking costs Tyler more than reading costs you.

## Look before you make

- Before you draft any deliverable - memo, minutes, sheet, letter, deck - find its type in `G:\Shared drives\LIBRARY - Reference\00 Office Standards and Administration\Reference Sets\README.md` (`atlas refs` lists them). Read its `SET.md`, then the `NOTES.md` and file of the 1-2 exemplars nearest this project by jurisdiction, use case and size.
- Start from the skeleton the card names, never from an exemplar. Facts come from this project only: `BRIEF.md`, `PROJECT.md`, `decisions/`, cited sources. Form comes from the exemplar. Process comes from the skill; a skill's hard rule beats an exemplar.
- Put `<!-- architecture-studio:reference: <type> <E1,E2> -->` in the draft, naming the set and the exemplars you opened. Before you hand it back, run the card's Review checklist and `atlas refs check <draft>` (add `--project <this project's folder>` if the draft is kept outside it). A copied fact is a defect: replace it with this project's own. A hit on a fact that is truly this project's too - the same contractor, a shared date - stays as written; name it in the receipt. Never reword or drop a true fact to clear the check. No `atlas` command on this PC: search the draft for each opened exemplar's `leak_list` yourself and say so in the receipt.
- The run receipt names the set: `Reference: code-analysis E1, E3`. A set still marked `candidate` is used the same way; say so in the receipt.
- No set for this type: say so in the receipt's asks, name the nearest set you used, and ask Tyler for one example. That question is always allowed.
- Never copy from `REF-` packages or `Precedent Sets` into a deliverable. Never start from another project's file of the same type.

## After every meeting

Recording -> Dicta transcript in `11 Meetings/`. Then one run does all six, in order:

1. Minutes: `YYMMDD - <Name> - Meeting Minutes.md` beside the transcript. Decisions made, action items with owner, open questions.
2. Decisions: one record per decision made or changed (`/decision`, or the project's own register if this file says it keeps one). Supersede; never overwrite a rationale.
3. Facts: update `PROJECT.md` front matter and its mirror rows, each with source and date.
4. To-do list: every action item becomes a task in `00 Tasks/TASKS.md` - `TYLER` for Tyler's own, `AGENT` or `MODEL` for work an agent can take, `WAIT` for someone outside - each linked to the minutes. Close tasks the meeting finished. No `TASKS.md` yet: create it from Atlas's template first.
5. Brief: rebuild `BRIEF.md` - answered questions move to Settled, new ones go to Open, update Now and Latest meeting, bump `updated:`.
6. Report: minutes path, decisions added/changed, tasks added/closed, brief updated.

Not done until all six. A meeting whose minutes exist but whose brief and tasks are stale is the leak that makes agents re-ask.

## Control files stay small

- `BRIEF.md` under 150 lines. `PROJECT.md` facts only. Past 30 KB, look for narrative to move out; never cut a fact to hit a size.
- No line over 1,000 characters in `BRIEF.md`, `PROJECT.md`, `TASKS.md` or minutes: agent file readers cut long lines off silently.
- Session narrative never goes in `PROJECT.md`. Found some: back up, then move it verbatim to `.agent/PROJECT-HISTORY.md`, newest first.
- `00 Tasks/TASKS.md`: done items older than 30 days -> `00 Tasks/Archive/YYMM-done.md`.
- Decisions kept in a spreadsheet: keep a generated Markdown copy at `decisions/REGISTER.md`, regenerated whenever the spreadsheet changes. Agents read the copy, write the spreadsheet.
- Never point at a file through a Windows `.lnk` shortcut; agents cannot follow one. Write the full target path.

## Where agent work goes

- Scratch - scripts, receipts, JSON, captures, check exports, before/after images, saved web pages - goes in `.agent/runs/YYMMDD-<slug>/`, started from `.agent/runs/_RUN-TEMPLATE.md`. Nowhere else.
- File a result in a numbered folder only when a person will read it: minutes, a code memo, a draft to send, an issued set. Name it `YYMMDD_Title.md`, in the section its subject belongs to. Most runs file nothing there.
- Tasks live in `00 Tasks/TASKS.md`, and only there. A longer list for one scope goes in `00 Tasks/Lists/`, copied from `00 Tasks/_Task List Template.md` and linked from `TASKS.md`.
- `PROJECT.md` holds facts only. Never a session log, never a task list.
- Before editing `PROJECT.md`, `AGENTS.md` or `TASKS.md`, copy it to `.agent/backups/`. Never leave a backup at the project root.
- Handoffs: keep `.agent/handoff/CURRENT.md` current; write a dated `HANDOFF-*.md` only at a stopping point. No artefacts in `handoff/`.
- Permits and agency filings go in `13 AHJ/`, by stage, and every application has a row in `13 AHJ/AHJ-REGISTER.md`.
- Research: one report per question in its `06 Research & Existing Conditions` topic folder, raw captures in a `_sources/` folder beside it, every source a row in `RESEARCH-INDEX.md`.
- Unsent emails and letters go in `08 OUT/Drafts/`; move them to their dated folder once sent.
- New folders only through Atlas. Never `tmp`, `QA`, `New folder` or `Agent Sessions`. No tool caches (`__pycache__`, `.ruff_cache`) on the drive.

## Research and asking

- Day 1: send the questions in `00 Tasks/INTAKE.md` to Tyler as one message. Research and drafting start at once; an answer overrides anything researched.
- Research only what a sheet needs. Each question names the requirement row or sheet item it serves and its done-test: the fact at the precision that item draws or states. Done-test met = stop, even if more is knowable.
- Time-box: 30 min agent time per question; all research capped at a quarter of the job's agent budget. No silent extensions.
- At the box, draw with the best basis you have, then ask. Record it in `PROJECT.md` `basis:` (fact, value used, source, requirement row, printed yes/no, open/confirmed). Never on the sheet: no hedges, holds or internal codes.
- Asks go at the top of the pass receipt: max 5, printed values first; one fact, the value drawn, its source, a confirm-or-correct line. Questions for the County or client are drafted to `08 OUT/Drafts/` and listed as asks; never sent by an agent.
- Not issue-ready while an open basis row backs a printed value.
- Outside sheet scope: one line under "Parked - outside sheet scope" in `00 Tasks/TASKS.md` (finding, source, why it may matter); source row in `RESEARCH-INDEX.md`; no further work. Tyler reviews it at issue-ready.
