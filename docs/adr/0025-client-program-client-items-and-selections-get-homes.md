# 25. Client program, client items and selections get homes; map children carry a description

Date: 2026-11-04

## Status

Accepted. Map v4.5 (planned), Atlas release in phase 2 of the folder baseline plan. Amends
ADR 0012: a template may be marked `on-create`, and such a template is not carried by every
project.

Decided by Tyler on 2026-11-04, answering Q1-Q7 of
`docs/research/project-folder-baseline.md`. Q1 named the folder `Client Program` over the
report's recommended `Program & Requirements`; Q2-Q7 took the recommended defaults.

## Context

Tyler was photographing a client's kitchen equipment and coffee setup on Silverado, to size
cabinets and appliance garages, and found no folder for it. A walk of all 77 project folders
against map v4.4 (`docs/research/project-folder-baseline.md`) showed the same gap three
ways:

- **Program.** Two projects improvised a home (`06/Program and client Reqs` on Silverado,
  `Project Information/Client Prom Requirements` on 211 Centre). The old scaffold's
  `01 Model/Program Areas` held 0 files in all 8 projects that had it.
- **Client items.** The things a client brings or keeps (appliances, equipment, collections)
  and their sizes and hookups had nowhere to go.
- **Selections.** Appliance and fixture choices were filed in `12 CA` (64th Lane) and in a
  hand-made `05 Specs/Kitchen` (211 Centre).

The report counts seven gaps in all (the three above plus utilities, pay applications,
closeout and receipts), four smaller naming gaps, and one cause behind most drift: the map names folders but never says what goes in them.
Only `07 Correspondence` has a "where does it go" card (ADR 0022).

ADR 0012 copies every template into every project and has conform backfill it. A template
inside an on-demand folder would therefore create that folder everywhere.

## Decision

1. **`06 Research & Existing Conditions/Client Program`** is a new **seeded** child, with
   `PROGRAM.md`: who uses the place, rooms and areas, adjacencies, must-haves, and sources.
   Program source sent by the client (emails, wish lists, questionnaire answers) stays in
   `07 Correspondence/Client/In` as received; `PROGRAM.md` cites it by path.
2. **`Client Program/Client Items`** is created on demand, with `CLIENT-ITEMS.md`: one row
   per item, with size, clearances, power, water and drain, vent and heat, and its photos. Photos taken by
   Tyler or staff go straight here, named `YYMMDD_<Room>_<Item>_NN.<ext>`, originals kept.
3. **`05 Specs/00 Selections`** is created on demand, with `SELECTIONS.md`: what was chosen,
   who furnishes and who installs it, and its status. Cut sheets go in the division folder
   (`11 Equipment`, `22 Plumbing`); the register links them. A selection with a reason worth
   keeping also gets a project decision, linked from its row. Research is what we could use;
   selections are what we chose.
4. **Other new children, all on demand:** `06/Site Review/Field Measurements`,
   `06/Utilities & Services`, `05 Specs/10 Specialties`, `11 Equipment`, `12 Furnishings`,
   `01 Model/_Archive`, `02 Sheets/_Check Prints`, `03 Renderings/Material Studies`,
   `10 Legal/Receipts`, `12 Construction Administration/Pay Applications` and `Closeout`.
   No new top-level section.
5. **Received reference documents** (survey, geotech, hazmat, title, as-builts) stay where
   they arrived. The research index points to them; no second copy. Related filing rules:
   `06/Deed` takes title reports, CC&Rs and easements; `06/Survey` takes licensed surveys only
   (GIS goes to `GIS & Maps`); design review boards and HOAs are agencies, filed under
   `07/AHJ` with one register row each; contractor licence checks and prequalification go
   in `06/Costs & Bids`; permit rounds are `R<n>_YYMMDD`, always.
6. **Map children take an optional `description`**: one plain line, what goes in and what
   does not. Atlas shows it in Add-Section and generates the `06` filing card
   (`06 .../README.md`) from `06`'s descriptions, between markers, so the card cannot
   disagree with the map. `07`'s card stays hand-written. `atlas lint` warns on a seeded
   child with no description.
7. **Templates take `"when": "on-create"`.** Such a template is owed only once its folder
   exists. `atlas new` copies it only when that folder is seeded; Add-Section copies it with
   the folder. A folder that arrives any other way (a conform relocation, a folder made by
   hand) makes doctor report the template missing, and the next conform backfills it -
   backfills run before moves, so a relocation target gets its template on the following
   pass, never mid-move. Doctor does not report it while the folder is absent. The AGENTS.md
   block is the same in every project, so its index row says "only once its folder is added"
   rather than being left out. Every other template keeps the ADR 0012 rule.
8. **Hand-made folders are the signal.** When two projects improvise the same folder name, it
   goes to the map as a blessed child or a relocation.

Also settled with Q1-Q7: Beitz's example drawing sets from other projects move to the studio
Reference Sets library (ADR 0015); Coleman's cost-seg budget stays in `10 Legal`.

## Consequences

- Each project gains one seeded folder (`Client Program`), one template (`PROGRAM.md`) and
  the generated `06` filing card, which conform adds to existing projects too. The other new
  children cost nothing until used.
- Existing hand-made homes move by relocation: `06/Program and client Reqs` and
  `Project Information/Client Prom Requirements` to `06/Client Program`. Per-project moves are
  listed in section 4 of the report and run one project at a time, Silverado first.
- Permit rounds named `V<n>` (Pestoni, Beitz) are drift, not a second convention; they are
  renamed to `R<n>_YYMMDD` so the permit tracker (ADR 0024) can read them.
- The `06` filing card is staff-facing copy: no em dashes, plain words.
- Until the Atlas release lands, `Client Items` and `00 Selections` are made by hand, and their
  templates are copied by hand.
