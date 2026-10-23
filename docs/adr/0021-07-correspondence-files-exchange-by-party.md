# 21. 07 Correspondence files exchange by party

Date: 2026-10-22

## Status

Accepted. Map v4.0. Amended by ADR 0022 (map v4.1): `AHJ/05 Correspondence` is now
`AHJ/05 Letters & Emails`, and `Owner` is created on demand, not seeded. Amends ADR 0013: `13 AHJ` moves to
`07 Correspondence/AHJ` and AHJ rounds become folders instead of a file-name prefix. Its six
stages, register and "Submissions, never Submittals" rule carry over.

Decided by Tyler on 2026-10-22 against
`docs/research/correspondence-folder-structure.md`.

## Context

Exchange is filed three ways at once. `07 IN` sorts by party, `08 OUT` by instrument
(Transmittals, RFI, Submittals, Change Orders), `13 AHJ` by party then stage. Staff look
for what went to the city in IN / OUT, then remember AHJ.

On the drive (10 live projects, 2026-10-22): Monticello holds 95 county files in
`07 IN\Napa County PBES` with `13 AHJ` empty; Pestoni splits its county filing across
`07 IN\County`, `08 OUT\Resubmittal` and `13 AHJ`. Thirteen unblessed party folders were
invented under IN / OUT, mostly firm or agency names. The transmittal log in all 10
projects has one row in total.

Published practice is party-first (AIA "Keys to classifying project files", 5.0
Correspondence), with agency approvals as their own area (AIA 4.0) and RFIs, submittals and
transmittals as logged processes (Newforma, Procore). No source endorses a top-level
IN / OUT split.

## Decision

One section, **`07 Correspondence`**, holds every exchange with a party outside the studio.
Top level is the party, named by **role** from a closed list in the map, never by firm.
Parties with a formal process get process folders; the rest get `In` / `Out`.

```
07 Correspondence\
  TRANSMITTAL-LOG.md
  _Outbox\                    seeded - drafts awaiting Tyler's review before sending
  Client\    In\ Out\         seeded
  Owner\     In\ Out\         seeded
  AHJ\                        seeded - ADR 0013 stages + AHJ-REGISTER.md
    01 Requirements & Pre-Application\  02 Applications & Forms\  03 Submissions\
    04 Comments & Responses\  05 Correspondence\  06 Permits & Inspections\
  Consultants\                seeded empty
    <Discipline>\ In\ Out\    on demand: Architect, Structural, MEP, Civil, Surveyor,
                              Geotech, Landscape, Energy, Expediter
  Contractor\                 on demand, at bidding
    Bids\ RFIs\ Submittals\ Change Orders\ Sketches & ASIs\ In\ Out\
  Vendors\                    on demand
    In\ Out\
```

**Inside every `In` / `Out`:** one folder per exchange, `YYMMDD_<Description>`, holding the
files exactly as sent or received. A firm, vendor or agency name goes in that folder name
(`261022_Henrybuilt_Kitchen shop drawings`), never as a folder level: the map has no
free-text names (ADR 0013). This is why `Vendors` is `In` / `Out` and not one folder per
trade. The one exception is migration: a legacy vendor folder (`07 IN/Kitchen`) lands whole
as `Vendors/In/Kitchen` rather than being split, so nothing is renamed without a person.

**Transmittals:** one log, `07 Correspondence/TRANSMITTAL-LOG.md`, one row per package
sent. The package as sent goes in `YYMMDD_T-NNN_<Description>/` in the recipient's `Out`.

**Owner and Client are both seeded.** When they are the same person, file under `Client`
and leave `Owner` empty. This rule is in the AGENTS.md Atlas block.

**AHJ rounds are folders that pair across stages.** `03 Submissions\R1_YYMMDD` and
`04 Comments & Responses\R1_YYMMDD` share a prefix, so a resubmittal and the comments it
answers sort side by side. The response letter goes in the round's `04` folder; the agency
goes in the file name. This replaces ADR 0013's `R1_YYMMDD_` file prefix, because projects
already file whole rounds (Pestoni `V1 Submission`, `V2 Submission`).

**Boundaries that stay outside 07 Correspondence:**

- Proposals, contracts, invoices - `10 Legal`, even when sent to the client.
- Agendas and minutes - `11 Meetings`.
- What the code says - `06 Research & Existing Conditions/Code`. What an agency asked for
  and what we sent - `07 Correspondence/AHJ`.
- Field reports, punch lists, site visits - `12 Construction Administration`.

**Numbering:** reuses `07`. `08` and `13` are retired and left as gaps; renumbering
`09`-`12` would drift every project.

**Templates move:** `TRANSMITTAL-LOG.md` to the `07 Correspondence` root;
`AHJ-REGISTER.md` to `07 Correspondence/AHJ/`.

## Migration

**Order matters.** Conform runs backfills before relocations. Run plainly against a project
that still has `13 AHJ`, it would seed `07 Correspondence/AHJ` and a blank
`AHJ-REGISTER.md` first, and the move of `13 AHJ` would then collide on every child. So
each project migrates in two passes:

1. `atlas conform --project P --only relocate --apply` - `07 Correspondence` does not exist
   yet, so `13 AHJ` moves whole, register included, and nothing collides.
2. `atlas conform --project P --apply` - backfills whatever the moves did not bring.

Rehearsed on a mirror of all 10 projects (folder tree, placeholder files, real Markdown):
pass 1 moved every row below with 0 conflicts; after pass 2 doctor reported 0 conform and
0 drift on every project, and Pestoni's register arrived with its rows.

