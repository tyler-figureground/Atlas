# Atlas 0.33.0 deployment receipt

## Status and authority

User authorized deployment and laptop update to latest Atlas. **Deployment and laptop update completed and verified 2026-11-12.** No project conform, backfill, archive, or contact writes were run. The production map and root instructions were not modified.

- Release PR #103 merged at `81754049597bc17c0f0998dfef9334275d41cf5e`; release source `32704653ad6c4403422204290e8c49970d4d13d0`.
- Independent release review PASS; exact-head Atlas and Lint continuous integration checks succeeded before production deployment.
- Source launcher pin update accompanies this receipt, following release/deploy/pin ordering. Its pull request is the authority for final integration status.
- Previous versions: laptop 0.27.0; shared-drive launcher 0.32.0. Both now report `atlas 0.33.0`.

## Artifact and backup

- Deployed wheel: `G:\Shared drives\ARCHITECTURE\_tools\atlas\studio_atlas-0.33.0-py3-none-any.whl`
- SHA-256: `fc705cf7ef1576c610ba1825f230901af09a741440cfe8f9fa500d9194e99452`
- Backup and machine-readable deployment/verification receipt: `G:\Shared drives\ARCHITECTURE\_tools\logs\atlas-0.33.0-deploy-20261112-164324\receipt.json`
- Before changing production files, backed up all nine `_tools` launchers, `architecture-map.json`, `HOW-TO.md`, and drive-root `README.md` under that directory's `before` tree. Byte readbacks and SHA-256 recorded; preimages rechecked before deployment.
- Wheel copied and hash verified before launcher activation. Same-version artifact overwrite refused unless bytes identical. All repository launchers compared/copied; the Atlas pin changed to 0.33.0.
- HOW-TO install example now names 0.33.0 and describes nonzero/incomplete off-map digest counts. Other historical HOW-TO content left unchanged.
- Prior wheels retained for rollback. Configuration backup is precautionary; map hash unchanged after deployment.

## Verification

- This release session's full Windows/Python 3.12 suite: `uv run --locked --with pytest-timeout pytest -q --timeout=120`: **1873 passed**, no skips (326.12s).
- Repo lint passed. Supplemental ShellCheck run used temporary LF-normalized hook bytes matching CI; exact original checkout bytes restored, no hook changes. Remote Lint also passed.
- `uv build` succeeded. Wheel METADATA confirms studio-atlas 0.33.0, Python >=3.12 and py3-none-any; ZIP and all RECORD hashes/sizes verified by independent reviewer. All 63 packaged source/template files match release source modulo Git checkout CRLF.
- Actual drive `Atlas.bat --version`: `atlas 0.33.0`, exit 0.
- Actual drive `Atlas.bat lint --drive <root>`: exit 0; map v4.6 with sole preexisting DUP-CHILD Photos warning. Same warning observed through pinned 0.32.0 before deployment; no new errors.
- Laptop updated with `uv tool install --force` from the deployed wheel. Resolved executable: `C:\Users\Tyler\.local\bin\atlas.exe`.
- Laptop `atlas --version`: `atlas 0.33.0`; `atlas --help` and production-map lint succeed. All **63 installed package files** match the deployed wheel byte-for-byte.
- Installation provenance confirmed in `C:\Users\Tyler\AppData\Roaming\uv\tools\studio-atlas\uv-receipt.toml`: the drive's 0.33.0 wheel, not editable source or a transient worktree.
- Detailed command outputs and verification timestamp recorded in drive receipt, status `verified-drive-and-laptop`.

## Final integration / rollback

Complete the launcher-pin pull request after independent review and exact-head CI; then remove this session's merged branches/worktrees and temporary deployment scripts. No additional deployment or project mutation is needed.

If rollback is explicitly requested, the backup preserves original launchers/instructions; prior 0.32.0 and laptop 0.27.0 wheels remain available. Do not blindly replay a backup over later human edits; compare receipt hashes first. Other studio machines were not globally reinstalled; the shared launcher resolves the newly pinned wheel when run.
