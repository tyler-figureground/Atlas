# 9. File Rules file Loose root files by name and content, and emit nothing but Sweeps

Date: 2026-09-10

## Status

Accepted

Extends the drive map schema (spec section 8) with one optional key, `fileRules`.
Constrained by ADR 0004 (Filing State), ADR 0006 (the tree invents no action kinds)
and ADR 0008 (a fact owes a CLI form). Research behind it:
`docs/research/atlas-file-management-oss.md`.

## Context

Atlas conforms **folders**. The one thing it could do with a file was sweep it from
a project root into a folder, and only when a glob in `relocations` named it -
`"HANDOFF-*.md": ".agent/handoff/"`. Every other root file was Unfiled: a person had
to look.

Most of what lands at a project root is recognisable on sight. A fee proposal is an
`.xlsx`. An RFI is `260901_RFI-004.pdf`. A permit set says ISSUED FOR PERMIT in its
title block. A glob on the name catches the first two only if the author guessed
every spelling, and cannot catch the third at all.

The research asked which open-source tool could do this. The best fit was the design
of organize (tfeldmann/organize, MIT): rules of filters and actions, filters ANDed,
simulate-first. Its code was not a fit. It has its own config file, and the drive
map is the only folder-structure brain. It performs its own moves, and Atlas moves
nothing outside a Plan.

## Decision

**A File Rule is a map entry that makes a root file Loose.** It names a target folder
and a `match` of filters:

```json
"fileRules": [
  {
    "name": "Issued sets",
    "target": "08 OUT/Transmittals",
    "match": { "extensions": ["pdf"], "pdfText": ["issued for permit", "issued for construction"] }
  },
  { "name": "Fee sheets", "target": "10 Legal/Invoices", "match": { "extensions": ["xlsx"] } },
  { "name": "RFIs", "target": "08 OUT/RFI", "match": { "nameRegex": "^\\d{6}_RFI-\\d+" } }
]
```

- **Filters:** `extensions` (case-insensitive, dot optional), `names` (fnmatch globs,
  case-insensitive), `nameRegex` (`re.search`, case-insensitive), `pdfText` (any
  phrase, case- and whitespace-insensitive, in the document title, subject or
  keywords, or on page one). Every filter given must match; within one filter any
  value may.
- **Output is a Sweep and nothing else.** A matched file joins `ProjectReport.sweeps`,
  which is where Loose already came from. Conform, the tree's Filing State, the repair
  key, the inline confirm, the Guard, the Move Manifest, undo, `conform --node` and
  `conform --revert` all work unchanged. No new Action kind, no new Filing State - ADR
  0006's rule held with room to spare.
- **First match wins, in map order, after the glob relocations.** An older rule's
  meaning never shifts because a broader one was added below it.
- **Never the control plane, never a tolerated file, never a folder.** A rule for
  `*.md` does not file `PROJECT.md` away. Loose is a Filing State of files.
- **Root files only.** Below the root, containment decides Filing State (ADR 0007) and
  `doctor` does not descend. Rules below the root are ticket 26, not this.
- **A malformed rule refuses the whole map.** Structure is checked in `load_map`, not
  in lint. An unknown filter key, an empty `match`, a bad regex, or a target outside
  the project raises `MapError`. The failure this prevents is the dangerous one: a
  misspelled `extension` silently ignored leaves a rule that matches every root file,
  and a rule that matches more moves more. Lint keeps the semantic checks - a target
  outside the map (error), an unblessed child (warning), two rules sharing a name
  (warning).
- **Content is read last, and only when it can matter.** Name filters run first. Only
  a file named `*.pdf` is opened for `pdfText`. Never past `content.PDF_READ_LIMIT`
  (64 MB). Cached by path, size and mtime. A file that cannot be read - malformed,
  truncated, password-locked, not a PDF - never matches. A permission-only lock (the
  usual state of an issued set) opens with an empty password, hence
  `pypdf[crypto]`.
- **`doctor` names the rule.** `ProjectReport.sweep_rules` carries (file, rule name);
  `doctor` prints `(rule: NAME)`; `--json` sweeps carry `"rule"`, null for a glob
  sweep; the console's project detail shows it too. ADR 0008's obligation is met by
  the existing `doctor` and `conform`, with no new subcommand.

## Consequences

`pypdf[crypto]` is Atlas's second runtime dependency and its first native one:
`cryptography` ships Windows wheels, so `uv tool install --editable` still needs no
compiler.

`atlas.core.content` is the only module that opens a file to read it. That is a new
cost category: on the Drive mount, reading a file downloads it. The mitigations above
bound it but have not been measured against the studio drive, because development
never touches it. **Measure before putting a broad content rule on a real map.**

The same module silences the `pypdf` logger on import. pypdf reports damaged files
through `logging`, and with no handler that prints to stderr - on top of the console.
Two tests pin it, and both run in a subprocess, because pytest attaches its own
capture handlers to non-propagating loggers and hides the leak from any in-process
test.

The feature is inert until a drive's map carries a `fileRules` block. The PowerShell
tools read the map with `ConvertFrom-Json` and ignore keys they do not know. The
spec's section 8 schema table lives on the shared drive and still needs the key added
by hand.

Rules introduce **the first Filing State that can change without the directory
changing**. Edit a PDF so its title block no longer says ISSUED FOR PERMIT and the
file stops being Loose, though no listing moved. The Guard copes, because it
re-derives the Plan before writing and a Plan whose rule stopped matching is Stale.
But the tree's 60-second Shelf Life keys on listings, so a tree row can say Loose for
up to a minute after its content changed. Acceptable - the Guard refuses the write -
and recorded here so nobody rediscovers it.
