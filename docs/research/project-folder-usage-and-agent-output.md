# Project folders: how they are actually used, where agent output goes, and what to change

Date: 2026-10-02
Scope: `G:\Shared drives\ARCHITECTURE`, map `_tools\architecture-map.json` v2.2.
Method: full read-only walk of every 2026 project (7 active, 3 archived) plus the
2023-2025 legacy projects for contrast; every file classified by extension and name;
task-list, AHJ and research material traced by name and folder. Nothing on the drive
was changed.

> **Decided 2026-10-02** (ADRs 0011-0013, Atlas 0.7.0, map v3.0). Where this report says
> `tasks/`, read the numbered **`00 Tasks/`** (`TASKS.md`, `Lists/`, `Archive/`). Q2: the
> prompt vault's task queues move into each project's `TASKS.md`. Q3: closed runs are zipped
> after 14 days. Q4: `13 AHJ` is stage-first. Q5: the PowerShell tools are retired behind
> launchers that call Atlas, which now creates projects, folders and template files. Templates
> live in the repo at `tools/atlas/src/atlas/templates/project/`.

Confidence tiers: **Measured** = counted on the drive today. **Observed** = seen in
specific files, not counted exhaustively. **Proposed** = this document's recommendation.

---

## 1. Findings

### 1.1 Agent output is three quarters of every agent-heavy project (Measured)

Files per project, `.rws`/`.dat` Revit backup internals excluded. "Machine" =
`.json .py .txt .html .log .claim .ndjson .raw .out .ps1 .tsv .geojson` plus PNG
captures inside agent/verification folders.

