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

## Final round-2 P2 repair (#94 / PR #99)

- Base 660308a, fetched origin; ahead 0 / behind 0 at start. Round 2 has no P0/P1; review rounds capped at two. Both coordinator review reports remain untouched; no third review requested.
- Red-first public apply/manifest/CLI regression: relocate creates NewParent, rename raises PermissionError, post-write existence probe raises PermissionError. Returned FAILED action has no confirmed creations or moves. Serialized manifest with its prose note cleared loaded successfully, and `conform --revert --apply --json` incorrectly exited 0 with an empty inverse and leftover NewParent. Observed failure: expected 2, got 0.
- Added default-empty `Action.created_unknown` path tuple, appended after existing fields to preserve positional constructors. Apply retains uncertain creation paths alongside confirmed effects. Shared JSON serializer and both conform/archive loaders preserve it with their existing containment validation; legacy manifests missing the field still load with an empty tuple. Neither recovery path parses notes.
- Both inversion functions refuse uncertain effects before status/move shortcuts. Coverage includes uncertain actions with moves and DONE/FAILED/CONFLICT/SKIPPED statuses, legacy defaults, archive round-trip/refusal, and escaping paths. CLI regression now exits 2 and leaves the source and uncertain parent untouched.
- Consumer inspection: CLI conform/archive JSON use the shared serializer; both loaders explicitly reconstruct Actions and now retain the field; CLI revert preflight and TUI UndoStack use the inversion functions and inherit refusal. Tree/render/guard consumers retain existing behavior; no new action kind or guessed cleanup. Existing index_row/keep_index serialization behavior is outside this repair and unchanged.
- Full suite: `cd tools/atlas && uv run --locked --with pytest-timeout pytest -q --timeout=120`: 1670 passed in 316.95s, exit 0, no skips. Final focused rerun: `uv run pytest tests/test_apply_faults.py tests/test_agents_md.py tests/test_revert_safety.py tests/test_archive.py -q`: 143 passed in 5.93s, no skips. Repo lint and diff check passed; shellcheck unavailable locally (script skips).

## Next action

Final P2 repair verified and committed with this cursor, without pushing. Coordinator owns final-change inspection and push/integration; no third review requested or PASS claimed. Both existing review reports preserved. No merge, deployment, primary-checkout or studio-drive writes.
