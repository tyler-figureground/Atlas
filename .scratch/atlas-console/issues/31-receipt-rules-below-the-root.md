# Receipt Rules - machine-file sweeps below the project root

Type: task
Status: closed (2026-10-08)
Blocked by: -
Parent: ../map.md

Graduated from [ticket 26](26-file-rules-below-the-root.md), which decided the
design. Build it.

**Built 2026-10-08.** `receiptRules` map key (strict parse, name filters only,
targets restricted to `runsDir`/`backupsDir`), `core/receipts.py` deep pass
(prunable scandir walk, long_path at every level, workspace and junctions
never entered, unreadable reported), `doctor --deep PROJECT|--all` and
`conform --deep` planning receipt SWEEPs through the unchanged
plan/apply/manifest/`--revert` path; `--json` gains a per-project `receipts`
array flagged `"deep": true`; lint warns on duplicate receipt rule names. ADR
0009 amendment applied, Receipt Rule and Deep Pass landed in `/CONTEXT.md`,
research backlog item 2 marked done. 963 tests pass (926 before + 37 new).
Deviation: the deep pass is CLI-only - the console surfaces deep findings only
when an operator runs the deep pass there, and no console key was added
(ticket 31's done-when does not ask for one).

## What to build

A second, opt-in rule class in the drive map, `receiptRules`, that fires below
the project root. Decision and reasoning on ticket 26; the shape:

- **Map schema.** `receiptRules`: a list of `{name, target, match}` entries,
  same shape as `fileRules` but name filters only - `extensions`, `names`,
  `nameRegex`; `pdfText` in a Receipt Rule's `match` refuses the map. `target`
  must resolve inside the map's agent workspace (`runsDir` or `backupsDir`);
  anything else refuses the map. Malformed rule refuses the whole map, the ADR
  0009 discipline.
- **Deep pass, opt-in only.** `atlas doctor --deep PROJECT` walks one project
  and reports Receipt Rule matches as findings carrying Sweep Offers, with
  `(rule: NAME)` as File Rules do. `atlas conform PROJECT --deep` plans and
  applies the resulting Sweeps through the existing Plan / preview / Guard /
  Move Manifest / undo path - no new action kind (ADR 0006 stands; a SWEEP with
  a nested `src` already works through `_apply_sweep`, the scoped Guard's
  `parent_key`, and `invert_plan`). `--all --deep` is legal and pays the full
  drive walk by flag, never by default. The default `doctor` / `conform` pass
  is unchanged: root-only.
- **Filing State untouched.** A matched file is still Mapped by containment in
  the tree and earns no repair key. The finding lives on the doctor/conform
  surface and in `--json` (with a flag distinguishing deep sweeps from root
  sweeps). ADR 0004 and ADR 0007 are not amended.
- **CLI parity (ADR 0008).** The deep pass *is* the CLI form; the console
  surfaces deep findings only when the operator runs the deep pass from the
  console - same command, same plan, modal confirm (a deep conform is
  multi-action, so ADR 0006's confirmation-weight rule already puts it there).
- **ADR amendment.** Add the ticket 26 amendment text to ADR 0009 (drafted on
  ticket 26). Land the vocabulary - Receipt Rule, Deep Pass - in `/CONTEXT.md`.
- **Map delivery.** The first real `receiptRules` block for the studio map is a
  separate production write; this ticket ships the capability plus fixture-map
  coverage only.

## Constraints

- Never touch the production drive. Fixture drives only, per the map's standing
  constraints.
- No content reads below the root: no `pdfText`, no file opened, enumeration
  only. The deep pass walks; it never downloads.
- Emits a Sweep or it emits nothing (ticket 26's constraint).
- Guard strength follows scope (ADR 0006): the deep pass is a whole-project
  plan, so it keeps the project-wide guard; per-node inline repair does not
  apply.

## Done when

- `receiptRules` loads strictly (bad filter key, `pdfText`, or a target outside
  the agent workspace each refuse the map), and an old map without the key
  loads unchanged.
- `atlas doctor --deep PROJECT` on a fixture project with receipts in a
  numbered section reports them, names the rule, and `conform PROJECT --deep`
  sweeps them to `runsDir` with preview, modal-equivalent confirmation, Move
  Manifest and working undo (`conform --revert`).
- The default `doctor` on the same fixture reports none of it.
- Tests green (`uv run pytest`), including: containment still decides the deep
  node's Filing State; a swept receipt's undo restores the nested path; a name
  collision at the target is a Conflict, not a clobber.
- ADR 0009 amendment applied; `/CONTEXT.md` terms landed; the research backlog
  (`docs/research/atlas-file-management-oss.md` item 2) marked done.
