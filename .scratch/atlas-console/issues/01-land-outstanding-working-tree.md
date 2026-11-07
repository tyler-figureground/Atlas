# Land the outstanding Atlas working tree

Type: task
Status: resolved
Blocked by: -
Parent: ../map.md

## Question

Roughly thirty modified and untracked files sit in the working tree - the project
intake, shared contacts, and project/contact editing work - while `main` is ahead of
`origin/main` by one commit. The completed editing and intake handoffs recorded that
work as complete and production-deployed, and `CONTEXT.md`, `docs/adr/0003-...`, and five new core modules
with their tests are part of it.

Every redesign diff from this map lands on top of that. Until it is resolved, no
review of this effort's changes is legible and no bisect is meaningful.

Decide and execute:

- Does the outstanding work get committed as-is, split into reviewable commits, or
  partially discarded?
- Does it get pushed, given `main` is already ahead by one?
- Do `.agent/` and `.impeccable/` belong in the repository or in `.gitignore`?
- Does `.scratch/` - this map - belong in the repository or ignored?

This is a task, not a decision about Atlas. It unblocks clean execution of every
ticket after it. Resolve by actually landing the tree, then record what was done and
the resulting commit range.

## Answer

Landed. The whole working tree was committed - modified and untracked alike - on
the user's instruction to commit everything. `main` is now ahead of `origin/main`
by five and the tree is clean. Not pushed; that stays the user's call.

Verified before committing: `uv run pytest` 201 passed, `./scripts/lint.sh` all
checks passed (shellcheck unavailable locally, skipped by the script, CI runs it).

Four commits, oldest first:

- `24e1c82` feat(atlas): project intake, shared contacts, and safe editing
- `9873ca4` feat(project-dossier): intake contract and structured site address
- `0b9bd7d` docs(research): cost of reading a project tree over Google Drive
- `7737de7` chore: agent continuity, design critique, and the atlas-console map

Range: `c6d564a..7737de7`.

Ignore decisions, settled by committing rather than ignoring:

- `.agent/` is **tracked**. Handoffs are continuity the next session needs.
- `.impeccable/` is **tracked**. The critique is the evidence behind the
  operations-console direction.
- `.scratch/` is **tracked**. The map is this effort's canonical artifact and
  would be worthless if it lived only on one machine.

`.gitignore` was not modified. Nothing was discarded.
