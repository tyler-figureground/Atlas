---
title: "Project folder baseline: every document a project produces, where it goes, and what is missing"
date: 2026-11-04
generated_by: skills-for-architects
---

# Project folder baseline: every document a project produces, where it goes, and what is missing

Date: 2026-11-04
Scope: `G:\Shared drives\ARCHITECTURE`, map `_tools\architecture-map.json` v4.4, Atlas
templates in `tools/atlas/src/atlas/templates/project/`.
Method: full read-only walk of all 77 project folders (11 active + `00 Competitions`,
64 archived, `00 Templates`): 8,705 folders, 38,150 files, 19 s over Drive File Stream.
Every folder compared with the map's blessed names; folders the map does not know were
listed with their file types and sample names; filenames scanned for program,
equipment, selection, budget, title, utility, calc, closeout and receipt terms. Nothing on
the drive was changed. Trigger: Tyler photographing the Silverado client's kitchen
equipment and coffee setup and finding no folder for it.

Confidence tiers: **Measured** = counted on the drive today. **Observed** = seen in
specific files, not counted exhaustively. **Proposed** = this document's recommendation.

Builds on, does not re-open: `project-folder-usage-and-agent-output.md` (agent scratch,
tasks, AHJ, fuller `06` seed - all shipped), `correspondence-folder-structure.md` and ADRs
0021-0022 (exchange filed by party), ADR 0023 (one task file), ADR 0024 (permit tracker).

---

## 0. Summary

