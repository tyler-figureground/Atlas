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
| `atlas doctor --deep NAME [--json]` | The opt-in deep pass: walk below one project's root. One enumeration per folder gathers Receipt Rule matches, over-long paths already on disk (Win32's 260 - dirs flag at 259, the enumeration suffix needs the extra room), deep unreadable folders, and the item count against the 400,000 shared-drive cap. Enumeration only, depth-guarded; `--deep --all` pays the full drive walk by flag, never by default. With the map's `meetings` and `fileBudgets` keys it also warns on meetings with no minutes and on control files past their budget (reading only the budgeted files); warnings never change the status or the exit code |
| `atlas lint [--drive D] [--json]` | Validate the map file itself |
| `atlas new --name NAME --street STREET --city CITY --state ST --zip ZIP --use-case USE_CASE --billing-contact ID_OR_EMAIL [...]` | Create a complete mapped project |
| `atlas contacts list [--drive D] [--json]` | List reusable drive contacts |
| `atlas contacts add --first-name FIRST --last-name LAST --email EMAIL [...]` | Add a reusable drive contact |
| `atlas contacts edit ID_OR_EMAIL [--yes] [...]` | Edit a shared contact; stable ID retained |
| `atlas project edit FOLDER [--yes] [...]` | Edit project intake; safely preview/confirm folder rename |
| `atlas add --project NAME --section SECTION` | Add map-approved project folders |
| `atlas clean --project NAME [--apply]` | Preview or remove folders with no files anywhere beneath |
| `atlas tree NAME [--depth N] [--json]` | One project's folders and files below the root: Filing State, Load State, child counts, and unmet Expectations as a separate list. Read-only |
| `atlas dossier NAME [--drive D] [--json]` | One project's validated dossier facts through `load_project_record`: identity (name, address, use case, description, created), the billing/client contact snapshots, and the decisions summary (count and latest titles). Never raw Markdown. Exit 0 with the record; a missing, malformed or legacy `PROJECT.md` exits 2 with the reason. `--json` emits `drive`, `project`, `path`, `name`, `address`, `use_case`, `use_case_category`, `description`, `created`, `billing_contact`/`client_contact` (`id`, `name`, `email`, `phone`, `company`, `address`), `decisions` (`count`, `latest`) and `source_digest` |
| `atlas search QUERY [--content] [--no-archived] [--drive D] [--json]` | Drive-wide search: projects, folders and files whose name or path contains the query (case-folded); `--content` also searches PDF text and Markdown via the local Content Index (`atlas index build` builds it) - never a content read off the drive at query time. Archived projects (each folder under the map's `archiveRoot`) are searched read-only, tagged `[archived]` and listed after every live match; `--no-archived` leaves them out. Exit 0 with matches, 1 with none, 2 on error. `--json` emits `drive`, `query`, `total`, `shown`, `cap`, `archived` (count), `results` (`project`, `path`, `name`, `kind`, `archived`) and `unreadable`; with `--content` it adds `content`: null when no index exists, else `indexed_at`, `total`, `shown`, `cap`, `stale`, `archived` and `results` (`project`, `path`, `kind`, `snippet`, `archived`). An archived hit's `project` is its own folder name; its `path` keeps the archive prefix |
| `atlas index build [--no-archived] [--drive D] [--json]` | Build or top up the per-machine Content Index: PDF text and Markdown under the project roots and the archived projects, extracted over the mount and cached on this machine (platformdirs user cache, `$ATLAS_CACHE_DIR` to override) - never on the drive. Incremental by path+size+mtime: the first build reads every candidate; later runs re-read only what changed. Damaged and over-64 MB files are skipped silently. The archive's first extraction is the long one; `--no-archived` defers it and keeps any archived entries already stored. `--json` adds `archived` (archived files indexed). Writes nothing to the drive |
| `atlas index status [--drive D] [--json]` | Report the local Content Index: the Indexed-At Stamp, file and skip counts, cache path. Exit 0 with an index, 1 when none exists yet, 2 on error |
| `atlas conform --project NAME [--apply]` | Preview or apply mapped repairs. `--deep` includes Receipt Rule matches below the project root (one project's walk per project planned) |
| `atlas conform --project NAME --node PATH [--apply]` | Preview or apply the repair for one node, by project-relative path |
| `atlas conform --revert FILE [--apply]` | Preview or undo an applied conform from the `--json` manifest it printed; refuses a manifest from another drive or one whose paths leave the project |
| `atlas runs (--project NAME \| --all) [--days N] [--apply]` | List agent runs; zip the closed ones into `.agent/archive/` (ADR 0011). Preview by default |
| `atlas archive NAME [--apply]` / `atlas unarchive [NAME] [--revert FILE] [--apply]` | Archive a project to the map's `archiveRoot` (default `_Archived Projects`), stamping its project-index row; bring one back by name, or undo from the JSON manifest (ADR 0019). Preview by default |
| `atlas tyler [--write]` | Tyler digest: open errands from every project's `TYLER.md` + `DECISION` blockers from `TASKS.md` (ADR 0016). Opens with the Action Queue (send now, decide ranked by tasks blocked, due, oldest; 15 lines), then meetings not closed out when the map has a `meetings` rule. Prints; `--write` regenerates `_tools\TYLER-TODAY.md` |
| `atlas permits [NAME] [--json]` | Permit tracker (map key `permits`, ADR 0024): every application in each project's AHJ register, its Ball In Court (`US` / `AHJ` / `FIELD` / `CLOSED` / `?`, from the Status cell's first word) and days in the current state, dated by the `R<n>_YYMMDD` round folder when it can be, else by the register's own dates. Names round folders newer than the register and folders that do not parse. Read-only; exit 0 whatever it finds, 2 when the map has no rule |
| `atlas meetings [NAME] [--pending] [--json]` | Meeting Inbox (map key `meetings`): each project's recorded meetings and the minutes that close them, paired by the leading `YYMMDD` date (same day, then up to `windowDays` later). `--pending` lists only meetings with no minutes - the queue a scheduled `/meeting-closeout` works from. Read-only; exit 0 whatever it finds, 2 when the map has no rule |

TUI keys:

| Key | Does |
|---|---|
| `Enter` | Drill one Region in (list, tree, Companion), or confirm an armed repair or undo |
| `Escape` | Back one Region, clear a filter, or cancel an armed repair |
| `Tab` | Next Region |
| `/` | Filter the focused Region: projects by name or health, the tree by the names it has opened (never reading more). In the Companion it says what it can filter |
| `space` | Open or close a folder in the tree; mark a project in the list |
| `d` | Cycle the Companion: unmet Expectations, project health, dossier (the Dossier Facts Table: validated intake, contact snapshots, decisions summary - read-only; `e` edits, `o` opens), deep pass |
| `g` | Search the whole drive: live over the session Name Index, plus PDF text and Markdown from the local Content Index (built in the background on first use; `atlas index build` tops it up). Content matches rank below name matches with the matched line as a snippet; the Indexed-At Stamp shows under the results. `Enter` reveals the hit (the project in the list, or the node in the tree), `o` opens it, `Escape` closes. Archived projects are searched too: their rows say `archived` and come after every live row; `Enter` on one moves nothing and says so on the operation line (`U` unarchives it into the tree, `o` opens it in place). Results cap at 500 with the overflow counted |
| `[` / `]` | Collapse or restore the project list / the Companion |
| `z` | Zoom the focused Region to full width; press again to restore |
| `f` | Conform what has focus (below) |
| `u` | Preview undoing the last repair in this project; `Enter` confirms |
| `o` | Open what has focus (below) |
| `y` | Copy the full path of what has focus |
| `n` / `e` / `m` | New project / edit selected project / manage contacts |
| `a` / `c` | Add map-approved folders / clean folders with no files |
| `A` / `U` | Archive the focused project / list archived projects and un-archive one. Always the modal (ADR 0019 - never the inline confirm), carrying the model-file and open-task warnings and the vault/contacts-untouched note. The list drops (or regains) the project on the rescan after apply |
| `D` | Deep pass on the focused project: the opt-in walk below the root (receipt-rule sweeps, over-long paths, deep unreadables, item count), findings in the Companion's DEEP mode. No inline repair key - `atlas conform --deep --apply` sweeps from the CLI |
| `x` | Conform marked projects |
| `s` / `r` / `l` | Sort / rescan / last result |
| `?` / `Ctrl+P` / `q` | Help / command palette / quit. Palette entries name their key for `/`, `g`, `d`, `[`, `]`, `z`, `f`, `u`, `o`, `y`, `c`, `A`, `U` and `D` |

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
batch conform clears that project's, and switching drives clears all of it. Archives ride
their own undo: an archived project leaves the list, so there is no row for `u` to select -
`U` is the inverse, running the un-archive plan through the same Guard and modal (ADR 0019).

Which Region has focus reads without moving the cursor, in both Compositions: the focused
Region's frame is heavy and full-strength, the rest are muted, and Region titles follow.
The distinction is weight and luminance, never hue alone (ADR 0008); the same rule covers
the filter inputs, modals and the search overlay.

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

## Receipt Rules below the root

File Rules stop at the project root. Agent scratch - a run zip, a log - that lands
inside a numbered section is the same filing mistake one folder down, and the map's
`receiptRules` catch it (ticket 26, ADR 0009 amendment):

```json
"receiptRules": [
  { "name": "Run zips", "target": ".agent/runs",    "match": { "extensions": ["zip"] } },
  { "name": "Logs",     "target": ".agent/backups", "match": { "nameRegex": "\\.log$" } }
]
```

Same shape as `fileRules`, three fences tighter: name filters only (`pdfText` refuses
the map - a content test at depth is a download per candidate), and the target must
resolve inside the agent workspace (`runsDir` or `backupsDir`), so a Receipt Rule can
move machine receipts out of the numbered tree and can never reorder a person's
filing. A match is a finding, never a Filing State - a receipt inside `06 Research`
is still Mapped by containment.

Receipt Rules are evaluated only in the opt-in deep pass: `atlas doctor --deep NAME`
reports matches as `sweep pending (deep)` with the rule name, and `atlas conform
--project NAME --deep` previews and applies the resulting Sweeps through the same
Plan, Move Manifest and `conform --revert` undo as any other conform. The walk
enumerates and never opens a file; it is one project at a time (`--all --deep` pays
the full drive walk by flag, never by default). The default `doctor` / `conform`
pass stays root-only. In `--json`, deep matches are the project row's `receipts`
array, flagged `"deep": true` beside the root-only `sweeps`.

The same walk gathers three more findings, each its own line in the report and its own
`--json` field, never bundled into the sweep counts (plan 1.4-1.6):

- **Over-long paths** (`overlong`): paths already past the length Win32 opens without the
  extended-length prefix, named with their length - ticket 04's warning covers what Atlas
  is about to create; this covers what nobody is moving. Only the first crossing per
  branch is named; everything below an over-long folder inherits it. A warning finding:
  it never changes a project's status, because shortening a path is a person's call.
- **Deep unreadable folders** (`unreadable_deep`): a folder the walk could not open is
  reported, never read as empty (ADR 0004) - even on a map with no `receiptRules` at all.
- **Item counts** (`items`, and the drive-level `budget` block): files and folders per
  project against the 400,000-item shared-drive cap, free on top of the enumeration.
  The text report prints a one-line budget summary once the count passes half the cap;
  `--json` always carries it, with `items: null` and `counted: false` in the default
  pass - uncounted is null, never a silent zero.

A pathological tree is bounded by a depth guard (64 levels); a folder at the boundary is
named in `depth_capped` rather than the scan pretending it saw everything.

## Root names Atlas never flags

Some files only work at a project root: `.mcp.json` is read from the root by MCP-capable
agents, `.pi` holds Pi session state. Filing them would break the tools, so flagging them
Unfiled is a finding nobody can act on. The map's `tolerated` list names them (ADR 0018):

```json
"tolerated": [".mcp.json", ".pi", ".claude", ".codex", ".agents"]
```

Doctor never reports a tolerated name as unfiled, no File Rule matches one, and conform
never plans on one. The skip is stated, not silent: doctor prints tolerated entries as
`ignored` and `--json` carries an `ignored` array per project. Entries are bare root
names or globs - a path separator refuses the map. An older Atlas reading a newer map
ignores the key and simply keeps flagging the names.

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

A child in the map may be `{"name": "Archive", "seed": true}`. Seeded children of a seeded
section are created with a new project, kept by clean, and backfilled by conform.

## Reference sets

```
atlas refs [--root DIR] [--json]
atlas refs check <draft> [--type TYPE] [--exemplar ID ...] [--project DIR] [--json]
atlas refs doctor [--root DIR] [--json]
atlas refs index [--root DIR] [--apply] [--json]
atlas refs gallery [--root DIR] [--json]
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
then `$ATLAS_REFERENCE_SETS`, then the drive map's top-level `referenceSets`.

`atlas refs doctor` validates every set: card front matter (all governance keys, `status`
in candidate|approved|retired, ISO dates, approval fields on approved cards), a `NOTES.md`
with a non-empty `leak_list` in every exemplar/near-miss/redline folder, every exemplar id
the card names existing on disk, card under 150 lines with no line over 2,000 characters,
and no `.lnk` shortcuts. A `next_review` in the past flags the set STALE - a warning, not
a problem. Exit 0 clean, 2 on problems or error.

`atlas refs index` rebuilds the sets README's contents block (between
`<!-- atlas:contents-begin -->` / `<!-- atlas:contents-end -->` markers) from card front
matter (ergonomics plan Phase 2, rules/visual-markdown.md). The block is a Mermaid
`flowchart LR` band map - one subgraph per lifecycle band (bands from the folder-number
prefix: 01-09 due diligence, 10-13 client & control, 14-16 permitting, 19 design, 20-29
drawings, 40-49 construction, 90-99 control files; a data-driven table in
`core/refsets.py`, so a new band is a one-line edit), one short node per set, status as
classDef colour plus a word legend, never a click link - then one 3-column table per band
(`Set | Status | Card`, %20-escaped relative links, `(STALE)` as a word, never colour
alone). Map and tables come from the same front matter, so they cannot drift. Dry run
prints the diff; `--apply` writes. An unchanged regenerate is byte-identical.

`atlas refs gallery` writes `Reference Sets.html` beside the README - the
human-facing browse page (Tyler, 2026-10-09): one tile per set under the same
bands, status as word plus colour, the card's first "Use when" line, card,
folder and per-exemplar links (a frozen PDF links directly), and a thumbnail
from an exemplar's `Pages/` PNGs where a drawing set has them. Self-contained
- inline CSS, a vanilla JS filter box, a sticky band nav, every href relative
and URL-encoded - so it opens from `file://` on the library drive. No
timestamps: an unchanged regenerate is byte-identical. Writes directly and
prints the path; exit 0, 2 on error.
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

Every capability that writes, and every fact the console can show, has a CLI form with `--json` (ADR 0008): `doctor` for the drive, `tree` for the nodes below a project root and its unmet Expectations, `search` for the drive-wide Name Index, `index status` for the per-machine Content Index, `conform --node` for a single repair, `conform --revert` for undo, and `--deep` on `doctor`/`conform` for the deep pass below a project root (in the console, `D` runs the same walk for the focused project and the Companion's DEEP mode renders it). Two differences remain. The console's undo stack lives in memory for one session, while the CLI undoes from the manifest a `--json` apply printed. `tree` reads only as deep as `--depth` asks, where the console reads each folder as you open it. The CLI is plain text and is the supported path for automation - and for anyone the console does not serve.

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
