# Handoff - outstanding repo work after the 2026-11-09 bug sweep

## Goal

Pick up everything still outstanding in the Atlas repo now that the GitHub queue is empty: turn the leftovers below into issues (or decisions), then work them one at a time (Tyler's standing preference - sequential, not a parallel drain).

## Queue cursor

- **GitHub queue: empty.** At `df20fe7` (main, CI green): 0 open issues, 0 open PRs. Check again with `gh issue list --state open` and `gh pr list --state open` before starting.
- **Last finished:** the `/sweep kind=bugs areas=tools/atlas` run. Issues #54-#68 merged via PRs #69-#73, #75-#77, #79, #80, #82-#86. Follow-ups #74 (PR #87) and #78 (PR #88) merged. #81 closed (not a bug, evidence in the issue).
- **Next items:** none are filed yet. Candidates, in suggested order:
  1. **Release 0.32.0 - needs Tyler.** `CHANGELOG.md` **Unreleased** holds 17 fixes. `tools/atlas/pyproject.toml` is still `0.31.0`, and `tools/atlas/launchers/Atlas.bat` is pinned to 0.31.0. Nothing reaches the drive until a release and a redeploy. Pattern: PR #52 (version bump plus changelog heading), then a deploy, then PR #53 (pin `Atlas.bat`). Deploying is Tyler's call; ask, don't do it.
  2. **Baseline plan item 6.1** (`docs/research/project-folder-baseline.md`, section 5, Phase 6): "Off-map count in the Tyler digest, per project, only when non-zero". Not implemented: there is no off-map code in `tools/atlas/src/atlas/core/tyler.py`. Doctor `--deep` already counts off-map folders (2.5). File as `ready-for-agent`.
  3. **Deferred review P3s.** Each is recorded in the named PR's "Independent review" comment. Bundle related ones into a few issues; don't file 15 one-liners:
     - **Conform, #69:** the `cmd_revert` loop has no per-project catch; mid-chain folders created before a FAILED action are not recorded; the vanished-project fallback ignores `--only`.
     - **Path limits, #75:** a 248-259 character folder window (the directory limit is 248, not 260); UNC paths refused 2 characters early; the Path Length Warning uses `>` while `_dest` refuses at `>=` 260.
     - **Runs, #73:** the stale-partial sweep doesn't use `long_path`.
     - **Content index, #71:** a worker cancelled before it starts could leave a root in `_content_live`; a live build's periodic save can downgrade a CLI-complete cache until it finishes.
     - **Search overlay, #86:** the narrowest fallback drops the stale count. **#84:** the stamp has no zone marker.
     - **Text handling, #77:** an Atlas marker sharing a line with a separator reads as broken; block placement changes when a file starts with a separator. **#88:** `update_project_index_row` re-renders a hand-written Status cell through `_table` (separator becomes a space).
     - **Small, #76, #80, #85, #87:** the `keep_index` early return duplicates the DONE tail; a rollback-failed CONFLICT isn't written to the drive log; no explicit "no traceback" assertion; the DOM-gone guard isn't tested separately.
  4. **Recurring, baseline plan 6.2:** the quarterly read-only re-walk of the drive, due about 2027-02. Not now.
- **Skipped on purpose:**
  - `.scratch/atlas-console/issues/27-duplicate-files-as-a-doctor-finding.md` and `28-more-content-filters.md` are **parked** (2026-10-07). Don't start them without Tyler.
  - Baseline plan Phase 0 (0.1, 0.2) is Tyler's own site work.

## Claimed items (leases)

None. Every `agent:active` label from this session has been removed, and every issue it touched is closed. Nothing to release.

## Next action

File one `ready-for-agent` issue for baseline 6.1 and 2-4 bundled issues for the P3 groups above. Search first with `gh issue list --state all --search <keyword>`. Then take them one at a time: worktree under `.claude\worktrees\`, claim, TDD (red first), PR, independent review, merge on green CI. Separately, ask Tyler about the 0.32.0 release and about the branch below.

## Needs Tyler (ask once, together)

- **Release and deploy 0.32.0?** (item 1)
- **`origin/prd-0002-cad-bim-ingestion`:** 119 commits ahead of main, last commit 2026-07-17, no PR. Merge it, open a PR, or archive it? Don't touch it without an answer.
- **Remote branches safe to delete:** `agent/19-set-sweep`, `agent/3766-adr-0001-ahj-profile`, `agent/6-ncs-sheet-numbers`, `drawing-sets-tracker`. All four PRs are merged and each branch is 0 commits ahead of main. Safe for `/cleanup`, but only the three `agent/*` ones were created by agents.
- **Heavy-run lock:** `C:\Users\Tyler\.claude\state\heavy-run.lock` still names the Gear-Head `prs` run from 15:48Z. If that session is dead, the lock blocks every Workflow run (`/swarm`, `/sweep`, `/drain`) on this machine.

## Traps (each cost time this session)

- **Heredocs mangle backslashes** in Git Bash, as `AGENTS.md` warns. `\u2028`, `\xef`, `G:\typo` were silently rewritten 4 times. Write test and edit scripts with the Write tool, then run them.
- **Line endings.** Source and test files are CRLF in the working copy. Edit with the Edit tool, or with Python opened `newline=""` and a CRLF-aware replace. A plain `sed` or `cat >>` produces mixed endings (git normalises them on commit).
- **Auto-merge is disabled** in this repo, and repo settings are off-limits. Wait for both checks (`Lint`, `Atlas`) on the **head SHA**: `gh run list --branch <b> --json headSha,status,conclusion`. `gh pr checks --watch` and grepping `gh pr checks` can match an earlier commit's runs. Then `gh pr merge <n> --merge`. Its "main already used by worktree" error is harmless.
- **Removing a worktree** fails with "Permission denied" while the shell sits inside it or its `.venv` is busy (uv creates a `.venv` per worktree). Run `git worktree remove --force` from the repo root, then delete the empty folders left behind (check they contain no files or links first).
- **Reviewer subagents deleted files from the scratchpad** once. Tell them to use their own subfolder and never touch the parent's files.
- **The lint (`scripts/lint.sh`) checks link-shaped text even inside CHANGELOG code spans.** A Markdown image example with a relative path failed it once; write the path alone (`img/p.png`). Locally the lint can pass where CI fails, so wait for CI.
- **Tests that assert a raw UTC date fail on a Pacific machine after about 4 pm.** Use `tui.search._stamp_short`.
- `tests/test_path_length.py` long-path and trailing-space tests are Windows-only. CI (ubuntu) doesn't run them, so run them locally.
- Full suite: `cd tools/atlas && PYTHONUTF8=1 uv run pytest -q -p no:cacheprovider`. About 1,645 tests, about 5 minutes. Capture the output to a file and check the exit code; don't pipe.

## Suggested skills

- `tdd`: every fix this session went red first.
- `triage`: if new issues arrive unlabeled.
- `cleanup`: merged remote branches and stale leases, once Tyler answers.
- `code-review` or a separate reviewer subagent: an independent review before every merge.
- `sweep`: only when the heavy-run lock is clear and a new hygiene pass is wanted (`kind=tests` hasn't been run yet).
