# Every project carries a brief, and agents read before they ask

Date: 2026-10-03

## Status

Accepted

Map v3.3 template `BRIEF.md`. Atlas 0.8.0-0.8.2. Builds on ADR 0010 (AGENTS.md holds the
instructions), ADR 0011 (agent workspace) and ADR 0012 (project templates).

## Context

Agents working in Montez Press Radio asked Tyler to re-approve scope the client Decision
Register had already settled: white paint, cabling underway, kitchen in scope, millwork as a
separate alternate (`.agent/runs/261002-gseries-general-notes/261003-scope-authority-correction.md`
in that project). Drive sync was not the cause - every file was current to the minute. The
cause was retrieval:

- The register sat three hops from `AGENTS.md`, behind a Windows `.lnk` an agent cannot
  follow, in an `.xlsx` an agent cannot search.
- `PROJECT.md` had grown to 344 KB (about 85k tokens), most of it session narrative. 32 lines
  ran past 2,000 characters, where agent file readers silently cut them off. The current
  facts were buried among history that contradicted them.
- Old "Open" items stayed listed after later decisions closed them, so a skimming agent saw
  open questions and asked them.
- The meeting workflow (recording, transcript, minutes, register, dossier, tasks) produced
  documents for people. Nothing short told the next agent what was settled.

A drive-wide check found the same shape in three more projects (`PROJECT.md` 157-201 KB).

## Decision

**Every project carries `BRIEF.md` at its root, and the AGENTS.md rules make reading it
the first act and asking Tyler the last.**

- `BRIEF.md` (template) has five headings: Now; Settled - do not ask; Open - ask only these;
  Holds - do not do; Latest meeting. Under 150 lines. Listed on Settled = answered; not
  listed on Open = not open.
- `agents-rules.md` gains three sections in every Atlas block:
  - **Read first, ask last** - read the brief, then tasks, then the handoff. Every question
    to Tyler cites what was checked and why it does not answer it. An answer given in chat
    is recorded before the session ends.
  - **After every meeting** - one run does six steps in order: minutes, decisions, facts,
    to-do list in `00 Tasks/TASKS.md` (`TYLER` / `AGENT` / `MODEL` / `WAIT` lanes), brief,
    report. Not done until all six.
  - **Control files stay small** - `PROJECT.md` facts only; past 30 KB, move narrative to
    `.agent/PROJECT-HISTORY.md`, never cut a fact to hit a size. No line over 1,000
    characters. A decision register kept in a spreadsheet gets a generated Markdown copy,
    `decisions/REGISTER.md`. No `.lnk` pointers.
- Conform backfills `.agent/runs` and `.agent/backups` (map `workspace_dirs`) into projects
  made before the workspace existed, so "back up first" has somewhere to write.

## Consequences

- The brief is a derived file and goes stale like any other. The after-meeting rule rebuilds
  it; an agent asking a settled question is the signal it was skipped.
- Backfilled projects needed a one-off pass: briefs filled from each project's files, and
  session narrative moved verbatim out of `PROJECT.md` with a lossless check and the YAML
  front matter byte-identical (2026-10-03). Four `PROJECT.md` files remain 50-74 KB of facts;
  the size rule is a prompt, not a cap.
- `decisions/REGISTER.md` is generated per project by a small exporter beside it
  (`decisions/export-register.py`). It is not yet an Atlas command; if more projects adopt
  spreadsheet registers, that is the next step.
- Staff Atlas must be 0.8.2 or later: older wheels lack the `BRIEF.md` template the map names.
