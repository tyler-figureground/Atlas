# Atlas: the highest-ROI next features for the office

Date: 2026-10-30
Scope: what to build next in Atlas (`tools/atlas`) and the plugins so the studio gets the
most back per hour of build time. Based on `origin/main` at `423905c` (Atlas 0.20.0 on the
drive, unreleased seat-ready and `revit:` backfill work on main), the console map, the
robustness plan's progress log, ADRs 0001-0023, and a read-only measurement of
`G:\Shared drives\ARCHITECTURE` taken today. Nothing on the drive was changed.

Confidence: **Measured** = counted on the drive today. **Observed** = seen in specific
files. **Proposed** = this plan's recommendation.

---

## 0. The answer in one screen

The folder-health console is done: open tickets zero, search, content index, dossier,
archive, deep pass, refs and the digest all shipped. The leverage has moved. The studio's
bottleneck is no longer *where files go*; it is **Tyler's attention, permit status nobody
can see, and agent work that waits for a human to start it.**

Ranked by value per build-week:

| Rank | Feature | Why it pays | Size |
|---|---|---|---|
| 0 | Housekeeping: push the stranded commit, release 0.21.0, conform Entrada Rd | Work exists that no PC and no colleague has | Hours |
| 1 | **Tyler action queue** - the digest becomes a ranked, aged, top-15 list | 115 errands + 23 blocking decisions on one flat wall; 0 carry a date | 2-3 days |
| 2 | **Decision unblocker** - each blocking decision shows what it holds up, with a pre-drafted ask | 23 decisions gate the 77 MODEL + 27 AGENT tasks | 2 days |
| 3 | **Permit tracker** - AHJ registers filled from the folders, permits in the digest | 6 of 10 registers are the bare template, the other 4 hold 2-4 rows, while round folders exist | 1 week |
| 4 | **Meeting inbox** - transcripts with no minutes surface and queue closeout | 64th Lane: 10 transcripts, 7 minutes | 2-3 days |
| 5 | **Cross-project production queue** - `atlas tasks`, stale claims, a nightshift feed | 27 AGENT tasks sit until someone opens the project | 1 week |
| 6 | **Control-file budget** - doctor flags bloated `PROJECT.md`, agent splits it | MPR `PROJECT.md` 1,333 lines; rule says ~400; every agent session reads it | 2 days |
| 7 | **California site due diligence** - parcel, zoning, permit history for CA jobs | Due-diligence and zoning plugins are NYC-only; most active jobs are California | 2-3 weeks |
| 8 | **Transmittals** - generate the transmittal and log row from an `Out` folder | Template exists; every issue to client/AHJ/consultant is hand-built | 1 week |

Do 0-2 first (one week: `core/tyler.py` plus the shared task parser in `core/tasks.py`). They change what Tyler does every morning
and cost almost nothing. 3-6 are the next month. 7-8 after that.

---

## 1. Evidence (Measured 2026-10-30, read-only)

| Fact | Number | Source |
|---|---|---|
| Active projects on the drive root | 11 (+ 2 `00` folders) | `ls G:\Shared drives\ARCHITECTURE` |
| Open Tyler errands across projects | 115 (`TYLER-TODAY.md` header says 112) | `00 Tasks/TYLER.md` x 10 |
| Errands with a due date | **0** | grep `due` |
| Errands with a pre-drafted artifact (`ready:`) | 14 | grep `ready:` |
| Open production tasks | 136: `MODEL` 77, `AGENT` 27, `DECISION` 23, `WAIT` 9 | `00 Tasks/TASKS.md` x 10 |
| Errands concentrated in one project | MPR 52 of 115 | per-project count |
| AHJ registers with an application row | ~4 of 10 have 2-4 rows; 6 are the bare template (12 lines) | `07 Correspondence/AHJ/AHJ-REGISTER.md` |
| `PROJECT.md` size | MPR 1,333 lines, Silverado 576, Monte Vista 535, 64th Lane 457, San Vicente 403 | `wc -l` |
| Transcripts vs minutes | 64th Lane 10 vs 7; others roughly even | `11 Meetings` |
| Project with no control files | `21042 Entrada Rd` - no `PROJECT.md`, no task files | digest says "run conform" |
| Drive version vs repo | drive pins `studio_atlas-0.20.0`; main carries unreleased #14/#16 work | `_tools\Atlas.bat`, `CHANGELOG.md` |
| Stranded commit | `99a15cd` (California permit reference routing) is on local `main` only, on no remote | `git branch -r --contains 99a15cd` is empty |

