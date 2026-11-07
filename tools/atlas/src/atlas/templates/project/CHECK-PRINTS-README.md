# Check prints - {{project_name}}

Sets printed to be checked, never issued. One folder per check, so a set and its redline
stay together. Find the row, file it, done.

| I have... | It goes in |
|---|---|
| A set printed for review (by Tyler, staff or an agent) | A new folder here: `YYMMDD_<Scope>`, for example `261107_A-Series Layout` |
| The PDF itself | That folder, named `YYMMDD_<Scope>_Check.pdf` |
| The marked-up copy that comes back | Same folder, `YYMMDD_<Scope>_Redline.pdf` |
| What the set covers and what changed since the last one | Same folder, `NOTE.md`, a few lines (agents always write one) |
| A second print of the same scope on the same day | Same folder, `_Check R2.pdf`, `_Redline R2.pdf` |

**Not here.**

- An agent's in-between prints while it works: its run folder, `.agent/runs/<run>/print/`.
  Only the set handed over for review comes here.
- An issued set: its phase folder in `02 Sheets` (`2 Schematic`, `4 Construction`, ...).
- A set sent to the client, an agency or a consultant: that party's `Out` in
  `07 Correspondence`, with a row in `TRANSMITTAL-LOG.md`.
- Drawing sets from other projects used as examples: the studio Reference Sets library.

**Printing.** Always print to a named file in the right folder. Files called `1.pdf` or
`23542.pdf` mean the print went to a default folder and a default name.

**Keeping.** Nothing here is deleted by an agent. Tyler clears old checks.
