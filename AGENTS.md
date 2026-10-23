# AGENTS.md

Architecture Studio: a Claude Code / Claude Desktop plugin marketplace of agents, skills, and rules for architects, designers, and AEC professionals, plus Atlas, the studio drive tool. Content is Markdown, not application code. Single instruction source for every agent; `CLAUDE.md` is an `@`-import pointer.

## Agent conduct

- Sacrifice grammar for concision. Fragments beat sentences. Lead with outcome. Never pad.
- Absolute paths in every reply, backslash form: `C:\Users\Tyler\Documents\GitHub\Atlas\...`. Copy-paste ready. Never relative, never `~`. In-file links stay relative (worktrees).
- Progressive disclosure. This file is the map, not the manual. Follow a link only when the task lands on it. Detail lives in the linked docs, never here.
- Global rules at `C:\Users\Tyler\AGENTS.md` apply on top (verification is done-ness, shell and Windows hazards, no em dashes in public-facing copy).
- Finish the job. Stop only when done or genuinely blocked (a decision only Tyler can make, a secret or login only he has, a destructive or outward-facing action). Ask every foreseeable question before the run, in one message. Stuck mid-run: exhaust this repo (`docs/adr/`, `docs/research/`, `.agent/handoff/`, `.scratch/`; for studio projects the brief, decisions and latest minutes), then the internet, then ask. A filling context window is not a reason to stop: keep the handoff current, let auto-compaction run. Studio projects get the same rule from `tools/atlas/src/atlas/templates/project/agents-rules.md`.

## New projects

Every new studio project starts with `AGENTS.md` (instructions and index) and a one-line `CLAUDE.md` (`@AGENTS.md`). Never split instructions across the two. On the studio drive Atlas writes and backfills both; see `docs/adr/0010-agents-md-holds-the-instructions-and-claude-md-points-at-it.md`.

## Commands

Repo lint. Structural checks over the Markdown and JSON surface. Same command CI runs. Run it before claiming any change done.

```bash
./scripts/lint.sh
```

Deps: `jq`, `python3`, and PyYAML (`pip install pyyaml`).

## Layout

- `plugins/` - installable plugin bundles, numbered by project lifecycle. Skills live in `plugins/<n>-<name>/skills/<skill>/SKILL.md`; agents in `plugins/<n>-<name>/agents/`.
- `plugins/10-norma/agents.md` - universal context shared by the six Norma code skills; its fuller reference is `plugins/10-norma/reference/norma-context.md`.
- `tools/` - application code, the one exception to content-is-Markdown (ADR 0002). `tools/atlas/` is the studio drive/project TUI-CLI: self-contained uv project, own tests (`cd tools/atlas && uv run pytest`), not a plugin, not covered by `scripts/lint.sh`. CI runs the suite on `ubuntu-latest` via `.github/workflows/atlas.yml` when `tools/atlas/**` changes.
- `tools/atlas/src/atlas/templates/project/` - the studio's project template files (`TASKS.md`, `AHJ-REGISTER.md`, `RESEARCH-INDEX.md`, run log, the AGENTS.md filing rules). Edit here; Atlas copies them into every new project (ADR 0012). `tools/atlas/launchers/` holds the `_tools\*.bat` launchers.
- `agents/` - agents index.
- `rules/` - cross-cutting conventions.
- `docs/adr/` - architecture decision records.
- `docs/research/` - evidence reports. Indexed below.
- `scripts/lint.sh` - the lint.
- `.claude-plugin/marketplace.json` - marketplace manifest listing every plugin and its source path.

Adding or renaming a plugin means updating `.claude-plugin/marketplace.json` and `README.md`.

## Conventions

- `SKILL.md` files require YAML frontmatter. `scripts/lint.sh` enforces it.
- `plugins/10-norma` shells out to the `norma` CLI. Never `python tools/...` directly, never grep a raw corpus path. Use `norma <verb>`. Lint enforces both.
- Norma skills answer the architect of record as a peer and never emit the studio's professional-disclaimer marker. Rationale in `plugins/10-norma/agents.md`.
- Decision-register spreadsheets: follow `docs/decision-register.md`. Workbook stays canonical; six-column Team View, full history on a detail tab. `scripts/decision_register.py` builds/checks presentation; `scripts/export_decision_register.py` exports short summary plus unclipped evidence. Tests: `uv run --with openpyxl python -B -m unittest discover -s scripts/tests -v` (also in CI). Never truncate evidence or append meeting histories to front-sheet cells.

## Research index

Evidence reports live in `docs/research/`. Read the relevant one **before** starting an implementation it covers or re-opening a question it settled.

| Report | What it settles | Continue at |
|---|---|---|
| `atlas-file-management-oss.md` | Which open-source file-management projects Atlas should adopt, port, shell out to, or skip; a tool that writes on its own bypasses Atlas's Plan, preview and undo. | Its **Implementation backlog**. Tickets 26-28. ADR 0009. |
| `atlas-tree-widget-evidence.md` | Textual trees: plain `Tree`, never `DirectoryTree`; lazy loading; two silent-corruption traps. | ADR 0007, ticket 05. |
| `atlas-drive-tree-read-cost.md` | Reading a tree over Google Drive File Stream: enumeration is the cost, watching is not a staleness signal, `Path.rglob` is banned. | ADR 0007, tickets 06, 11. |
| `atlas-drive-latency-measurement.md` | The measured drive: 7,956 folders, 18,536 files, 4.24s full walk; two live MAX_PATH failures. | Ticket 12, ADR 0006. |
| `project-folder-usage-and-agent-output.md` | How projects actually use their folders; proposes `.agent/runs/`, AHJ section, fuller `06` seed, agent filing contract. | Its **Implementation plan** and **Open questions**. |
| `correspondence-folder-structure.md` | Exchange filed by party, AHJ by stage; no source endorses a top-level IN / OUT split. | ADRs 0021, 0022. |
| `reference-sets.md` | Curated, Tyler-approved reference sets per deliverable type, with leak lists. | Its **Implementation plan** and **Open questions**. |
| `drawing-production-reference-sets.md` | Drawing reference sets: per sheet type a `RULES.yaml`, exemplar, redline pair, print-first sheet check. | Its **Implementation plan** (phases A-F) and **Open questions**. |
| `agent-baseline-rules-evidence.md` | What every project's `AGENTS.md` block carries for JDP, Maestro and Norma; Pyvoid reconciliation. | ADR 0017; Pyvoid #769. |
| `atlas-tui-ux-evidence.md` | Console direction; never preload files on the shared drive. | ADR 0005, `.agent/handoff/atlas-tui-research.md`. |

Atlas work: `.scratch/atlas-console/map.md`, tickets in `.scratch/atlas-console/issues/`. Session continuity: `.agent/handoff/`. Vocabulary: `/CONTEXT.md`.