Reading of the evidence:

- **Tyler is the throughput limit.** 23 decisions block production. The digest lists them
  but does not rank them, age them, or say what each one holds up.
- **The digest is a wall, not a queue.** 115 lines in project order, clipped at 160
  characters, no priority, no age, no "ready to send" lane. It gets read once and ignored.
- **Permits are invisible.** The AHJ register exists in every project (ADR 0013/0021) but
  nobody fills it. Permit rounds already live in `R<n>_YYMMDD` folders Atlas can read.
- **Agent capacity is idle by default.** 27 `AGENT` tasks are pickable today, but only when
  someone opens that project and asks. Nightshift exists; nothing feeds it.

---

## 2. Already built - do not rebuild

Folder conform/repair/undo (ADR 0006-0009), deep pass and receipt rules (tickets 26, 31),
global name and content search incl. archive (tickets 33-35, ADR 0020), dossier Companion
Mode (ticket 36), archive verb (ADR 0019), reference sets with `refs check`/`doctor`/
`index`/gallery (ADR 0015), run archiving (ADR 0011), two task files then one-file prompts
(ADR 0016, 0023), `07 Correspondence` (ADR 0021-0022), the Tyler digest (0.10.0),
Pyvoid seat scaffold and `revit:` backfill (Pyvoid #1541/#1545/#1546).

Every feature below reuses those seams. None adds a second folder brain: the drive map stays
the only structure source, and every write still crosses a Plan with preview and confirm.

---

## 3. Ranking rule

ROI = (hours saved per week across Tyler + staff + agents) x (how often it bites) /
(build days + risk). Two tie-breakers from the standing constraints:

1. **Read-only first.** A feature that only reads and reports ships with no Guard, no undo
   and no ADR 0006 surface. Most of the top five are read-only.
2. **Markdown stays the source of truth.** Atlas reads and rolls up the project files;
   it does not move the data into a database or an app (decision-register principle).

---

## 4. Phase 0 - Housekeeping (hours, do today)

| # | Work | Done when |
|---|---|---|
| 0.1 | ~~Re-land `99a15cd` (California routing)~~ **Done by PR #18**: section in the packaged `agents-rules.md`, AHJ path per ADR 0021, override scripts not carried over. Local `main` still holds the old commit; reset it to `origin/main` once #18 merges | Section on `origin/main`; 0.2's conform restores it in projects |
| 0.2 | Release Atlas 0.21.0 (seat-ready scaffold, `.mcp.json`, `revit:` backfill), deploy per `tools/atlas/README.md`, repin `Atlas.bat`, conform `--all` dry run then apply | `Atlas.bat --version` = 0.21.0; deploy backup under `_tools\logs\` |
| 0.3 | Conform `21042 Entrada Rd` (or archive it if dormant - Tyler's call, see Q1) | Digest no longer says "TYLER.md missing" |
| 0.4 | Confirm no `ATLAS_TEMPLATES` override is set on any studio PC (retired 2026-10-07; it masked newer templates) | Env var absent at User and Machine level; `atlas new` on a fixture uses the packaged templates |

---

## 5. Features

### F1. Tyler action queue (digest v2) - rank 1

**Problem.** 115 errands, flat, in project order, undated. 14 already have a drafted email or
letter waiting (`ready:`) and are buried among the rest.

**What.** `atlas tyler` renders a queue at the top of `TYLER-TODAY.md`, above today's
per-project detail (which stays, unchanged, below):

1. **Send now** - every open errand with `ready:`. One line each, link to the draft. These
   take minutes and unblock others.
2. **Decide** - the `DECISION` lane, ranked by F2's blocked count.
3. **Due / overdue** - errands with a `due:YYYY-MM-DD` token, soonest first.
4. **Oldest** - top 10 by age; age from a `(added YYYY-MM-DD)` token, else the date in the
   linked minutes filename, else unknown (shown as `?`, never guessed).
5. Counts per project, so MPR's 52 is visible as a load problem.

Cap the queue at 15 lines. The point is one screen.

**Format additions** (backward compatible - old lines still parse):
`due:YYYY-MM-DD`, `added:YYYY-MM-DD`, existing `ready:`. The `/tasks` and
`/meeting-closeout` skills write `added:` on every new item and `due:` when the minutes give
one. Template `TYLER.md` documents the tokens.

**Files.** `tools/atlas/src/atlas/core/tyler.py` (`DigestItem` gains `due`, `added`,
`ready`; `render` gains the queue), `tools/atlas/tests/test_tyler.py`,
`templates/project/TYLER.md`, `plugins/09-project-dossier/skills/tasks/SKILL.md`,
`.../meeting-closeout/SKILL.md`, `CONTEXT.md` (Action Queue). `--json` emits the queue
(ADR 0008 fact obligation).

**Done when.** Fixture drive with mixed old/new lines renders the five sections in order,
capped; an undated item never shows a made-up age; live dry run (no `--write`) on the drive
shows the 14 `ready:` errands first.

**Risk.** Low. Read-only. The only behaviour change for agents is two optional tokens.

### F2. Decision unblocker - rank 2

**Problem.** A `DECISION` line says what to decide. It does not say what waits on it, so
Tyler cannot tell the decision that frees ten model tasks from one that frees nothing.

**What.**
- Tasks may carry `after:T-012` (blocked by). `atlas tyler` counts, per decision, how many
  open tasks name it, and ranks the Decide section by that count.
- The `/tasks` skill, when it files a `DECISION`, also files a ready-to-send question in
  `07 Correspondence/_Outbox/` when the decision needs the client - so the decision becomes
  a `ready:` errand Tyler can send in one step.
- Digest line shape: `T-012 Window supplier - blocks 9 (64th Lane) - ready: <draft>`.

**Files.** `core/tyler.py`, `templates/project/TASKS.md` (document `after:`),
`agents-rules.md` (when blocked, write `after:`), `/tasks` skill. CONTEXT.md: Blocks.

**Done when.** Fixture: three decisions blocking 0/2/5 tasks rank 5-2-0; a decision with no
`after:` references shows `blocks ?` until agents start writing them, not `blocks 0`.

**Risk.** Low. The count is only as good as agents' `after:` discipline - so the rule goes
in `agents-rules.md` and `/meeting-closeout` the same release.

### F3. Permit tracker - rank 3

**Problem.** Permits are the long pole on every California residential job and the main
thing a client asks about. The register is empty while the evidence sits in folders:
`07 Correspondence/AHJ/03 Submissions/R<n>_YYMMDD`, `04 Comments & Responses/R<n>_YYMMDD`,
`06 Permits & Inspections`.

**What.**
1. **Read (core).** `core/permits.py`: per project, read the AHJ stage folders one
   enumeration per folder (no walks - drive cost rule), derive per agency/round: submitted
   date (from `R<n>_YYMMDD`), comments-received date, response date, issued permit present.
   Agency from the filename convention the register template already requires.
2. **Report.** `atlas permits [--project NAME] [--json]`: one row per application -
   status, round, days in current state. Ball-in-court: `AHJ` when submitted and no comments
   folder for that round, `US` when comments exist with no response, `DONE` when a permit
   file is present.
3. **Digest.** `atlas tyler` gains a Permits block: anything `US` (we owe a response),
   anything at the AHJ longer than a threshold (default 30 days - Q3).
4. **Write, through a Plan.** `atlas permits --sync --apply` proposes register rows that the
   folders prove and the register lacks. Only appends rows; never edits a human-written row;
   preview shows each row. This is an edit to an existing file, so it is an explicit
   exception to ADR 0012's create-only rule, and ADR 0024 must say so.
5. **Console.** A `permits` Companion Mode beside unmet Expectations / health / dossier
   (`d` cycles). No new layout.

**Files.** New `core/permits.py`, `cli.py` (`cmd_permits`), `tui/app.py` (Companion Mode),
`templates/project/AHJ-REGISTER.md` (machine-readable status vocabulary is already there),
tests with a fixture AHJ tree. New ADR 0024: "The AHJ register is derived from the AHJ
folders; Atlas appends, people edit." CONTEXT.md: Ball In Court, Permit Round.

**Done when.** Fixture with three rounds across two agencies reports correct ball-in-court
and days; `--sync` dry run proposes rows, `--apply` appends them, re-run proposes nothing;
live dry run on Pestoni and San Vicente matches what Tyler knows (Tyler spot-check, 10 min).

**Risk.** Medium-low. Reads are bounded. The write only appends. The weak point is folder
naming discipline - so `doctor` should report a round folder that does not parse as
`R<n>_YYMMDD` (one finding, warning level).

**Ties.** Pyvoid's proposed `ahj_profile` front matter (branch
`agent/3766-adr-0001-ahj-profile`, ADR 0001 amendment) - read the jurisdiction from there
when present instead of guessing from the address (the California routing rule: never assume
County from a postal address).

### F4. Meeting inbox - rank 4

**Problem.** `/meeting-closeout` is the pipeline that fills both task lists, decisions and
the brief. It only runs when someone remembers. A transcript without minutes is a meeting
whose action items were never filed.

**What.**
- `doctor` finding (warning, never changes project status): a transcript in `11 Meetings`
  with no minutes file for the same meeting stem/date. Rule lives in the map
  (`meetingPairs` or a receipt-style rule), not hard-coded names - drive map stays the brain.
- Digest line: `64th Lane: 3 meetings not closed out - oldest 2026-10-14`.
- `atlas meetings --pending [--json]` lists them for a scheduled agent.
- Nightshift recipe (skill-side, not Atlas): for each pending transcript, run
  `/meeting-closeout`; Tyler reviews minutes in the morning. Agents never send.

**Files.** `core/doctor.py` or `core/deep.py`, `core/mapfile.py` (rule key), `cli.py`,
`core/tyler.py`, map lint, `nightshift` queue entry documented in
`plugins/09-project-dossier/skills/meeting-closeout/SKILL.md`.

**Done when.** Fixture with paired and unpaired transcripts reports exactly the unpaired;
live dry run lists 64th Lane's gap; one nightshift closeout runs end to end and Tyler accepts
the minutes.

**Risk.** Low for detection. The closeout itself is already-shipped skill behaviour.

### F5. Cross-project production queue - rank 5

**Problem.** 27 `AGENT` tasks across projects are pickable today, but agents only find them
from inside a project. 30 lines mention a claim; some are surely stale, and the TASKS.md
claim protocol has no expiry Atlas checks.

**What.**
- `atlas tasks [--lane AGENT|MODEL|...] [--all] [--json]`: every open task across projects,
  with claim, claim age, `after:` blockers (F2) and whether its agent prompt is present
  (ADR 0023 puts the prompt under the task).
- Stale claim = claim older than 2 h with no run folder activity (same lease rule as the
  global workflow). Reported, never auto-released - releasing is an edit to a project file
  and goes through the `/tasks` skill.
- `atlas tasks --next --lane AGENT --json` returns the top unblocked, unclaimed task with a
  prompt: what nightshift and `claude --bg` consume. `MODEL` tasks route to Pyvoid seats
  (`/maestro`, `/jdp`) only where `revit:` is filled.

**Files.** `core/tasks.py` (parser shared with `core/tyler.py` - one parser, not two),
`cli.py`, tests. CONTEXT.md: Stale Claim, Pickable.

**Done when.** Fixture: blocked, claimed, stale-claimed and pickable tasks classified
correctly; `--next` never returns a blocked or freshly claimed task; one overnight run
completes two real `AGENT` tasks from the queue with receipts in `.agent/runs/`.

**Risk.** Medium - unattended agents writing into client projects. Mitigated by the
existing run-folder, backup-first and receipt rules, and by starting with `AGENT` lane only.

### F6. Control-file budget - rank 6

**Problem.** Every agent session starts by reading `BRIEF.md` and `PROJECT.md`. MPR's is
1,333 lines; ADR 0014 says facts only and points narrative to `.agent/PROJECT-HISTORY.md`.
Long control files cost tokens on every run and hide the facts agents need.

**What.** Deep-pass `doctor` finding: `PROJECT.md` over N lines (map key, default 400),
`BRIEF.md` over one screen, `TASKS.md` Done section older than 30 days present (prune due).
Each finding names the skill that fixes it (`/project-dossier` split, `/tasks prune`).
Warning level only; never changes status.

**Done when.** Fixture flags only the oversize file; live dry run flags MPR, Silverado,
Monte Vista, 64th Lane; one supervised split of MPR keeps every fact (diff checked line by
line against ADR 0014's "never cut facts").

**Risk.** Low.

### F7. California site due diligence - rank 7

**Problem.** `00-due-diligence` (7 skills) and `02-zoning-analysis` are NYC-only, inherited
from the fork. Most active jobs are Napa / St. Helena / Bay Area. Parcel facts, zoning,
overlays (flood, fire hazard severity zone, WUI, Williamson Act, ag preserve), and permit
history are gathered by hand per job.

**What.** Research first (one session, `docs/research/ca-due-diligence-sources.md`): which
county GIS / assessor / permit portals expose usable APIs or exports for Napa, Sonoma and
Alameda counties; CAL FIRE FHSZ and FEMA NFHL services. Then a `ca-property-report` skill in
`00-due-diligence` that writes the parcel facts into `PROJECT.md` front matter (ADR 0001),
cites every source, and hands code questions to Norma. Respect the routing rule: jurisdiction
comes from the parcel, never from the postal address.

**Done when.** Report on three past jobs matches what their `PROJECT.md` already records
(holdout check, same method as the reference-set pilot).

**Risk.** Medium - external data sources vary by county. Bounded by doing research before
any build and shipping county by county.

### F8. Transmittals - rank 8

**Problem.** `TRANSMITTAL-LOG.md` ships in every project; transmittals are hand-built for
each issue to client, AHJ or consultant.

**What.** `atlas transmittal <folder> --to <party>`: lists the files in an `Out` or
`R<n>_YYMMDD` folder, writes a transmittal Markdown (then `atlas pdf`) into the same folder
and appends one log row - a Plan, previewed, create-only. Agents prepare; Tyler sends.
Gets a reference set like every deliverable type (ADR 0015, Phase 6 gap list names
transmittal).

**Done when.** Fixture issue folder produces transmittal + log row; re-run refuses to
duplicate; Tyler approves the reference set card.

**Risk.** Low-medium.

---

## 6. Sequencing

| Week | Work | Release |
|---|---|---|
| 1 | Phase 0; F1 + F2 (shared parser in `core/tasks.py` from day one, since F5 needs it) | 0.21.0 (housekeeping), 0.22.0 (queue) |
| 2 | F4 meeting inbox; F6 control-file budget (both deep-pass findings, one release) | 0.23.0 |
| 3-4 | F3 permit tracker (ADR 0024 first, then read, report, digest, sync, Companion Mode) | 0.24.0 |
| 5 | F5 production queue; first supervised overnight run | 0.25.0 |
| 6-8 | F7 research then first county; F8 transmittals | 0.26.0+ |

Each release follows the existing deploy path: tests green (`cd tools/atlas && uv run
pytest`), repo lint (`./scripts/lint.sh`), headless renders at the measured widths for any
console change, wheel to `_tools\atlas`, repin `Atlas.bat`, deploy log, HOW-TO updated.

---

## 7. Not recommended now

| Idea | Why not now |
|---|---|
| Fees, hours, invoicing in Atlas | No data in the projects to roll up; would be a second system. Revisit if Tyler names it as a pain (Q5) |
| Portfolio dashboard | Ruled out at charting (console map). F1's queue is a text digest, not a dashboard |
| Duplicate-file finding (ticket 27) | Parked: hashing on a streaming mount downloads every file. Unpark bar unchanged |
| DXF / lying-extension filters (ticket 28) | Parked until a real drive example |
| Drive API read path (ticket 11) | Closed 2026-10-08: filesystem-only is a standing constraint; the content index builds over the mount (ADR 0020) |
| Drawing checks in Atlas | Pyvoid owns standards and every check (2026-10-05 ruling). This side supplies sets and evidence |
| Moving task data into a database or web app | Markdown is the source of truth; Atlas rolls up, never owns |

---

## 8. Open questions for Tyler (answer once, up front)

| # | Question | Recommended default |
|---|---|---|
| Q1 | `21042 Entrada Rd`: conform as active, or archive? | Archive if no work in 90 days; else conform |
| Q2 | Digest queue length | 15 lines |
| Q3 | Permit "stuck at AHJ" threshold | 30 days, per-agency override later |
| Q4 | Nightshift allowed to run `/meeting-closeout` and `AGENT` tasks unattended? | Yes for closeout and `AGENT` lane; never `MODEL`, never sends |
| Q5 | Is fee/hours tracking a pain worth a later plan? | Not now |
| Q6 | F7 counties, in order | Napa, Sonoma, then wherever the next job is |

---

## 9. How we will know it worked

| Measure | Baseline (2026-10-30) | Target after 6 weeks |
|---|---|---|
| Open `DECISION` tasks | 23 | under 10 |
| Errands older than 30 days | unknown (no dates) - F1 starts measuring | falling month over month |
| AHJ registers with every live application | ~0 of 10 complete | 10 of 10 |
| Transcripts without minutes | 3+ (64th Lane) | 0 older than 2 days |
| `AGENT` tasks completed overnight per week | 0 | 5+ |
| `PROJECT.md` over 400 lines | 5 projects | 0 |

---

## Progress log

- 2026-10-30: plan written from a read-only drive measurement. Local `main` found diverged
  from `origin/main` (70 behind, 1 stranded commit `99a15cd`); plan written on
  `origin/main` in a worktree. Nothing built yet.
- 2026-10-31: **Phase 0.1 done** (PR #18; old commit tagged `archive/ca-routing-99a15cd`).
  **0.2 done**: Atlas 0.21.0 released (PR #20) and deployed; `Atlas.bat --version` 0.21.0;
  backup and manifests in `_tools\logs\atlas-0.21.0-deploy-20261031-101021\`. Backfill conform
  on 10 projects: California + Pyvoid seat sections in 10/10 AGENTS.md (additions only), blank
  `revit:` block in 3 PROJECT.md; re-run idempotent. `.mcp.json` still pending - needs a run on a
  PC with `ATLAS_PYVOID_MCP_SERVER` set. **0.4 done on the tower** (no override at User, Machine
  or Process level); laptop unchecked. **0.3 open**: `21042 Entrada Rd` is an empty, hand-made
  folder from 2026-10-26 - a new job, not dormant; needs Tyler's intake (name, address, contacts)
  or a rename to `YYMMDD_` form before conform.
- 2026-10-31: **0.3 settled** - Tyler creates `21042 Entrada Rd` through `atlas new` once he
  has the intake; no conform or archive. **F1 + F2 done** (PR #22, Atlas 0.22.0, deployed:
  `_tools\logs\atlas-0.22.0-deploy-20261031-105352\`). `core/tasks.py` is the shared parser;
  the digest opens with the Action Queue (13 send-now, 23 decide, 22 oldest on the live drive).
  Every decision reads `blocks ?` until agents write `after:`; age known for 35 of 113 errands
  until they write `added:`. Token rule refreshed into 10/10 AGENTS.md blocks (2 lines each);
  drive HOW-TO tasks section rewritten (it still described retired scoped lists).
  Review round fixed before deploy: `ready:` stopping at tokens, angle-bracket links, file-name
  dates, one section per item. **Next: F4 meeting inbox + F6 control-file budget (week 2).**
- 2026-10-31: **F4 + F6 done** (PR #24, Atlas 0.23.0, map v4.3 with `meetings` and
  `fileBudgets`, deployed: `_tools\logs\atlas-0.23.0-deploy-20261031-180116\`). Pairing is by
  leading `YYMMDD` date (same day, then named minutes, then nearest within 3 days), because
  drive naming varies too much for name matching. Live: 16 meetings in 4 projects, all closed -
  the 64th Lane gap in section 1 was closed out by hand before this shipped, so the "lists 64th
  Lane's gap" check had nothing to find; fixtures cover it. Budgets flag `PROJECT.md` in MPR
  1,334, Silverado 578, Monte Vista 542, 64th Lane 457, San Vicente 403 (5, not the 4 the plan
  guessed), and stale Done in 64th Lane (19), West Ln (6), Silverado (5). Two review rounds:
  an older meeting could take a newer one's minutes; folder-check failures read as absent.
  Still open from F4/F6 "done when": one supervised nightshift closeout, one supervised MPR
  split (both need a real pending meeting / Tyler's go). **Next: F3 permit tracker (ADR 0024
  first).**
- 2026-10-31: **F3 done, narrowed** (PR #26, Atlas 0.24.0, map v4.4 `permits`, ADR 0024,
  deployed: `_tools\logs\atlas-0.24.0-deploy-20261031-191258\`). The survey reversed F3's
  premise: the 4 projects with live applications already keep full register rows, only
  Monticello names rounds `R<n>_YYMMDD`, and no file carries an agency. So the register is
  the source, folders date states and flag a stale register, and `--sync` is deferred - no
  ADR 0012 exception. Live: 7 applications; Monticello BR26 at the County 50 days since R4;
  we owe Pestoni (comments, 30 days), West Ln and San Vicente (preparing); Pestoni and West
  Ln `V1`/`V2` folders flagged. Two review rounds: unreadable register read as empty; header,
  future-date, unclear-status and round-cell edge cases. Still open from "done when": Tyler's
  10-minute spot-check of the Permits block. **Next: F5 production queue (week 5).**
- 2026-10-31: Tyler confirmed the Permits block. **F5 queue done** (PR #28, Atlas 0.25.0,
  deployed: `_tools\logs\atlas-0.25.0-deploy-20261031-204100\`). `atlas tasks` / `--next`
  apply the template's own picking rule across projects. Deviations: stale claim uses the
  template's 7-day rule (claims are dated, not timed); a prompt ranks a task up instead of
  being required (1 of 25 live `AGENT` tasks has one). Live: 25 pickable `AGENT` tasks in 7
  projects, 0 blocked, 0 claims. The parser now pairs code fences CommonMark-style, so a
  prompt quoting `- [ ]` lines or a stray fence can never add or hide tasks (two review
  rounds; live files parse identically). **Open: the overnight run.** nightshift only runs
  git repos through worktree + PR; studio tasks write to G: with no PR gate, so a studio
  lane is a design decision for Tyler.
- 2026-11-01: **Week 5 done: nightshift studio lane** (nightshift `c186f40`, Tyler's
  2026-10-31 call). `python nightshift.py studio [--task "<project>:T-NNN"]`; nightly when
  `[studio] enabled`. Per task: pick via `atlas tasks --next --lane AGENT --json` (or a pin),
  back up control files to `<project>/.agent/runs/<run>/backup/`, claim in `TASKS.md` under an
  exclusive lock with an atomic replace (`claimed YYYY-MM-DD by nightshift`), engine with cwd =
  the project, file manifest before/after into `RUN.md` and the morning report's Studio section.
  Two review rounds (claim write could lose the backup; fenced lines read as tasks; scan errors
  read as deletions; per-lane engine login). **First supervised run: 64th Lane T-326** - pi
  glm-5.3, 10 min, done: `12 Construction Administration/261101_Framing-Review-Checklist.md` +
  PDF, T-326 moved to Done, only `TASKS.md` changed, 2 asks in the receipt. Found and fixed on
  the way: nightshift had been dead since 10-29 19:00 (orphaned run lock; nightshift
  `668de33`). Still `enabled = false`: Atlas's `--next` top task is Pestoni T-001 (umbrella
  over the retired vault list, ADR 0023), on the lane's skip list, which stops the lane.
  **Next: Tyler closes or re-lanes Pestoni T-001 and flips `enabled`; then F7 (week 6).**
