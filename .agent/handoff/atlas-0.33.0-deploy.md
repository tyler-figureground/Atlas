# Atlas 0.33.0 release / deploy checkpoint

## Authority and boundary

User authorized production deployment and laptop update. This worker prepares and commits release sources only in `agent-release-0.33.0`; coordinator owns independent review, integration and deployment. No push, pull request, merge, drive writes or laptop tool installation in this session.

Starting state supplied by user: laptop Atlas 0.27.0; drive launcher pin 0.32.0; latest main `2fdbdfd`. Fetch confirmed base matches origin/main (ahead 0 / behind 0).

## Plan / evidence

- Release version: 0.33.0; changelog dated 2026-11-12, existing Unreleased notes preserved under that release; empty Unreleased retained.
- `uv lock` completed without upgrade flags; only studio-atlas changed from 0.32.0 to 0.33.0. Dependencies unchanged.
- Exact CI (continuous integration) command: `uv run --locked --with pytest-timeout pytest -q --timeout=120` in `tools/atlas`, Windows with `UV_PYTHON=3.12` (CPython 3.12.13): **1873 passed in 326.12s**, no skips. This is local Windows evidence, not an Ubuntu CI run. Release sources and this checkpoint are committed together; identify the commit with `git log -1 -- .agent/handoff/atlas-0.33.0-deploy.md`.
- Repo lint: `./scripts/lint.sh` passed initially with ShellCheck unavailable. Supplemental run with ephemeral `shellcheck-py` exposed checkout CRLF errors (SC1017), not release changes. Rerun with the four hook files temporarily normalized to CI-equivalent LF passed every check, including ShellCheck; exact original hook bytes restored afterward. Counts: 23 JSON files, 47 skills, 264 Markdown files, 4 shell scripts, 26 metadata-hook cases, 18 reference-hook cases, 17 deliverable skills. No hook source changes.
- `uv build` passed, producing wheel and source archive. ZIP integrity clean; inspected wheel METADATA: Name `studio-atlas`, Version `0.33.0`, Requires-Python `>=3.12`; WHEEL tag `py3-none-any`.
- Wheel: `C:\Users\Tyler\Documents\GitHub\Atlas\.claude\worktrees\agent-release-0.33.0\tools\atlas\dist\studio_atlas-0.33.0-py3-none-any.whl`
- Wheel SHA-256: `fc705cf7ef1576c610ba1825f230901af09a741440cfe8f9fa500d9194e99452`.
- Launcher pin intentionally stays 0.32.0, following separate release / post-deploy pin pull requests #90/#91.

## Remaining coordinator tasks

1. Independent review and integration of release source commit; verify integrated source and checks before deployment.
2. Follow `tools/atlas/README.md` deployment checklist. Back up drive `_tools` launchers, map and instructions into `_tools/logs/atlas-0.33.0-deploy-<YYYYMMDD-HHMMSS>/` before writes.
3. Copy approved 0.33.0 wheel to drive `_tools/atlas/`; record and compare SHA-256 after copying. Do not overwrite an existing different wheel under the same version.
4. Deploy launchers with production Atlas.bat pin set to 0.33.0 only after wheel placement. Do not blindly copy this source tree's still-0.32.0 Atlas.bat over the new pin.
5. Verify deployed launcher reports `atlas 0.33.0`; run production-map `atlas lint`, checking for no new errors. Update drive HOW-TO.md for changed commands as needed.
6. Update laptop from reported 0.27.0 to approved 0.33.0 artifact; verify resolved executable/install provenance and version. Coordinate other seats before writing Organization/null-Client records (0.30.0 compatibility note).
7. After successful deployment, prepare separate launcher-pin source pull request (pattern #90/#91), recording deployment/backup/hash and laptop verification evidence. No project conform/backfill is implied by this release preparation.
