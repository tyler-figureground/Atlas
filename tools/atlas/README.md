# Atlas

Map-driven TUI/CLI for studio shared-drive project tooling. Replaces the PS1/BAT
generation (`New-Project`, `Add-Section`, `Clean-Empty`, `Conform-Project`) per the spec:
`LIBRARY - Reference\_House Standard\atlas-tui-spec.md` (Google Shared Drives).

The drive's `_tools\<drive>-map.json` is the only folder-structure brain - Atlas hard-codes zero canonical folder names. Reusable contacts live beside it in `_tools\billing-contacts.json`.

## Status: operations console

Atlas diagnoses and safely repairs mapped project-folder differences. Every mutation uses the
same core plan as the CLI. Conform previews exact changes, never overwrites destinations, and
leaves conflicts in place. Clean removes only folders with no file anywhere beneath them
(**Fileless** in `/CONTEXT.md`) - not merely folders with nothing directly inside.

| Command | Does |
|---|---|
| `atlas [--drive D]` | Interactive operations console: inspect, filter, sort, create, clean, and conform. `--drive` skips the drive picker |
| `atlas doctor [--drive D] [--json]` | Drive-wide read-only conformance report |
| `atlas lint [--drive D] [--json]` | Validate the map file itself |
| `atlas new --name NAME --street STREET --city CITY --state ST --zip ZIP --use-case USE_CASE --billing-contact ID_OR_EMAIL [...]` | Create a complete mapped project |
| `atlas contacts list [--drive D] [--json]` | List reusable drive contacts |
| `atlas contacts add --first-name FIRST --last-name LAST --email EMAIL [...]` | Add a reusable drive contact |
| `atlas contacts edit ID_OR_EMAIL [--yes] [...]` | Edit a shared contact; stable ID retained |
| `atlas project edit FOLDER [--yes] [...]` | Edit project intake; safely preview/confirm folder rename |
| `atlas add --project NAME --section SECTION` | Add map-approved project folders |
| `atlas clean --project NAME [--apply]` | Preview or remove folders with no files anywhere beneath |
| `atlas tree NAME [--depth N] [--json]` | One project's folders and files below the root: Filing State, Load State, child counts, and unmet Expectations as a separate list. Read-only |
| `atlas conform --project NAME [--apply]` | Preview or apply mapped repairs |
| `atlas conform --project NAME --node PATH [--apply]` | Preview or apply the repair for one node, by project-relative path |
| `atlas conform --revert FILE [--apply]` | Preview or undo an applied conform from the `--json` manifest it printed; refuses a manifest from another drive or one whose paths leave the project |
| `atlas runs (--project NAME \| --all) [--days N] [--apply]` | List agent runs; zip the closed ones into `.agent/archive/` (ADR 0011). Preview by default |

TUI keys:

| Key | Does |
|---|---|
| `Enter` | Drill one Region in (list, tree, Companion), or confirm an armed repair or undo |
| `Escape` | Back one Region, clear a filter, or cancel an armed repair |
| `Tab` | Next Region |
| `/` | Filter the focused Region: projects by name or health, the tree by the names it has opened (never reading more). In the Companion it says what it can filter |
| `space` | Open or close a folder in the tree; mark a project in the list |
| `d` | Cycle the Companion: unmet Expectations, project health, dossier |
| `[` / `]` | Collapse or restore the project list / the Companion |
| `z` | Zoom the focused Region to full width; press again to restore |
| `f` | Conform what has focus (below) |
| `u` | Preview undoing the last repair in this project; `Enter` confirms |
| `o` | Open what has focus (below) |
| `y` | Copy the full path of what has focus |
| `n` / `e` / `m` | New project / edit selected project / manage contacts |
| `a` / `c` | Add map-approved folders / clean folders with no files |
| `x` | Conform marked projects |
| `s` / `r` / `l` | Sort / rescan / last result |
| `?` / `Ctrl+P` / `q` | Help / command palette / quit. Palette entries name their key for `/`, `d`, `[`, `]`, `z`, `f`, `u`, `o`, `y` and `c` |

`f` acts on whatever has focus: the whole project from the list, one folder or file from the
tree, one unmet control-plane Expectation (a missing `decisions`, `AGENTS.md`...) from the
Companion. A missing section says to use `a` instead - conform creates a section only as
the folder of a template file the map says every project carries (`00 Tasks`, `13 AHJ`).

