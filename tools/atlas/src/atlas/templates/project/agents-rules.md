## Read first, ask last

- Start every session with `BRIEF.md`, then `00 Tasks/TASKS.md`, then `.agent/handoff/CURRENT.md`. `PROJECT.md`, `decisions/` and the latest minutes in `11 Meetings/` for detail. Tyler's personal errands are in `00 Tasks/TYLER.md` - never work from it; it is add-only for agents.
- Told to work on the project with no specific task: take the top unblocked `AGENT` or `MODEL` item from `00 Tasks/TASKS.md` (Now, then Next), claim it in the **In progress** section (`claimed YYYY-MM-DD by <name>`) before starting, work one task at a time, close it with evidence and a run receipt. Never start a `DECISION` or `WAIT` item - if everything actionable is blocked, say so and name the blockers. A claim stale more than 7 days with no run receipt may be reclaimed; check `.agent/handoff/CURRENT.md` first.
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

## California permit requirements

- Before California architectural, mechanical, electrical, plumbing or site-plan requirements research, drawing review or permit preparation, establish location, reviewing agencies, scope, application date and code cycle from `BRIEF.md`, `PROJECT.md` and agency records. A Napa mailing address does not establish City jurisdiction. Unknown jurisdiction stays unresolved; do not choose an agency by proximity.
- Shared reference root: `G:\Shared drives\LIBRARY - Reference\01 Codes and Regulations\California`. The available indexed collection is **Napa - Permit Guidance**, covering City of Napa, Napa County, NapaSan and related agencies. This is not statewide coverage. For other California jurisdictions, obtain that authority's guidance; Napa handouts are not their requirements. For non-California projects, skip this collection unless a specific cross-jurisdiction comparison is requested.
- For an applicable Napa agency, read `G:\Shared drives\LIBRARY - Reference\01 Codes and Regulations\California\Napa - Permit Guidance\_agent\START_HERE.md`, then its `INDEX.md` task routes and the parent library's `02 Conflicts and Gaps.md`. Use the shared collection in place; never copy its corpus, search database or build caches into a project.
- Retrieve requirements with `_agent\tools\library.py` or the linked `_agent\documents\*.md`. From the `_agent` folder: `python tools/library.py search "building labels" --jurisdiction county --json`, then `python tools/library.py read county-7162 --pages 1`. Choose `city`, `county`, `napasan` or `related` from the actual reviewing agency; check each applicable agency separately. Read requirement pages and context, not search snippets alone. Use Markdown directly if Python is unavailable. If the drive is inaccessible, report the missing source and use official agency material; never claim the local index was checked.
- At project setup, select applicable task routes. Before permit submission or drawing-review closeout, check the plan-set and site-plan guidance, then scope-triggered architectural, MEP, fire, civil, water/sewer and environmental-health requirements. Include existing/proposed building and use labels in the site-plan check. Use `_agent\PROJECT_REVIEW_PROMPT.md` for the review format; this instruction does not authorize issuing or submitting drawings.
- Record source title, document ID, issuer, edition, physical PDF page or worksheet and official URL for every requirement used. Preserve OCR and visual-content flags; request targeted visual verification when a number, symbol or graphic controls the conclusion. The collection is a dated snapshot: confirm the governing edition and current agency instructions, read known conflicts, and distinguish missing drawing information from checks that cannot be completed. Archived material requires explicit applicability review.
- This reference collection supplies agency guidance, not Norma's verified governing-code corpus. Continue using `norma <verb>` for code analysis; never treat extracted handouts as adopted code or silently replace the project's code basis. A newer meeting note can establish scope, not override an agency requirement.
- Log sources actually relied on in `06 Research & Existing Conditions/RESEARCH-INDEX.md`: an original agency document is `official`; the shared text index is a `derived` finding aid. File project-specific requirement reviews in `13 AHJ/01 Requirements & Pre-Application/`, code analyses in `06 Research & Existing Conditions/Code/`, and scratch in `.agent/runs/`. Record source/page, applicability, drawing evidence, missing information and unresolved conflicts; add actionable omissions to `00 Tasks/TASKS.md`. Do not mark compliance, approval or permit status from the act of linking this library.

## After every meeting

Recording -> Dicta transcript in `11 Meetings/`. Then one run does all six, in order:

