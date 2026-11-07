# 26. Check prints have one seeded home, and agent iterations stay in the run

Date: 2026-11-07

## Status

Accepted. Map v4.6, Atlas 0.28.0. Amends ADR 0025 decision 4 (`02 Sheets/_Check Prints` was
on demand; it is now seeded) and narrows ADR 0011 (one class of agent export leaves the run).

Decided by Tyler on 2026-11-07: hand-off sets only, one folder per check, seeded with a
card, and existing prints moved in.

## Context

Tyler: "agents are printing drawings and placing them all over the place." A walk of the
drive on 2026-11-07 found check prints in at least seven kinds of place:

- `02 Sheets/Phase 3/Check Set` (211 Centre): 69 files, 20+ of them one sheet's iterations
  (`A101-CURTAINS-CHECK-R2..R8`, `-CLEAN`, `-FINAL`, `-PROVEN`, `-ISSUE-READY`), each
  stamped `NOT-ISSUED` in the name because the folder did not say so.
- `02 Sheets/4 Construction` (Beitz): 20+ numbered review prints (`Review-60` to `-76`)
  beside the issued sets.
- `02 Sheets` itself (64th Lane), and an empty hand-made `Check Sets` beside it.
- `02 Sheets/_Check Prints` (Silverado, 211 Centre): the v4.5 home, used by Tyler, holding
  printer-named files (`1.pdf` ... `7.pdf`).
- Run folders, under four names: `print/`, `print/before`, `print/after`, `export/`, and on
  Silverado `stray-prints/` (19 files named `23542.pdf`, `wewer435.pdf`).

The agent rules said "export the sheets and look at every page" but never said where to,
and sent "check exports" to the run folder, which a person never opens. So the set an agent
wanted Tyler to look at had no home; each agent invented one. `_Check Prints` was on the map
(ADR 0025) but on demand and undescribed, so no agent knew it existed.

## Decision

1. **`02 Sheets/_Check Prints` is seeded,** with a description and a filing card
   (`README.md`, template `CHECK-PRINTS-README.md`). Every project has it from day one.
2. **One folder per check:** `YYMMDD_<Scope>/` holding `YYMMDD_<Scope>_Check.pdf`, the
   markup returned as `YYMMDD_<Scope>_Redline.pdf`, and a `NOTE.md` (sheets, what changed,
   the run that made it). A second print that day is `_Check R2.pdf`. The folder says it is
   not issued; names never carry `NOT-ISSUED`.
3. **Only the hand-off set goes there.** An agent's in-between prints stay in its run
   folder, always under `print/`, and are zipped with the run (ADR 0011).
4. **Every export names its folder and file.** A printer-default name is a misfiled print.
5. **Issued and sent sets do not move.** Phase folders keep issued sets; `07 Correspondence`
   keeps what was sent. Only prints made to be checked move.
6. **Existing check prints move in,** one previewed move manifest per project in
   `_tools\logs\`, grouped into dated check folders. That covers prints nested where no
   relocation reaches (211 Centre's `02 Sheets/Phase 3/Check Set`, Beitz's review prints in
   `4 Construction`). For folders made by hand later, the map relocates `02 Sheets/Check
   Set(s)`, `Check Prints`, `Test Prints` and `Tylers Review` into `_Check Prints` whole, as
   `<name> (moved)`, so their prints never land loose beside the card. Relocation matches
   exact spelling; other spellings are a per-project move.

## Consequences

- Each project gains one folder and one card; conform adds both, and refreshes the AGENTS.md
  block with the print rule. The card is owed always, not on create, so conform also makes
  `02 Sheets` in a project that lacks it, as the `07 Correspondence` templates already do.
- Map v4.6 names a template only Atlas 0.28.0 bundles. Older Atlas loads the map but fails
  when `atlas new` or conform renders the card, so the wheel and `Atlas.bat` pin deploy
  before the map.
- Run folders keep most print volume, so the drive item count does not grow with each pass.
- Loose printer-named files already in run folders stay there and archive with their run.
