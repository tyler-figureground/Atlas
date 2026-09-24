# The same file in four folders, as a doctor finding

Type: task
Status: open
Blocked by: -
Parent: ../map.md

## Question

From `docs/research/atlas-file-management-oss.md`. A studio drive accumulates the same
issued PDF in the transmittal folder, the consultant folder, a dated subfolder, and
someone's desktop copy. Atlas has no opinion about it.

Report duplicates read-only, as a finding beside the existing ones.

- **fclones** (MIT, Rust) is the tool: JSON output, and a published benchmark puts it
  about 4x faster than rmlint and 9x faster than jdupes. Windows-capable; its
  copy-on-write dedupe is Linux-only and irrelevant here.
- **Report mode only.** Never `fclones remove` or `link`. Every Atlas write crosses a
  Plan, and a deletion that Atlas did not plan is a deletion it cannot undo. If
  duplicates ever become removable, the removal is an Action with a Move Manifest, and
  it is a separate ticket.
- **Optional dependency.** Atlas must run identically with fclones absent. Missing
  binary means the finding is not produced, said plainly - never a silent zero, which
  is the same false negative as an unreadable folder reporting as empty.
- Decide what the unit is: duplicates within one project, or across the drive. Across
  is more useful and much more expensive, and `doctor` is already 4.24 seconds.
- Hashing every file on a streaming mount **downloads every file**. This is the
  headline cost and it may sink the whole idea. Size-and-name pre-filtering, or
  scoping to one project on demand, are the obvious mitigations - measure before
  building.

## Constraints

- Fixture drives only. If a real measurement is needed, read-only, and ask first.
- Exit codes follow the existing contract: `0` clean, `1` findings, `2` error.
- ADR 0008: the finding owes a `--json` shape.
