# Project template files live in the repo, and Atlas copies them

Date: 2026-10-02

## Status

Accepted

Map v3.0 key `templates`. Atlas 0.7.0. Constrained by ADR 0010 (agent files) and the
create-only backfill rule.

## Context

Agents wrote task lists in at least five formats across seven places in a project, and
research indexes, AHJ trackers and run logs in as many shapes as there were sessions. A
standard file only helps if every project has it from day one and if one person can change
the standard in one place.

## Decision

**The words live in the repo; the map says where they go.**

- Template files live in `tools/atlas/src/atlas/templates/project/` and ship inside the
  Atlas wheel. That folder is the one place to edit them.
- The drive map lists what every project carries:
  `{"path": "00 Tasks/TASKS.md", "template": "TASKS.md", "index": "..."}`. Atlas still
  hard-codes no folder names; it hard-codes no template names either.
- `{{project_name}}`, `{{project_folder}}` and `{{created}}` are filled in. An unknown
  placeholder is left visible rather than blanked.
- `atlas new` writes every template; a missing template stops intake before the project
  folder exists. Doctor reports an absent template file; conform creates it, with its
  folder, and never overwrites one that exists - however far it has drifted, it is the
  project's own.
- An `index` text adds a row to the AGENTS.md index. The filing rules template
  (`controlPlane.agentsRules`) is the one template that is not copied: its words become part
  of the Atlas block, which conform refreshes in place.
- `ATLAS_TEMPLATES` points Atlas at another folder, to try a change against a real drive
  before releasing it.

Children in the map may now be objects, `{"name": ..., "seed": true}`. A seeded section's
seeded children are made with a new project, kept by clean, and backfilled by conform when
the section exists or a template is about to create it. Conform still never creates a
section for its own sake.

## Consequences

- An edit to a template reaches Tyler's editable install at once and staff with the next
  wheel. Existing projects keep their copy; only the AGENTS.md rules refresh everywhere.
- A template whose target section is absent creates that section - deliberately, for
  `00 Tasks` and `13 AHJ` (ADR 0013).
- Lint errors on a template it cannot find or a target outside the map.
