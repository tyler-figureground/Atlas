# Project folder structures: the next robustness and usefulness plan

Date: 2026-10-07
Scope: `G:\Shared drives\ARCHITECTURE` project structure, its control plane, the
reference-set system on `LIBRARY - Reference`, and the Atlas tooling that enforces both.
Method: re-read of every settled research report and ADR 0011-0017, the Atlas console
map and open tickets, plus a measured spot-check of the live drives (map v3.5, Atlas
0.11.2 deployed, three active projects and the Reference Sets root inspected).

This plan covers only what is **not yet done**. Everything already decided or shipped is
listed in section 1 so nothing gets re-opened.

---

## 1. Already settled - do not re-litigate

Shipped and verified on the drive today:

- Three-layer project structure: control plane (root files, `decisions/`, `00 Tasks/`,
  `.agent/`) vs numbered tree `01`-`13` (ADR 0011-0013, map v3.x). Active projects carry
  `00 Tasks/TASKS.md` + `TYLER.md` + `Lists/` + `Archive/`, `13 AHJ` stage-first children,
  and the fuller `06` seed.
- Two task files - production `TASKS.md` (lanes `AGENT`/`MODEL`/`DECISION`/`WAIT`, claim
  protocol) and Tyler's `TYLER.md` (Y-NNN, agents add-only) - ADR 0016. `/tasks`,
  `/meeting-closeout`, `/project-dossier`, `/decision` skills exist in
  `plugins/09-project-dossier/skills/`.
- `atlas runs` (zip closed runs), `atlas tyler` + `_tools\TYLER-TODAY.md` digest,
  `atlas refs check` leak gate + Dispatcher post-write hook, `atlas tree`, `atlas pdf`.
- Reference Sets root with 8 sets: Code Analysis, Meeting Minutes, G-Series, Floor Plans,
  Schedules, RCPs, Details, Elevations - each with E1-E3 exemplars and near-miss or
  redline pair. Drawing cards cite S+V rule ids. Pilot eval: with-set preferred 5/5,
  edits to Tyler-ready -38% (ADR 0015, evals folder on the library drive).
