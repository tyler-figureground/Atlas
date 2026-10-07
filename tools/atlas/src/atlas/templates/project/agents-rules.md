## How these rules bind

Every rule below is one of four kinds. Know which before you ask.

- **Hard line** - nothing crosses it, not even a request: never fabricate a fact, measurement, check result, sync or approval; never take or release another user's borrowed Revit elements; never write while a second writer (Tyler, another agent, another Revit) holds the model; never send anything out of the studio.
- **Tyler's call** - needs his words naming the thing, in the current conversation or as a standing rule in this project's own section below the block: sync, issue a revision, export for transmittal, delete data or files, change design beyond the brief, make a code-bearing choice, edit the office template or a library master. When he says it, do it - no second prompt, no gate in his way. Record it.
- **House default** - everything else here. Do it without asking. A project rule below this block, or Tyler, may override; record the override in `decisions/`.
- **Project input** - values that vary by job: Tyler's role, code edition, dimension datum and precision, sheet numbering, annotation mode, phase map. They live in `PROJECT.md`. Never infer one. Missing: ask once by name with your default, use the default meanwhile.

Precedence: Tyler's current words > project rules below this block > this block > skill standards (S+V drawing standards in the `jdp` skill) > reference-set exemplars. Gates protect the model and the client, not the process: when Tyler directs past a default, comply.

## Finish the job - Tyler is the last line of defence

- Work every task to done. Stop only when it is done or genuinely blocked. Never end a run idle while unblocked work remains.
- Before the run: list every issue you can foresee - missing inputs, access, files you cannot open, decisions only Tyler can make, conflicting sources - and ask Tyler all of them up front, in one numbered message, a default beside each. Then start on the defaults; never wait on an answer you can work around.
- Stuck mid-run: exhaust your own resources before asking, in this order. (1) This project: `BRIEF.md`, `PROJECT.md`, `decisions/`, `00 Tasks/TASKS.md`, the latest minutes in `11 Meetings/`, `06 Research & Existing Conditions`, `RESEARCH-INDEX.md`, `.agent/handoff/`, the model's virtual tour or point cloud. (2) The studio library and your skills and tools. (3) The internet: code text, agency and jurisdiction sites, manufacturer data. Only then ask, and name what you checked.
- Genuinely blocked means: a decision only Tyler or the client can make, a login or secret only Tyler has, or an action that sends something out of the studio or destroys data. Not a failed check, an unfamiliar file, or a fact the web holds - diagnose, fix, re-run.
- Blocked on one item: record the ask, draw with the best basis (`PROJECT.md` `basis:`), move on to the next item. Missing evidence blocks only what it touches. Asks go to Tyler batched at the end, not one at a time mid-run.
- No check-ins on routine, reversible work. Every "proceed?" costs Tyler a turn.
- A filling context window is not a reason to stop. Keep `.agent/handoff/CURRENT.md` current as you go, let auto-compaction run, and keep working. Write a dated handoff and stop only at done or genuinely blocked.

## Do the task asked

- Do exactly the task asked. "Proceed" or "yes" approves the last concrete thing you proposed, not wider scope. Never touch the model on a non-model task (prompts, renders, research, minutes).
- Progress is change on a sheet or in a deliverable. Another audit, a renamed PDF or one more research round is not progress. Keep process light; check the paper hard.
- Work only on what this issue prints. Internal standards sheets and scope Tyler is not issuing: leave alone.
- Document the approved design. Geometry, structure, lateral, MEP and symbol choices the brief does not settle: flag them as a proposal or a `MODEL` task; never decide them silently.
- Approvals are exact. Never re-ask one given; never reuse one for changed text or targets. A proposal is not an approval; a recommendation is not an award.
- Know Tyler's role on the job (`PROJECT.md`): architect of record, code or permit consultant, drawings only. Never hand him another party's task.
- Work inside Tyler's system. Never invent a folder, package, numbering scheme, firm name, address, measurement, route or size. Unknown = blank and asked, or a labelled proposal.
- Firm name, address, job number: copy verbatim from `PROJECT.md`; show spelling variants side by side when they differ. Dates in file and folder names are `YYMMDD`.
- A fact changes: update every record that carries it in one pass - `PROJECT.md`, `BRIEF.md`, title block, sheets, handoffs - and fix pointers it breaks.
- Edit Tyler's working files in place. Never regenerate a file over his hand edits.

## Read first, ask last

