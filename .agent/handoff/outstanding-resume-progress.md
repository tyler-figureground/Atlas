# Outstanding work resume

## Decisions and verified base

- User deferred release/deploy and old cad-bim-ingestion branch. No drive writes or branch cleanup.
- Fetched origin: primary main at 29d3f64, ahead 0 / behind 0, clean. Open issue/PR queues initially empty.
- Original handoff release note stale: PRs #90 and #91 already merged release and pin 0.32.0. Deployment not independently verified.
- Work sequentially, not parallel implementation.

## Plan and cursor

1. #93: baseline 6.1 implemented in agent/outstanding-digest. User confirmed collect/render and atlas tyler CLI seams, temp-project fixtures and filesystem failure injection. Reuses scan_deep, hides complete zero counts, retains unreadable/depth-capped warnings, qualifies partial nonzero counts as "at least"; JSON carries count and warnings. Implementation agent must commit only owned files plus this coordinator deliverable; no push/PR/merge or primary/drive writes. Independent review and later integration belong to coordinator.
2. Filed and read back four bundled deferred-review issues: #94 conform/undo recovery; #95 Windows path boundaries and stale archive cleanup; #96 content-search lifecycle and presentation; #97 text preservation and remaining guard regressions. All ready-for-agent; original comments checked. #80 drive-log detail comes from handoff, not its short review summary; verify before changing.
3. Implement each bundle sequentially with the same verification/review/merge gates.
4. Update this cursor after each merge. Leave parked tickets 27/28, quarterly walk, and human site work alone.

## Verification

- TDD red confirmed before implementation for nonzero project counts, unreadable warnings (zero and nonzero), depth-capped warnings, and CLI JSON. Each slice passed after its implementation.
- Focused: `cd tools/atlas && uv run pytest tests/test_tyler.py tests/test_deep_pass.py -q`: 30 passed. Includes exclusions, first-off-map-level counting, no payload reads, default read-only output, and --write in a temp drive.
- `./scripts/lint.sh`: passed; optional shellcheck unavailable locally, skipped by script.
- Full Atlas suite: `cd tools/atlas && uv run --locked --with pytest-timeout pytest -q --timeout=120`: 1651 passed in 556.54s, exit 0, no skips.
- Implementation complete and ready for coordinator's independent review; no push, PR, merge or deployment performed.
- `git diff --check`: passed. No studio-drive access or primary-checkout writes.
- Independent review required before every merge. Auto-merge is disabled; use merge commit only after both Lint and Atlas checks succeed on exact PR head.