| Project | Files | Machine | Machine % | Where the bulk sits |
|---|---:|---:|---:|---|
| 211 Centre (Montez Radio) | 4,147 | 3,255 | 78% | `11 Meetings\Agent Sessions\` - 3,317 files |
| 80-23 64th Lane | 1,842 | 1,475 | 80% | `tmp\` at root - 1,386; `12 Construction Administration\` - 260 |
| 295 West Ln (Beitz Fire) | 1,724 | 1,321 | 77% | `.agent\handoff\` - 1,010; `06 ...\Code\` - 241 |
| 2981 Silverado Trail | 1,412 | 999 | 71% | `06 ...\Model Verification\` - 425; `GIS and Maps\` |
| 2267 Monticello | 190 | 11 | 6% | saved web pages in `07 IN` |
| 1673 St. Helena (Pestoni) | 28 | 4 | 14% | - |
| 262 Monte Vista | 45 | 0 | 0% | - |
| **All seven** | **9,388** | **7,065** | **75%** | |

382 Markdown files carry agent-run names (report, resume, closeout, preflight,
handoff, journal, audit, proposal...). 211 Centre alone wrote eight
`260924-p3-tags-resume-HHMM.md` files in one evening.

### 1.2 Agents file scratch wherever the map has no answer (Observed)

The map gives agents exactly one home - `.agent/handoff/` for `HANDOFF-*.md`. Every
other kind of agent output was improvised, and each project improvised differently:

| Pattern | Example | What it should have been |
|---|---|---|
| Session scratch inside a human section | `211 Centre\11 Meetings\Agent Sessions\` (3,317 files) | per-run scratch outside the numbered tree |
| Scratch in an unmapped root folder | `64th Lane\tmp\` (1,386), `64th Lane\QA\` | same |
| Handoff dir used as scratch | `Beitz Fire\.agent\handoff\` - 165 `.py`, 337 `.json`, 145 `.claim`, 275 `.png` | handoffs only; scratch elsewhere |
| Verification evidence as "research" | `Silverado\06 ...\Model Verification\` (425) | per-run scratch; one finding filed, if any |
| Raw web scrapes beside the finding | `Beitz Fire\06 ...\Code\` - 5 reports, 236 `.html/.txt/.metadata.json/.links.json` | report in `Code\`, captures in a `_sources\` sub-folder |
| Design/doc audits filed as CA | `64th Lane\12 Construction Administration\` - 59 `.md`, mostly dimension/annotation passes during pre-construction | per-run scratch; Tyler-facing result in the right section |
| Control-file backups at root | `211 Centre\PROJECT.backup-2026091x-*.md` (6) + 4 `.bak-*` | `.agent\backups\` (Silverado already does this) |
| Tool caches synced to Drive | `.ruff_cache\`, `__pycache__\` (Beitz Fire, 64th Lane) | never on the drive |
| Hand-made strays | `_Duplicates (review and delete)`, `New folder`, `Submittal\New folder` | Atlas Plan, or nothing |

### 1.3 Task lists live in at least seven places, in at least five formats (Observed)

| Where | Example | Format |
|---|---|---|
| `PROJECT.md` "Open items" section | 64th Lane, 260 lines of a 1,616-line PROJECT.md | bullets |
| `06 ...\Project Information\` | Beitz Fire `OPEN-ITEMS.md` - "Single active register" | holds table H01-H15 |
| `11 Meetings\` | 64th Lane `260916_Tyler-Action-List.md`, `260918_CD-Set-Annotation-Audit-Task-List.md`, `260923_Drawing-Set-Update-Checklist.md` | checkboxes by date / T-NNN IDs with lanes |
| `.agent\handoff\` | Silverado `TASKS-revit-material-story-2026-09-29.md` | numbered agent-session prompt blocks |
| Project root | Silverado `SITE-VISIT-CHECKLIST.md` | checklist |
| `08 OUT\` | Silverado `00-MEETING-PREP-CHECKLIST.md` | checklist |
| Prompt vault | `_tools\Architecture-Prompts\02 Architecture Projects\<project>.md` "Task queue" | numbered prompt tasks |

The Beitz Fire cleanup had to write "Older tables/prompts/trackers are historical, not
parallel task lists" into its register - the cost of having no fixed home is that every
agent must first work out which list is current.

The best lists share four traits, and the template in Appendix A keeps them:

- one line per task, checkbox first (Tyler-Action-List);
- an owner lane - `[TYLER] [AGENT] [MODEL] [NORMA]` (CD-Set audit list);
- an acceptance check per task - "verify on a fresh sheet export" (CD-Set audit list);
- a holds table with the responsible party and the gate it blocks (OPEN-ITEMS H01-H15).

### 1.4 PROJECT.md has become a session log (Measured)

| Project | PROJECT.md lines |
|---|---:|
| 64th Lane | 1,616 (of which "Current issue" session log ~1,040, "Open items" ~260) |
| Silverado | 1,379 |
| 211 Centre | 1,090 |
| Monte Vista | 707 |

ADR 0001 makes PROJECT.md the facts contract Norma reads. Agents append a dated
`### <session> - <date>` block per run because there is no run log anywhere else, and
snapshot the file before each edit for the same reason (1.2).

### 1.5 AHJ material is spread over five sections (Observed)

5 of 7 recent projects carry permitting-authority material. None has one home:

