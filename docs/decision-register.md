# Human-readable decision registers

## Two depths, one workbook

The spreadsheet stays canonical. `Team View` is the team's entry point; the original
`Decision Register` tab is the evidence record. IDs link the two. No second register,
no discarded history, no migration of client work into a new app.

Six visible columns:

| Column | Content | Character budget |
|---|---|---|
| ID | Permanent reference; link to detail | Existing ID |
| Topic | Plain-language subject | 55 |
| Current position | Current choice or explicitly tentative direction | 150 |
| Status | Existing decision status | Existing vocabulary |
| Owner | Recorded owner, not guessed authority | 40 |
| Next / due | Outstanding question/action; date only when sourced | 100 |

Priority, phase, stakeholders, cost/schedule impacts, source links, old questions,
comments and full rationale stay available in detail. None needs a front column.
A decided design choice can still have an unresolved repair or verification. Keep
that visible in Next / due; don't silently change its decision status.

**One screen means no horizontal scavenger hunt.** It does not mean shrinking an
entire project to 79 unreadable rows. Vertical scrolling and deliberate status
filtering are normal. Default opens with every record visible, headings frozen,
readable text, bounded row heights and no hidden columns.

## Every update

1. Back up the workbook outside the client-facing folder; check no other writer.
2. Read full evidence for affected IDs. Update detail without erasing prior rationale.
3. Replace short front summaries. Never append dated paragraphs to these cells.
4. Read all changed rows back. Preserve uncertainty, safety qualifications and sources.
5. Run the saved-workbook checker. Fix failures without truncating text or shrinking it.
6. Regenerate short Markdown summary and full Markdown detail. These are read-only copies.
7. Inspect actual spreadsheet rendering when available. Report a missing renderer;
   character counts and formatting properties alone are not a visual pass.

## Tooling

Requires Python and `openpyxl`. `check --render` additionally uses
`aspose-cells-python` to measure actual wrapped row heights; it never saves that
engine's copy or publishes evaluation-watermarked images. Use it before handoff
alongside visual inspection, not as a substitute for reading the summaries.
From the repository root:

```bash
uv run --with openpyxl python scripts/decision_register.py build register.xlsx --summaries summaries.json --output candidate.xlsx
uv run --with openpyxl --with aspose-cells-python python scripts/decision_register.py check candidate.xlsx --render
uv run --with openpyxl python scripts/decision_register.py export-summaries register.xlsx --output summaries.json
uv run --with openpyxl python scripts/export_decision_register.py candidate.xlsx decisions/REGISTER.md
uv run --with openpyxl python -m unittest discover -s scripts/tests -v
```

Supported detail layout: `Decision Register`, row 4 headers, rows 5 onward, columns
A-V (Montez's existing format). Other layouts need an explicit adapter, not guessed
column positions. `build` writes a different output file; validate and compare the
candidate before replacing the live workbook. Keep a rollback copy. Do not use
`data_only=True` when writing: it destroys formulas.

Summary input is a JSON list with `id`, `topic`, `position`, `next`. It is migration
input, not another source of truth. Later edits start from the live workbook via
`export-summaries`; never replay an old JSON file over human edits. A checker cannot
prove that a short summary means the same thing as its source: that read-back remains
mandatory. Installed project-local tools travel with the project; refresh them when
the shared tool changes.

## Evidence behind this change

Montez inspection: 79 decisions, 22 columns; largest Comments cell 10,901 characters,
largest Open Questions cell 4,157, largest Decision Made cell 2,319. Existing workflow
explicitly required append-only cell updates. Its Markdown exporter cut cells at
800 characters, so the agent copy was not full evidence either.

This is a presentation migration, not a decision audit. Existing statuses, ownership,
source text, formulas and rationale must survive. Short summaries must not silently
resolve disputed or outdated facts. No drive-wide migration is implied: apply to
Montez first, then use the shared contract when other registers are updated.
