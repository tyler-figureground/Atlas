# California reference routing - 2026-10-06

INTENT: integrate the shared Napa agent-readable library into new Atlas projects
and existing active projects, conditional on project jurisdiction.

DECISION: extend the canonical agents-rules template. Link the shared library in
place. Keep agency handouts separate from Norma's verified governing-code corpus.
Do not assume County jurisdiction from a Napa postal address or apply Napa rules
to all California projects.

DECISION: live launcher uses 0.11.0, checkout application is 0.10.1, former bare CLI
was 0.5.0. Preserve live application/rules. Merge only the new section into a shared
template override. Upgrade bare CLI to the existing deployed 0.11.0 wheel and give
it the same rules. User ATLAS_TEMPLATES points to the shared override. No package
version changed in the repository.

RESULT: 15 non-archived ARCHITECTURE project roots updated using Atlas Plans.
Each AGENTS.md backed up; only the new section changes nonblank instruction text.
PROJECT.md hashes unchanged; CLAUDE.md remains @AGENTS.md. Repeated block refresh
is idempotent. New projects tested for Napa CA, Oakland CA and New York NY using
both the installed runtime and shared override (six disposable projects total).

Evidence: project-local run receipts and `.agent/backups/` copies on the drive.
The deployment manifests stayed in the original local commit `99a15cd` and were
not carried to main (run manifests are untracked since 2026-10-07). No compliance review,
permit submission or drawing issuance was performed by this integration.

Validation: 100 project-template and project-contract tests passed. Repository lint
passed, including all 26 metadata-hook and 18 reference-hook cases; optional shellcheck
is not installed locally. Initial metadata-hook failure cleared on retry without hook
changes. Internal links were checked again after staging the new documentation (219
Markdown files). Both installed and shared-template new-project smoke runs passed.

Maintenance: see [routing guide](../../docs/california-reference-routing.md).
Source collection entry:
`G:\Shared drives\LIBRARY - Reference\01 Codes and Regulations\California\Napa - Permit Guidance\_agent\START_HERE.md`.

## Update 2026-10-30 - superseded delivery

The override this handoff installed was retired on 2026-10-07 (it masked newer
templates); the conform rewrite that followed removed the section from every
project, and this commit never left one PC's local `main`. Measured 2026-10-30:
0 of 11 active projects carried the section. Re-landed on main in the packaged
`agents-rules.md` (after `## Code work`, AHJ path updated to ADR 0021), with a
template test. The deploy and override-smoke scripts are dropped. Restore in
projects with the next Atlas release and `atlas conform --all --only backfill`.
