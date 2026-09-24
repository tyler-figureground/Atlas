# Changelog

All notable changes to **Architecture Studio** (`tyler-figureground/skills-for-architects`) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

### Fixed

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