`o` opens what has focus - the project folder from the list, the file or folder under the
cursor in the tree. An Unfiled node is revealed in Explorer instead of opened. `y` copies the
full path, Unfiled nodes included. Neither writes. On the CLI, a node's path is its Node Key in
`atlas tree --json`, relative to the project folder.

A single repair previews on the operation line and waits for `Enter`; nothing is written
until then. `u` previews the undo the same way - inline for one move, in a modal for a
merge's several - and the repair stays on the undo stack until the undo actually moves
something. The stack holds 50 per project, in memory for this session; a project-wide or
batch conform clears that project's, and switching drives clears all of it.

Exit codes: `0` clean, `1` findings/pending work, `2` error - every CLI error, including a
bad map, a missing drive and an unknown project, exits `2`. `--project` takes one folder name
from the drive root, never a path. `--json` is the agent interface.

## Filing loose files by rule

A file at a project root that the map can recognise is **Loose**: Atlas knows where it
belongs and can file it with one key. Two things make a file Loose - a glob in
`relocations`, and a **file rule**, which can also match on what is inside the file.

Rules live in the drive map, under `fileRules`, and are tried in order after the glob
relocations. The first that matches wins.

```json
"fileRules": [
  {
    "name": "Issued sets",
    "target": "08 OUT/Transmittals",
    "match": { "extensions": ["pdf"], "pdfText": ["issued for permit", "issued for construction"] }
  },
  { "name": "Fee sheets", "target": "10 Legal/Invoices", "match": { "extensions": ["xlsx"] } },
  { "name": "RFIs",       "target": "08 OUT/RFI",        "match": { "nameRegex": "^\\d{6}_RFI-\\d+" } }
]
```

| Filter | Matches |
|---|---|
| `extensions` | File extension, case-insensitive, leading dot optional |
| `names` | Glob on the file name, case-insensitive |
| `nameRegex` | Regular expression searched in the file name, case-insensitive |
| `pdfText` | A phrase in the PDF's title, subject, keywords, or first page - case- and spacing-insensitive |

Every filter given must match; within one filter, any value may. `doctor` names the rule
that filed each file, in text and in `--json`.

Rules produce the same repair a glob sweep does, so preview, confirm, undo, and
`conform --node` all work on them unchanged. A rule never touches `PROJECT.md`,
`CLAUDE.md`, `desktop.ini`, or a folder, and never reaches below the project root.

A malformed rule refuses the whole map rather than being skipped - a misspelled filter
key would otherwise leave a rule matching more files than its author wrote. Run
`atlas lint` to check targets.

**Content costs a read.** On the Drive mount, reading a file downloads it. Atlas only
opens a file after the rule's name filters pass, only when it is named `*.pdf`, and
never above 64 MB. Reads are cached per file until it changes. A PDF that cannot be
read - damaged, or locked with a password - never matches; a set that is merely locked
against editing reads normally.

## New project intake

Press `n` in the TUI. Three steps collect:

1. Required Project Name, structured US Project Address, and Project Use Case; optional Description
2. Required Billing Contact and Client Contact; Client defaults to Billing but can be overridden
3. Exact folder, project facts, and contact review before creation

Folder format: `YYMMDD_<street number + street>-<description>`. Unit, city, state, and ZIP remain in `PROJECT.md` but stay out of the folder name. Selecting **Other** as Project Use Case requires a custom label. **Add new contact…** writes to the selected drive's shared contact directory; first name, last name, and email are required.

## Agent files

Every project carries `AGENTS.md` and `CLAUDE.md` at its root (ADR 0010). `AGENTS.md` holds the instructions and the index; `CLAUDE.md` holds one line - `@AGENTS.md` - so Claude Code reads the same file Codex and every other agent reads. The pointer is relative, so a folder rename cannot strand it.

Atlas owns the block between `<!-- atlas:agents-begin -->` and `<!-- atlas:agents-end -->`: house working style plus an index built from the drive map. Everything outside the markers belongs to the project and is never rewritten.

Doctor reports `AGENTS.md` when it is absent or its block is stale, and `CLAUDE.md` when it is anything but the pointer. Conform backfills both. A project carrying a hand-written `CLAUDE.md` is migrated: its words move into `AGENTS.md` first, and `CLAUDE.md` becomes the pointer only once every line of it is provably present there - otherwise it is left alone as a conflict for a person to merge. A hand-saved `Agents.md` is renamed to the canonical spelling rather than duplicated.

