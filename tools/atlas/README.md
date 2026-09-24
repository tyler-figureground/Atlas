# Atlas

Map-driven TUI/CLI for studio shared-drive project tooling. Replaces the PS1/BAT
generation (`New-Project`, `Add-Section`, `Clean-Empty`, `Conform-Project`) per the spec:
`LIBRARY - Reference\_House Standard\atlas-tui-spec.md` (Google Shared Drives).

The drive's `_tools\<drive>-map.json` is the only folder-structure brain - Atlas hard-codes zero canonical folder names. Reusable contacts live beside it in `_tools\billing-contacts.json`.

## Status: operations console

Atlas diagnoses and safely repairs mapped project-folder differences. Every mutation uses the
same core plan as the CLI. Conform previews exact changes, never overwrites destinations, and
leaves conflicts in place. Clean removes file-empty folders only.

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
| `atlas clean --project NAME [--apply]` | Preview or remove empty folders |
| `atlas conform --project NAME [--apply]` | Preview or apply mapped repairs |
| `atlas conform --project NAME --node PATH [--apply]` | Preview or apply the repair for one node, by project-relative path |
| `atlas conform --revert FILE` | Undo an applied conform from the `--json` manifest it printed |

TUI keys: `n` new project, `e` edit selected project, `m` manage contacts, `/` filter the
focused Region (projects by name or health; the tree by the names it has opened, never reading more),
`Enter` drill in or confirm, `Escape` back, `Tab` next Region, `Space` mark or open a folder,
`x` conform marked, `a` add folders, `f` conform, `u` undo, `?` help, `Ctrl+P` command palette.
Additional actions remain searchable in the palette.

`f` acts on whatever has focus: the whole project from the list, one folder or file from the
tree. A single repair previews on the operation line and waits for `Enter`; nothing is written
until then. `u` undoes the last repair in that project.

Exit codes: `0` clean, `1` findings/pending work, `2` error. `--json` is the agent interface.

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

## Editing projects and contacts

Select a project and press `e`. Atlas pre-populates every intake field, shows the derived folder name, then requires a second confirmation when Address or Description changes the folder path. It refuses collisions and updates `PROJECT.md` plus the project-index row together. Project contact reassignment refreshes that project's snapshots only.

Press `m` to edit the shared contact directory. Contact IDs remain stable. Contact mailing addresses accept numbered streets, `PO Box`, and `P.O. Box`; project site addresses still require a physical numbered street. Shared contact edits do not rewrite historical project snapshots.

CLI edit commands are interactive when run in a terminal. Omitted fields retain their current values. Automation and `--json` require `--yes`; a folder rename also requires separate `--rename` approval. Use `--dry-run` to inspect the project-update plan without changing files. Run `atlas project edit --help` or `atlas contacts edit --help` for field flags.

## Accessibility

Atlas has not been validated with assistive technology and makes no accessibility conformance claim. Textual's screen-reader support is unresolved upstream ([textual#2425](https://github.com/Textualize/textual/issues/2425)), so the console should not be assumed usable with a screen reader.

Every capability that writes, and every fact the console can show, is also reachable from the CLI with `--json`. That path is plain text and is the supported one for automation - and for anyone the console does not serve.

Within the console, colour reinforces a distinction and never carries one alone. A folder or file with something wrong with it names what is wrong in words; when the terminal is too narrow for the full phrase the word abbreviates - `NAME`, `PLACE`, `LOOSE`, `UNMAPPED`, `unread` - rather than leaving the glyph and its colour to say it. A long name shortens in the middle so the word always stays on screen.

## Install

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

## Dev

```bash
cd tools/atlas
uv sync
uv run pytest
atlas doctor --drive "G:/Shared drives/ARCHITECTURE"
```