Relocations in the map. **Entry order is load-bearing**: a child relocation must come before
its parent's (`07 IN/Fabricator/Shop Drawings` before `07 IN/Fabricator`), or the parent
carries the child away and the child's row is skipped as "source gone". And `13 AHJ` comes
before every row that targets `07 Correspondence/AHJ/...` (`07 IN/County`,
`08 OUT/Resubmittal`, `10 Legal/Permits`), or that row creates `AHJ` first and `13 AHJ`
collides with it. The map lists the rows in the order of this table, `13 AHJ` first.

| From | To |
|---|---|
| `13 AHJ` | `07 Correspondence/AHJ` |
| `07 IN/Client` | `07 Correspondence/Client/In` |
| `07 IN/Architect` | `07 Correspondence/Consultants/Architect/In` |
| `07 IN/General Contractor` | `07 Correspondence/Contractor/In` |
| `07 IN/Bids` | `07 Correspondence/Contractor/Bids` |
| `07 IN/Fabricator/Shop Drawings` | `07 Correspondence/Contractor/Submittals` |
| `07 IN/Fabricator` | `07 Correspondence/Vendors/In` |
| `07 IN/Expediter` | `07 Correspondence/Consultants/Expediter/In` |
| `07 IN/MEP Engineer`, `07 IN/Electrical` | `07 Correspondence/Consultants/MEP/In` |
| `07 IN/Structural Engineer` | `07 Correspondence/Consultants/Structural/In` |
| `07 IN/Civil` | `07 Correspondence/Consultants/Civil/In` |
| `07 IN/Solar Vendor`, `07 IN/Kitchen`, `07 IN/Speaker Consul` | `07 Correspondence/Vendors/In/<same name>` |
| `07 IN/County`, `07 IN/Napa County PBES`, `07 IN/AHJ` | `07 Correspondence/AHJ/05 Correspondence` |
| `08 OUT/Drafts` | `07 Correspondence/_Outbox` |
| `08 OUT/RFI`, `08 OUT/3 RFI` | `07 Correspondence/Contractor/RFIs` |
| `08 OUT/Submittals`, `08 OUT/4 Submittals` | `07 Correspondence/Contractor/Submittals` |
| `08 OUT/Change Orders`, `08 OUT/change Orders` | `07 Correspondence/Contractor/Change Orders` |
| `08 OUT/Sketches` | `07 Correspondence/Contractor/Sketches & ASIs` |
| `08 OUT/Kitchen` | `07 Correspondence/Vendors/Out/Kitchen` |
| `08 OUT/Resubmittal` | `07 Correspondence/AHJ/03 Submissions` |
| `10 Legal/Permits` | `07 Correspondence/AHJ/06 Permits & Inspections` |

The v3 relocations `08 OUT/3 RFI`, `08 OUT/4 Submittals` and `08 OUT/change Orders` are
retargeted above; `08 OUT/5 Transmittals` is dropped (its target section is retired).

Not automatic, triaged by hand or by an agent run with Tyler approving each move (about 60
files on the mirror, 42 of them 64th Lane transmittals):

- `08 OUT/Transmittals` - each `YYMMDD_*` package goes to the `Out` of the party it was
  sent to; the old log's rows are copied into `07 Correspondence/TRANSMITTAL-LOG.md`. A
  relocation can only move a folder, so the log is moved by hand.
- `07 IN/Consultants` - split by discipline.
- Loose files and folders at the `08 OUT` root (211 Centre bid sets and TPA brief,
  Silverado `261108 - Property Feasibility Analysis`, Pestoni signage set) - usually
  `Client/Out` or `Contractor/Bids`.
- 64th Lane `08 OUT/Submittals` holds bid sets, not shop-drawing submittals. Move it to
  `Contractor/Bids` by hand before pass 1.
- AHJ material moved into `AHJ/05 Correspondence` - sorted into its stage folders.

When `07 IN` and `08 OUT` hold no files, `atlas clean --project P --apply` removes them.

## Consequences

Atlas creation and cleaning need no code change: seeded children may contain slashes
(`Client/In`), seeded paths are protected from `clean`, and `add` accepts
`07 Correspondence/Consultants/Structural/In`. Adding a discipline takes two `add` requests
(`In` and `Out`); a one-step discipline add is a follow-up, not a blocker.

Map lint needed one fix: `DUP-CHILD` counted `In` once per parent and warned that one
section was "13 sections". It now counts sections. Every parent (`Client`, `AHJ`,
`Contractor`, `Consultants/<Discipline>`, `Vendors`) is listed as a child in its own right,
or relocations into it warn as unblessed. The discipline is `Surveyor`, not `Survey`, so it
does not collide with `06 Research & Existing Conditions/Survey` (the survey itself).

The bundled templates change with this ADR: `agents-rules.md` (filing rules in every
AGENTS.md Atlas block), `TYLER.md`, `TRANSMITTAL-LOG.md`, `AHJ-REGISTER.md`. They name
`07 Correspondence` paths, so the Atlas release that carries them, map v4.0 and the
migration ship together: an AGENTS.md rewritten from the new rules while the map is still
v3.9 would send agents to folders that do not exist yet.

A leftover agency folder under `07 IN` shows in doctor as `07 IN` Unfiled at the project
root, not under its own name; find it by opening `07 IN`. Project notes in `AGENTS.md`
and `PROJECT.md` that name `07 IN`, `08 OUT` or `13 AHJ` are updated by hand during
migration. ADR 0016 (`08 OUT/Drafts`) and ADR 0009's example targets name retired paths;
read them through this ADR.
