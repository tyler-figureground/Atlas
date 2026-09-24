# AGENTS.md

Architecture Studio: a Claude Code / Claude Desktop plugin marketplace of agents, skills, and rules for architects, designers, and AEC professionals. Content is Markdown, not application code.

## User-Facing Writing Style

Sacrifice grammar for concision. Fragments beat sentences. Cut articles, hedges, preamble, and restatement of the question.

- Drop "I've gone ahead and", "It looks like", "Great question", "Let me".
- Drop articles where meaning survives: "Config now points at new endpoint."
- Lead with the outcome. Caveats after, if at all.
- One idea per line. Prefer a fragment over a subordinate clause.
- Never pad to sound thorough. Length is not evidence of effort.

Bad: "I've gone ahead and updated the config file so that it now points to the new endpoint."
Good: "Config now points at new endpoint."

Bad: "It looks like the tests are currently failing, which appears to be because of a missing dependency."
Good: "Tests fail. Missing dep."

**Applies to:** chat replies, status updates, task summaries, commit bodies, PR descriptions, error copy, UI microcopy, release notes.

**Does not apply to:** code, code comments, ADRs, PRDs, or any spec where precision and full context outrank brevity. Never drop a qualifier that changes meaning - concision is not ambiguity.

Never use em dashes in public-facing copy. Use a spaced hyphen ( - ) instead.

## Paths

Every file or handoff path you hand back is a full absolute path, drive letter first, so it copy-pastes: `C:\Users\YOLOTRON\Documents\GitHub\skills-for-architects\docs\adr\0010-....md`, not `docs/adr/0010-....md`. Applies to chat replies, task summaries, handoff notes, and anything pointing at a file on the studio drive.

## New projects

Every new project starts with two files at its root:

- `AGENTS.md` - the instructions and the index. What every coding agent reads.
- `CLAUDE.md` - one line, `@AGENTS.md`, and nothing else.

Never split instructions across the two. On the studio drive Atlas writes and backfills both; see `docs/adr/0010-agents-md-holds-the-instructions-and-claude-md-points-at-it.md`.

## Commands

Repo lint. Structural checks over the Markdown and JSON surface. Same command CI runs.

```bash
./scripts/lint.sh
```

Deps: `jq`, `python3`, and PyYAML.

```bash
pip install pyyaml
```

## Layout

- `plugins/` - installable plugin bundles, numbered by project lifecycle. Skills live in `plugins/<n>-<name>/skills/<skill>/SKILL.md`; agents in `plugins/<n>-<name>/agents/`.
- `tools/` - application code, the one exception to content-is-Markdown (ADR 0002). `tools/atlas/` is the studio drive/project TUI-CLI: self-contained uv project, own tests (`cd tools/atlas && uv run pytest`), not a plugin, not covered by `scripts/lint.sh`. CI runs the suite on `ubuntu-latest` via `.github/workflows/atlas.yml` when `tools/atlas/**` changes.
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

## Research index

Evidence reports live in `docs/research/`. Read the relevant one **before** starting an
implementation it covers or re-opening a question it settled. Each carries confidence
tiers, sources, and negative evidence, so it answers "was this already ruled out" faster
than a fresh search, and says what was measured rather than assumed.

| Report | What it settles | Continue at |
|---|---|---|
| `atlas-file-management-oss.md` | Which open-source file-management projects Atlas should adopt, port, shell out to, or skip - and the rule that decides: a tool that writes on its own bypasses Atlas's Plan, preview and undo. Produced File Rules. | Its **Implementation backlog** table, which carries per-row status. Open tickets 26, 27, 28. ADR 0009. |
| `atlas-tree-widget-evidence.md` | Textual 8.2.8 trees: build on plain `Tree`, never `DirectoryTree`; how lazy loading works; two silent-corruption traps (`str` labels, cursor restore by line number). | ADR 0007, ticket 05. |
| `atlas-drive-tree-read-cost.md` | Reading a tree over Google Drive File Stream: enumeration is the unit of cost, filesystem watching is not a dependable staleness signal, `Path.rglob` is banned. | ADR 0007, ticket 06, ticket 11. |
| `atlas-drive-latency-measurement.md` | The measured drive: 7,956 folders, 18,536 files, 4.24s for a full walk; the cost is all in the tail. Found two live MAX_PATH failures. | Ticket 12, ADR 0006. |
| `atlas-tui-ux-evidence.md` | Console direction - an expert operations console - plus "do not preload files on the shared drive", because a preview downloads remote content. | ADR 0005, `.agent/handoff/atlas-tui-research.md`. |

Atlas work is tracked in `.scratch/atlas-console/map.md` (destination, closed decisions,
fog) with tickets in `.scratch/atlas-console/issues/NN-*.md`. Session continuity is in
`.agent/handoff/`. Vocabulary is in `/CONTEXT.md` - new terms land there, not in a
docstring.
