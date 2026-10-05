# Hooks

Hooks are event-driven automations that run automatically during Claude Code sessions. Unlike skills (invoked manually) and rules (reference documents), hooks fire on lifecycle events — after a file is written, before a commit, etc.

## Available Hooks

| Hook | Event | What it does |
|------|-------|-------------|
| [post-write-disclaimer-check](./post-write-disclaimer-check.sh) | After Write | Warns if a regulatory output (zoning, occupancy, code analysis) is missing the professional disclaimer |
| [post-output-metadata](./post-output-metadata.sh) | After Write | Stamps YAML front matter (title, date) onto marked plugin reports that lack it; leaves all other Markdown alone |
| [post-write-reference-check](./post-write-reference-check.sh) | After Write | Greps a draft marked with a reference set for facts copied from its exemplars; hands leaks back to the agent |
| [pre-commit-spec-lint](./pre-commit-spec-lint.sh) | Before git commit | Scans staged markdown files for malformed CSI section numbers |

## Installation

None. The hooks ship with the **Dispatcher** plugin via [`hooks.json`](./hooks.json) and register automatically when the plugin is enabled:

```bash
claude plugin install 08-dispatcher@skills-for-architects
```

Run `/hooks` in Claude Code to confirm they're loaded. Disable them by disabling the plugin, or per-session via `/hooks`.

> Versions ≤ 1.1.3 distributed these hooks as a `settings-snippet.json` requiring a manual merge into `~/.claude/settings.json`. If you did that merge, remove those entries — the plugin now registers the same hooks itself, and the old entries point at a path that no longer exists.

## Behavior

Three hooks **warn but do not block**; `post-write-reference-check` answers with exit 2 so the agent sees its report and fixes the draft (the Write itself is never undone). They print messages to stderr when issues are found but allow the action to proceed. To make any hook enforce (block the action), change `exit 0` to `exit 2` at the warning point in the script.

### post-write-disclaimer-check

Checks written `.md` files for the `<!-- architecture-studio:requires-disclaimer -->` marker that regulatory skills emit. If the marker is present but the canonical disclaimer block is missing, prints a warning. Marker-driven — silent on files without the marker.

### post-write-reference-check

Marker-driven. A skill that modelled a draft on a reference set writes `<!-- architecture-studio:reference: <type> <E1,E2> -->` into it (see [`rules/reference-sets.md`](../../../rules/reference-sets.md)). On a Write of a marked `.md` file the hook runs `atlas refs check <file>`, which greps the draft for the leak list of each named exemplar - the address, parcel, client, permit numbers and other facts that belong to the exemplar's project. Leaks: report on stderr, exit 2. Clean, no `atlas` on PATH, or no reference sets configured: silent, exit 0. Skips README, SKILL, CLAUDE, AGENTS, NOTES and SET files and anything under rules/, hooks/, .claude-plugin/ or a Reference Sets folder.

Verified by [`tests/check_post_write_reference.py`](./tests/check_post_write_reference.py) (stub `atlas`, temp files only), which `scripts/lint.sh` runs.

### post-output-metadata

Marker-driven, like the disclaimer check. Report-writing skills emit `<!-- architecture-studio:report -->` as the first line of the report body (see [`rules/output-formatting.md`](../../../rules/output-formatting.md)); the hook prepends a YAML front matter block (`title` from the first `# ` heading, else the file name; `date`; `generated_by`) only to `.md` files that carry that marker and do not already start with `---`. A stamped file starts with `---`, so a second write adds no second block.

Any Markdown without the marker is left byte-identical, in any repo. Before `1.2.0` the hook stamped every `.md` it saw, which spliced front matter into notes, issue drafts and machine-read files in unrelated repos (Pyvoid#1842, this repo's #63). Files named README.md, SKILL.md, CLAUDE.md or AGENTS.md, and files under rules/, hooks/ or .claude-plugin/, are skipped even when marked. Never blocks a Write - every path exits 0.

Verified by [`tests/check_post_output_metadata.py`](./tests/check_post_output_metadata.py) (stdlib only, temp files only), which `scripts/lint.sh` runs.

### pre-commit-spec-lint

Checks staged `.md` files for CSI section number formatting errors:

- Missing spaces: `092900` → should be `09 29 00`
- Dashed format: `09-29-00` → should be `09 29 00`
- Dotted format: `09.29.00` → should be `09 29 00`
- Missing section title: `09 29 00` → should be `09 29 00 — Gypsum Board`

## Customization

Each script is a standalone bash file. Edit to fit your workflow:

- Change warning to enforcement: replace `exit 0` with `exit 2` after the warning message
- Add project-specific metadata fields to the front matter stamp
- Adjust CSI lint patterns for your specification style
