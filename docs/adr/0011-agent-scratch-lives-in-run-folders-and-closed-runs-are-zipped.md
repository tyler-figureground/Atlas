# Agent scratch lives in run folders, and closed runs are zipped

Date: 2026-10-02

## Status

Accepted

Map v3.0 keys `controlPlane.runsDir`, `backupsDir`, `archiveDir`, `runRetentionDays`,
`agentsRules`. Atlas 0.7.0. Evidence: `docs/research/project-folder-usage-and-agent-output.md`.

## Context

Agent runs make far more files than people do. In the four 2026 projects agents worked
hardest, 7,050 of 9,125 files (77%) were scripts, receipts, JSON and screenshots. The map
gave agents one home, `.agent/handoff/` for `HANDOFF-*.md`, so everything else was filed by
analogy and every project analogised differently: `11 Meetings/Agent Sessions/` (3,317
files), a root `tmp/` (1,386), `06/Model Verification/` (425), and a `handoff/` folder used
as scratch (1,010). The Tyler-facing results sat beside hundreds of run reports with the same
date prefix, and the drive paid for every one of them against the 400,000-item cap and in
enumeration cost.

## Decision

**Scratch from one agent run lives in one folder: `.agent/runs/YYMMDD-<slug>/`.** It holds
everything the run makes that a person will not read, and a `RUN.md` log copied from the run
template. A run files a result in the numbered tree only when a person will read it.

**Copies of control files taken before an edit go to `.agent/backups/`,** never beside the
file at the project root.

**A closed run is zipped into `.agent/archive/<run>.zip` by `atlas runs --apply`.** Closed
means: nothing in it has changed for `runRetentionDays` (14), no task list in `00 Tasks/`
and no handoff names it, and every part of it could be read. The zip is written to a
`.partial` name, read back, CRC-checked and compared file-for-file with the folder; only then
is it renamed into place and the folder removed. An existing zip is never overwritten.
Preview is the default, as with clean and conform. The zip is the undo.

**The rules ride in the AGENTS.md Atlas block.** `controlPlane.agentsRules` names a bundled
template (ADR 0012) whose words become a "Where agent work goes" section of the block, so
every agent reads them first and conform refreshes them in every project when they change.

## Consequences

- Clean never removes a folder of the agent workspace; doctor never reports one as unfiled.
- A run is one Drive item once archived instead of hundreds.
- The relocations in map v3.0 (`11 Meetings/Agent Sessions`, `tmp`,
  `06 .../Model Verification` -> `.agent/runs/legacy-*`) turn the existing dumps into runs,
  so they archive like any other once idle. Moving them is a per-project conform the
  operator previews and can undo.
- Archiving is not scheduled by Atlas. `_tools\Archive-Agent-Runs.bat` runs it drive-wide;
  a scheduled task can call the same command.