- **The gap Tyler hit is real and repeated.** Two projects already improvised the folder:
  Silverado `06\Program and client Reqs` (empty, made by hand) and 211 Centre
  `06\Project Information\Client Prom Requirements` ("Dream office from Tom, Stacy, and
  Max.docx"). Silverado has three decisions about the coffee station (0014, 0017, 0037)
  and no folder holding the evidence they were made from. (Measured)
- **It is one of seven gaps, not one.** The map covers the regulatory and drawing life of
  a project well. It is thin on the **client side** of design: what the client needs
  (program), what they own and the design must house (client items), what was selected
  for them (selections), and how the job ends (pay applications, closeout). Plus a
  business and a site home: receipts, utilities. Four smaller naming gaps besides.
  (Section 1)
- **Drift is moderate and fixable.** 78 folder names the map does not know hold 2,253
  files across the 11 active projects (Revit backup folders, `_sources` and dated
  exchange folders excluded). Most map to an existing home; the relocation table is in
  section 4. (Measured)
- **Discoverability is half the problem.** The map lists names, never what goes in them.
  Only `07 Correspondence` has a "Where does it go?" card. Tyler did not know where coffee
  photos go because no section says. (Observed)
- **Plan:** map v4.5 adds 14 children and 3 templates (`PROGRAM.md`, `CLIENT-ITEMS.md`,
  `SELECTIONS.md`); Atlas learns child descriptions and on-create templates; a `06`
  filing card is generated from the map; seven projects are conformed one at a time.
  Section 5.

---

## 1. The baseline: every document type, where it goes, verdict

One row per kind of document an architecture project of this studio's size produces
(residential and small commercial, design through CA). Home = the map v4.4 location.
Owner-supplied items follow AIA B101 Article 5 (program, budget, survey, geotech, legal
information); not re-verified against the document text this session.

**Verdict:** `ok` home exists and is used - `ok*` home exists, rule is unclear -
**`GAP`** no home - `drift` home exists, projects file elsewhere.

### 1.1 Start-up and client

| Document | Home today | Verdict | Evidence |
|---|---|---|---|
| Proposal, contract, amendments | `10 Legal/Proposals-Contracts` | ok | 14 legacy + active projects |
| Day-1 intake answers | `00 Tasks/INTAKE.md` -> `PROJECT.md` | ok* | INTAKE is permit-shaped (APN, setbacks, utilities); asks nothing about how the client lives or works |
| **Client program and requirements** - rooms, sizes, users, adjacencies, must-haves, wish lists, questionnaires | none | **GAP** | Silverado `Program and client Reqs` (hand-made); 211 `Project Information/Client Prom Requirements`; 1221 `00 Project Information & Narrative`; Coleman strategy docs in `Project Information` |
| **Client items** - photos and sizes of what the client owns that the design must house: appliances, coffee and bar gear, cookware, collections, art, furniture kept, equipment | none | **GAP** | Silverado photos (today); Silverado decisions 0014, 0017, 0037; 211 Keurig and mini-fridge families built from guesses |
| Client-sent inspiration and precedent | `06/Inspiration` | ok* | 211 cabinet shortlist; Silverado `03 Renderings/Inspiration` (drift); 211 `03 Renderings/References` (drift) |
| Owner budget, pro forma, cost targets | `06/Costs & Bids` (on demand) | drift | 1221 `00_Proforma`; Coleman `10 Legal/1757_Coleman_Budget_CostSeg.xlsx` |
| Project facts, narrative, parcel report | `06/Project Information`, `PROJECT.md` | ok* | 211 files product-selection memos here; Beitz uses it for intake scratch |
| Decisions | `decisions/` | ok | 10/10 active |
| Brief, tasks, errands | `BRIEF.md`, `00 Tasks/` | ok | shipped (ADR 0014, 0016, 0023) |

### 1.2 Site, existing conditions, regulation

| Document | Home today | Verdict | Evidence |
|---|---|---|---|
| Site photos | `06/Site Review/Photos` | drift | Beitz `06/Photos` (26 HEIC) |
| **Field measurements** - tape dims, laser notes, hand sketches | none (`01 Model/03 Field Verified` is the model) | **GAP** (minor) | 64th Lane `Contractor/In/As Built Dimensions`; Beitz measured nothing to file |
| Scans, virtual tours, point clouds | `06/Site Review/Scans & Tours`, `01 Model/Reality Capture` | drift | Monticello `Site Review/Virtual Tour`; 211 Matterport pack at `06` root (159); 64th Lane `06/Reality Capture` |
| As-builts, record drawings, prior sets | `06/As-Builts & Record Drawings` | drift | Silverado `1998 As-Builts`, `CAD Deliverables`; Beitz `Reference Drawing Sets` |
| Existing CAD/PDF backgrounds | `06/Site Review/Ex CADs & PDF` | ok | San Vicente iGUIDE DWGs |
| Survey | `06/Survey` | ok* | Beitz `Survey` holds 90 GIS fetch files, not a survey |
| Title, deed, easements, CC&Rs | `06/Deed` | ok* | name says "Deed" only; Beitz easement request sat in `_Outbox` with nowhere to land |
| Public records, permit history, assessor | `06/Public Records` | drift | Beitz `County Records - Site Review`, `County Assesor Parcel Maps`; Monte Vista permit history in `Project Information` |
| GIS, aerials, flood maps, vicinity | `06/GIS & Maps` | drift | Beitz `Vicinity Map`, `Google Maps` |
| Zoning | `06/Zoning` | ok | |
| Code research and analysis | `06/Code` | ok | Norma `analysisDir` |
| Hazards: flood, fire zone, hazmat, soils | `06/Environmental & Hazards` | ok* | 64th Lane asbestos report in `Client/In/Asbestos`, no research-side pointer |
| **Utilities and site services** - will-serve letters, septic and well records, service capacity, utility releases | none | **GAP** | Beitz septic records in `Reference Drawing Sets`; Monticello septic evaluation in `Consultants/Architect/In`; INTAKE q8-9 ask for them |
| Geotech, structural, energy reports | `07 Correspondence/Consultants/<discipline>/In` | ok | Monticello GeoTech, Structural Calcs, Energy Calcs |
| Permit applications through final | `07 Correspondence/AHJ/01-06` | drift | Pestoni and Beitz rounds named `V1`-`V3`, not `R<n>_YYMMDD` - the permit tracker cannot date them |
| Design review boards, HOA, historic commission | none stated | ok* | 1221 Preservation Committee filed as a `04 Presentation` folder |

### 1.3 Design and documents

| Document | Home today | Verdict | Evidence |
|---|---|---|---|
| Models, families, materials | `01 Model/...` | drift | `01 Model/Families` in 3 projects, `Materials` in 1 - should be `00 Library/` |
| Superseded models | none | **GAP** (naming) | `Archive`, `archive`, `aRCHIVE`, `_Archive Mile Stones` in 6 projects |
| Sheets by phase | `02 Sheets/0-5` | ok | |
| Check prints and redlines | none | **GAP** (minor) | Silverado `Test Prints` (8), 211 `Tylers Review` |
| Renderings, sketches, videos | `03 Renderings/...` | ok | |
| Material and colour studies | none | **GAP** (minor) | Silverado `Material Studies` (12), `04 Presentation/Purple Material` (14) |
| Presentations by date | `04 Presentation/YYMMDD-n Name` | ok | |
| Product research memos | `06/Products & Materials` | ok | 64th Lane appliance connection research |
| **Selections** - the client-approved list of fixtures, appliances, finishes, lighting, hardware, with responsibility (OFCI, CFCI) and status | none | **GAP** | 64th Lane selection memos in `12 CA` (Laundry, Dishwasher, Heater Fuel, OFCI Tile Schedule); decisions 0012, 0022; Silverado decision 0022 finish set; 211 `05 Specs/Kitchen/Kitchen_Equipment_Schedule.xlsx`; legacy `_SpecBook/Kitchen`, `Light Fixtures`, `Restroom`, `04_Equipment List/Cutsheets` |
| Specifications by division | `05 Specs/<div>` | drift | divisions 10, 11, 12 missing: Coleman `11 Equipment` (fridge cut sheets, AV), 211 `Kitchen` |
| Physical samples | `05 Specs/_Samples` | ok | |

### 1.4 Bidding, construction, closeout, business

| Document | Home today | Verdict | Evidence |
|---|---|---|---|
| Bids, bid leveling | `07/Contractor/Bids`, `06/Costs & Bids` | ok | 64th Lane |
| Contractor licence and prequalification | none stated | ok* | Beitz `06/C-22 Licensed Contractors` |
| RFIs, submittals, change orders, ASIs | `07/Contractor/...` | ok | |
| **Contractor pay applications** | none | **GAP** | no active project in pay-app stage yet; standard AIA G702/G703 |
| Field reports, punch, construction photos | `12 CA/...` | ok | |
| **Closeout** - warranties, O&M manuals, record set, lien releases, attic stock list, final CofO copy | none (`AHJ/06` holds the final) | **GAP** | legacy `Record Sets/Maintenance` (124 files); no 2026 project closed yet |
| Invoices, timesheets | `10 Legal/Invoices` | ok | |
| **Receipts and reimbursables** - county fees, prints, records, shipping | none | **GAP** | Coleman `10 Legal/Receipts` (hand-made); Beitz county receipt filed in `County Assesor Parcel Maps`; legacy scaffold had `Receipts` and `Shipping` in 12 projects |
| Insurance, licences, certificates | `10 Legal/Certificates` | ok | |
| Meetings, minutes, recordings | `11 Meetings/...` | ok | 64th Lane `10 Legal/Comms` holds one `.m4a` |
| Marketing | `09 Marketing` | ok | |

**Tally:** 47 document types. 19 `ok`, 8 `ok*` (home exists, rule unclear), 9 `drift`,
11 **`GAP`**: seven substantive (program, client items, utilities, selections, pay
applications, closeout, receipts) and four naming-level (field measurements, model
archive, check prints, material studies). Specification divisions 10-12 counted under
drift.

---

## 2. Findings

### 2.1 Program is the oldest gap on the drive (Measured)

The pre-2026 scaffold had `01 Model/Program Areas` in 8 projects. It holds **0 files** in
all 8: program filed under the model is a place nobody looks. Since then every project
that captured a program improvised a home:

| Project | Where the program went |
|---|---|
| 2981 Silverado | `06/Program and client Reqs` - empty, hand-made; photos taken but not yet filed |
| 211 Centre | `06/Project Information/Client Prom Requirements/Dream office from Tom, Stacy, and Max.docx` |
| 1221 Hayes | `06/00 Project Information & Narrative` (narrative, 47 existing photos, deed, survey, zoning) |
| 1757 Coleman | `06/Project Information` - project reference, tenant tech stack, deck and landscaping strategies |
| 80-23 64th Lane | program lives in decisions (0006 range stays gas, 0007 hood, 0014 kitchenette) and `PROJECT.md` |

`INTAKE.md` asks twelve permit questions and none about use. `BRIEF.md` holds what is
settled and open, not the program. So the program exists only as fragments in decisions
and minutes, and an agent sizing a coffee station or appliance garage has no measured
source. Silverado decision 0017 (coffee station appliance garage with bar sink) is
exactly the case: the decision is recorded, the equipment it must fit is not.

### 2.2 Client items are a distinct kind of document (Observed)

Photos of the client's kitchen equipment are not site photos (they move with the client,
they are sized for casework, not for existing conditions) and not inspiration (they are
facts, not taste). They need four things site photos do not: the item, its size, its
service needs (power, water, drain, vent, heat clearance) and the room it goes to. The
best existing analogue is the Beitz `intake-photo-inventory.json` an agent built to make
sense of 26 HEIC photos - a register, beside the photos. A `CLIENT-ITEMS.md` register is
the human-readable version of that.

