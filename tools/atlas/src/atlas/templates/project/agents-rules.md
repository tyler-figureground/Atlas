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
