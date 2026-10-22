# 21. 07 Correspondence files exchange by party

Date: 2026-10-22

## Status

Accepted. Map v4.0 (not yet applied). Supersedes the `13 AHJ` placement in ADR 0013; its
six stages, register and "Submissions, never Submittals" rule carry over unchanged.

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
trade.

**Owner and Client are both seeded.** When they are the same person, file under `Client`
and leave `Owner` empty. This rule goes into the AGENTS.md Atlas block.

**AHJ rounds pair across stages.** `03 Submissions\R1_YYMMDD` and
`04 Comments & Responses\R1_YYMMDD` share a prefix, so a resubmittal and the comments it
answers sort side by side. The response letter goes in the round's `04` folder.

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

Relocations in the map, applied per project with per-folder confirmation:

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
| `08 OUT/RFI` | `07 Correspondence/Contractor/RFIs` |
| `08 OUT/Submittals` | `07 Correspondence/Contractor/Submittals` |
| `08 OUT/Change Orders` | `07 Correspondence/Contractor/Change Orders` |
| `08 OUT/Sketches` | `07 Correspondence/Contractor/Sketches & ASIs` |
| `08 OUT/Kitchen` | `07 Correspondence/Vendors/Out/Kitchen` |
| `08 OUT/Resubmittal` | `07 Correspondence/AHJ/03 Submissions` |
| `08 OUT/Transmittals/TRANSMITTAL-LOG.md` | `07 Correspondence/TRANSMITTAL-LOG.md` |

Not automatic, triaged by hand or by an agent run with Tyler approving each move:

- `08 OUT/Transmittals/YYMMDD_*` packages - the recipient is not recorded; each goes to
  the `Out` of the party it was sent to.
- `07 IN/Consultants` - split by discipline.
- Loose `08 OUT` folders (Silverado `261108 - Property Feasibility Analysis`) - usually
  `Client/Out`.
- 64th Lane `08 OUT/Submittals` holds bid sets, not shop-drawing submittals - those go to
  `Contractor/Bids`.
- AHJ material moved into `AHJ/05 Correspondence` - sorted into its stage folders.

## Consequences

Atlas creation and cleaning need no change: seeded children may contain slashes
(`Client/In`), seeded paths are protected from `clean`, and `add` accepts
`07 Correspondence/Consultants/Structural/In`. Adding a discipline takes two `add` requests
(`In` and `Out`); a one-step discipline add is a follow-up, not a blocker.

Map lint needed one fix: `DUP-CHILD` counted `In` once per parent and warned that one
section was "13 sections". It now counts sections. Every parent (`Client`, `AHJ`,
`Contractor`, `Consultants/<Discipline>`, `Vendors`) is listed as a child in its own right,
or relocations into it warn as unblessed. The discipline is `Surveyor`, not `Survey`, so it
does not collide with `06 Research & Existing Conditions/Survey` (the survey itself).

Unmapped agency folder names not listed above surface as Unfiled in doctor and are moved by
hand. Project AGENTS.md notes that name `07 IN`, `08 OUT` or `13 AHJ` need updating when the
relocation runs. Older Atlas versions that do not know map v4.0 will see `07 Correspondence`
as an unknown section and must be upgraded first.
