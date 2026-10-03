# 00 Tasks and 13 AHJ are seeded sections

Date: 2026-10-02

## Status

Accepted

Map v3.0. Decided by Tyler on 2026-10-02 against the options in
`docs/research/project-folder-usage-and-agent-output.md` section 5.

## Context

Task lists had no home: `PROJECT.md` "Open items", `OPEN-ITEMS.md` in research, action
lists in `11 Meetings`, prompt blocks in `.agent/handoff`, checklists at the root and in
`08 OUT`, and task queues in the prompt vault under `_tools\Architecture-Prompts`.

Permitting-authority work had no home either. 5 of 7 recent projects carried it, spread
over `02 Sheets`, `06`, `07 IN`, `08 OUT` and `10 Legal`. Pestoni filed its county
submission in `08 OUT/Submittal`, a word the map already uses for contractor submittals.

## Decision

**`00 Tasks`** - numbered, so it sorts first and reads as a place for people too, not only
agents. Seeded, with `Lists` and `Archive`. Holds `TASKS.md`, the one live task list, and
`_Task List Template.md` for longer lists on one scope. The prompt vault's per-project task
queues move into each project's `TASKS.md`; the vault keeps prompts and headers.

**`13 AHJ`** - stage-first, seeded with all six stages:
`01 Requirements & Pre-Application`, `02 Applications & Forms`, `03 Submissions`,
`04 Comments & Responses`, `05 Correspondence`, `06 Permits & Inspections`, plus
`AHJ-REGISTER.md`. Agency goes in the file name and the register, not a folder level: the
map has no free-text names, and most projects have one primary agency. Rounds are a file
prefix (`R1_YYMMDD_`). "Submissions", never "Submittals".

Number 13, not a renumber: inserting it earlier would drift every project. `10 Legal/Permits`
relocates into `13 AHJ/06 Permits & Inspections`. What the code says stays in
`06 .../Code`; what this agency asked for and what we sent lives in 13 AHJ.

`10 Legal` becomes seeded (5 of 7 recent projects use it).

## Consequences

Conform adds both sections to every existing project through their template files, with
their seeded folders, in one pass. Project notes in `AGENTS.md` that name `10 Legal/Permits`
need updating by hand when the relocation runs.