- Baseline agent rules classified into four kinds with Revit, drawing and code sections
  (ADR 0017, Atlas 0.11.x block in every mapped project's AGENTS.md).
- File Rules at project root (ADR 0009, ticket 25); tree repairs, undo, Move Manifests
  (ADR 0006-0008).

Open by design (tracked elsewhere, not re-decided here): Pyvoid owns all drawing
standards and sheet checks (#2888, #769/#770, #3095); this side supplies evidence,
fixtures and reference sets that cite rule ids.

## 2. Measured gaps (what this plan closes)

| # | Gap | Evidence |
|---|---|---|
| G1 | ~~All 8 reference sets are `status: candidate`.~~ Corrected 2026-10-07: Code Analysis and Meeting Minutes are already `approved` (2026-10-05). Six candidates remain: G-Series (carries Tyler's own "card stays candidate" ruling - approving reverses it), Floor Plans, Schedules (no S+V schedule standard exists), RCPs (E2 predates the Round 2 fix; card says re-export), Details, Elevations | Review Pack 2026-10-07 |
| G2 | No `atlas refs doctor` / `nominate` / `promote` / `retire`; index `README.md` is hand-maintained; no stale flags | `atlas refs --help` shows only `check` |
| G3 | Text-deliverable types have no sets: decision-record, zoning-memo, client-email, client-brief, research-report, agency-letter, ahj-register, presentation-deck, cd-set, control files (BRIEF/PROJECT/TASKS) | Reference Sets root listing |
| G4 | Gap types with zero studio candidates still empty: specs, RFI, transmittal, field report, punch list, submittal review, comment-response letter; `_tools\New+ Templates\` folders still empty | reference-sets.md Phase 6 |
| G5 | Filing contract is unenforced below project root: File Rules reach root only (ticket 26 open); no doctor finding for machine files in numbered sections, over-long paths, or deep unreadable folders | `.scratch/atlas-console` tickets 26, fog list |
| G6 | No drive item-budget report against the 400k shared-drive cap (folder report Phase 5.2) | `atlas doctor` has counts, no budget view |
| G7 | Tyler's judge-calibration sample from the pilot eval never done; sets can't graduate on evidence alone | reference-sets.md Phase 3.3 |
| G8 | Legacy and unmapped folders on the drive root (`103 Mosco`, `389 Bushwick Ave`, `ADNY LL97`, `242924...Dekalb`, `250622...Huckleberry`, `250828...Coleman`, `_Archived Projects`) have no stated disposition: conform, freeze, or archive | drive root listing; map has no per-project overrides |
| G9 | Atlas capability frontier parked: global search (08), dossier panel (09), Drive API read path (11); TUI focus-legibility fog item | console map open tickets |
| G10 | No measurement loop for drawings: rounds-to-acceptance baseline (r4-r38, 47 drafts) recorded but not tracked monthly | drawing-production report Phase F |
| G11 | Rituals exist as commands but not as a calendar: `atlas runs` sweep, `/tasks prune`, refs review, Tyler digest | commands exist; no schedule |

## 3. Implementation plan

Order: approvals and enforcement first (cheap, protects everything else), then content
expansion, then capability. Each phase has a done-test. Atlas execution items graduate
into `.scratch/atlas-console/issues/` tickets per the console map's convention.

### Phase 0 - Approvals and dispositions (one sitting with Tyler, ~1 h)

| # | Work | Done when |
|---|---|---|
| 0.1 | Tyler reviews the 8 candidate sets in batches (Code Analysis + Meeting Minutes + G-Series first - the measured pilots; then the 5 drawing sets). Agents pre-stage: card diffs since pilot, eval RESULTS.md summary per set | `status: approved` + `reviewed:` bumped on approved cards; corrections filed as Known issues or near-misses same sitting |
| 0.2 | ~~Tyler grades the pilot calibration sample~~ **Declined 2026-10-07 (Tyler): trusts the LLM judge as-is.** The judge is not unanchored - his 2026-10-05 grading of 4 pilot drafts already calibrates it and surfaced the standing caveat: judges undercount real edits ~3x, so judge scores are comparative signals, not absolute bars. Calibration Sample folder stays filed on the drive as the ready-made instrument if trust ever needs re-checking (e.g. after a model change) | Closed - no action |
| 0.3 | Disposition per unmapped root folder (G8). **Decided 2026-10-07 (Tyler):** conform them anyway - live projects get the full migration; archive everything dormant EXCEPT `250828_1757 Coleman A-Rental`, which stays on the root and conforms. Dormant = 103 Mosco, 389 Bushwick Ave, ADNY LL97, 242924 Dekalb, 250622 Huckleberry; these move under `_Archived Projects` via Atlas Plans | Every root folder is mapped, conformed, or archived |
| 0.4 | Answer open questions (section 5) | Answers recorded here |

### Phase 1 - Enforcement and drive health (Atlas 0.12.0, ~1 week agent)

| # | Work | Done when |
|---|---|---|
| 1.1 | `atlas refs doctor`: card front matter valid; exemplars and NOTES exist; every NOTES has a leak list; card < 150 lines; no `.lnk`; `next_review` passed -> stale flag; sets listed with problems. `--json` per ADR 0008 | Runs clean against all 8 sets; CI test on a fixture set |
| 1.2 | `atlas refs` index generation: README contents block rebuilt from card front matter between markers (library `atlas:contents` pattern) | Hand-edit between markers is reproduced byte-for-byte by the generator |
| 1.3 | Ticket 26 (File Rules below the root) grilled and built: the filing contract's machine-file rules (`*.json`/`*.png`/`*.log` receipts in numbered sections -> SWEEP offer to `.agent/runs/`) become map rules, not prose | Doctor finding + conform Offer on a fixture; no false positives on the 7 active projects' current state |
| 1.4 | Doctor finding: paths over MAX_PATH warn even when nothing is being moved (fog item) | Finding lists the two known live cases from the latency report plus any new |
| 1.5 | Doctor deep-unreadable check: one enumeration per project section top (not a walk) so an unreadable folder nobody opened still surfaces | Finding reproduces on a fixture; cost measured on the live drive |
| 1.6 | Drive item budget (G6): `atlas doctor --json` gains items-per-project-per-layer and total vs the 400k cap; printed in the console project list header | Number matches a counted baseline within noise; visible without flags |
| 1.7 | Confirm `Atlas.bat` pins the 0.12.0 wheel, `_tools\HOW-TO.md` current (staff redeploy step from the console map, repeated each release) | Fresh launch on a staff machine reports 0.12.0 |
| 1.8 | `uv run pytest` green; release 0.12.0; CHANGELOG | Green |

### Phase 2 - Reference set expansion (2-3 weeks agent, ~3 h Tyler spread out)

Text types first - highest frequency, strongest candidates already inventoried
(reference-sets.md section 1.9 table). Drawing sets pause behind Pyvoid rule-id delivery
(Phase 3).

| # | Work | Done when |
|---|---|---|
| 2.1 | Build sets in batches of 3, in this order: (a) `decision-record`, `meeting-adjacent client-email`, `client-brief`; (b) `zoning-memo`, `research-report`, `agency-letter`; (c) `ahj-register`, `presentation-deck`, `cd-set` (cartoon set first). Each: card from template, 2-3 diverse exemplars frozen, leak lists, one near-miss, `status: candidate` | Cards on drive; `atlas refs doctor` clean |
| 2.2 | Control-file sets (`brief-md`, `project-md`, `tasks-md`): skeleton-only sets (card + Atlas template as skeleton + checklist) - exemplars measured unneeded for template-driven files; drop to skeleton-first per the expertise-reversal evidence | 3 skeleton sets approved |
| 2.3 | Tyler approves each batch (the 0.1 rhythm) | `status: approved` |
| 2.4 | `## Reference` step added to each newly-covered deliverable skill; `scripts/lint.sh` gains the rule: a deliverable skill with no Reference step fails lint | Lint green with rule active |
| 2.5 | Fictional sanitized `examples/` bundled in the public skills for outside users (repo is public; studio exemplars never enter it) | Each deliverable skill has an example; leak check against studio exemplars passes on the fictional content |
| 2.6 | Gap types (G4): as the studio next issues a spec, RFI, transmittal, field report, punch list, submittal review or comment-response, that one is made carefully, Tyler-reviewed, frozen as E1; until then the card ships with the skeleton plus the third-party precedent marked precedent-only. Skeletons land in `_tools\New+ Templates\` at the same time | `_tools\New+ Templates\` Meeting/Transmittal/Site Visit folders hold skeletons; each gap type has at minimum card + skeleton |
| 2.7 | Junior onboarding: one-page note in `00 Office Standards and Administration` (where sets live, the first-use crit, the "where mine differs" three lines, the tiers); first 3 crits done with Tyler | Note filed; 3 "where mine differs" notes collected |

### Phase 3 - Drawing QA follow-through and measurement (ongoing, gated on Pyvoid)

| # | Work | Done when |
|---|---|---|
| 3.1 | Before each drawing set graduates past candidate, re-read Pyvoid #2888 (print critic), #770 (VS-006), #3095 (model compliance). **Amended 2026-10-07 (Tyler): approval is Tyler's review alone - no Pyvoid gate.** Cited rule ids that don't exist yet are named in the card's Known issues until Pyvoid ships them | Each approved card reviewed by Tyler; dangling rule ids listed under Known issues |
| 3.2 | Keep feeding redline pairs from live reviews (next: MPR A100 revision series, any 64L v10+ QA round) into R-folders; each redline mark tagged with the rule it violates, doubling as Pyvoid's regression fixture | >= 1 new pair per active CD project per month |
| 3.3 | Measurement loop (G10): rounds-to-acceptance and defects-reaching-Tyler per sheet, logged per drawing run in the run receipt; monthly one-page trend vs the recorded baseline (MPR r4-r38; BZ 47 drafts) | First monthly report filed; trend visible by month 2 |
| 3.4 | Open S+V conflicts on #769 (standard-header naming, isolated eighth-inch precision) chased to a Tyler ruling; baseline block updated via Atlas release + conform. **Progress 2026-10-07: the three Floor Plans conflicts settled by Tyler in the review-pack pass (clouds in view; witness lines pulled back off elements; numbering bottom-up then left - all toward the existing standards), recorded on the card as SETTLED and posted to #769.** Standard-header naming and eighth-inch precision remain open | Conflicts closed or explicitly deferred by Tyler |

### Phase 4 - Atlas capability frontier (as phases 1-3 free capacity)

Priority order by studio leverage. Each is a grilling ticket first, per the console map.

| # | Work | Done when |
|---|---|---|
| 4.1 | Ticket 08 - global search scope, then build. Full-drive walk measured at 4.24 s, so cost is no objection; the question is what the one-keystroke search searches (filenames? Markdown content? PDFs?) | Ticket closed with a scope; search shipped with CLI parity |
| 4.2 | Ticket 09 - dossier panel: PROJECT.md rendered as a Companion Mode; facts contract (ADR 0001) stays the parser | PROJECT.md readable in-app; stale facts visible |
| 4.3 | Ticket 26 follow-on: if below-root rules prove out (1.3), extend to content filters (ticket 28 unpark) only with a real drive example | The 27/28 unpark bar met or re-parked |
| 4.4 | Ticket 11 - Drive API read path: ~~grill whether Atlas reads through the Drive API instead of the mount. Only worth it if 1.5/1.6 measurements show mount enumeration hurting~~ **Promoted 2026-10-07 by Q1: PDF-text search needs an index, and the mount makes one expensive. Grill the Drive API read path as the search prerequisite** | Decision recorded; indexing design follows if API path clears |
| 4.5 | Focus legibility everywhere (fog): modals, filter input, search overlay show which Region holds focus without moving the cursor; measured at the six known widths | Headless renders at 179/153/120/87/77/46 cols assert focus is legible |

### Phase 5 - Legacy disposition execution (after 0.3)

**Measured 2026-10-07: every legacy project already conforms** (`atlas conform`
dry-run clean on Coleman, Dekalb, Huckleberry, 103 Mosco, 389 Bushwick, ADNY LL97)
- earlier `conform --all` runs covered them. Phase 5 is therefore archive moves
only, gated on ticket 29 (Atlas has no whole-project move verb). Per the 0.3
decision: 103 Mosco, 389 Bushwick Ave, ADNY LL97, 242924 Dekalb and 250622
Huckleberry move under `_Archived Projects`; Coleman stays. One Atlas Plan per
project, Tyler approves each, Move Manifest per project, undo restores. Done when
the drive root holds only active projects, `_Archived Projects`, `_tools` and the
two `00` folders.

## 4. Standing rituals (the calendar that keeps it clean - G11)

| Cadence | Ritual | Mechanism that exists | What to add |
|---|---|---|---|
| Daily | Tyler digest | `Tyler-Digest.bat` -> `_tools\TYLER-TODAY.md` | Nothing - habit only |
| Weekly | Sweep closed agent runs | `atlas runs` (dry-run default) | A scheduled task or a line in the Monday startup prompt; apply after preview |
| Monthly | `/tasks prune` per active project (Done > 30 days -> Archive); drawing metrics report (3.3) | `/tasks` skill | Calendar reminder; report filed to the project's `11 Meetings` or office admin |
| Quarterly | `atlas refs doctor` glance; stale sets triaged | 1.1 | Calendar reminder |
| Triggered | Code edition adopted / skill rule changed -> affected sets `next_review: now`; model or skill change -> holdout evals re-run | Eval harness from the pilot | The trigger line added to `agents-rules.md` release checklist |
| Annually | Two-year-unreviewed sets retired, with the library's own sweep | Library policy | Joint calendar entry |

## 5. Open questions for Tyler

| # | Question | Recommended default |
|---|---|---|
| Q1 | ~~Global search scope (ticket 08)~~ **Answered 2026-10-07: everything, including PDF text.** This pulls ticket 11 (Drive API read path) forward - it becomes a prerequisite investigation for content search, not an optional grill | - |
| Q2 | ~~Legacy Coleman/Huckleberry/Dekalb: conform or freeze?~~ **Answered 2026-10-07: conform anyway; archive all dormant projects except Coleman (stays live, conforms)** | - |
| Q3 | `_Archived Projects`: leave outside the map forever, or map read-only so search (4.1) can reach them | Map read-only once search exists; leave alone until then |
| Q4 | ~~Drawing-set approval gate: wait for Pyvoid rule ids (3.1)?~~ **Answered 2026-10-07: approve on Tyler's review alone; dangling rule ids go in Known issues** | - |
| Q5 | ~~Automate the weekly sweep and monthly prune?~~ **Default adopted 2026-10-07: human-triggered for one quarter, automate after the dry-runs stay boring** | - |

## 6. Risks

| Risk | Mitigation |
|---|---|
| Tyler approval becomes the bottleneck (8 candidate sets now, 9+ more coming) | Batches of 3, agent-pre-staged diffs; skeleton-only sets where exemplars don't measure out (2.2) |
| Below-root File Rules false-positive on legitimate project files (1.3) | Fixture-first build; dry-run against all 7 active projects before any apply; Offers, never silent moves |
| Reference sets go stale silently | `next_review` + stale flags in `atlas refs doctor` + quarterly ritual; retire, never delete |
| Pyvoid stalls drawing-set graduation | 3.4 escalation path; force-approve valve in Q4; text expansion (Phase 2) is not gated on Pyvoid |
| Ritual fatigue - calendar entries die | Every ritual maps to an existing command with a dry-run default; automate only after a boring quarter (Q5) |
| Drive item cap creep from new run volume | 1.6 budget line in the console header makes it a number Tyler sees, not a surprise |

---

## Summary of what changes for an agent working a project

Nothing about where things go - the three-layer structure and filing contract are
settled and stay. What changes: the contract gets *teeth* below the project root
(1.3-1.5), every deliverable type gets a card worth reading (Phase 2), drawing cards
only cite checks that exist (Phase 3), and the drive's health becomes a visible number
instead of a periodic surprise (1.6, Phase 5).

---

## Progress log

**2026-10-07**
- Phase 0.3 decided (Tyler): conform anyway; archive all dormant projects except
  Coleman. Measured: every legacy project already conforms -> Phase 5 is archive
  moves only, gated on new ticket 29 (Atlas has no whole-project move verb).
- Q1 answered: global search includes PDF text -> ticket 11 (Drive API read path)
  promoted to search prerequisite. Q4 answered: set approval is Tyler's review
  alone, no Pyvoid gate. Q5 default adopted (human-triggered rituals for one
  quarter).
- Phase 1.1/1.2 in flight (subagent sa-1): `atlas refs doctor` + index generation,
  TDD, fixture-based.
- Phase 0.1/0.2 pre-staging in flight (subagent sa-2): Review Pack for the 8
  candidate sets + blind calibration sample, on the library drive.
- Tickets filed: 29 (archive a project), 30 (agent config files at root -
  `.mcp.json`/`.pi` UNFILED on MPR and Beitz).
- Health baseline: `atlas doctor` green except the two UNFILED configs; `atlas runs
  --all` shows 2 closed runs to zip; `atlas tyler` digest works (51 errands / 40
  DECISION blockers - dormant projects add placeholder noise that archiving will
  remove).

**2026-10-07 (late) - landed**
- `atlas refs doctor` + `atlas refs index` built (subagent sa-1): 21 new tests,
  fixture-only; real drive reads 0 problems across 8 sets. `refs index` needs
  `atlas:contents` markers wrapped around the README's Sets section - fold into the
  post-approval write. New term recorded in CONTEXT.md.
- Review Pack + blind Calibration Sample written to the library drive (sa-2).
  Correction: Tyler already graded 4 of 10 pilot drafts on 2026-10-05
  (TYLER-GRADING.md); the sample uses the 5 ungraded + 1 replication draft.
- **Found and fixed a live template-override failure**: a persistent machine
  `ATLAS_TEMPLATES` env var pointed Atlas at a stale pre-reconciliation drive copy
  of `agents-rules.md`, so the ADR 0017 Pyvoid reconciliation (one writer per
  model, workset completeness) was in no project's AGENTS.md despite releases
  0.11.0-0.11.2. Also broke 5 repo tests locally (CI green - no override there).
  Fixed: env var removed (User level), drive copy retired to
  `_tools/_deprecated/templates-ATLAS_TEMPLATES-override-20261007/`, conftest now
  isolates the suite from the override, and `conform --all --apply --only backfill`
  rewrote the Atlas block in all 15 projects (verified: rule present). Suite: 913
  passed.
- Ticket collision reconciled with a parallel session that shipped ticket 29
  (dotfiles `tolerated` map list, code + tests in tree): my archive ticket renumbered
  to 30, my duplicate dotfiles ticket deleted.
- Drive map v3.8: `tolerated: [".mcp.json", ".pi"]` added (ticket 29's map half);
  version field caught up with its own v3.6/v3.7 notes. `atlas doctor`: 15/15
  conform, 0 unfiled, 0 drift.
- Pending from the parallel session's ticket 29: ~~an Atlas release (>= 0.11.3) so the
  deployed wheel parses `tolerated`; until then staff 0.11.2 ignores the key (safe)
  but still flags the dotfiles.~~ Done same day: parallel session landed ADR 0018,
  released and deployed Atlas 0.12.0 (refs doctor/index + tolerated), launcher
  repinned on the drive and in the repo. Staff-redeploy fog item closed.

**2026-10-07 (later still)**
- Ticket 26 grilled closed (sa-4): below-root rules become an opt-in `receiptRules`
  class - findings not Filing States, no content filters at depth, deep pass only
  (`doctor --deep PROJECT`), sweeps target only the agent workspace. Build ticket 31.
- Ticket 30 grilled closed (sa-4): archiving is a new drive-scoped ARCHIVE/UNARCHIVE
  action kind, modal-always confirm, index row stamped `archived` not removed,
  archived projects invisible to doctor/console. Build ticket 32 - unblocks Phase 5.
  ADR amendments drafted in the tickets (0009, 0006, new 0019), not yet accepted.
- Phase 2.4/2.5 done (sa-3): all 17 deliverable skills carry a `## Reference` step;
  lint check 10 enforces it; 15 fictional examples bundled; the leak gate caught a
  real collision ("Bakery") and the fictional project was renamed. 0 leak hits.
- Junior quick start filed at `Reference Sets - Junior Quick Start.md` (2.7 note).

**2026-10-07 (review processed)**
- Tyler reviewed all 8 sets in the Review Pack. APPROVED: G-Series (reversing his
  2026-10-05 "stays candidate" ruling), Schedules, RCPs, Details, Elevations;
  Code Analysis + Meeting Minutes reconfirmed. Front matter flipped, README table
  and v1.3 row updated, `atlas refs doctor` clean (7 approved, 1 candidate).
- Floor Plans: NEEDS WORK - stays candidate, but Tyler's notes settled all three
  Tyler-vs-S+V conflicts (clouds in view; witness lines pulled back so they never
  cross building elements; view numbering bottom-up then left). Card updated,
  rulings posted to Pyvoid #769 (comment 6087898819). Remaining blocker for its
  approval: no issued, clean plan exemplar exists yet (card's own Known issue).
- Calibration sample declined by Tyler 2026-10-07 (trusts the judge; his
  2026-10-05 grading of 4 pilot drafts already anchors it). Folder stays filed as
  the ready-made instrument.
- Weekly ritual first run: `atlas runs` zipped 64th Lane's `legacy-qa` and
  `legacy-tmp` runs - both archived, run folders gone, zero closed runs remain.
  **Cost datum:** 1,386 files took 48 min to zip over Drive File Stream - big-run
  sweeps are a background job, not an interactive one; feed into Q5's automation
  timing.

**2026-10-08/09 - the big push (Tyler: "proceed, don't stop until all phases are done")**
- Phase 2.1 batches (b) and (c) + 2.2 + 2.6 all drafted: 19 new candidate sets
  total across the day (batches a/b/c + 7 gap-type cards + 3 control-file
  skeleton sets). **`atlas refs doctor`: 0 problems across 27 sets.** Every set
  awaits Tyler's batch review (2.3).
- Tickets 08/09/11 grilled closed: search = names now (background walk) +
  content via a per-machine index (never on the drive); dossier = read-only
  facts Companion Mode + `atlas dossier`; Drive API = no build (filesystem-only
  is now a standing constraint with a written reversal trigger). Build tickets
  33-36 opened.
- Ticket 31 built (sa-7): `receiptRules`, `doctor --deep`, `conform --deep`,
  ADR 0009 amendment. 963 tests.
- Ticket 32 built (sa-11 died mid-run on the model's 5-hour quota; finished
  in-session): `atlas archive`/`unarchive`, ADR 0019, ADR 0006 amendment. 1021
  tests.
- **Phase 5 executed:** 103 Mosco, 389 Bushwick, ADNY LL97, Dekalb, Huckleberry
  archived with manifests logged to `_tools\logs\archive-20261009\`; Coleman
  excepted per Tyler. Drive root = active projects only; doctor 10/10 conform.
  Note: legacy projects had no `_Project Index.md` rows - the no-row case,
  nothing stamped (ADR 0019).
- Baseline template corrected to the 2026-10-07 settlements (clouds in view;
  witness lines pulled back) - 0.11.1 had shipped the reversed rulings; all
  project AGENTS.md blocks need one more conform pass after 0.13.0 deploy.
- **Atlas 0.13.0 released and deployed** (wheel + sha256, launchers repinned,
  backup in `_tools\logs\atlas-0.13.0-deploy-20261011-114830`, HOW-TO archive
  section, `Atlas.bat --version` verified 0.13.0, lint clean).
- New+ Templates filled (meeting, site visit, transmittal, presentation
  skeletons in the PowerToys `$YY$MM$DD_*` folders).
- NOT done (blocked on the subagent model's 5-hour quota, then ready): tickets
  33-36 (search overlay, content index, dossier mode), plan 1.4-1.6 (MAX_PATH
  doctor finding, deep unreadable, drive item budget), refs index richer
  columns (Entity/Exemplars/Skill) before markers go into the README.

**2026-10-09 (quota reset) - the queue cleared**
- Tickets 33, 34, 35, 36 all built and closed: session Name Index + Search
  Overlay on `g` + `atlas search`; per-machine Content Index (PDF text +
  Markdown, path+size+mtime keyed, background resumable builds, ADR 0020);
  content matches in the overlay and `--content`; DOSSIER Companion Mode +
  `atlas dossier`. **Console map open tickets: zero.** 1119 tests.
- Plan 1.4-1.6 built: over-long path finding (dirs 259, files 260, warning
  never a status change), deep unreadable as its own finding, drive item
  budget vs the 400k cap behind `--deep`. `core/deep.py` generalizes the walk.
- refs index now emits Entity/Exemplars/Skill; the real README's Sets table is
  wrapped in `atlas:contents` markers and `atlas refs index --apply` ran -
  regenerate is byte-idempotent. Exemplars cell uses folder descriptors after
  NOTES prose proved to clip mid-sentence.
- **Atlas 0.14.0 released and deployed** (backup `_tools\logs\atlas-0.14.0-deploy-
  20261011-155213`, `Atlas.bat --version` verified, HOW-TO search/dossier
  section, lint clean). Repo pushed to origin/main.
- **Human-facing gallery (Tyler 2026-10-09: "I won't navigate a README, let alone
  an intern"): `atlas refs gallery` generates a self-contained `Reference Sets.html`
  beside the README - 27 tiles in 7 lifecycle bands, status badges as word+colour,
  filter box, exemplar/PDF direct links, thumbnails from drawing sets' Pages PNGs,
  junior quick-start link. Generated from the same front matter as the README map,
  so the two can never drift. HOW-TO "Look at a good one first" points at it.
  Atlas 0.16.0 deployed. The README stays the agent/maintainer index.
- **Reference Sets renumbered with lifecycle-order prefixes** (Tyler 2026-10-09:
  the flat 27-folder list was overwhelming): 01 Research Reports -> 03 Code
  Analysis, 10-16 client/control/permitting, 19-26 drawings, 40-45
  construction, 90-92 control files. Numbers never reused, gaps deliberate;
  flat, no subfolders (library shallowness rule). 12 in-card cross-references
  updated; README table regenerates in prefix order (v1.8); refs doctor clean;
  leak check verified post-rename.
- Known pre-existing: 2 test_project_data.py rename tests fail on clean HEAD;
  post-output-metadata hook times out on this machine (environmental).

**2026-10-13 - the remaining agent-buildable items landed (Atlas 0.17.0)**
- Console keys for the CLI-only verbs: `A` archive (modal always, per ADR 0019),
  `U` unarchive via picker, `D` deep pass into a new DEEP Companion mode.
- Focus Rule shipped: the focused Region carries a heavy frame, unfocused a
  muted rail - weight, not hue; every modal, input and overlay follows. The
  console map's last fog item is cleared; open tickets remain zero.
- Flakes fixed at the root: transient Windows rename locks (WinError 5/32) retry
  with bounded backoff; the follow-timer race (NoMatches at teardown /
  ScreenStackError) is guarded at both vectors. 1186 tests; four consecutive
  clean full-suite runs.
- Drawing QA measurement loop live (Phase 3.3): RUN.md template measurement
  block, baseline record and monthly report shell in Library
  Administration/Evals; aggregation is manual until tooled.
- 0.17.0 deployed to the drive (backup `_tools\logs\atlas-0.17.0-deploy-*`,
  launcher verified) and the repo pushed.
- Recurring environment annoyance recorded: stale `.git/index.lock` files appear
  after long test runs (idle VS Code git watcher nearby); removed three times
  this session. If it recurs, the watcher is the suspect.
- 2026-10-09: README visual redesign landed (Phase 2 of the ergonomics plan):
  `refs index` now emits a Mermaid band map plus per-band 3-column tables from
  card front matter; applied to the real Reference Sets README (v1.9).
- 2026-10-09: ergonomics plan Phase 3+4 - 27 card top strips, HOW-TO visual map.
- 2026-10-09: drawing QA measurement loop - RUN template measurement block,
  baseline record, monthly report shell (Phase 3.3; aggregation manual until tooled).

**2026-10-08 - Phase 2.1 batch (a) drafted (sa-5)**
- Three new candidate sets, `atlas refs doctor` clean across all 11 sets:
  `decision-record` (E1 Monte Vista 0001, E2 Bucktown 0002 supersedes pattern,
  E3 64th Lane 0010; N1 Coleman DECISION-LOG reconstructed-months-later; 149-line
  card), `client-email` (Bucktown critical-path, 64th Lane window-hold, San Vicente
  JADU - a found third beyond the brief), `client-brief` (211 Centre TPA brief only
  - CA-residential and code-issue cells honestly open).
- README Sets table + v1.4 row updated on the library drive.
- Held for Tyler's batch review (2.3) before batch (b) - zoning-memo,
  research-report, agency-letter - starts, so his edits to batch (a) set the bar.
- `refs index` follow-up: the generator's table (type/title/status/reviewed/card)
  is thinner than the README's hand-maintained one (adds Entity, Exemplars, Skill).
  Do NOT wrap `atlas:contents` markers or apply until the generator emits those
  columns from card front matter (`skill`, entity, exemplar folders) - applying
  today would degrade the README. Extending the generator is a small Atlas change;
  queued behind the parallel session's tree.
