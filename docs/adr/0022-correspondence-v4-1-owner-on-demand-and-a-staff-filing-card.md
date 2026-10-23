---
title: "22. Correspondence v4.1: Owner on demand, `05 Letters & Emails`, a staff filing card"
date: 2026-10-22
generated_by: skills-for-architects
---

# 22. Correspondence v4.1: Owner on demand, `05 Letters & Emails`, a staff filing card

Date: 2026-10-22

## Status

Accepted. Map v4.1, Atlas 0.19.1. Amends ADR 0021.

Decided by Tyler on 2026-10-22, after a review of the drive the same day as the v4.0
migration.

## Context

The v4.0 tree is right; the drive after migration showed where people will still misfile:

- `07 Correspondence\AHJ\05 Correspondence` repeats its parent's name. Monticello's V1 and
  V2 county plan-check reviews landed there (by relocation from `07 IN\Napa County PBES`),
  not in `04 Comments & Responses`.
- `Owner` is seeded on every project. On most jobs owner and client are the same person, so
  an empty `Owner\In` / `Out` is a second, wrong place to drop things.
- The filing rules live in `AGENTS.md`, which staff do not read.
- The AHJ registers already on the drive were created before ADR 0021 and still teach the
  ADR 0013 `R0_YYMMDD_` file prefix. Conform never overwrites a template file.

## Decision

1. **`AHJ/05 Correspondence` is renamed `AHJ/05 Letters & Emails`.** A map relocation moves
   the existing folder; the register template and the agents rules name the new folder and
   say agency review comments go in `04`, never `05`.
2. **`Owner` is no longer seeded.** It stays a blessed child (with `In` / `Out`), created on
   demand when the owner is a separate party from the client. Existing empty `Owner` folders
   may be removed by `clean`; projects with a separate owner keep or recreate theirs.
3. **`07 Correspondence/README.md` is a project template**: a one-page "I have... / it goes
   in" card for staff. Conform creates it and never overwrites it.
4. **Existing AHJ registers** get their stage table brought to the current template by hand
   (round folders, `05 Letters & Emails`). Rows are untouched.

## Consequences

- Rename order: the relocation runs in `conform --only relocate --apply` before the
  backfill pass, so `05 Letters & Emails` is never seeded empty beside the old folder.
- A project whose owner is separate and whose `Owner` folder was cleaned away gets it back
  with `atlas add` (`07 Correspondence/Owner/In`, `.../Out`).
- The README is staff-facing copy: no em dashes, plain words.
