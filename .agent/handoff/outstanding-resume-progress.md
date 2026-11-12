# Outstanding work resume

## Decisions and verified base

- User deferred release/deploy and old cad-bim-ingestion branch. No drive writes or branch cleanup.
- #93 merged as PR #98, merge e613122. Full suite 1651 passed; independent review verification 113 passed; CI green (coordinator evidence).
- #94 worktree fetched origin/main at session start: ahead 0 / behind 0. No open PR duplicates. No primary-checkout or studio-drive writes.
- Original handoff release note stale: PRs #90 and #91 already merged release and pin 0.32.0. Deployment not independently verified.
- Work sequentially, not parallel implementation.

## Plan and cursor

1. #93 complete and merged: Tyler digest off-map folder counts and incomplete-scan warnings.
2. #94 current: conform/undo recovery implementation in `agent-outstanding-recovery`. User approved public core/CLI test seams, temporary filesystems and injected failures. Commit only implementation plus this cursor; no push, PR or merge. Coordinator owns independent review and integration.
3. #95 Windows path boundaries/stale archive cleanup, #96 content-search lifecycle/presentation, #97 text preservation/remaining guard regressions: pending. Do not start in this worktree.
4. Leave parked tickets 27/28, quarterly walk, human site work, deployment and old branch alone.

## #94 implementation and evidence

- Read issue #94 through gh, original PR #69/#76/#80 comments, global/repo rules, TDD skill and references, domain glossary, ADRs 0006 and 0019, original outstanding-work handoff.
- Red-green: batch revert lost JSON on a later OpsError or OSError (2 cases); now earlier manifests survive and the third project runs. Existing preflight still checks every project before any write.
- Red-green: failed/conflicted parent creation lost `created` metadata (2 cases); both now pass through common effect recording. Corrected the initial test target from an unsupported backfill target to the fixture's analysis directory, then explicitly restored the old exception continues and confirmed both failures before restoring the fix.
- Red-green: rollback-failed agent-file rename lacked both its Move Manifest and conflict log record. A specific OpsError subtype carries the stranded move; narrow expected catches retain it. Conflicted partial merges also use the conflict logging branch.
- Red-green: vanished-project fallback marked `--only` exclusions failed; exclusions now stay skipped with the same filtering note.
- Unexpected RuntimeError propagates; already completed actions still reach the drive log. No broad exception suppression added.
- Invalid runtime premise: archive `keep_index` duplicated source code, not execution or output. Its early return already prevented a second DONE tail. Consolidated the tail without changing index preservation, manifest, note or pruning behavior; existing failed-stamp undo regression passes. No manufactured failing test for an already-correct behavior.
- Existing safety boundary retained: conflicted BACKFILL is not automatically invertible; the stranded file's explicit manifest and manual-recovery note are retained, not permission to guess at undoing content edits.
- Focused: `cd tools/atlas && uv run pytest tests/test_apply_faults.py tests/test_agents_md.py tests/test_revert_safety.py tests/test_archive.py -q`: 130 passed in 10.22s, no skips.
- Full suite: `cd tools/atlas && uv run --locked --with pytest-timeout pytest -q --timeout=120`: 1657 passed in 489.97s, exit 0, no skips. Windows / Python 3.13.15; exact CI test command.
- Repo lint passed after changelog/cursor updates; optional shellcheck unavailable locally, skipped by script.
- `git diff --check` passed. Implementation and cursor ready for commit; no push, PR, merge, deployment or independent-review claim.

## PR #99 independent-review repairs

- Review FAIL P1 reproduced red at public `apply_plan`: a successful earlier rename followed by a successful sweep and denied post-write `Path.exists` raised PermissionError, losing the returned Plan. Probe errors now catch only OSError per path, retain prior/current Move Manifests and confirmed `created` entries, append an explicit unknown-state note, and mark the affected action failed. Other Action metadata and notes survive; JSON round-trip and drive log are asserted.
- CLI regression additionally verifies exit 2 with both manifests and the earlier DONE status intact. Removing the probe fix made this test fail with missing JSON; restoring it passes. Initial CLI test used an invalid comma-separated `--only`; corrected to repeated flags before the removal control.
- Review FAIL P2 reproduced red using a real parent mkdir followed by an injected denied rename. `invert_plan` now rejects creation-only effects with NotInvertible before building any inverse, including FAILED actions. No new undo action type or deletion behavior.
- Focused final run: `cd tools/atlas && uv run pytest tests/test_apply_faults.py tests/test_agents_md.py tests/test_revert_safety.py tests/test_archive.py -q`: 133 passed in 8.77s, no skips.
- Full suite: `cd tools/atlas && uv run --locked --with pytest-timeout pytest -q --timeout=120`: 1660 passed in 384.60s, exit 0, no skips; Windows / Python 3.13.15. Repo lint passed (optional shellcheck unavailable locally); `git diff --check` passed. No primary-checkout or studio-drive writes; local branch started ahead 0 / behind 0 after fetch.

## Next action

Review repairs verified and ready in this commit, without pushing. Coordinator owns independent re-review of PR #99 and any push/integration; no review PASS claimed here.
