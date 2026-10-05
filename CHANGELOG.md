# Changelog

All notable changes to **Architecture Studio** (`tyler-figureground/skills-for-architects`) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Reference Sets** (ADR 0015, `docs/research/reference-sets.md`). One curated, Tyler-approved set per deliverable type in `LIBRARY - Reference\00 Office Standards and Administration\Reference Sets\`: a card (`SET.md`), up to three exemplars - California residential, code issue, commercial - and a near-miss, each exemplar with a `NOTES.md` leak list. Pilot sets: Code Analysis, Meeting Minutes, G-Series Sheets (Solid Void). The third-party drawing sets folder is renamed `Precedent Sets`.
- **Atlas `0.9.0` - look before you make.** `atlas refs` lists reference sets with status, review dates and problems; `atlas refs check <draft>` greps a draft for the facts its exemplars' projects own. `agents-rules.md` gains "Look before you make": read the set, mark the draft, check it, name the set in the run receipt. The run template gains a `Reference:` line. Drive map v3.4 adds top-level `referenceSets`.
- **Atlas `0.9.2` - `atlas pdf` and Tyler's calibration.** `atlas pdf <file.md>` prints a Markdown deliverable to a PDF beside it through headless Edge or Chrome (nothing to install on a Windows PC); a PDF newer than its source is kept unless `--force`. From Tyler's blind grades: minutes are prepared by Tyler, carry no file paths, transcript or transcription tool, and flag doubt inline; narrative items are lists, tables only for numeric grids; everything filed for a person gets a PDF. 10-norma `1.4.1`: dwelling memos run occupant load for the most likely use, labelled informational; memos are printed with `atlas pdf`.
- **Atlas `0.9.1` - leak check without false alarms.** The pilot eval (10 blind drafts, with-set preferred 5 of 5, 38% fewer edits) found no copied facts but false hits on every draft, and agents rewording true facts to clear them. `atlas refs check` now ignores dates, times, sums, dimensions and short IDs (`DR-019`); takes `--project` for a draft kept outside its project; reads studio-wide names from `leak_ignore` in the sets README. The rule now says a true fact stays and is named in the receipt.
- **08-dispatcher `1.3.0` - `post-write-reference-check` hook.** On a Write of a draft carrying `<!-- architecture-studio:reference: ... -->`, runs `atlas refs check`; leaks go back to the agent (exit 2). Silent without `atlas`. Rule `rules/reference-sets.md`.
- **10-norma `1.4.0` - code-analysis.** Reference-set step and marker; a dwelling variant that keeps the nine headings and maps them to the residential code; verify suffixes use a spaced hyphen, not an em dash.

- **Atlas `0.7.0` - project templates.** A drive map's `templates` list names files every project carries; the words live in `tools/atlas/src/atlas/templates/project/` and ship in the wheel. `atlas new` writes them, doctor reports an absent one, conform creates it and never overwrites. `controlPlane.agentsRules` puts the agent filing rules into every AGENTS.md Atlas block. ADR 0012.
- **Atlas `0.7.0` - seeded children.** A map child may be `{"name": ..., "seed": true}`: made with a new project, kept by clean, backfilled by conform when its section exists.
- **Atlas `0.7.0` - `atlas runs (--project NAME | --all) [--days N] [--apply]`.** Lists agent runs under `controlPlane.runsDir` and zips closed ones (idle `runRetentionDays`, named by no task list or handoff) into `archiveDir`, verifying each zip before removing the folder. ADR 0011.
- **Studio templates** `TASKS.md`, `Task List Template.md`, `AHJ-REGISTER.md`, `RESEARCH-INDEX.md`, `RUN-TEMPLATE.md`, `agents-rules.md`.
- **Launchers** in `tools/atlas/launchers/`: every `_tools\*.bat` now goes through `Atlas.bat`; `Archive-Agent-Runs.bat` added.
- **`Setup-New-Plus.bat`** - once-per-PC setup for dated `YYMMDD_Description` folders from right-click: installs PowerToys if missing, turns on New+ and its date variables, points it at `_tools\New+ Templates`. The one launcher that does not call Atlas.
- **Atlas `0.7.1` - research and asking** (Pyvoid grill #2899): `agents-rules.md` gains the client-job research rule (requirement row + done-test, 30 min per question, draw with best basis then ask, asks at the top of the receipt, parked findings); new template `INTAKE.md` holds the 12 day-1 intake questions (map entry `00 Tasks/INTAKE.md`); `TASKS.md` gains "Parked - outside sheet scope"; new PROJECT.md front matter carries `basis: []`, documented in **09-project-dossier**.
- **Atlas `0.8.0` - brief and ask-last rules.** New template `BRIEF.md` at every project root (now, settled - do not ask, open, holds, latest meeting; map entry `BRIEF.md`). `agents-rules.md` gains "Read first, ask last" (read the brief before anything; every question cites what was checked), "After every meeting" (minutes, decisions, facts, to-do list in `TASKS.md`, brief, report - all six), and "Control files stay small" (`PROJECT.md` facts only, no line over 1,000 characters, session narrative to `.agent/PROJECT-HISTORY.md`, spreadsheet registers mirrored to `decisions/REGISTER.md`, no `.lnk` pointers). Fixes agents re-asking settled scope. ADR 0014.
- **Atlas `0.8.1`/`0.8.2`.** Conform backfills `.agent/runs` and `.agent/backups` into projects made before the agent workspace existed, so the back-up-first rule has somewhere to write. The `PROJECT.md` size rule becomes a prompt to move narrative out, never to cut facts.
- ADRs 0011 (agent run folders), 0012 (project templates), 0013 (`00 Tasks` and `13 AHJ`). Research report `docs/research/project-folder-usage-and-agent-output.md`.

### Changed

- **09-project-dossier `1.4.0`:** PROJECT.md holds no tasks and no session logs; they go to `00 Tasks/TASKS.md` and the run's `RUN.md`.
- Atlas: the PROJECT.md canonical-map block points at Atlas, not `Add-Section.bat`, and tags seeded children.

### Fixed

- Atlas test `test_new_project_wizard_creates_complete_project` asserted a `260` date prefix and failed from October 2026; it now checks today's stamp.
- `scripts/lint.sh` link check skips fenced code and HTML comments, where example links such as `Lists/YYMMDD-slug.md` are text.

## [1.8.0] - 2026-09-23

Studio drive release. Atlas `0.2.0` through `0.6.0`, the dispatcher's marker-driven metadata hook, and the report-marker patch bumps it needed. Atlas `0.6.0` closes the 2026-09 audit (#62): about 55 fixes to writes, undo, drive reads, the console and the CLI contract.

### Added

- **Atlas `0.6.0` - `atlas tree PROJECT [--depth N] [--json]`.** The tree's facts on the CLI: Filing State, Load State and child counts below a project root, and unmet Expectations as a separate list with whether conform can backfill each. Never a zero count on an Unread or unreadable folder; `--depth` reads one enumeration per folder, never a walk. Exit `0` clean, `1` findings, `2` error. (#30)
- **Atlas `0.6.0` - `atlas --drive D`** opens the console on that drive. The drive picker already told operators to do this; it was an argparse error. (#53)
- **Atlas `0.6.0` - new Companion and tree keys.**
  - `/` with the tree focused filters the tree to the loaded nodes whose names match, plus the folders leading to them. Never reads the drive. `Enter` keeps the filter, `Escape` restores the tree as it was. In the Companion, `/` says what it can filter. (#41)
  - `o` opens the file or folder under the tree cursor; an Unfiled node is revealed in Explorer instead. `y` copies the node's full path, Unfiled nodes included. From the list, both act on the project. Neither writes. (#45)
  - `f` in the Companion arms a one-Action Backfill for the unmet control-plane Expectation under its cursor, confirmed with `Enter`. On a missing section it says to use `a`. (#42)
  - `u` now previews the undo and waits for `Enter` (below).
  - The command palette names the key for `/`, `d`, `[`, `]`, `z`, `f`, `u`, `o`, `y` and `c`, and gains entries for the Companion mode, collapse, zoom, copy path and undo.
- **Atlas console and folder tree - shipped in `0.4.0`, recorded here late.** The `0.4.0` wheel was built after these landed and no CHANGELOG entry carried them.
  - Three Regions - Project List, Tree Region, Companion Region - in two Compositions: side by side at 100 columns and up, one at a time below. `Tab` next Region, `Enter` drills one Region in, `Escape` backs out. `[` and `]` collapse the list and the Companion, `z` zooms the focused Region. ADR 0005.
  - The health modal is gone: `d` cycles the Companion between unmet Expectations, project health and the dossier.
  - A lazily loaded folder tree for the selected project. Each node carries a Filing State (Mapped, Drifted, Misplaced, Loose, Unfiled) and a Load State; a folder is read only when opened. `space` opens and closes a folder. ADR 0004, 0007.
  - `f` conforms what has focus: the whole project from the list, one node from the tree. A one-Action repair previews on the operation line and waits for `Enter`. `u` undoes the last repair in that project. ADR 0006.
  - CLI forms for both: `conform --project NAME --node PATH` and `conform --revert FILE`. `conform --json` actions gain `moved` (the Move Manifest) and `path_length`. ADR 0008.
  - The Fault Word abbreviates at narrow widths - `NAME`, `PLACE`, `LOOSE`, `UNMAPPED` - and is never dropped, so colour never carries a distinction alone. ADR 0008.
- **Atlas `0.5.0` - File Rules, shipped with the agent files.** A drive map can carry an optional `fileRules` list that files Loose root files by name, extension, regex, or the text on a PDF's first page. Rules only ever propose Sweeps, so every one previews, confirms and undoes like any other repair; `doctor` names the rule behind each sweep in text and `--json`. Inert until a map carries the key. The operation line now reports a repair in the same words it offered it, and names the project root instead of printing an empty arrow. ADR 0009. `0.4.0` was the agent-files build alone, and is what the studio drive ran before this release. `atlas --version` now reads the installed package instead of a literal, which had gone stale: the `0.4.0` wheel reported `0.3.0`.
- **Atlas `0.4.0` agent files: AGENTS.md holds the instructions, CLAUDE.md points at it.** Every project now carries both. `AGENTS.md` carries an Atlas-owned, marker-wrapped block - house working style plus an index built from the drive map - and whatever the project has learned about itself outside those markers; `CLAUDE.md` carries one line, `@AGENTS.md`, so Claude Code reads the file Codex and every other agent already reads and no second copy can drift. The pointer is relative, because the hand-written absolute one on the live drive went stale the week its folder was renamed. Doctor reports a missing or stale block and a `CLAUDE.md` that is anything but the pointer; conform backfills both, migrates a hand-written `CLAUDE.md` into `AGENTS.md` before pointing at it - and refuses, as a conflict, unless every line of it is provably present there - and renames a hand-saved `Agents.md` to the canonical spelling instead of duplicating it. New projects get both files at creation, from Atlas and from the drive's `New-Project.ps1` / `Conform-Project.ps1`, in byte parity. ADR 0010.
- **`09-project-dossier` (`1.3.2`) - preferences live in AGENTS.md.** The skill and README used to send user preferences and firm conventions to `CLAUDE.md`; they now name the project's `AGENTS.md`, which is where instructions live under ADR 0010. The dossier still holds project facts only.
- **`08-dispatcher` (`1.1.1`) - the metadata hook leaves `AGENTS.md` alone.** It already skipped `README.md`, `SKILL.md` and `CLAUDE.md`; `AGENTS.md` is the same kind of file and must not collect report front matter.
- **The SOLID+VOID ATLAS header.** A 3D extruded, gradient-mapped wordmark rendered in half-blocks, so it costs four rows where whole blocks would cost seven - and the gradient gains a band rather than losing one, because there are more pixel rows to sample. Collapses by terminal width: full mark at 115 columns and up, a compact composition with ATLAS set beside the mark at 82-114, and a single knocked-out bar below that.
- **A token layer.** One Python module owns the palette and the folder-state glyph table and generates the Textual stylesheet from it, because tree nodes take no CSS and must read their colours from Python. Colour is tested by contrast and structure rather than by hex literal: every text token must clear 4.5:1 against the ground, and a hand-edited colour in the generated CSS fails the suite.

- **Atlas tells "empty" apart from "could not read".** `list_entries` now returns a `Listing` carrying a Load State rather than an empty tuple on error, so a folder Atlas failed to open is never rendered as a folder with nothing in it. A project whose root is unreadable reports REVIEW instead of READY or SETUP, gains a `COULD NOT READ` block in the detail pane, and appears under a new `unreadable` key in `--json`. Found on the live studio drive, where a folder containing one item was being reported as empty.
- **Atlas reads paths past Windows MAX_PATH.** `long_path()` applies the extended-length prefix on demand at the three read chokepoints, fixing real studio-drive folders over 260 characters that failed to open while their own parents listed them. Writes are deliberately unchanged: a move can lengthen a path past the limit, and Atlas must not create paths that Explorer, Revit and the PowerShell tools cannot open.

- **Atlas `0.3.0` project and contact editing.** Select a project and press `e` to edit intake fields, reassign contacts, refresh project snapshots, and preview/confirm collision-safe folder renames. Press `m` to edit shared contact details while retaining stable IDs. Matching `atlas project edit` and `atlas contacts edit` commands support interactive and confirmed automation modes. Contact mailing addresses now accept physical streets or PO boxes while Project Address remains a physical site address. `PROJECT.md` gains additive structured site-address keys for reliable round-trip editing.
- **`09-project-dossier` (`1.3.1`) - structured editable site addresses.** Documents the additive address component keys while retaining the formatted `address` key and Identity mirror for consumers.
- **Atlas `0.2.0` complete project intake.** New three-step TUI wizard and CLI parity require Project Name, structured US Project Address, Project Use Case, Billing Contact, and Client Contact. Folder names derive from short street address. Reusable contacts persist per drive in `_tools/billing-contacts.json`; each project dossier stores stable IDs plus historical snapshots. Expanded project indexes omit contact personal data and migrate legacy tables with a backup.
- **`09-project-dossier` (`1.3.0`) - Atlas intake contract.** Adds Project Use Case and flat Billing/Client Contact snapshot keys and Identity rows while preserving existing Norma fields.
- **Atlas operations console.** Responsive project-health detail, filtering,
  sorting, contextual help, durable operation results, and marked-project batch
  conform. Shared-drive scans and mutations run through background workers.
  Confirmed plans now reject stale project or map state; constructive writes use
  exclusive file creation and never recreate a missing project root.
- **`09-project-dossier` (`1.2.0`) - Virtual tour slot.** The Identity table
  gains a `Virtual tour` row for Matterport / iGuide / video walkthrough links
  (human-only fact; no front-matter key, like Client). Added in the skill
  template, both Atlas generators (`new` and the `conform` stub, Atlas
  `0.1.1`) and the drive's `New-Project.ps1` / `Conform-Project.ps1`, so every
  writer stays in byte parity.

### Changed

- **Atlas `0.6.0` - what a script calling Atlas will notice.**
  - **`conform --revert` is a dry run unless `--apply`.** It used to apply at once, with no guard. It now prints the inverse Plan in conform's shape, honours `--json`, checks that every inverse source is still where the repair left it before anything moves, and exits `1` when any inverse action is not done and `2` when one failed. (#9)
  - **`conform --json` records `drive`, and `--revert` refuses a manifest without it** or from another drive. A manifest printed by `0.5.0` or earlier cannot be reverted by `0.6.0`. Manifest paths that are absolute, drive-lettered, hold `..`, or are empty where a move needs one are refused. (#9)
  - **`conform --json` actions gain `created` and `prune`**: what a write brought into existence other than by a move, and the created folders its undo removes if they are then empty. Both default to empty when read back. (#22)
  - **New action status `failed`.** An OS error mid-apply (a file open in Revit, Excel or Word) fails that one action and carries on. A failed merge keeps the manifest of what it moved first, `--revert` reverses it, and the CLI prints the partial manifest and exits `2`. (#4)
  - **`doctor --json`: a relocation's `file_count` may be `null`**, meaning files unknown, with the unreadable folder listed under `unreadable`. Text output says "files unknown", prints the unreadable lines and counts them as pending (exit `1`). Conform leaves such a source in place as a conflict. (#24)
  - **`doctor --json`: `sections_present` may be `null`** for a project whose root cannot be read. That project reports REVIEW with every other finding empty; conform skips it and exits `1`. (#13)
  - **Every CLI error exits `2`.** A missing drive, an unknown project, a malformed map and an OS error used to exit `1` or print a traceback. A map whose `relocations`, `driftMap`, `sections` or `children` has the wrong shape is refused at load. (#27)
  - **An unreadable drive root is an error**: `doctor` and `conform` exit `2` naming it, instead of reporting a clean, empty drive. (#26)
  - **`--project` must be one folder name** from the drive root's listing that the scan would call a project. A path, a separator, a drive colon, `.` or `..` exits `2` before anything is read. (#14)
  - **`conform --node` matches however the path is spelled** (`08 OUT\Invoices`, `08 OUT/Invoices/`). A node that does not exist exits `2` instead of "needs no repair". `--all` with `--project` or `--node` exits `2`. (#29)
  - **`conform` on a project with only Unfiled work** prints `[REVIEW] nothing Atlas can repair` and exits `1`, instead of `[OK]` and `0`. (#27)
  - **CLI output is UTF-8** when stdout or stderr is redirected, so a name outside cp1252 no longer crashes a command after its write. (#28)
- **Atlas `0.6.0` - `u` previews.** Undo arms its inverse on the operation line, or opens the modal for a merge's several moves, and waits for `Enter`. Its guard is the drive as the repair left it, so it catches a colleague's change made since. The entry leaves the stack only once the undo moves something; the stack holds 50 per project and is cleared by a project-wide or batch conform. (#6, #7)
- **Atlas `0.6.0` - Clean says what it removes.** The palette entry and confirm read "Clean folders with no files": Clean removes folders with no file anywhere beneath, not merely folders with nothing directly inside.
- **`09-project-dossier` (`1.3.3`) - Atlas-owned keys and rows.** The skill states the shape Atlas needs to edit a dossier: flat one-line scalars for Atlas's keys, one address in three places that must agree, value-first Identity rows with provenance after, `Created` starting with its date, Client as a human fact, UTF-8 CRLF. The template quotes ZIP codes, since an unquoted `02134` is the integer 1116 to a YAML reader. ADR 0001 records the same. (#36)

### Fixed

- **Atlas `0.6.0` - writes and undo.**
  - A rename of a folder with no files renames it; it used to delete it, report done, and leave nothing to undo. (#5)
  - Undo runs last-first, so a move nested inside a rename comes back out. (#21)
  - A merge that collides on a seeded skeleton folder can be undone from its manifest. (#48)
  - Undoing a sweep records the file at the project root, not at `/name`. (#51)
  - The tree shows what a write created or removed, not only what it moved. (#22)
  - An armed tree repair is cancelled when its context goes - project change, filter, rescan, drive picker, Region move, a modal, a resize - and `Enter` never commits it for a project off screen. (#2, #3)
  - A tree repair reports what happened (Done, Skipped, Conflict, removed), not what was previewed, and names a merge as a merge. (#20)
  - A tree repair updates its project's list row, so a following project conform is not refused as stale. (#25)
  - Switching drives drops the undo stack, the tree cache and any armed repair; a same-named project on another drive can no longer be undone into. (#8)
  - The scoped Guard walks nothing, tree repairs arm and commit off the UI thread, and the project-wide conform guards with the project's own Guard. (#46)
  - The MAX_PATH warning measures what Windows will see: relative `--drive` paths, deep subtrees and undo included, and per line in multi-action confirms. (#23)
  - Clean, file counts and empty-folder removal never walk into a junction or symlink. (#49)
  - A node's Filing State is the first map rule that matches, so the tree's word matches the action conform takes. (#60)
- **Atlas `0.6.0` - reading the drive.**
  - An unreadable project root reads as unreadable everywhere - REVIEW, "sections unknown", `?` in the list, and one `cannot read` row in the tree - never as an empty project. (#13)
  - A file count over an unreadable subfolder is unknown, never zero. (#24)
  - The Companion says `PROJECT.md - no front matter` instead of listing a present file as missing. (#58)
  - The tree takes every rescan and keeps its open folders and cursor across one. (#12, #40)
  - Budgets from the live-drive measurement are in place: a 120 ms loading delay, four concurrent folder loads, and a 500-entry cap past which a folder lists as Partial. (#46)
- **Atlas `0.6.0` - the console.**
  - The tree cursor is visible, so the operator can see which row `f` will act on. (#17)
  - Keyboard focus follows the Region on screen, never a hidden one. (#11)
  - `Enter` and `Tab` belong to a modal, the filter or the palette when one is on top. (#10)
  - A resize redraws for the new size, not the previous one. (#18)
  - Long names are middle-ellipsized so the Fault Word, Load State and the part of a project name that tells two apart stay on screen; Load State abbreviates to `unread`, and `cannot read` never shortens. (#19, #38)
  - A bracketed project name reads the same in the list, modals and toasts. (#37)
  - The status line, footer and inline confirm clip visibly, never silently. (#57)
  - The tree and list draw on token grounds, so every text pair clears 4.5:1. (#39)
  - `shift+space` no longer expands every folder in the tree. (#50)
  - Four traced races: a cache iterated while written, a stale tree load, a latent conform loop, a silent `f` on an unbuilt tree. (#52)
- **Atlas `0.6.0` - project editing and contacts.**
  - Project edit rewrites only the Identity rows whose value changed and keeps their provenance; refuses, naming both values, when the address fields disagree. (#35)
  - Project edit parses only Atlas's own front-matter keys and reads `# comments` as comments, so a mixed occupancy list or a commented template line no longer blocks an edit. (#15, #32)
  - A dossier written by the skill loads in Atlas: LF, a BOM, a missing final newline and one-word contact names are tolerated. (#36)
  - An edit form's staleness check starts when the form opens, so a change made while typing is not overwritten. (#31)
  - Interactive project edit keeps contacts by stable ID, not by a snapshot email. (#16)
  - Project edit warns on a log failure after a successful write, previews a rename collision, and follows the map's `projectFile`. (#56)
  - Control characters, including U+2028 and NEL, are refused at the form and never written raw. (#34)
  - A folder name never ends in a space Windows would drop. (#33)
  - The shared contact directory keeps fields this build does not know. (#54)
  - An index edit carries the Status cell through without re-escaping it. (#55)
  - The fixture builder replaces only a drive it built itself. (#44)
- **`08-dispatcher` (`1.2.0`) - the metadata hook stamps only reports that ask for it.** `post-output-metadata` used to prepend front matter to every `.md` written in any repo, which put 372 stamped blocks into 315 files of another project in two weeks: blocks spliced mid-file, stacked in appended files, and opening 71 GitHub issue bodies drafted in `.md` files. It is now marker-driven, like the disclaimer check: it stamps only files carrying `<!-- architecture-studio:report -->`, only when they do not already start with `---`, and leaves every other Markdown file byte-identical. It still never blocks a Write. `plugins/08-dispatcher/hooks/tests/check_post_output_metadata.py` covers the contract against temp files, and `scripts/lint.sh` runs it. (#63)
- **Report-writing skills emit the report marker.** `rules/output-formatting.md` now asks for `<!-- architecture-studio:report -->` as the first line of every Markdown report body, and the skills and agents that write one carry it: `00-due-diligence` (`1.1.1`) `/nyc-property-report`; `01-site-planning` (`1.1.1`) `/demographics-analysis`, `/environmental-analysis`, `/history`, `/mobility-analysis` and the Site Planner agent; `02-zoning-analysis` (`1.2.1`) `/zoning-analysis-nyc` and the NYC Zoning Expert agent; `03-programming` (`1.1.1`) `/occupancy-calculator`, `/workplace-programmer`; `04-specifications` (`1.1.1`) `/spec-writer`; `05-sustainability` (`1.1.1`) `/epd-compare`, `/epd-to-spec`; `10-norma` (`1.3.1`) `/code-analysis`, `/drawing-analysis`.
- **CI runs the Atlas test suite.** New `.github/workflows/atlas.yml` runs `uv run --locked pytest` in `tools/atlas` on `ubuntu-latest` whenever `tools/atlas/**` changes, with a 120-second per-test ceiling from `pytest-timeout` so one hang fails one test instead of stalling the run. Until now every "N tests pass" was a local claim; ADR 0002's separate Atlas gate had no runner. The suite passes on Linux as-is (474 passed, 1 skipped - the MAX_PATH test, already guarded as Windows-only). (#47)

## [1.7.0] - 2026-07-25

### Added

- **`10-norma` plugin** (`1.3.0`) - the skills now name the governing and
  non-governing layers the Norma engine has been returning for some time. The
  engine and the architect-facing surface had drifted apart: no skill file
  mentioned `adopted`, `dgs`, `standards_confidence` or `adopted_confidence`, so
  an agent following the installed skill on a Napa County road-width or
  defensible-space question had no instruction to look at the controlling
  instrument, and none to read either parallel verdict.
  - `agents.md` gains **the dossier's five blocks and their authority**
    (`candidates` and `adopted` govern and are citable; `standards` is
    edition-routed; `dgs` and `advisory` never govern), **the three confidence
    verdicts** with the invariant that only the code verdict drives `abstain`,
    and the **six California local overlays** with their `-j` keys. The source
    types table gains local-ordinance, adopted-instrument and state-advisory
    rows, and `norma answer` joins the tool stack.
  - `/ibc`, `/code-analysis`, `/egress` and `/drawing-analysis` each route the
    reader to the `adopted` block where it bites - site access, road width,
    dead-end length, turnaround geometry, driveway grade, defensible space -
    and state that a locality question answered from `-j ca` is wrong.

### Fixed

- **`10-norma` A117.1 routing was stale.** The known-divergences table said
  "adopted (edition pending - verify Ch 35)" for both IBC and NYC; the engine
  now holds both editions and resolves `matched` for each. Corrected to IBC
  adopts **2003**, NYC adopts **2009**, California adopts neither.

## [1.6.0] - 2026-07-23

### Changed

- **`10-norma` plugin** (`1.2.0`) - the PATH-repair fallback moves from
  `python "$NORMA_HOME/tools/norma_cli.py" <verb>` to `python -m norma.cli <verb>`
  across `agents.md`, the plugin README, and all six skill headers. Same repair
  (missing Scripts dir on PATH), no `NORMA_HOME` coupling, and it survives the
  Norma engine's v0.3 removal of the `tools/*.py` compatibility adapters.
- **`scripts/lint.sh`** Norma drift-guard tightened: it now also fails on the
  `$NORMA_HOME/tools/` and `tools/norma_cli.py` fallback forms, not just
  `python tools/…`, so a stale fallback cannot rot silently after v0.3.

## [1.5.0] - 2026-07-18

### Changed

- **`10-norma` plugin** (`1.1.0`) — CAD/BIM source files now flow through
  `norma ingest` in `/drawing-analysis`, `/egress`, and `/code-analysis`, with
  the fidelity order IFC → DXF/DWG → vector PDF → vision. California `/ibc`
  guidance now routes across the full 2025 Title 24 family and carries the
  instrument-scoped citation and amendment-sidecar cautions required by
  PRD-0008.

## [1.4.0] - 2026-06-24

### Added

- **`10-norma` plugin** (`1.0.0`) — [Norma](https://norma.llc) building-code analysis joins the studio: six skills — `/ibc` (code Q&A), `/egress` (occupant load, exits, egress width, travel distance, common path / dead-end), `/allowable-area` (allowable height / stories / area), `/code-analysis` (full cited cover sheet), `/compare` (cross-jurisdiction provision diff), and `/drawing-analysis` (vision-grounded life-safety review of a floor-plan PDF). Every answer is grounded in a local code corpus (IBC 2009, NYC 2022, CA 2025) and cited verbatim — no code answers from memory. The skills are a thin **surface**: calculators, corpus, and data live in the editable-install **`norma` engine** and are called as `norma <verb>`, so engine edits go live everywhere with no re-publish. Norma scopes from the workspace `PROJECT.md` front-matter (the contract added in 1.3.0) via `norma project active`, guards the active project against the drawing under review (`norma project scope-check`), and writes cited sheets into `06 Research & Existing Conditions/Code/`. Plugin-level [`agents.md`](./plugins/10-norma/agents.md) carries the persona, source types, corpus routing, tool stack, and known per-edition pitfalls. Norma answers the architect of record as a peer and deliberately does **not** emit the professional-disclaimer marker. Part of PRD-0004 (project-agnostic Norma).

### Changed

- **`scripts/lint.sh`** gains a Norma drift-guard check: fails CI if any `10-norma` skill or its `agents.md` calls `python tools/…` directly or greps a raw corpus path (`rg … <juris>/20NN/`) instead of the `norma` CLI — the surface must shell out to the engine, never reach into a working directory.
- **README** + **`/skills` menu** — counts move to 45 skills / 11 plugins; Norma plugin row, catalog section, and architecture-diagram line added.
- **Canonical marketplace install moves to the `tyler-figureground/skills-for-architects` fork.** Install commands, Desktop "add marketplace from GitHub" instructions, `git clone` URLs, and the release badge across the README and every per-plugin/skill doc now point at the fork, which is where this and future releases are published. Historical release links (v1.2.1 and earlier) still point at the original repo where those release pages live.

## [1.3.0] - 2026-06-24

### Changed

- **`09-project-dossier` plugin** (`1.1.0`) — `PROJECT.md` gains a **YAML front-matter machine contract** at the top of the file: the tool-authoritative project facts that [Norma](https://norma.llc) and other architect skills read to auto-scope code answers. Keys: `project`, `address`, `jurisdiction`, `edition`, `occupancy_group`, `construction_type`, `sprinklered`, `stories`, `building_area_sf`, `frontage_ft`, `existing_co_occupant_load`, `existing_exits`, `place_of_assembly_strategy`, `tenancy`. The human Code table expands to mirror the contract (occupancy, construction type, sprinklered, stories, area, frontage, existing C-of-O load, existing exits, PA strategy, tenancy), and the front-matter is the machine mirror of the sourced/dated table rows. `/project-dossier init`/`update` now writes and maintains the front-matter, keeping it in sync with the tables (new hard rule 5); older dossiers without a front-matter block get one backfilled on `update`. Verified by round-trip: a dossier-produced `PROJECT.md` resolves through `norma project active` to the right jurisdiction / occupancy / construction / sprinklered. Part of PRD-0004 (project-agnostic Norma).

## [1.2.1] - 2026-06-10

### Changed

- **README** — "What's New in 1.2" section added below the headline, summarizing the dossier plugin, native subagents, and self-registering hooks; links to the CHANGELOG for full history.

## [1.2.0] - 2026-06-10

### Added

- **`09-project-dossier` plugin** (`1.0.0`) — persistent per-project state as plain files in the project folder. `/project-dossier` maintains `PROJECT.md`, the facts layer (identity, site, zoning, program, code — every entry sourced and dated, updated in place). `/decision` captures the reasoning layer: ADR-style records in `decisions/NNNN-slug.md` with context, options considered, the call, consequences, and a status (proposed / decided / superseded — never deleted, never renumbered). Eleven analysis skills now read the dossier before fetching, append their findings after completing, and propose `/decision` when an analysis forces a choice (zoning path, code edition, GWP threshold). Collaboration is deliberately git-native: files, not infrastructure.
- **Agents register as native Claude Code subagents.** The 7 agents moved from the repo root into their plugins' `agents/` directories with `name`/`description` frontmatter — installing a plugin now registers its agent (automatic delegation, routing by description). `/studio` still routes to them; reading the agent file inline is the documented fallback when a plugin isn't installed. `agents/README.md` remains as the cross-plugin index.
- **Hooks auto-register.** The 3 hooks moved to `plugins/08-dispatcher/hooks/` with a `hooks.json` — enabling the Dispatcher plugin registers them automatically. The manual `settings-snippet.json` merge is retired (users who merged it should remove those entries).

### Changed

- **`slide-deck-generator` restructured for progressive disclosure** — `SKILL.md` 869 → 145 lines; component markup moved to `slide-types.md`, the HTML/CSS/JS template to `html-template.md`, the image workflow to `image-handling.md`, each loaded on demand.
- **4 NYC due-diligence descriptions rewritten** (`nyc-acris`, `nyc-bsa`, `nyc-dob-permits`, `nyc-dob-violations`) with trigger + boundary phrasing — the description is the only signal Claude uses to auto-select among 39 skills.
- **`allowed-tools` added** to the 4 skills missing it: `occupancy-calculator`, `workplace-programmer`, `color-palette-generator`, `slide-deck-generator`.
- **`rules/` enforcement documented honestly** — 2 rules are hook-enforced (disclaimer, CSI), 5 are advisory conventions the skills are written against; nothing auto-loads a `rules/` directory.
- **README** — architecture diagram reflects plugin-native agents and hooks; counts now 39 skills / 10 plugins.

### Removed

- **`user-invocable` frontmatter field** from 25 skills — not part of the current SKILL.md schema; skills are slash-invocable by default. `PATTERNS.md` §1 updated.

## [1.1.3] - 2026-06-10

### Changed

- **README** — release badge added next to the license badge; Materials Research plugin row notes SIF + [Norma](https://norma.llc) export; CHANGELOG linked from Contributing.

## [1.1.2] - 2026-06-10

### Changed

- **`06-materials-research` is standalone** (plugin `1.1.0`). The plugin's config file is renamed `canoa.json` → `master-schedule.json`; `/master-schedule` migrates a legacy `canoa.json` automatically on its next run. `/product-spec-bulk-fetch` now points schedule export at [Norma](https://norma.llc). The Google Sheet workflow itself has no product dependency.
- **NYC zoning terminology** (plugin `02-zoning-analysis` `1.1.1`). `zoning-analysis-nyc`'s reference-file table header and step heading renamed from "Normativa" to "Zoning Rules" / "Rules File".
- **`PATTERNS.md` examples are self-contained.** External-org references removed from the conventions doc (sibling-repo list, naming tables, dispatcher reference implementations, layout names); examples now draw on this repo and canoa only.

## [1.1.1] - 2026-05-08

### Changed

- **`PATTERNS.md` rule #6 expanded.** Versioning discipline now spans three artifacts that must move together on every shipped change: the JSON `version` field (`plugin.json` and/or `marketplace.json` `metadata.version`), a git tag (`git tag -a vX.Y.Z`), and a GitHub release (`gh release create vX.Y.Z --notes-file <changelog-section>`). The rule previously stopped at JSON + CHANGELOG, leaving repo discoverability gaps — `git checkout v1.1.0` didn't resolve, no shareable release URL existed. Backfilled tags + releases for `v1.1.0` (this repo) and `v0.2.0` (canoa).

## [1.1.0] - 2026-05-08

### Added

- **`PATTERNS.md`** — canonical reference for ALPA's plugin and marketplace conventions. Ten principles distilled from canoa V1 and skills-for-architects v1.0: small one-verb skills, dispatcher matching plugin name, `<plugin>-<verb>` naming for single-plugin layouts, marker-driven rules, version bump per ship, public default, MCP bundling via `${CLAUDE_PLUGIN_ROOT}`, hard rules captured from real production bugs. Linked from README. Rule #6 (versioning) covers both `plugin.json` and `marketplace.json` `metadata.version`.
- `.gitignore` covering macOS, editor, and local-env artifacts.
- `scripts/lint.sh` — repo lint script with six structural checks: no tracked `.DS_Store`, JSON validity, SKILL.md frontmatter (`name` + `description` required), count consistency (plugins, per-plugin skill counts, marketplace.json), internal markdown link resolution, and shellcheck on `hooks/*.sh`.
- `.github/workflows/lint.yml` — runs `scripts/lint.sh` on push to `main` and on every PR.

### Changed

- **Disclaimer hook is now marker-driven, not keyword-sniffed.** `rules/professional-disclaimer.md` now requires every regulatory output to end with the canonical disclaimer block followed by `<!-- architecture-studio:requires-disclaimer -->`. The `post-write-disclaimer-check` hook checks for the marker and verifies the canonical block is present, instead of pattern-matching keywords like `FAR`, `setback`, `egress`. This eliminates false positives on non-regulatory documents that mention regulated terms in passing (READMEs, changelogs, meeting notes) and false negatives on terse regulatory replies that happen not to use those keywords.
- **Skill counts now reflect actual file count.** README headline, details summary, plugin table, and the dispatcher's `/skills` menu all read **37 skills** (up from "35"). The 2-skill gap was the dispatcher's `/studio` and `/skills`, which were uncounted by convention. The README catalog now includes a Dispatcher section listing them. `scripts/lint.sh` enforces that headline, details summary, catalog row count, plugin-table per-row counts, skills-menu, and `marketplace.json` plugin list all match the real file count — drift fails CI.

### Removed

- 11 tracked `.DS_Store` files. Now ignored repo-wide via `.gitignore`.

## [1.0.0] - 2026-05-06

First public release.

### Added

- **7 agents** — `site-planner`, `nyc-zoning-expert`, `workplace-strategist`, `product-and-materials-researcher`, `ffe-designer`, `sustainability-specialist`, `brand-manager`.
- **35 skills** across **9 plugins**:
  - `00-due-diligence` (7) — NYC landmarks, DOB permits, DOB violations, ACRIS, HPD, BSA, combined property report.
  - `01-site-planning` (4) — environmental, mobility, demographics, history.
  - `02-zoning-analysis` (2) — `/zoning-analysis-nyc` (PLUTO + Zoning Resolution), `/zoning-envelope` (Three.js 3D viewer).
  - `03-programming` (2) — workplace programmer, IBC occupancy calculator.
  - `04-specifications` (1) — CSI MasterFormat outline specs.
  - `05-sustainability` (4) — EPD parse, research, compare, spec.
  - `06-materials-research` (12) — product research, spec extraction, schedule cleanup, image processing, master schedule, SIF crosswalk.
  - `07-presentations` (3) — slide decks, color palettes, image resizing.
  - `08-dispatcher` (2) — `/studio` router, `/skills` menu.
- **7 rules** — units & measurements, code citations, professional disclaimer, CSI formatting, terminology, output formatting, transparency.
- **3 hooks** — post-write disclaimer check, post-output metadata, pre-commit spec lint.
- Marketplace install: `claude plugin marketplace add AlpacaLabsLLC/skills-for-architects`.

[Unreleased]: https://github.com/tyler-figureground/skills-for-architects/compare/v1.5.0...HEAD
[1.5.0]: https://github.com/tyler-figureground/skills-for-architects/releases/tag/v1.5.0
[1.4.0]: https://github.com/tyler-figureground/skills-for-architects/releases/tag/v1.4.0
[1.3.0]: https://github.com/tyler-figureground/skills-for-architects/releases/tag/v1.3.0
[1.2.1]: https://github.com/AlpacaLabsLLC/skills-for-architects/releases/tag/v1.2.1
[1.2.0]: https://github.com/AlpacaLabsLLC/skills-for-architects/releases/tag/v1.2.0
[1.1.3]: https://github.com/AlpacaLabsLLC/skills-for-architects/releases/tag/v1.1.3
[1.1.2]: https://github.com/AlpacaLabsLLC/skills-for-architects/releases/tag/v1.1.2
[1.1.1]: https://github.com/AlpacaLabsLLC/skills-for-architects/releases/tag/v1.1.1
[1.1.0]: https://github.com/AlpacaLabsLLC/skills-for-architects/releases/tag/v1.1.0
[1.0.0]: https://github.com/AlpacaLabsLLC/skills-for-architects/releases/tag/v1.0.0