### 2.3 Selections have no home, so they land in CA and decisions (Measured)

64th Lane wrote five selection memos into `12 Construction Administration` (laundry,
dishwasher, heater fuel, historical plumbing selections, OFCI tile schedule) because the
selection happened during pre-construction and `12` was the nearest open folder. 211
Centre keeps a kitchen equipment schedule in a hand-made `05 Specs/Kitchen`. Silverado
records its finish set as decision 0022. Legacy restaurant projects kept
`_SpecBook/Kitchen`, `Light Fixtures`, `Restroom` and `Equipment List/Cutsheets`.
Selections are a living register (proposed -> client approved -> ordered -> installed,
with who furnishes and who installs), not a decision and not a spec section. Decisions
record *why* a choice was made; the register records *what is currently selected*.

### 2.4 Five small homes projects already hand-made (Measured)

| Gap | Projects that hand-made it | Proposed home |
|---|---|---|
| Superseded models | 6 (`Archive`, `archive`, `aRCHIVE`, `_Archive Mile Stones`) | `01 Model/_Archive` |
| Check prints, redlines | 2 (`Test Prints`, `Tylers Review`) | `02 Sheets/_Check Prints` |
| Material studies | 1 (two folders, 26 files) | `03 Renderings/Material Studies` |
| Receipts | 1 active + 12 legacy | `10 Legal/Receipts` |
| Spec divisions 10-12 | 2 (`11 Equipment`, `Kitchen`) | `05 Specs/10 Specialties`, `11 Equipment`, `12 Furnishings` |

