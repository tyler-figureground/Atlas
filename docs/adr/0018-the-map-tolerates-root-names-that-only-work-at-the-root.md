# 18. The map tolerates root names that only work at the root

Date: 2026-10-09

## Status

Accepted

Extends the drive map schema with one optional key, `tolerated`. Constrained by
ADR 0004 (never a silent zero), ADR 0008 (the fact owes a CLI form) and ADR 0009
(a rule never touches what the map has claimed). Ticket:
`.scratch/atlas-console/issues/29-agent-dotfiles-are-not-unfiled.md`.

## Context

Agents write config at the project root because that is the only place their
tools read it: `.mcp.json` is MCP server config resolved from the working
directory, `.pi` holds Pi session state, and `.claude`, `.codex`, `.agents` are
the same idea for other harnesses. Doctor flagged all of them Unfiled - a
finding whose only definition is "a person has to look and file it" - but
filing them breaks the tools. The finding was unactionable, the one thing an
Unfiled finding must never be.

A hard-coded exemption was rejected. `TOLERATED_ROOT_FILES` already exists in
`doctor.py` for universal background (`desktop.ini`, the PRD-209 ledger family),
and it is the wrong home for a studio decision: which agent harnesses are
blessed is the studio's call, it changes as tools change, and the drive map is
the only folder-structure brain (ADR 0002, the spec's map-first rule). A blanket
"skip all dotfiles" was rejected too: it would pass `.~lock` and `.DS_Store`
junk silently - the same false negative as an unreadable folder reading as
empty.

## Decision

**`tolerated` is a top-level map key: a list of bare root names or fnmatch
globs that doctor never flags.**

```json
"tolerated": [".mcp.json", ".pi", ".claude", ".codex", ".agents"]
```

- **Map-owned, one list, one place.** Doctor, conform and the tree all read the
  same list from the map. The tree agrees for free: it draws Filing State from
  the same `ProjectReport.unfiled` doctor builds.
- **Ignored, not invisible.** A root entry the list claims is reported on the
  project as `ignored` - in doctor text and in `--json` - so the skip is a
  stated fact, never a silent absence (ADR 0004's rule applied to a skip).
  Hard-coded OS noise stays silent: a `desktop.ini` line on every project is
  noise, not information.
- **Never actionable.** Tolerated entries are excluded from File Rule matching
  (a `*.json` rule must not file `.mcp.json` away) and conform plans nothing
  for them, exactly as it plans nothing for Unfiled.
- **Strict parse.** A `tolerated` entry with a path separator, an empty
  string, or a non-string refuses the whole map - a pattern with a separator
  would tolerate nothing while looking like it works.
- **Old Atlas, new map.** The key is optional and unknown keys are ignored, so
  a drive on an older wheel keeps working; it simply keeps flagging the
  dotfiles until it is upgraded.

## Consequences

- Map v3.8 carries the first list. Adding a newly adopted agent tool is a map
  edit plus a version note, not a release.
- `ProjectReport` gains `ignored`; the doctor `--json` project row gains an
  `ignored` array. Both are additive - consumers that predate them are
  unaffected.
- `desktop.ini` and the `jdp-time-ledger.ndjson` family stay hard-coded. They
  are universal background, not studio decisions; moving them to the map would
  add an `ignored` line to nearly every project on the drive.
