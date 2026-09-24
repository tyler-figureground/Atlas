# atlas tree - the tree's facts on the CLI

Type: task
Status: resolved (GitHub #30) - `cmd_tree` in `cli.py`, tests in `tests/test_tree_cli.py`
Blocked by: -
Parent: ../map.md

## Question

ADR 0008: a capability that **produces a fact** owes a CLI form. The tree produces
one nothing else does - the Filing State and Load State of every node **below** a
project root. `doctor` stops at the root, because `report_project` has no opinion
deeper than that and its 4.24-second drive-wide cost is bounded precisely because
it does not descend.

This is ticket 22's retroactive debt. The widget shipped in session 8, before ADR
0008 existed, so the obligation is being paid late and on purpose rather than
folded into another ticket's commit.

Build `atlas tree PROJECT [--drive D] [--json] [--depth N]`:

- **A thin wrapper over `core.tree`.** The seam is built, tested and lazily
  expanding. This subcommand should own no filesystem logic of its own - if it
  needs any, that is a sign the seam is missing something and the seam is where it
  goes.
- **`--depth N`** gives the caller the cost control the TUI gets from lazy
  expansion. Default shallow. Unbounded depth on a streaming mount is the thing
  ticket 06 spent a session ruling out, and `Path.rglob` is banned outright - it
  swallows every `OSError`.
- **`--json` emits nodes keyed by Node Key**, each carrying `filing`, `load`,
  `is_dir`, and - only where Load State is Read - `folders` and `files`. Never a
  zero count on an Unread folder: ticket 13's rule, and the same false negative as
  an unreadable folder reporting as empty.
- **Plain-text output is for a person reading a terminal.** Indented outline, the
  Fault Word spelled out. It is not the `--json` shape rendered.
- **Unmet Expectations are not nodes** (ADR 0004). If they appear at all they are
  a separate list, exactly as the Companion draws them - never inline.
- **`doctor` is untouched.** Its output shape is the one worth keeping stable.

## Why it is worth doing

Without it there is a fact Atlas knows and no agent can reach, which is precisely
the hole ADR 0008 was written to close. It is also the cheapest possible test of
whether the seam ticket 07 built is actually a seam: a second consumer that is not
a Textual widget either uses it cleanly or exposes what the widget was carrying.

## Constraints

- ADR 0007 is the seam. ADR 0004 is the state model. ADR 0008 is why this exists.
- Exit codes follow the existing contract: `0` clean, `1` findings, `2` error.
- Fixture drives only.
- Ticket 13 stands: immediate-child counts only, never recursive.
- `--json` has no consumers today. Design the shape for the one that is coming,
  and do not infer a requirement from a caller that does not exist.