1. Minutes: `YYMMDD - <Name> - Meeting Minutes.md` beside the transcript. Decisions made (each linked to the register), action items with owner, open questions; every item in the transcript, walked end to end. `Prepared by: Tyler`. A bare `[mm:ss]` timestamp on every decision and action, never explained. Mark doubt inline with `(confirm)`. Never name file paths, the transcript, the recording or the transcription tool; no limits paragraph, no internal-draft label.
2. Decisions: one record per decision made or changed (`/decision`, or the project's own register if this file says it keeps one). Supersede; never overwrite a rationale.
3. Facts: update `PROJECT.md` front matter and its mirror rows, each with source and date.
4. To-do lists: every action item goes to exactly one list, linked to the minutes. Production work (model, sheets, research, drafting) -> `00 Tasks/TASKS.md` as `AGENT` or `MODEL`. A decision only Tyler can make that blocks production -> `TASKS.md` as `DECISION`. Tyler's personal errands (call, email, send, sign-off) -> `00 Tasks/TYLER.md` (Y-NNN series); if the artifact can be prepared now, draft it to `08 OUT/Drafts/` and link it with `ready:`. Someone outside -> `WAIT` in `TASKS.md`. Close tasks the meeting finished. No `TASKS.md`/`TYLER.md` yet: create from Atlas's templates first.
5. Brief: rebuild `BRIEF.md` - answered questions move to Settled, new ones go to Open, update Now and Latest meeting, bump `updated:`.
6. Report: minutes path, decisions added/changed, tasks added/closed, brief updated.

Not done until all six. A meeting whose minutes exist but whose brief and tasks are stale is the leak that makes agents re-ask.

## Control files stay small

- `BRIEF.md` under 150 lines. `PROJECT.md` facts only. Past 100 KB, look for narrative to move out; never cut a fact to hit a size.
- No line over 2,000 characters in `BRIEF.md`, `PROJECT.md`, `TASKS.md` or minutes: agent file readers cut longer lines off silently.
- Session narrative never goes in `PROJECT.md`. Found some: back up, then move it verbatim to `.agent/PROJECT-HISTORY.md`, newest first.
- `00 Tasks/TASKS.md`: done items older than 30 days -> `00 Tasks/Archive/YYMM-done.md`.
- Decisions kept in a spreadsheet: keep a generated Markdown copy at `decisions/REGISTER.md`, regenerated whenever the spreadsheet changes. Agents read the copy, write the spreadsheet.
- Never point at a file through a Windows `.lnk` shortcut; agents cannot follow one. Write the full target path.

## Where agent work goes

- Scratch - scripts, receipts, JSON, captures, check exports, before/after images, saved web pages - goes in `.agent/runs/YYMMDD-<slug>/`, started from `.agent/runs/_RUN-TEMPLATE.md`. Nowhere else.
- File a result in a numbered folder only when a person will read it: minutes, a code memo, a draft to send, an issued set. Name it `YYMMDD_Title.md`, in the section its subject belongs to. Most runs file nothing there.
- Everything filed for a person gets a PDF beside it: `atlas pdf "<file.md>"` (re-run after every edit; the Markdown stays the source). Write decisions, actions, findings and open questions as short labelled lists; keep tables for numeric grids - occupant loads, areas, allowable vs actual - never sentences in table cells.
- Production tasks live in `00 Tasks/TASKS.md`; Tyler's personal errands live in `00 Tasks/TYLER.md`. No other task lists anywhere. A longer list for one scope goes in `00 Tasks/Lists/`, copied from `00 Tasks/_Task List Template.md` and linked from `TASKS.md`. Agents add to `TYLER.md` but never check its items off and never send its artifacts.
- `PROJECT.md` holds facts only. Never a session log, never a task list.
- Before editing `PROJECT.md`, `AGENTS.md` or `TASKS.md`, copy it to `.agent/backups/`. Never leave a backup at the project root.
- Handoffs: keep `.agent/handoff/CURRENT.md` current; write a dated `HANDOFF-*.md` only at a stopping point. No artefacts in `handoff/`.
- Permits and agency filings go in `13 AHJ/`, by stage, and every application has a row in `13 AHJ/AHJ-REGISTER.md`.
- Research: one report per question in its `06 Research & Existing Conditions` topic folder, raw captures in a `_sources/` folder beside it, every source a row in `RESEARCH-INDEX.md`.
- Unsent emails and letters go in `08 OUT/Drafts/`; move them to their dated folder once sent.
- Every package that leaves the studio gets a row in `08 OUT/Transmittals/TRANSMITTAL-LOG.md` when it is sent, and the package as sent goes in a dated `YYMMDD_Transmittal-T-NNN/` folder beside the log. Agents never send; when Tyler says a package went out, log the row and file the folder.
- New folders only through Atlas. Never `tmp`, `QA`, `New folder` or `Agent Sessions`. No tool caches (`__pycache__`, `.ruff_cache`) on the drive.

## Research and asking

- Day 1: send the questions in `00 Tasks/INTAKE.md` to Tyler as one message. Research and drafting start at once; an answer overrides anything researched.
- Research only what a sheet needs. Each question names the requirement row or sheet item it serves and its done-test: the fact at the precision that item draws or states. Done-test met = stop, even if more is knowable.
- Time-box: 30 min agent time per question; all research capped at a quarter of the job's agent budget. No silent extensions.
- At the box, draw with the best basis you have, then ask. Record it in `PROJECT.md` `basis:` (fact, value used, source, requirement row, printed yes/no, open/confirmed). Never on the sheet: no hedges, holds or internal codes.
- Asks go at the top of the pass receipt: max 5, printed values first; one fact, the value drawn, its source, a confirm-or-correct line. Questions for the County or client are drafted to `08 OUT/Drafts/` and listed as asks; never sent by an agent.
- Not issue-ready while an open basis row backs a printed value.
- Outside sheet scope: one line under "Parked - outside sheet scope" in `00 Tasks/TASKS.md` (finding, source, why it may matter); source row in `RESEARCH-INDEX.md`; no further work. Tyler reviews it at issue-ready.