### 2.5 Permit rounds named `V<n>` blind the permit tracker (Measured)

ADR 0024's tracker dates rounds from `R<n>_YYMMDD` folder names. Pestoni files
`V1 Submission`, `V2 Submission`, `V3 Submission - Water Permit`, `Working`; Beitz `V2`;
Monticello `floodplain`. The tracker reads none of the Pestoni or Beitz rounds.
Monticello's `R2_260728 (600807)` is read already (`permits.py` `ROUND_FOLDER` has no end
anchor); renaming it is tidy-up only. A relocation (rename) closes it; the stray `Working` folder belongs in `_Outbox`.

### 2.6 The map has names, not meanings (Observed)

Every child in `architecture-map.json` is a bare name. Atlas's Add-Section menu shows the
name; nothing says that "Deed" also takes title reports and easements, that
"Project Information" is not the program, or that "Survey" means a licensed survey and
not GIS. `07 Correspondence/README.md` (ADR 0022) is the only "Where does it go?" card
and it is the section with the least drift. `06` has 16 children and the most drift.

### 2.7 Received reference documents have two plausible homes (Observed)

A geotech report arrives from a consultant: ADR 0021 says file it in
`Consultants/Geotech/In` exactly as received. It is also the site's standing soils
reference, which `06` would hold. Projects do both: Monticello's GeoTech lives in
`Consultants/Geotech/In`, in `AHJ/06` as approved, and in `00 Tasks/Archive/_Duplicates`.
64th Lane's asbestos survey is only in `Client/In/Asbestos`, with no row in its research
index. A copy in both places creates duplicates (ticket 27's finding); a copy in one place
leaves the other section looking empty. The research index already has a `Path` column:
it can point into `07` without a copy.

### 2.8 Archived projects confirm the list, add nothing new (Measured)

The 64 archived projects (7,314 folders, 18,865 files) are mostly the old 730-folder
scaffold, empty. Where they hold files, the same gaps appear: `05 Specs/Kitchen` (93),
`_SpecBook/Kitchen` (90), `Light Fixtures`, `Restroom`, `04_Equipment List/Cutsheets`
(selections); `Record Sets/Maintenance` (124, closeout); `Corrsepondaence/Health
Inspector` (an AHJ); `Receipts`, `Shipping` (12 projects each, receipts). No document type
appears in the archive that section 1 does not already list.

---

## 3. Proposed structure - map v4.5 (Proposed)

Existing names stay verbatim. Fourteen children added, three templates added, one new map
field. Seed stays minimal: one new seeded folder.

### 3.1 New children

| Section | Child | Seed | Template | Absorbs |
|---|---|---|---|---|
| `06 Research & Existing Conditions` | `Client Program` | **yes** | `PROGRAM.md` | Silverado `Program and client Reqs`; 211 `Client Prom Requirements`; 1221 narrative |
| `06 Research & Existing Conditions` | `Client Program/Client Items` | no | `CLIENT-ITEMS.md` (on create) | Silverado equipment and coffee photos |
| `06 Research & Existing Conditions` | `Site Review/Field Measurements` | no | - | `Contractor/In/As Built Dimensions` working copies |
| `06 Research & Existing Conditions` | `Utilities & Services` | no | - | septic, well, will-serve, service capacity |
| `05 Specs` | `00 Selections` | no | `SELECTIONS.md` (on create) | 64th Lane `12 CA` selection memos, 211 kitchen schedule |
| `05 Specs` | `10 Specialties`, `11 Equipment`, `12 Furnishings` | no | - | Coleman `11 Equipment`, 211 `Kitchen` |
| `01 Model` | `_Archive` | no | - | six `Archive` spellings |
| `02 Sheets` | `_Check Prints` | no | - | `Test Prints`, `Tylers Review` |
| `03 Renderings` | `Material Studies` | no | - | Silverado `Material Studies`, `Purple Material` |
| `10 Legal` | `Receipts` | no | - | Coleman `Receipts`, Beitz county receipt |
| `12 Construction Administration` | `Pay Applications`, `Closeout` | no | - | legacy `Record Sets/Maintenance` |

Names, and why:

- **`Client Program`** (Tyler's decision, Q1). Under `06`, as Tyler asked and where
  `Project Information` already sits. Seeded because every project has a program, even a
  one-line one, and the seed costs one Drive item.
- **`Client Items`**, under the program: they are requirements with dimensions. Not under
  `Site Review` - they are not the site. On demand: many projects (code compliance,
  permit-only) never need it.
- **`05 Specs/00 Selections`**: `00` sorts it above the divisions and matches MasterFormat's
  Division 00 slot for procurement. Cut sheets for a selection go in the division folder
  (`11 Equipment`, `22 Plumbing`); the register links them.
- **`_Archive`, `_Check Prints`**: underscore prefix matches `_Samples`, `_Outbox`,
  `_Templates` - working folders that sort first and are not deliverables.
- **No new top-level section.** Every gap fits under an existing number.

### 3.2 Filing rules that change no folders

| Rule | Goes into |
|---|---|
| Program **source** sent by the client (email, wish list, questionnaire answers) stays in `07/Client/In` as received; `PROGRAM.md` cites it by path | `PROGRAM.md` template, `06` card |
| Photos **Tyler or staff take** of client items go straight to `Client Items`, named `YYMMDD_<Room>_<Item>_NN.<ext>`, originals kept (HEIC stays HEIC), one row each in `CLIENT-ITEMS.md` | `CLIENT-ITEMS.md`, `06` card |
| Received reference documents (survey, geotech, hazmat, title, as-builts) stay where they arrived; the research index row points to them. No second copy | `RESEARCH-INDEX.md` filing note, `06` card |
| `06/Deed` takes title reports, CC&Rs and easements; `06/Survey` takes licensed surveys only (GIS goes to `GIS & Maps`) | map descriptions (3.3) |
| Design review boards and HOAs are agencies: `07/AHJ`, one register row each | `CORRESPONDENCE-README.md` |
| Contractor licence checks and prequalification go in `06/Costs & Bids` | `06` card |
| Selections change through the register; a selection with a reason worth keeping also gets a decision, linked from its row | `SELECTIONS.md`, `/decision` skill |
| Permit rounds are `R<n>_YYMMDD`, always; `V<n>` is drift | `CORRESPONDENCE-README.md` (already says it), relocations |

### 3.3 New map field: `description`

Child entries already accept `{"name": ..., "seed": true}`. Add an optional
`"description"` - one line, plain words, what goes in it and what does not. Atlas shows it
in the Add-Section menu and generates the `06` filing card (`06 .../README.md`) from it,
so the card can never disagree with the map. `07`'s card stays hand-written (ADR 0022);
the generated card is for sections whose rules are one line per folder.

---

## 4. Relocations for current drift (Measured, proposed targets)

One Plan per project, preview first, Tyler approves (ADR 0006). Revit-linked files never
move (CAD links, point clouds, families loaded by path) - the conform guard applies.

| Project | From | To |
|---|---|---|
| 2981 Silverado | `06/Program and client Reqs` | `06/Client Program` |
| | `06/1998 As-Builts` | `06/As-Builts & Record Drawings/1998 As-Builts` |
| | `06/CAD Deliverables` (iGUIDE DWGs) | `06/Site Review/Ex CADs & PDF` |
| | `01 Model/Families`, `01 Model/Materials` | `01 Model/00 Library/Families`, `.../Materials` (only if not loaded by path) |
| | `01 Model/Archive`, `Concept`, `Schematic` | `01 Model/_Archive`, `04 Conceptual`, `05 Design` |
| | `02 Sheets/Test Prints` | `02 Sheets/_Check Prints` |
| | `02 Sheets/Warm Floors` (vendor DWG) | `07/Vendors/In/YYMMDD_Warm Floors` |
| | `03 Renderings/Material Studies`, `04 Presentation/Purple Material` | `03 Renderings/Material Studies` |
| | `03 Renderings/Inspiration` | `06/Inspiration` |
| 211 Centre | `06/Project Information/Client Prom Requirements` | `06/Client Program` |
| | `06/Project Information/*Selection*`, `*Coating*` memos | `06/Products & Materials` (per file) |
| | `06/mp_matterpak_Montez-Press_*` (159) | `06/Site Review/Scans & Tours/YYMMDD_Matterport` |
| | `05 Specs/Kitchen` | `05 Specs/11 Equipment` (schedule rows into `SELECTIONS.md`) |
| | `03 Renderings/References` | `06/Inspiration` |
| | `02 Sheets/Tylers Review` | `02 Sheets/_Check Prints` |
| 80-23 64th Lane | `12 CA/*Selection*`, `*OFCI-Tile-Schedule*` memos | `05 Specs/00 Selections` (rows into `SELECTIONS.md`) |
| | `12 CA/260929_Plumbing-Riser-Evidence` (199 json/png/py) | `.agent/runs/legacy-plumbing-riser-evidence` |
| | `06/Reality Capture` | `01 Model/Reality Capture/pointcloud` (check Revit links first) |
| | `10 Legal/Comms` (.m4a) | `11 Meetings/Recordings` |
| | `01 Model/Archive`, `Families` | `01 Model/_Archive`, `00 Library/Families` |
| 315 West Ln (Beitz) | `06/Photos` | `06/Site Review/Photos` |
| | `06/Vicinity Map`, `06/Google Maps` | `06/GIS & Maps` |
| | `06/County Records - Site Review`, `06/County Assesor Parcel Maps` | `06/Public Records` (receipt -> `10 Legal/Receipts`) |
| | `06/Reference Drawing Sets/Site Reference - Individual Files` | `06/As-Builts & Record Drawings` |
| | `06/Reference Drawing Sets` (other projects' example sets) | studio Reference Sets library (ADR 0015), or `06/Inspiration` |
| | `06/Survey` (90 GIS fetch files) | `GIS & Maps/_sources` (report) and `.agent/runs` (scripts) |
| | `06/C-22 Licensed Contractors` | `06/Costs & Bids` |
| | `02 Sheets/4 Construction/Vicinity Map` (py/json) | `.agent/runs/` |
| | `AHJ/03 Submissions/V2` | `AHJ/03 Submissions/R2_YYMMDD` |
| 1673 Pestoni | `AHJ/03 Submissions/V1`, `V2`, `V3 ... Water Permit` | `R1_YYMMDD`, `R2_YYMMDD`, `R3_YYMMDD` (dates from the filed sets) |
| | `AHJ/03 Submissions/Working` | `07/_Outbox` |
| | `AHJ/04 Comments & Responses/V1` | `R1_YYMMDD` |
| 2267 Monticello | `06/Site Review/Virtual Tour` | `06/Site Review/Scans & Tours` |
| | `AHJ/04 .../R2_260728 (600807)`, `floodplain` | `R2_260728` (permit # into register), `R2_260728` or `05 Letters & Emails` |
| | `00 Tasks/Archive/_Duplicates (review and delete)` | delete after a hash check confirms each file has a twin |
| | `01 Model/aRCHIVE` | `01 Model/_Archive` |
| 1757 Coleman | `10 Legal/Receipts` | blessed as-is by v4.5 |
| | `05 Specs/11 Equipment` | blessed as-is by v4.5 |
| | `10 Legal/1757_Coleman_Budget_CostSeg.xlsx` | stays (owner's tax cost seg is the client's business record), or `06/Costs & Bids` - ask |
| 1221 Hayes | `06/00 Project Information & Narrative` and its `Deed`, `Survey`, `Zoning`, `Existing Photos` | `06/Project Information`, `Deed`, `Survey`, `Zoning`, `Site Review/Photos` |
| | `06/00_Proforma`, `Potential Contractors` | `06/Costs & Bids` |
| | `06/Building Code`, `ADU Information` | `06/Code`, `06/Zoning` |
| | `06/Materials` | `06/Products & Materials` |
| | `06/Solar Quotes and Analysis` | `07/Vendors/In/YYMMDD_Solar quote` |
| | `06/Vacation Rental Application` | `07/AHJ/02 Applications & Forms` |
| | `01 Model/01 Library`, `_Archive Mile Stones` | `01 Model/00 Library`, `_Archive` |
| | `02 Sheets/0 Feasability Sketches` | `02 Sheets/0 Feasibility` |
| | `05 Specs/0NN ...` (32 empty legacy folders) | `clean` removes them |
| 262 Monte Vista, 1655 San Vicente | - | clean today (San Vicente's iGUIDE pack is a dated instance inside `Scans & Tours`) |

Map-level relocations (`relocations` key) for names that recur: `01 Model/Archive`,
`01 Model/archive`, `01 Model/aRCHIVE`, `02 Sheets/Test Prints`, `06/Photos`, `06/Vicinity Map`, `06/Google Maps`,
`06/County Records - Site Review`, `06/Site Review/Virtual Tour`, `06/Reality Capture`,
`06/Program and client Reqs`. The rest of the table is project-specific and stays a
per-project move. `01 Model/Families` and `Materials` stay per-project moves: a Revit
model may load them by path, so each move is checked by hand before it runs.

App working folders: `11 Meetings/.dicta` (Dicta) and `01 Model/Revit_temp` are machine
state. `meetings.py` and `scan.py` already skip dot folders; the doctor off-map
count (2.5) skips them the same way (`tolerated` only takes root names, ADR 0018), and confirm `Revit_temp` is treated like the Revit `_backup` folders `scan.py`
already exempts.

---

## 5. Implementation plan

Order: unblock Silverado today, decide, teach Atlas the two new map behaviours, ship
map v4.5 and templates, update the rules agents read, migrate one project at a time,
then keep it clean.

### Phase 0 - Today (no code)

| # | Work | Done when |
|---|---|---|
| 0.1 | Silverado: put the equipment and coffee photos in the existing hand-made `06\Program and client Reqs\Client Items\` (create the subfolder by hand once). Phase 5 renames the parent to `Client Program`; the photos move with it | photos filed, named `YYMMDD_<Room>_<Item>_NN` |
| 0.2 | Note each item's W x D x H and service needs while on site; a plain list is fine, it becomes `CLIENT-ITEMS.md` rows in 5.x | list exists |

### Phase 1 - Decide and record (1 session)

| # | Work | Done when |
|---|---|---|
| 1.1 | Tyler answers section 6 | done 2026-11-04; see section 6 |
| 1.2 | ADR 0025 - client-side homes: program, client items, selections; the received-document rule (3.2); `description` on map children; amends ADR 0012 (on-create templates are not carried by every project) | done 2026-11-04: `docs/adr/0025-client-program-client-items-and-selections-get-homes.md` |
| 1.3 | `CONTEXT.md` terms: Program, Client Item, Selection, Selections Register, Filing Card | done 2026-11-04, plus On-Create Template |

### Phase 2 - Atlas (one release)

| # | Work | Files | Done when |
|---|---|---|---|
| 2.1 | Child entries accept `"description"`; unknown-key check updated; `atlas lint` warns on a seeded child without one | `core/mapfile.py`, `core/lintmap.py`, tests | done 2026-11-04, Atlas 0.27.0 |
| 2.2 | Template entries accept `"when": "on-create"`: copied when Atlas creates that folder (Add-Section, conform relocation target), never by new-project or conform backfill. Today every template is copied unconditionally, so a template in an on-demand folder would create the folder in every project | `core/mapfile.py`, `core/ops.py`, `core/conform.py`, `core/doctor.py` (missing-template list and explained top folders skip on-create templates whose folder is absent), `core/projectmd.py` (AGENTS.md index lists only present templates), check `core/runs.py`, tests | done 2026-11-04, Atlas 0.27.0 |
| 2.3 | Add-Section menu shows the description beside each name | TUI add-section screen | done 2026-11-04, Atlas 0.27.0 |
| 2.4 | Generated filing card: `06 .../README.md` built from `06`'s child descriptions; conform rewrites it in place between markers, Tyler's notes outside the markers kept (same pattern as the AGENTS.md block) | `core/templates.py` or new `core/filingcard.py` | done 2026-11-04, Atlas 0.27.0 |
| 2.5 | Doctor `--deep`: off-map folder count per project (excluding Revit backups, dated instances, `_sources`), so drift has a number | `core/doctor.py`, `core/deep.py` | done 2026-11-04, Atlas 0.27.0 |
| 2.6 | `uv run pytest` green; CI green; release | `tools/atlas` | green |

### Phase 3 - Map v4.5 and templates

| # | Work | Where | Done when |
|---|---|---|---|
| 3.1 | Add the children in 3.1 and a description for every `06` child and the new children | `_tools\architecture-map.json` | `atlas lint` clean |
| 3.2 | Templates: `PROGRAM.md` (seeded), `CLIENT-ITEMS.md` and `SELECTIONS.md` (`on-create`) - Appendices A-C | `tools/atlas/src/atlas/templates/project/` | done 2026-11-04, shipped in Atlas 0.27.0 |
| 3.3 | Relocations from section 4's map-level list | map `relocations` | `conform --only relocate` previews them on a fixture; targets such as `01 Model/00 Library`, `04 Conceptual`, `05 Design`, `02 Sheets/0 Feasibility` confirmed as map children, or `atlas lint` warns `RELOC-UNBLESSED-CHILD` |
| 3.4 | `INTAKE.md`: add three design questions - who uses the building and how; what they own that must fit; budget band - pointing answers to `PROGRAM.md` | template | done 2026-11-04, Atlas 0.27.0 |
| 3.5 | `RESEARCH-INDEX.md` filing note: received documents are indexed where they arrived, never copied | template | done 2026-11-04, Atlas 0.27.0 |
| 3.6 | `CORRESPONDENCE-README.md`: rows for design review / HOA (AHJ) and for client program material (`Client/In`, cited from `PROGRAM.md`) | template | done 2026-11-04, Atlas 0.27.0 |
| 3.7 | Drive `README.md` v1.5 change record and `_tools\HOW-TO.md` "where does it go" pointer | drive | |

### Phase 4 - Rules and skills agents read

| # | Work | Where |
|---|---|---|
| 4.1 | Filing rules: program -> `PROGRAM.md`; client item photos -> `Client Items` + register row; selections -> `SELECTIONS.md`, never in `12 CA` or decisions alone | `templates/project/agents-rules.md` (Atlas block of every AGENTS.md) (done 2026-11-04) |
| 4.2 | `/project-dossier`: read `PROGRAM.md` alongside `PROJECT.md`; program facts that are code inputs (occupancy, occupant count) also go into `PROJECT.md` front matter | `plugins/09-project-dossier/skills/project-dossier/SKILL.md` (done 2026-11-04) |
| 4.3 | `/meeting-closeout`: program changes heard in a meeting update `PROGRAM.md` (with a dated change line) and selections update `SELECTIONS.md` | `plugins/09-project-dossier/skills/meeting-closeout/SKILL.md` (done 2026-11-04) |
| 4.4 | `/decision`: a decision that changes a selection links its `SELECTIONS.md` row | `plugins/09-project-dossier/skills/decision/SKILL.md` (done 2026-11-04) |
| 4.5 | `./scripts/lint.sh` green | repo |

A dedicated `/program` skill (walk the client through the program questionnaire, turn
photos into `CLIENT-ITEMS.md` rows by reading dimensions off a tape in the photo) is
worth considering after two projects have used the templates by hand - not before.

### Phase 5 - Migrate (one project at a time, pilot first)

Each project: conform preview -> Tyler approves -> apply -> undo available. Section 4 is
the move list.

| Order | Project | Why this order |
|---|---|---|
| 1 (pilot) | 2981 Silverado | the trigger; live program work; photos waiting |
| 2 | 211 Centre | second program improvisation; kitchen schedule into `SELECTIONS.md` |
| 3 | 1673 Pestoni | `V<n>` -> `R<n>` so the permit tracker sees it |
| 4 | 80-23 64th Lane | selection memos out of `12 CA` |
| 5 | 315 West Ln | largest `06` drift |
| 6 | 2267 Monticello | small; duplicates to resolve |
| 7 | 1221 Hayes, 1757 Coleman | legacy-shaped `06` |
| - | 262 Monte Vista, 1655 San Vicente | conform adds the new seed and card only |

Per project, done when: doctor off-map count 0 (2.5); `Client Program/PROGRAM.md`
exists with at least the client's own words or a "none received" line; every selection
memo is a register row; `atlas permits` dates every round; Revit opens with no missing
links.

### Phase 6 - Keep it clean

| # | Work | Done when |
|---|---|---|
| 6.1 | Off-map count in the Tyler digest, per project, only when non-zero | digest shows it |
| 6.2 | Re-run this walk (`walk.py`-style, read-only) quarterly; diff against this report's section 1; any new document type gets a row and a home before it gets a hand-made folder | next report dated 2027-02 |
| 6.3 | Hand-made folders are the signal: when two projects improvise the same name, it goes to the map | rule in `docs/adr/0025` |

---

## 6. Decisions (Tyler, 2026-11-04)

All seven questions answered. Q1 overrode the recommended name; Q2-Q7 took the default.

| # | Question | Decision |
|---|---|---|
| Q1 | Name of the program folder | `Client Program` (Tyler's call over the recommended `Program & Requirements`) |
| Q2 | Client items: subfolder of the program or its own `06` child? | Subfolder: `Client Program/Client Items` |
| Q3 | Seed `Client Program` in every new project? | Yes, with `PROGRAM.md` |
| Q4 | Selections register location | `05 Specs/00 Selections` |
| Q5 | Received reference documents (geotech, survey, hazmat) | Pointer only from the research index; no working copy |
| Q6 | Beitz's example drawing sets from other projects | Move to the studio Reference Sets library (ADR 0015) |
| Q7 | Coleman's cost-seg budget | Stays in `10 Legal` |

---

## Appendix A - `06 .../Client Program/PROGRAM.md` template

```markdown
---
project: "{{project_folder}}"
updated: {{created}}
---

# Program - {{project_name}}

What the people who use this place need from it, in their words first. Facts the code
needs (occupancy, occupant count, bedrooms) also go in `PROJECT.md`. Why a requirement
changed -> `decisions/`. What was chosen to meet it -> `05 Specs/00 Selections/SELECTIONS.md`.

**Sources** - client material stays where it arrived; cite it here.

| Date | What | From | Path |
|---|---|---|---|

## Who uses it and how

<!-- People, ages, mobility, pets, work-from-home, guests, staff. A normal day, a busy day. -->

## Spaces

| Space | Size or count | Must have | Nice to have | Adjacent to | Notes |
|---|---|---|---|---|---|

## Things that must fit

See `Client Items/CLIENT-ITEMS.md` for every item with its size and service needs.

## Budget and time

<!-- Budget band, what it includes, hard dates. -->

## Not wanted

<!-- Things the client has ruled out. -->

## Changes

Newest first. `YYYY-MM-DD - what changed - source (meeting, email) - decision ref`.
```

## Appendix B - `Client Program/Client Items/CLIENT-ITEMS.md` template

```markdown
# Client items - {{project_name}}

What the client owns that the design must house. One row per item; photos beside this
file, named `YYMMDD_<Room>_<Item>_NN`. Originals kept as taken (HEIC stays HEIC).

| ID | Item | Room / destination | W x D x H (in) | Clearances | Power | Water / drain | Vent / heat | Keep, replace, buy | Photos |
|---|---|---|---|---|---|---|---|---|---|
| CI-01 | | | | | | | | | |

**Dimensions:** measured on site unless marked `(spec)` - from the maker's sheet, linked -
or `(est)`. Estimated sizes never go on a sheet; they become a task to measure.
```

## Appendix C - `05 Specs/00 Selections/SELECTIONS.md` template

```markdown
# Selections - {{project_name}}

What is currently selected for this project. Decisions record why; this records what.
Cut sheets go in the division folder beside this one (`11 Equipment`, `22 Plumbing`...).

| ID | Item | Location | Make / model / finish | Furnished by | Installed by | Status | Cut sheet | Decision |
|---|---|---|---|---|---|---|---|---|

**Furnished / installed by:** `owner` · `contractor` · `vendor` (OFCI = owner furnished,
contractor installed).
**Status:** proposed · client approved · ordered · delivered · installed · substituted (link the replacement row)
```
