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
