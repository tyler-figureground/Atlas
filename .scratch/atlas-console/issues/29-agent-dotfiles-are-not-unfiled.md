# Agent dotfiles at the project root are not unfiled

Type: task
Status: built and deployed (2026-10-09, Atlas 0.12.0 on the drive)
Blocked by: -
Parent: ../map.md

Raised from a live conform sweep (2026-10-09): after every real item was filed,
`doctor` still reported `260527_211 centre street ny-Montez Radio (MPR)` and
`260924_315 West Ln-Beitz Fire Cleanup` as UNFILED on exactly two entries each -
`.mcp.json` and `.pi`. Both are agent tool config that must sit at the project
root to function: `.mcp.json` is read from the root by MCP-capable agents, and
`.pi` holds Pi session state. Filing them into a section breaks the tools, so
the finding is unactionable - the one thing an unfiled finding must never be.

## Question

Agent config at a project root (`.mcp.json`, `.pi`, and their successors -
`.claude`, `.codex`, `.agents` are the obvious next ones) is control-plane by
nature, not drift. Doctor's unfiled scan should not count it. Two shapes:

- **Ignore list in the map.** `architecture-map.json` gains an `ignore` (or
  `controlPlane.dotfiles`) list of root names doctor skips. The map is the
  studio standard, so the list is versioned and lintable beside the sections.
  New agent tools mean a map edit - which is correct: the studio decides what
  is blessed.
- **Skip all dotfiles.** Doctor never reports a root entry whose name starts
  with `.`. Simpler, no map change, but it blesses anything hidden - a stray
  `.~lock` or `.DS_Store` would pass silently, and a genuinely misfiled
  dotfolder would too.

First shape fits the house rule that Atlas says plainly what it skipped rather
than passing a silent zero; the ignore list itself is the plain statement.

## Constraints

- The skip must be visible in `--json` (ADR 0008): an `ignored` count or list
  on the project report, never a silent absence - same false-negative trap as
  an unreadable folder reporting as empty.
- `conform` must never plan an action on an ignored entry, and the tree view
  should agree with doctor on what is ignored (one list, one place - the map).
- Map version bump with a `versionNote`; existing projects conform without a
  conform pass, since the change only removes findings.
- Fixture drives only for tests. Exit codes keep the contract: `0` clean,
  `1` findings, `2` error.

## Built (2026-10-09)

The first shape. `tolerated` is a top-level map key - bare root names or
fnmatch globs, a separator or non-string refuses the whole map. Doctor excludes
matches from unfiled and from File Rule matching, and reports them as `ignored`
in text and `--json`; conform plans nothing for them, and the tree agrees for
free since it draws Filing State from the same report. Hard-coded OS noise
(`desktop.ini`, the ledger family) stays hard-coded and silent - a map-listed
`ignored` line on every project would be noise. ADR 0018; drive map at v3.8
with the first list (`.mcp.json`, `.pi`, `.claude`, `.codex`, `.agents`);
Atlas 0.12.0. 8 new tests, 926 pass. Deployed same day: wheel on
`_tools\atlas\`, `Atlas.bat` repinned, verified through the launcher - doctor
15 conform / 0 drift / 0 unfiled on map v3.8. Deploy commit `a505faf`.

One hazard surfaced mid-build: a concurrent session wrote its own v3.8/
tolerated draft to the drive map (as "Atlas >= 0.11.3") while this one was
applying the same change, and Google Drive sync interleaved the two writes -
two v3.8 notes and a clobbered list. Repaired to one note and the five-name
list, but the other session may still be holding its draft.