| Project | AHJ material and where it went |
|---|---|
| Monticello | county comments `07 IN\Napa County PBES\V1 Review`, `V2 Review (600807)`; sets as filed `02 Sheets\4 Construction\V1-V4 Submission`; saved portal pages `07 IN\Napa County PBES\...files\` (91 files) |
| Pestoni | county letters `07 IN\County`; filings `08 OUT\Submittal`, `08 OUT\Resubmittal\Working`; draft code confirmation `10 Legal\Permits` |
| Beitz Fire | blank county forms `10 Legal\Permits`; county records and process research `06 ...\County Records - Site Review`, `06 ...\Code`; question list and response matrix `02 Sheets\4 Construction\COUNTY-*` |
| 64th Lane | DOB route through `07 IN\Expediter`; filing history only inside PROJECT.md |
| 211 Centre | TPA filing brief `08 OUT\260804 - TPA Filing Route - Client Brief.md` |

Legacy projects tried `07 IN\AHJ` (1221 Hayes) and `02 Sheets\Permit` (372 Dekalb).

Vocabulary collision: the map's `08 OUT\Submittals` means contractor submittals
(construction-phase shop drawings), but Pestoni used `08 OUT\Submittal` for its county
filing. A new AHJ section must not reuse the word.

### 1.6 Research outgrew `06` in every research-heavy project (Observed)

Map children today: `Site Review/Photos`, `Site Review/Ex CADs & PDF`, `Inspiration`,
`Deed`, `Survey`, `Zoning`, `Climate`, `Code`, `Project Information`.

What projects actually created beside them:

| Topic | Created as | Projects |
|---|---|---|
| GIS, aerials, flood, topo | `GIS`, `GIS and Maps\FEMA Map`, `Survey` (holding GIS, not survey), `Vicinity Map`, `Google Maps` | Beitz Fire, Silverado |
| Public / county records | `County Records - Site Review`, `County Assesor Parcel Maps` | Beitz Fire |
| As-builts, record drawings | `1998 As-Builts`, `Reference Drawing Sets`, `CAD Deliverables` | Silverado, Beitz Fire |
| Virtual tour / scans | `Site Review\Virtual Tour`, Matterport assets in `03 Renderings` | Monticello, 211 Centre |
| Contractors, bids, costs | `C-22 Licensed Contractors\Estimates`, `07 IN\Bids`, `00_Proforma`, `Potential Contractors` | Beitz Fire, 64th Lane, 1221 Hayes |
| Products, materials | `Materials`, `Cabinets` | legacy + 372 Dekalb |
| Index of sources | `EVIDENCE-INDEX.md`, `00-RESEARCH-PACKAGE.md`, `README.md` | Beitz Fire, Silverado |

The Beitz Fire `EVIDENCE-INDEX.md` (source, authority, date, reliability, path) is the
single most useful research artefact on the drive: it is what lets a new agent tell a
county record from a client photo. It should be standard.

### 1.7 What the seed actually gets used for (Measured, 7 active 2026 projects)

| Section | Seeded today | Has files |
|---|---|---:|
| 01 Model | yes | 6/7 |
| 02 Sheets | yes | 6/7 |
| 03 Renderings | yes | 3/7 |
| 04 Presentation | yes | 1/7 |
| 05 Specs | no | 1/7 |
| 06 Research & Existing Conditions | yes | 7/7 |
| 07 IN | yes | 4/7 |
| 08 OUT | yes | 4/7 |
| 10 Legal | **no** | **5/7** |
| 11 Meetings | yes | 3/7 |
| 12 Construction Administration | no | 1/7 (misused) |
| AHJ material (no section) | - | **5/7** |
| `decisions/` | control plane | 7/7 |

Only top-level sections are ever seeded - `ops.new_project` creates `section.id` and
nothing below it, and `find_empty_dirs` protects only seeded tops and control-plane
dirs. A seeded child folder would be swept by the next `clean`. So "on by default" for
anything below the top level needs a map schema change, not just a flag flip.

### 1.8 Costs that follow from the noise (Measured / from prior research)

- **Drive item cap.** 7,065 machine files in seven projects, against Google's 400,000
  item cap per shared drive. The 2026-06 redesign removed ~730 empty folders per project
  for this reason; agent runs now add more than that per project per month.
- **Read cost.** `atlas-drive-tree-read-cost.md`: enumeration is the unit of cost on
  Drive File Stream. Thousands of tiny receipts are the worst case for Atlas, sync and
  Explorer alike.
- **Path length.** Run artefacts carry long stamped names
  (`site65-checkpoint-POST-EXIT-20260930T200559164261Z.json`) under already-long
  project roots. `atlas-drive-latency-measurement.md` found live MAX_PATH failures.
- **Signal.** Tyler-facing results (minutes, code memos, drafts to send) sit beside
  dozens of run reports with the same date prefix.

---

## 2. Diagnosis

One cause underneath all of 1.2-1.5: **the map describes where documents go, and has
nothing to say about work.** Agents produce three kinds of thing - scratch (scripts,
receipts, captures), state (tasks, handoffs, run logs) and results (a memo, minutes, a
drawing). Only results have homes. Scratch and state get filed by analogy - "this is
from a meeting", "this is research", "this is CA" - and each project's agents invent a
different analogy.

The fix is to give scratch and state fixed homes in the control plane, keep the
numbered tree for results and source documents, and write the rule into the Atlas block
of every `AGENTS.md`, where every agent reads it first.

---

## 3. Proposed structure (Proposed)

### 3.1 Three layers

```
<project>/
├── AGENTS.md  CLAUDE.md  PROJECT.md  jdp-time-ledger.ndjson   control plane - root files
├── decisions/                       control plane - why (existing)
├── tasks/                           control plane - what next (NEW, seeded)
│   ├── TASKS.md                     the one live register, copied from the template
│   ├── lists/                       scoped lists, each linked from TASKS.md
│   └── archive/                     closed lists and pruned Done sections
├── .agent/                          agent workspace - not for people (extended)
│   ├── handoff/                     CURRENT.md + HANDOFF-*.md only (existing)
│   ├── runs/YYMMDD-<slug>/          ALL scratch from one run + RUN.md (NEW)
│   ├── backups/                     pre-edit copies of control files (NEW; Silverado's convention)
│   └── archive/YYMMDD-<slug>.zip    closed runs, one Drive item each (NEW)
└── 01 Model ... 13 AHJ              numbered tree - results and source documents only
```

### 3.2 The agent filing contract (goes into the Atlas block of every `AGENTS.md`)

1. Scratch - scripts, receipts, JSON, captures, check exports, before/after PNGs,
   saved web pages - goes in `.agent/runs/YYMMDD-<slug>/`. Nowhere else.
2. A run files a result in the numbered tree only when a person will read it: minutes,
   a code memo, a draft to send, an issued set. Named `YYMMDD_Title.md`, in the section
   its subject belongs to. Most runs file nothing there.
3. Tasks live in `tasks/TASKS.md`. A scoped list goes in `tasks/lists/` and is linked
   from TASKS.md. Never a task list in `11 Meetings`, `06`, `.agent/handoff` or the root.
4. Run log: `RUN.md` inside the run folder. PROJECT.md takes facts only - never a
   session log.
5. Backups of PROJECT.md, AGENTS.md, TASKS.md go to `.agent/backups/`.
6. Handoff: update `.agent/handoff/CURRENT.md`; dated `HANDOFF-*.md` only at a stopping
   point. No artefacts in `handoff/`.
7. Raw research captures go in a `_sources/` folder beside the report that cites them.
8. Unsent outgoing drafts go in `08 OUT/Drafts/`; move to the dated folder when sent.
9. New folders only through Atlas. No `tmp`, `QA`, `New folder`, `Agent Sessions`.
10. No tool caches on the drive (`.ruff_cache`, `__pycache__`): set
    `PYTHONDONTWRITEBYTECODE=1` / run tools from `.agent/runs/` with caches disabled.

### 3.3 `13 AHJ` - permitting authority section, seeded

```
13 AHJ/
├── AHJ-REGISTER.md                  one row per application, copied from the template
├── 01 Requirements & Pre-Application   checklists, submittal requirements, pre-app notes, blank forms
├── 02 Applications & Forms          completed forms, authorisations, fee receipts
├── 03 Submissions                   exactly what was filed: R0 YYMMDD, R1 YYMMDD ...
├── 04 Comments & Responses          plan-check comments in, response matrix out, by round
├── 05 Correspondence                letters, emails, records requests to and from agencies
└── 06 Permits & Inspections         issued permits, approved stamped sets, inspection cards, final/CofO
```

- Stage-first, not agency-first: the map has no free-text names, and most projects have
  one primary agency. Agency goes in the filename prefix (`PBES_`, `DOB_`, `BAAQMD_`) and
  the register's Agency column.
- Round folders `R0 YYMMDD` under 03 and 04 are dated instances - the same pattern as
  `04 Presentation\240815-1 Concept`. Atlas needs an "instance" child kind to generate
  them (Phase 1).
- `03 Submissions`, not "Submittals": `08 OUT/Submittals` keeps its construction meaning.
- Boundary with `06/Code`: what the code *says* stays in `06/Code` (Norma's
  `analysisDir`, unchanged). What *this agency asked for and what we sent* goes in 13 AHJ.
- `10 Legal/Permits` is retired by relocation into `13 AHJ/06 Permits & Inspections`.
- Number 13, not a renumber: inserting AHJ before `11 Meetings` would drift every
  project. `11`/`12`/`13` already break lifecycle order; the map is the index.

### 3.4 `06 Research & Existing Conditions` - fuller seed

Keep every existing child name verbatim (zero drift for existing projects). Add the
homes projects kept inventing. Unnumbered, as today.

| Child | Seed | Absorbs (from 1.6) |
|---|---|---|
| `RESEARCH-INDEX.md` (file) | yes | EVIDENCE-INDEX, 00-RESEARCH-PACKAGE, README |
| `Project Information` | yes | brief, intake, client program |
| `Site Review/Photos` | yes | |
| `Site Review/Ex CADs & PDF` | no | |
| `Site Review/Scans & Tours` | no | Virtual Tour, Matterport |
| `As-Builts & Record Drawings` | no | 1998 As-Builts, Reference Drawing Sets, CAD Deliverables |
| `Public Records` | yes | County Records, permit history, assessor maps |
| `Survey` | no | legal survey only |
| `Deed` | no | |
| `GIS & Maps` | yes | GIS, FEMA Map, Vicinity Map, Google Maps, aerials |
| `Zoning` | yes | |
| `Code` | yes (analysisDir) | |
| `Environmental & Hazards` | no | flood, fire hazard zone, soils, hazmat, air district |
| `Climate` | no | |
| `Products & Materials` | no | Materials, Cabinets, product data |
| `Costs & Bids` | no | proforma, estimates, contractor checks, comps |
| `Inspiration` | no | |

Inside any child: report `YYMMDD_Title.md` at the top, raw captures in `_sources/`.

### 3.5 Other map changes

- `10 Legal` becomes `seed: true` (5/7 use; invoices and the rendered timesheet land
  there). `10 Legal/Permits` is removed from children and relocated (3.3).
- `08 OUT/Drafts` added (unsent outgoing, 1.2).
- New relocations: `Agent Sessions`, `tmp`, `QA`, `*/Model Verification` ->
  `.agent/runs/`; `PROJECT.backup-*`, `*.bak-*` -> `.agent/backups/`;
  `07 IN/AHJ`, `07 IN/County`, `10 Legal/Permits` -> 13 AHJ children.
- `.ruff_cache`, `__pycache__` become doctor findings with a delete Offer.
- 03/04 stay seeded despite low use: an empty seeded section costs one item.

---

## 4. Implementation plan

Order matters: decisions, then the map and Atlas (so the new structure is generated, not
hand-made), then templates and skills, then migration one project at a time, then
enforcement.

### Phase 0 - Decide and record (1 session)

| # | Work | Done when |
|---|---|---|
| 0.1 | Tyler answers the open questions (section 5) | answers recorded |
| 0.2 | ADR 0011 - agent workspace and filing contract (3.1, 3.2) | accepted |
| 0.3 | ADR 0012 - `tasks/` register and template (3.1, Appendix A) | accepted |
| 0.4 | ADR 0013 - `13 AHJ` section (3.3) | accepted |
| 0.5 | CONTEXT.md terms: Task Register, Scoped List, Run, Run Folder, AHJ Register, Research Index, Instance Child | terms land |

### Phase 1 - Map v3.0 and Atlas 0.7.0

| # | Work | Files | Done when |
|---|---|---|---|
| 1.1 | Child entries may be objects: `{"name": "...", "seed": true}` or `{"name": "R{n} {YYMMDD}", "instance": true}`; plain strings still load | `core/mapfile.py`, tests | old map loads unchanged; new keys round-trip |
| 1.2 | `controlPlane` keys: `tasksDir`, `tasksFile`, `agentRunsDir`, `agentBackupsDir`, `agentArchiveDir`, `templatesDir`; template map `{"tasks/TASKS.md": "TASKS.md", "13 AHJ/AHJ-REGISTER.md": "AHJ-REGISTER.md", ...}` | `core/mapfile.py` | accessors default sensibly when absent |
| 1.3 | `new_project` seeds child folders and copies templates (create-only, never overwrite), substituting project name/address | `core/ops.py` | new project has `tasks/TASKS.md`, `13 AHJ/*`, seeded 06 children |
| 1.4 | Conform backfills the same, create-only, as a Plan with preview | `core/conform.py` | conform on a 2.2 project adds, never replaces |
| 1.5 | `find_empty_dirs` protects seeded children and the new control-plane dirs | `core/ops.py` | `clean` leaves them |
| 1.6 | AGENTS.md Atlas block: index rows for tasks, runs, AHJ register, research index + the filing contract (3.2) | `core/projectmd.py` | conform rewrites the block in place, project notes untouched |
| 1.7 | Doctor findings: machine files in numbered sections, tool caches, control-file backups at root, task-list names outside `tasks/` | `core/doctor.py`, File Rules below root (ticket 26) | each finding carries a move/delete Offer |
| 1.8 | Instance child generation in Add-Section (`R1 261002`) | `core/ops.py`, TUI | no free text typed |
| 1.9 | Map v3.0 written: 13 AHJ, 06 children, 08 OUT/Drafts, 10 Legal seed, relocations (3.5) | `_tools\architecture-map.json` | `atlas lint` clean |
| 1.10 | Retire `New-Project.ps1`/`.bat` and `Add-Section.ps1` to `_deprecated` (or teach them 1.1-1.3). Two writers with different seeds would reintroduce drift | `_tools\` | one writer |
| 1.11 | `uv run pytest` green; release 0.7.0; CI | `tools/atlas` | green |

### Phase 2 - Templates (on the drive, single source)

`G:\Shared drives\ARCHITECTURE\_tools\templates\` - Atlas copies from here, so Tyler
edits a template without an Atlas release.

| Template | Copied to | Source |
|---|---|---|
| `TASKS.md` | `tasks/TASKS.md` | Appendix A |
| `task-list.md` | `tasks/lists/YYMMDD-<slug>.md` (by agents, on demand) | Appendix B |
| `AHJ-REGISTER.md` | `13 AHJ/AHJ-REGISTER.md` | Appendix C |
| `RESEARCH-INDEX.md` | `06 .../RESEARCH-INDEX.md` | Appendix D, after Beitz Fire EVIDENCE-INDEX |
| `RUN.md` | `.agent/runs/<run>/RUN.md` (by agents) | Appendix E |

### Phase 3 - Skills, prompts and docs that tell agents where to write

| # | Work | Where |
|---|---|---|
| 3.1 | New `/tasks` skill: add, complete, hold, prune to archive - always in the template's shape | `plugins/09-project-dossier/skills/tasks/` |
| 3.2 | `/project-dossier`: PROJECT.md is facts only; "Open items" -> TASKS.md; session logs -> RUN.md | `plugins/09-project-dossier/skills/project-dossier/SKILL.md` |
| 3.3 | Cross-cutting rule `rules/agent-filing.md` = 3.2 verbatim | `rules/` |
| 3.4 | Prompt vault: "Close out this session" / "Resume this project" read and write `tasks/TASKS.md`, `.agent/handoff/CURRENT.md`, `.agent/runs/`; project notes keep headers and prompts, link to TASKS.md for the queue | `_tools\Architecture-Prompts\` |
| 3.5 | Drive README v1.4, `_tools\HOW-TO.md`, `folder-standard.md` | drive |
| 3.6 | `./scripts/lint.sh` green | repo |

### Phase 4 - Migrate the seven active projects (one at a time, pilot first)

Each project is one Atlas Plan: preview, Tyler approves, apply, undo available. Moves
use a Move Manifest written to `.agent/MOVES.md` so old paths in dated reports still
resolve. Guard: nothing referenced by a Revit model (CAD links, point clouds, families)
moves.

| Order | Project | Main moves |
|---|---|---|
| 1 (pilot) | Pestoni | `08 OUT/Submittal`, `Resubmittal`, `07 IN/County`, `10 Legal/Permits` -> 13 AHJ; JSON guards -> `.agent/runs/` |
| 2 | Monticello | `07 IN/Napa County PBES` -> 13 AHJ/04 by round; V1-V4 Submission copies -> 13 AHJ/03; saved web pages -> `.agent/runs/` or delete; `_Duplicates` resolved |
| 3 | Monte Vista | PROJECT.md open items -> TASKS.md (small) |
| 4 | Beitz Fire | `.agent/handoff` scratch -> `.agent/runs/` (keep CURRENT + HANDOFF-*); Code raw captures -> `Code/_sources/`; County Records -> Public Records; GIS/Survey/Vicinity/Google Maps -> GIS & Maps; OPEN-ITEMS.md -> TASKS.md holds; EVIDENCE-INDEX -> RESEARCH-INDEX; county forms and question list -> 13 AHJ; caches deleted |
| 5 | Silverado | Model Verification -> `.agent/runs/` (findings worth keeping stay filed); TASKS-*, checklists -> `tasks/lists/`; GIS and Maps -> GIS & Maps |
| 6 | 64th Lane | `tmp/`, `QA/` -> `.agent/runs/`; `12 CA` audit reports -> `.agent/runs/` (true CA items stay); action lists and audit task lists -> TASKS.md + `tasks/lists/`; PROJECT.md "Current issue" log -> run logs, "Open items" -> TASKS.md |
| 7 | 211 Centre | `11 Meetings/Agent Sessions` (3,317) -> `.agent/runs/`; root PROJECT backups -> `.agent/backups/`; TPA brief -> 13 AHJ; PROJECT.md log split as above |

Per project, done when: Atlas doctor clean; TASKS.md is the only open list and holds
every open item from the old lists (checked off line by line); PROJECT.md under ~400
lines; no machine files in the numbered tree; Revit opens with no missing links.

Expected effect, from 1.1: the numbered trees of the four agent-heavy projects drop
from ~9,100 files to ~2,100 (7,050 machine files leave; agent-run Markdown leaves too).

### Phase 5 - Keep it clean

| # | Work | Done when |
|---|---|---|
| 5.1 | `atlas runs sweep`: zips runs closed more than 14 days and not referenced from TASKS.md or CURRENT.md into `.agent/archive/<run>.zip` | dry run lists, apply zips, undo restores |
| 5.2 | Drive item report: items per project, per layer, against the 400k cap | `atlas doctor --drive` prints it |
| 5.3 | Monthly: `/tasks prune` moves Done older than 30 days to `tasks/archive/` | TASKS.md stays one screen of open work |

---

## 5. Open questions for Tyler

| # | Question | Recommended default |
|---|---|---|
| Q1 | Tasks folder name and place: `tasks/` beside `decisions/` (control plane, unnumbered) or a numbered `00 Tasks` | `tasks/` - same family as `decisions/`, and the map rule is that control-plane names never take numbers |
| Q2 | Prompt-vault task queues: move into each project's TASKS.md, or keep the vault as the queue | Move. Vault keeps headers and prompts; one live list per project |
| Q3 | Closed agent runs: zip after 14 days, or delete | Zip. One item per run, recoverable; delete only after the project is archived |
| Q4 | AHJ section: stage-first (3.3) or agency-first folders | Stage-first now; agency-first only if a project carries three or more agencies routinely |
| Q5 | Retire the PS1 tools or teach them the new seed | Retire. Atlas is the only writer |

---

## Appendix A - `tasks/TASKS.md` template

```markdown
---
project: "<project folder>"
updated: YYYY-MM-DD
---

# Tasks - <Project Name>

The one live task list for this project. Tyler and agents edit it in place.
Facts -> `PROJECT.md`. Why -> `decisions/`. Scoped lists -> `tasks/lists/`, linked below.

**Lanes:** `TYLER` decision, call, sign-off, sync · `AGENT` can run unattended ·
`MODEL` needs a live Revit session · `WAIT` someone outside (named in the task)

**Rules:** IDs never reused. One line per task; detail indented below it. Link the
source, do not paste it. Mark done only with evidence (file, export, receipt).

## Now

- [ ] T-001 `TYLER` <verb-first task> - done when <check>. From <link>.

## Next

- [ ] T-002 `AGENT` <task> - done when <check>.

## Waiting on others

| ID | Who | What | Asked | Chase by | Unblocks |
|---|---|---|---|---|---|

## Holds

| ID | Hold | Why | Evidence that clears it | Blocks |
|---|---|---|---|---|

## Scoped lists

- [YYMMDD-<slug>](lists/YYMMDD-<slug>.md) - <one line> - T-0NN

## Done

Newest first. Older than 30 days -> `tasks/archive/`.

- [x] T-000 YYYY-MM-DD <task> - <evidence link>
```

## Appendix B - `tasks/lists/YYMMDD-<slug>.md` scoped list template

```markdown
---
parent: T-0NN
created: YYYY-MM-DD
status: open | closed
---

# <Scope> - <date>

Parent task: T-0NN in `tasks/TASKS.md`. Close this list by moving it to `tasks/archive/`
and checking T-0NN off.

## Brief for the agent that picks this up

    ROOT: <absolute project path>
    TASK: <one line>
    READ: AGENTS.md, PROJECT.md, <only task-relevant sources>
    WRITE: scratch to .agent/runs/YYMMDD-<slug>/; results per AGENTS.md filing rules
    STOP AT: <holds>

## Items

- [ ] L-01 `AGENT` <item> - done when <check>
```

## Appendix C - `13 AHJ/AHJ-REGISTER.md` template

```markdown
# AHJ register - <Project Name>

One row per application. Files: `01`-`06` beside this register.

| Agency | Application / permit # | Type | Status | Submitted | Last round | Next action | Owner |
|---|---|---|---|---|---|---|---|

**Status words:** researching · preparing · submitted · in review · comments · resubmitted · approved · issued · inspections · finaled · withdrawn

## Contacts

| Agency | Role | Name | Email / phone | Portal |
|---|---|---|---|---|
```

## Appendix D - `06 .../RESEARCH-INDEX.md` template

```markdown
# Research index - <Project Name>

Every source an agent or person may rely on. Add a row when a source arrives.

| Topic | Source | From | Date | Authority | Path |
|---|---|---|---|---|---|

**Authority:** `official` agency-issued · `record` recorded/filed document ·
`professional` stamped/consultant · `client` supplied by client · `derived` our
analysis · `reference` public/non-authoritative (GIS, aerials, web)
```

## Appendix E - `.agent/runs/<run>/RUN.md` template

```markdown
# Run YYMMDD-<slug>

- Task: T-0NN
- Agent / model:
- Started / ended:
- Result filed: <absolute path, or "none">
- Tasks touched: T-0NN done, T-0NN added
- Open state left behind: <locks, unsynced model, held items>
```