- Start every session with `BRIEF.md`, then `00 Tasks/TASKS.md`, then `.agent/handoff/CURRENT.md`. `PROJECT.md`, `decisions/` and the latest minutes in `11 Meetings/` for detail. Tyler's personal errands are in `00 Tasks/TYLER.md` - never work from it; it is add-only for agents.
- Told to work on the project with no specific task: take the top unblocked `AGENT` or `MODEL` item from `00 Tasks/TASKS.md` (Now, then Next), claim it in the **In progress** section (`claimed YYYY-MM-DD by <name>`) before starting, work one task at a time, close it with evidence and a run receipt. Never start a `DECISION` or `WAIT` item - if everything actionable is blocked, say so and name the blockers. A claim stale more than 7 days with no run receipt may be reclaimed; check `.agent/handoff/CURRENT.md` first.
- Before asking Tyler anything, search `BRIEF.md`, `decisions/`, `PROJECT.md`, `00 Tasks/TASKS.md` and the latest minutes, then the internet. Answered in any of them = answered; act on it.
- Every question to Tyler names what you checked and why it does not answer it: "Checked BRIEF Settled + DR-061: covers paint colour, not touch-up scope." No citation, no question. Ask about the object first, the code or mark second: "the north bath door (D04)", not "D04".
- Newest source wins: latest minutes > `BRIEF.md` > `PROJECT.md` narrative > older handoffs. An old open question is not open unless `BRIEF.md` lists it under Open. When Tyler worked outside agents, `PROJECT.md` status beats handoff prose.
- Tyler answers in chat: record it before the session ends - decision record, fact in `PROJECT.md`, line moved to Settled in `BRIEF.md`. An answer left only in chat is lost to the next agent.
- Never re-ask settled scope to be safe. Asking costs Tyler more than reading costs you.

## Look before you make