## Project templates

Every project carries a few standard files - the task list, the AHJ register, the research
index, the run log template. Their words live here, in the repo:

`tools/atlas/src/atlas/templates/project/`

Edit a file there and every project created afterwards gets the new version: at once on an
editable install, and for staff with the next wheel. Existing projects keep their copy -
conform creates a template file only when it is absent, never over one that exists.

The drive map says which templates a project carries and where (ADR 0012):

```json
"templates": [
  {"path": "00 Tasks/TASKS.md", "template": "TASKS.md", "index": "Live task list"}
]
```

`index` adds a row to the AGENTS.md index. `{{project_name}}`, `{{project_folder}}` and
`{{created}}` are filled in. `controlPlane.agentsRules` names the one template that is not
copied: `agents-rules.md`, whose words become the rules sections of every AGENTS.md Atlas
block - read first and ask last, look before you make, after every meeting, control-file
limits, where agent work goes, research and asking. Edit it and conform refreshes the block
in every project.

`BRIEF.md` sits at the project root: now, settled (do not ask), open, holds, latest meeting.
Agents read it first and rebuild it after every meeting, so a decision made in a meeting
reaches the next agent without it digging through the register.

To try a template change on the real drive before releasing, point `ATLAS_TEMPLATES` at a
folder of templates.

A child in the map may be `{"name": "Lists", "seed": true}`. Seeded children of a seeded
section are created with a new project, kept by clean, and backfilled by conform.

## Reference sets

```
atlas refs [--root DIR] [--json]
atlas refs check <draft> [--type TYPE] [--exemplar ID ...] [--project DIR] [--json]
```

Generic strings - dates, times, sums, dimensions, short IDs like `DR-019` - are never
checked: every project has its own. Names that belong to the studio go in `leak_ignore:` in
the sets folder's `README.md` front matter. `--project` names the draft's own project when
the draft is kept outside it.

