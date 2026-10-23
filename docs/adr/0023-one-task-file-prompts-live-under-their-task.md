# 23. One task file per project; prompts live under their task

Date: 2026-10-22

## Status

Accepted. Drive map v4.2. Amends ADR 0013: `00 Tasks/Lists` and `_Task List Template.md` are retired.

Decided by Tyler on 2026-10-22 ("I don't want any additional files outside of our task list
... put them all in our task list"), after a Revit plan for 261006_1655 San Vicente Ave was
first written as two scoped lists with prompts.

## Context

ADR 0013 gave `00 Tasks` a seeded `Lists` folder and a template for a longer list on one
scope. In practice a scoped list split one plan across three files: task lines in
`TASKS.md`, the prompts and gap table in `Lists/`, links between them. Agents picking up
work read `TASKS.md` first; anything outside it is one more file to find, and anchors
between files break when a heading changes.

## Decision

- `TASKS.md` (production) and `TYLER.md` (errands) are the only task files in a project.
  No scoped lists, no prompt files.
- A longer scope (an audit, a revision round, a Revit plan) is a `###` group inside
  `TASKS.md`, under **Now** or **Next**.
- Each task's agent prompt sits indented under its task line in a `text` fence. Material a
  group shares (a mode card, a gap table) sits once under the group heading.
- The bundled `TASKS.md` loses its Lists section. `Task List Template.md` is removed from
  the bundle. Drive map: drop the `00 Tasks/_Task List Template.md` template entry; make
  `00 Tasks/Lists` an unseeded child so existing empty folders are reported and removed by
  `clean`, and any folder still holding a list is not flagged as unknown.

## Consequences

- `TASKS.md` grows with prompts. The 2,000-character line limit still applies; prompts are
  many short lines, so it holds.
- Existing projects keep any `Lists/` file until someone folds it into `TASKS.md`;
  conform does not move content.
- The `/tasks` skill and the AGENTS.md Atlas block say "no other task lists or prompt
  files".