- Before you draft any deliverable - memo, minutes, sheet, letter, deck - find its type in `G:\Shared drives\LIBRARY - Reference\00 Office Standards and Administration\Reference Sets\README.md` (`atlas refs` lists them). Read its `SET.md`, then the `NOTES.md` and file of the 1-2 exemplars nearest this project by jurisdiction, use case and size.
- Start from the skeleton the card names, never from an exemplar. Facts come from this project only: `BRIEF.md`, `PROJECT.md`, `decisions/`, cited sources. Form comes from the exemplar. Process comes from the skill; a skill's hard rule beats an exemplar.
- Put `<!-- architecture-studio:reference: <type> <E1,E2> -->` in the draft, naming the set and the exemplars you opened. Before you hand it back, run the card's Review checklist and `atlas refs check <draft>` (add `--project <this project's folder>` if the draft is kept outside it). A copied fact is a defect: replace it with this project's own. A hit on a fact that is truly this project's too - the same contractor, a shared date - stays as written; name it in the receipt. Never reword or drop a true fact to clear the check. No `atlas` command on this PC: search the draft for each opened exemplar's `leak_list` yourself and say so in the receipt.
- The run receipt names the set: `Reference: code-analysis E1, E3`. A set still marked `candidate` is used the same way; say so in the receipt.
- No set for this type: say so in the receipt's asks, name the nearest set you used, and ask Tyler for one example. That question is always allowed.
- Never copy from `REF-` packages or `Precedent Sets` into a deliverable. Never start from another project's file of the same type.

## Working in the Revit model

- One writer. Before the first write, confirm the open document is this project's local by title and path - never by GUID alone; models born from one template share it. Exactly one `Revit.exe`, no other agent on the model. Document already modified at session start: Tyler is mid-edit - work offline until he says.
- A pass: save local and copy a checkpoint (outside the job folder) -> small bounded transactions, one per sheet or view -> read back every effect (element ids, counts, values) -> save local. Save local after every verified batch; an unsaved pass is a lost pass.
- Recovery is forward. Never Ctrl+Z or a transaction-group rollback on a workshared local; correct forward or reopen the checkpoint.
- Sync is Tyler's act and his acceptance signal. Sync only when he asks - in the conversation, or by a standing rule in this project's section - then at once. Exiting Revit: save local, choose "do not synchronize" explicitly - never let a dialog default decide. Never detach or overwrite a local on your own.
- A timed-out call may still finish inside Revit. Reconcile - read the model, check the output folder - before any retry. Never replay a script that already committed; kept scripts are evidence, not instructions.
- Record the warning count at pass open. A rise at close is yours to explain.
- Read the parameter, never the name. A type called `30" x 60"` was 36" tall and hid an egress failure. Corroborate before a value drives a code answer, a quantity or a tag.
- Create elements on a view whose phase is the target phase, with the target workset active; read both back. Existing types carry the `Ex. ` prefix, never merged with new. After any reopen, confirm every user workset is open before exporting; never cancel the Opening Worksets prompt.
- The office template is the baseline: title block, view templates, phase filters, annotation and text types. Do not audit or rebuild it. Need a change: duplicate to a project-local copy; never edit a shared template or a library master in place.
- Graphics through view templates, filters and phase graphics. Never per-element overrides on a production view; never fake phase state with overrides, filters or detail lines.
- The model is the source of truth. A wrong tag, schedule or dimension means a wrong model: fix the parameter or the geometry, never the annotation.
- Existing conditions: open the model's virtual tour, point cloud or Matterport first. Label each condition observed, measured, inferred or unobservable.
- Delete only in scope, dependencies previewed first. No blanket purge. Tyler's own deletions are intent - never restore them.
- Never mark a revision Issued, export for transmittal or send - Tyler's call. Never renumber or change an issued sheet, detail, mark or revision. Read the issue state; never assume the revision number.
- Model work is billed through a JDP run: open one before the first write. A stray session auto-started on another project's model: close it at once.
- Tool detail lives in the `maestro` and `jdp` skills; never copy their trap tables here. This model's own traps go in `PROJECT.md` under "Model traps" - add one when you find it.

## Drawings - native over drawn

Everything on a sheet has a native Revit object. Use it. A drawn imitation looks right and breaks at the next change.

- Identity (door, window, wall type, room, fixture) -> native tag on the element, text from its parameter. Never text styled as a tag, a hand-drawn tag symbol or overridden tag text. Empty parameter: fill the parameter, then tag. Door marks `D01`, `D02`, `D03`. Ceiling heights in the ceiling tag label, read from the ceiling's height parameter.
- Leaders -> the tag's or text note's native leader. Never detail lines as leaders.
- Sizes, types, finishes, counts -> native schedule or key schedule, phase-filtered to the issued work. Never a grid of text notes, never a table drawn in lines. A schedule split by level goes one way per set: one master on a G-series sheet, or level by level on each level's sheet - never both.
- No pricing on drawings. Quantities, volumes, named allowances and notes only; prices and unit costs go in a separate supplement document.
- Keynotes -> native keynote tags where the API allows; otherwise numbered markers plus a numbered list in a legend view, checked that every number matches.
- Locations -> native dimensions to real references. Never a value override, never a lock or EQ constraint added by an agent. Strings sum to the overall at the printed rounding.
- Dimension defaults: 1/4" display precision, face of stud. A Concept or Schematic Design project may set centerline in `PROJECT.md`; Construction Documents are face of stud - switch before the first CD sheet is dimensioned. Witness lines fixed to the dimension line, pulled clear of the drawing: place the string clear of the plan first, then dimension. Casework is dimensioned as the subject, never as a reference - set `dimensioning.casework_subject_dimensions: true` in `PROJECT.md`.
- View titles -> the viewport title. North arrows, scale bars, section, elevation and callout heads -> annotation symbols; scale bar matched to the view scale, re-checked after any scale change.
- Cross-references -> live view and sheet references. Never hard-typed `3/A101` text.
- Plans, site plans, sections, elevations -> model views of model geometry. Drafting views only for details and diagrams with no model behind them.
- Revision clouds -> always on the sheet, never in a view; tight around the change; sketched clockwise so the arcs bulge out; reason in the cloud's Comments.
- Title-block fields -> parameters, filled from `PROJECT.md`. Never typed text.
- No native route works - proven, not assumed: use the fallback Tyler agreed, with its consistency check, and say so in the receipt. Never invent a new imitation. A one-off Tyler directs ("filled region so it hatches") goes in `decisions/`.

Drafting form:

- Leaders: horizontal shoulder first, then one angle to the target. Leave from the side nearest the target; justify text toward the leader. Notes stacked in aligned columns, elbows about equal, no crossings.
- Text: ALL CAPS everywhere on a sheet - no sentence case. Office text types only (body `00-Standard`; titles 1/4" and 1/8"). No underlining, no stray returns, no blank paragraph inside a numbered list. General notes as text on the sheet; a legend view only when they repeat across sheets.
- Sheet numbers: `A101`, `AD101`, `G001` - no hyphen. View numbers: standard-detail sheets by grid module; every other sheet from the lower-right corner, up then left. An issued sheet or detail number is never reassigned.
- Composition: standard scales only. View titles bottom-left of each cell on one grid, views evenly spaced. Tags in enlarged plans, not the overall plan, where both exist. Nothing overlaps on paper; nothing runs off the sheet.
- Sheets carry contract-document language only. Never hold codes, agent notes, status words, "UNVERIFIED" or "(RECORD APPROX)". Uncertainty goes in `PROJECT.md` `basis:`.
- Form beyond this file follows the S+V drawing standards in the `jdp` skill (annotation, dimensioning, tagging, notes, reference symbols). Where Tyler has ruled here, his ruling wins.

Done is checked on paper:

- Export the sheets with native PDF export and look at every page. Model checks and printed checks are separate; a check that could not run is BLOCKED, never passed. Data reads (schedule cell text, dimension value strings) do not prove what prints.
- Before every export, sweep for another project's names, addresses, firm names and revision rows.

## Code work

- Code basis first, in the first line of every code answer: jurisdiction -> governing edition -> code of record. Prove incorporated or unincorporated from a parcel source, not the postal city. `PROJECT.md` `edition:` blank: resolve it or ask; never assume. Never fall back to `-j ibc` - it is the 2009 IBC, which no studio jurisdiction enforces.
- Code of record vs analysis edition: where a filing names an edition (approved permit, prior-code election), judge compliance against it; label newer-code findings comparative. Cover sheets agree with each other.
- Governing document by scope: one- and two-family dwellings and townhouses -> residential code (CRC/IRC), not the building code. Alterations and changes of occupancy -> existing-building code; test the change-of-occupancy trigger first.
- The local layer governs where adopted: use the locality key (`-j napa`, `napa-city`, ...), quote the adopting ordinance. Never carry one authority's amendments - or another project's sheet text - to another.
- Use the governing cycle's section numbers. The 2025 CRC renumbered Chapter 3; never print IRC or 2022 numbers on a 2025 job.
- Every number from a `norma` calculator, never by hand; show the basis and the arithmetic. Before a calculator value is printed, read the governing table row yourself. A calculator gap is reported as a gap, never filled from memory.
- Quote controlling text verbatim; cite only locators found in the corpus; run `norma guard` on the final text.
- Test triggers, never read labels: WUI against its triggers, sprinklers with the arithmetic, seismic against the full required list. Read this project's own code folder and drawings first; name the drawing behind every dimension.
- Close every UNVERIFIED or ASSUMED item the sources can close before handing in. What remains names an outside owner.
- Dwellings still get occupant load: state the residential code sets none, then run the most likely use, labelled informational.
- Tyler is the professional. Never "consult a professional"; name the missing item.
- Studio rulings: the 2025 California Energy Code governs every California project, Napa County included. NYC rules stay in NYC; a pre-2008 NYC building gets its prior-code election and carve-outs stated.

## After every meeting

Recording -> Dicta transcript in `11 Meetings/`. Then one run does all six, in order:

1. Minutes: `YYMMDD - <Name> - Meeting Minutes.md` beside the transcript. Decisions made (each linked to the register), action items with owner, open questions; every item in the transcript, walked end to end. `Prepared by: Tyler`. A bare `[mm:ss]` timestamp on every decision and action, never explained. Mark doubt inline with `(confirm)`. Never name file paths, the transcript, the recording or the transcription tool; no limits paragraph, no internal-draft label. Leave out money, personal and off-topic talk; redact passwords and codes. Names are as heard - mark doubtful ones `(confirm)`; never guess a party's role.
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
- Decisions kept in a spreadsheet: the workbook remains canonical. Open on a compact `Team View`: ID, Topic, Current position, Status, Owner, Next / due. Keep evidence, rationale, dates, impacts and history on a separate detail tab, linked by permanent ID; do not delete them to simplify the front.
- Register presentation is part of every write, including meeting closeout. Replace the current summary; never append meeting paragraphs to front-sheet cells. Topic <=55 characters, current position <=150, next / due <=100, owner <=40. No invented owner/date, no automatic truncation, no hiding a safety qualification to meet a budget. Shorten wording or link detail; unknown stays unknown. A decided choice can still have an unresolved action.
- Six columns fit across a normal laptop at readable zoom (>=85%); vertical scrolling/filtering is expected, not 79 decisions squeezed onto one screen. Freeze headings, wrap text, keep body font >=11pt, row heights 36-48pt. No hidden rows/columns, stale filters, or shrink-to-fit to fake a pass. Read every changed row in the saved workbook; inspect the actual spreadsheet when a renderer is available and report when it is not.
- Before closing a register update, run the project's saved-workbook readability checker. For the A-V legacy layout, Architecture Studio provides `scripts/decision_register.py check <workbook> --render` (openpyxl plus aspose-cells-python for wrapped-text measurement, no renderer-written workbook); install a project-local copy when migrating. If the optional renderer is unavailable, run the structural check without `--render` and report the missing visual/fit evidence, not a complete pass. Failing checks mean the write is not done. Keep `decisions/REGISTER.md` a generated short summary and `decisions/DETAILS.md` the lossless evidence copy, regenerate both after each write. Agents read the summary first, then the linked detail before changing a decision; never hand-edit either generated file.
- Never point at a file through a Windows `.lnk` shortcut; agents cannot follow one. Write the full target path.

## Where agent work goes

- Scratch - scripts, receipts, JSON, captures, check exports, before/after images, saved web pages - goes in `.agent/runs/YYMMDD-<slug>/`, started from `.agent/runs/_RUN-TEMPLATE.md`. Nowhere else - not `handoff/`, not a `QA` folder.
- File a result in a numbered folder only when a person will read it: minutes, a code memo, a draft to send, an issued set. Name it `YYMMDD_Title.md`, in the section its subject belongs to. Most runs file nothing there.
- Everything filed for a person gets a PDF beside it: `atlas pdf "<file.md>"` (re-run after every edit; the Markdown stays the source). Write decisions, actions, findings and open questions as short labelled lists; keep tables for numeric grids - occupant loads, areas, allowable vs actual - never sentences in table cells.
- Production tasks live in `00 Tasks/TASKS.md`; Tyler's personal errands live in `00 Tasks/TYLER.md`. No other task lists anywhere. A longer list for one scope goes in `00 Tasks/Lists/`, copied from `00 Tasks/_Task List Template.md` and linked from `TASKS.md`. Agents add to `TYLER.md` but never check its items off and never send its artifacts.
- `PROJECT.md` holds facts only. Never a session log, never a task list.
- Before editing `PROJECT.md`, `AGENTS.md` or `TASKS.md`, copy it to `.agent/backups/`. Never leave a backup at the project root.
- Handoffs: keep `.agent/handoff/CURRENT.md` current; write a dated `HANDOFF-*.md` only at a stopping point. No artefacts in `handoff/`.
- Permits and agency filings go in `13 AHJ/`, by stage - never by where they came from or went to - and every application has a row in `13 AHJ/AHJ-REGISTER.md`.
- Research: one report per question in its `06 Research & Existing Conditions` topic folder, raw captures in a `_sources/` folder beside it, every source a row in `RESEARCH-INDEX.md`.
- Unsent emails and letters go in `08 OUT/Drafts/`; move them to their dated folder once sent.
- Every package that leaves the studio gets a row in `08 OUT/Transmittals/TRANSMITTAL-LOG.md` when it is sent, and the package as sent goes in a dated `YYMMDD_Transmittal-T-NNN/` folder beside the log. Agents never send; when Tyler says a package went out, log the row and file the folder.
- Issued sets are frozen. A revised set is a new file beside the old one; a retired sheet is marked not issued, never deleted.
- A `.rvt` moves only with its `_backup` folder. Delete a duplicate file only when its hash matches; otherwise keep both and flag it.
- New folders only through Atlas. Never `tmp`, `QA`, `New folder` or `Agent Sessions`. No tool caches (`__pycache__`, `.ruff_cache`) on the drive.

## Research and asking

- Day 1: send the questions in `00 Tasks/INTAKE.md` to Tyler as one message. Research and drafting start at once; an answer overrides anything researched.
- Research only what a sheet needs. Each question names the requirement row or sheet item it serves and its done-test: the fact at the precision that item draws or states. Done-test met = stop, even if more is knowable.
- Time-box: 30 min agent time per question; all research capped at a quarter of the job's agent budget. No silent extensions.
- At the box, draw with the best basis you have, keep working, then ask. Record it in `PROJECT.md` `basis:` (fact, value used, source, requirement row, printed yes/no, open/confirmed). Never on the sheet: no hedges, holds or internal codes.
- Asks go at the top of the pass receipt: max 5, printed values first; one fact, the value drawn, its source, a confirm-or-correct line. Questions for the County or client are drafted to `08 OUT/Drafts/` and listed as asks; never sent by an agent.
- Not issue-ready while an open basis row backs a printed value.
- Outside sheet scope: one line under "Parked - outside sheet scope" in `00 Tasks/TASKS.md` (finding, source, why it may matter); source row in `RESEARCH-INDEX.md`; no further work. Tyler reviews it at issue-ready.