A Reference Set is one folder per deliverable type: a card (`SET.md`) and up to three
exemplars plus a near-miss, each with a `NOTES.md` whose front matter lists `leak_list:` -
the facts its source project owns (ADR 0015). `atlas refs` lists sets with status, review
dates, stale flags and problems (exit 1 if any). `atlas refs check` greps a draft for the
leak lists of the exemplars its `<!-- architecture-studio:reference: <type> <E1,E2> -->`
marker names, else every set; exit 1 on a leak. It skips exemplars from the draft's own
project, strings listed by exemplars from two or more projects (a shared consultant is no
one project's fact), and lone words under five characters. The folder comes from `--root`,
then `$ATLAS_REFERENCE_SETS`, then the drive map's top-level `referenceSets`. Read-only.
The card templates are in `src/atlas/templates/reference-set/`.

## PDF export

```
atlas pdf <file.md> [--out PATH] [--force] [--json]
```

Renders the Markdown (front matter stripped, tables kept) with a print stylesheet and has
headless Edge or Chrome print it to a PDF beside the source - nothing to install on a
Windows PC. `ATLAS_BROWSER` names another Chromium browser. A PDF older than its source is a
stale export and is replaced; one newer than its source may hold later edits and is kept
unless `--force`.

## Agent runs

Agents keep scratch in `.agent/runs/YYMMDD-<slug>/` (ADR 0011). `atlas runs` lists every run
and why it is open or closed. A run is closed after `runRetentionDays` (14) with no change,
when nothing in `00 Tasks/` or `.agent/handoff/` names it. `--apply` zips each closed run
into `.agent/archive/<run>.zip`, reads the zip back, checks it holds every file, and only
then removes the folder. Staff run it drive-wide with `_tools\Archive-Agent-Runs.bat`.

## Editing projects and contacts

Select a project and press `e`. Atlas pre-populates every intake field, shows the derived folder name, then requires a second confirmation when Address or Description changes the folder path. It refuses collisions and updates `PROJECT.md` plus the project-index row together. Project contact reassignment refreshes that project's snapshots only.

Press `m` to edit the shared contact directory. Contact IDs remain stable. Contact mailing addresses accept numbered streets, `PO Box`, and `P.O. Box`; project site addresses still require a physical numbered street. Shared contact edits do not rewrite historical project snapshots.

CLI edit commands are interactive when run in a terminal. Omitted fields retain their current values. Automation and `--json` require `--yes`; a folder rename also requires separate `--rename` approval. Use `--dry-run` to inspect the project-update plan without changing files. Run `atlas project edit --help` or `atlas contacts edit --help` for field flags.

## Accessibility

Atlas has not been validated with assistive technology and makes no accessibility conformance claim. Textual's screen-reader support is unresolved upstream ([textual#2425](https://github.com/Textualize/textual/issues/2425)), so the console should not be assumed usable with a screen reader.

Every capability that writes, and every fact the console can show, has a CLI form with `--json` (ADR 0008): `doctor` for the drive, `tree` for the nodes below a project root and its unmet Expectations, `conform --node` for a single repair, `conform --revert` for undo. Two differences remain. The console's undo stack lives in memory for one session, while the CLI undoes from the manifest a `--json` apply printed. `tree` reads only as deep as `--depth` asks, where the console reads each folder as you open it. The CLI is plain text and is the supported path for automation - and for anyone the console does not serve.

Within the console, colour reinforces a distinction and never carries one alone. A folder or file with something wrong with it names what is wrong in words; when the terminal is too narrow for the full phrase the word abbreviates - `NAME`, `PLACE`, `LOOSE`, `UNMAPPED`, `unread` - rather than leaving the glyph and its colour to say it. A long name shortens in the middle so the word always stays on screen.

## Install

Two installs, for two audiences. An editable install is for whoever develops Atlas; it never reaches studio staff, who run a pinned wheel from the shared drive.

### Developer: editable

Install once as an editable uv tool. The `atlas` command then works from any directory, and local source changes take effect without reinstalling.

```bash
cd tools/atlas
uv tool install --editable .
atlas
```

If `atlas` is not found after installation, add uv's tool directory to `PATH`:

```bash
uv tool update-shell
```

### Staff: pinned wheel on the drive

Staff launch Atlas through `Atlas.bat`, a launcher on the ARCHITECTURE drive pinned to one wheel version. The wheel lives in the drive's `_tools\atlas\` folder - 0.3.0 went to `G:\Shared drives\ARCHITECTURE\_tools\atlas\studio_atlas-0.3.0-py3-none-any.whl`. Rebuilding from `HEAD` without a version bump produces a second, different wheel under the same number, so bump `version` in `pyproject.toml` first; `atlas --version` reads it from the installed package.

A redeploy writes to the production drive. Do it only with the user's go-ahead. What the deploy records (`.agent/handoff/atlas-editing-plan.md`, `atlas-project-intake-plan.md`) show each release doing:

1. Tests green (`uv run pytest`) and repo lint green.
2. Build: `uv build` in `tools/atlas` writes `dist/studio_atlas-<version>-py3-none-any.whl`.
3. Back up the drive's `_tools` launchers, map and instructions to `_tools\logs\atlas-<version>-deploy-<YYYYMMDD-HHMMSS>\`.
4. Copy the wheel to `_tools\atlas\` and record its SHA-256.
5. Copy `tools/atlas/launchers/*.bat` to `_tools\`; `Atlas.bat` carries the version pin.
6. Verify: the deployed launcher reports `atlas <version>`, and `atlas lint` on the production map shows no new errors.
7. Update the drive's `HOW-TO.md` for any key or command that changed.

The launchers are in the repo at `tools/atlas/launchers/` and are copied to `_tools\` on deploy. `Atlas.bat` is the only version pin; every other `.bat` calls it - `New-Project`, `Add-Section`, `Clean-Empty` and `Conform-Project-APPLY` open the console, `Conform-Project` previews `conform --all`, and `Archive-Agent-Runs` runs `runs --all --apply`. The PowerShell tools they used to call are retired to `_tools\_deprecated\`: Atlas is the only thing that creates projects or folders. The one launcher that skips Atlas is `Setup-New-Plus.bat`, a once-per-PC setup: it installs PowerToys if missing, turns on New+ and its date variables, and points New+ at `_tools\New+ Templates` (resolved next to the .bat, so any drive letter works). Staff then make dated `YYMMDD_Description` folders from right-click; the templates are plain folders named like `$YY$MM$DD_Site Visit`.

## Dev

```bash
cd tools/atlas
uv sync
uv run pytest
atlas doctor --drive "G:/Shared drives/ARCHITECTURE"
```
