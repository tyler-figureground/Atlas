# Run YYMMDD-<slug>

Copy to `.agent/runs/YYMMDD-<slug>/RUN.md` at the start of a run. Everything the run makes
that a person will not read - scripts, receipts, JSON, captures, check exports - stays in
that folder. Atlas zips a run into `.agent/archive/` once it has been idle 14 days and
nothing in `00 Tasks/` or `.agent/handoff/` names it.

- Task: T-NNN
- Agent / model:
- Started:
- Ended:
- Result filed: <absolute path, or none>
- Reference: <set and exemplars opened, e.g. code-analysis E1, E3 - or: no set for this type>
<!-- Fill both lines for any run that produces sheets; blank is fine otherwise. -->
- Rounds to acceptance: <n>
- Defects reaching Tyler: <n>
- Tasks touched: <T-NNN done, T-NNN added>
- Left open: <locks, unsynced model, held items>

## Log

-
