# 24. Permit status is read from the AHJ register; the round folders are evidence

Date: 2026-10-31

## Status

Accepted. Atlas 0.24.0, drive map v4.4 (`permits` key). Narrows roadmap F3
(`docs/plans/2026-10-atlas-roi-roadmap.md`): the `--sync` write it proposed is deferred, so
no exception to ADR 0012's create-only rule is made.

## Context

Roadmap F3 assumed the AHJ register (ADR 0013, 0021) was empty and the evidence sat in
`R<n>_YYMMDD` round folders, so Atlas would derive applications from the folders and append
register rows. A read-only survey of the drive on 2026-10-31 found the reverse:

- Every project with a live application (2267 Monticello, Pestoni, 315 West Ln, 1655 San
  Vicente) has a register with full rows - agency, permit number, status with its date,
  round, next action, owner - kept by agents during closeouts and correspondence work.
- Only Monticello files rounds as `R<n>_YYMMDD`. Pestoni uses `V1 Submission`, `V2
  Submission` and loose files; West Ln uses `V2` and loose files. No file name carries an
  agency, so a folder cannot say which application it belongs to.

Rows derived from the folders would be thinner than the rows already there, would duplicate
them, and could not name their agency. The register is the better source.

## Decision

- **The register is the source.** `atlas permits` reads each project's register
  `## Applications` table. One row is one application. Its Status cell starts with a word
  from the template's vocabulary, which sets the **Ball In Court**: `US` (researching,
  preparing, comments, approved - we owe the next move), `AHJ` (submitted, in review,
  resubmitted), `FIELD` (inspections), `CLOSED` (issued, finaled, withdrawn). A status
  outside the vocabulary is `?`, never guessed.
- **Folders are evidence.** The round folders under `03 Submissions` and
  `04 Comments & Responses` give dates. When a row's Round matches a folder round, the
  folder date dates the current state (submitted for `AHJ`, comments received for `US`).
  Folders carry no agency, so this applies only when exactly one row in the register has
  a round; with two, `R1` could be either one's. Otherwise the state is dated by the
  latest ISO date in the Status cell, then the Submitted cell; with none, days are
  unknown.
- **Disagreement is a finding, not a fix.** A folder round newer than any round in the
  register, round folders with an empty register, and a folder that does not parse as
  `R<n>_YYMMDD` are reported - in `atlas permits` and as `doctor --deep` warnings. Atlas
  never rewrites the register; the person or agent who keeps it updates it.
- **Paths and the stuck threshold live in the map** (`permits`: register, submissions,
  comments, permits folders, `stuckDays`, default 30). Absent key, check off.
- **Digest.** The Tyler digest gains a Permits block: every `US` application, every `AHJ`
  application past `stuckDays`, and the folder/register disagreements.
- **Console.** A Permits Companion Mode (`d` cycles) shows the selected project's
  applications. Read-only.

## Consequences

- Permit status is only as current as the register. That is where agents already write it,
  and the disagreement findings point at a register that has fallen behind its folders.
- No write path, so no Plan, preview or undo is needed, and ADR 0012 stands unamended.
- `--sync` (appending rows the folders prove) is deferred, not rejected. Revisit if
  round-folder naming becomes the norm and a register is found empty while its folders are
  full - the disagreement finding is how that case would surface.
- Projects that name rounds `V1`/`V2` get no folder dates until they follow the template's
  `R<n>_YYMMDD` rule; doctor names each such folder once.
