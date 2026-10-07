# California reference routing

Atlas's bundled `agents-rules.md` carries the California permit-reference workflow.
New projects inherit it through their generated AGENTS.md; CLAUDE.md remains the
one-line import. Existing project-owned notes stay outside the Atlas markers.

The shared collection lives at:

`G:\Shared drives\LIBRARY - Reference\01 Codes and Regulations\California\Napa - Permit Guidance`

Agent entry: `_agent\START_HERE.md`. Human entry: `07 FIND REQUIREMENTS.html`.
Content stays on the shared drive; projects receive instructions, not corpus copies.

## Applicability

- Determine project jurisdiction, reviewing agencies, scope, application date and code cycle.
- Napa: route independently to City, County, NapaSan and related-agency sources as applicable.
- Other California jurisdictions: obtain the actual authority's guidance. This collection is not statewide coverage.
- Non-California projects: conditional instruction is inactive unless a comparison is requested.
- Unknown facts: preserve the uncertainty. Postal city alone does not establish the permitting authority.

Use Markdown or page-level search before reparsing PDFs. Cite the original issuer,
edition, document ID, page and URL; preserve OCR and diagram limitations. The index
does not replace Norma's verified governing-code workflow. Record only sources
actually relied on, and file project-specific reviews in the existing mapped folders.

## Distribution and maintenance

Edit [the canonical template](../tools/atlas/src/atlas/templates/project/agents-rules.md).
The drive map must name `agents-rules.md` in `controlPlane.agentsRules`, as the
ARCHITECTURE map does. Editable Atlas installs pick up changes immediately; other
installations receive the template with the next package installation.

The live ARCHITECTURE launcher currently runs 0.11.0, newer than this checkout's
0.10.1 application and the former bare CLI (0.5.0). Deployment preserves the live
wheel and its newer house rules. `scripts/deploy-california-reference-routing.py`
copies the live wheel's project templates into `_tools/atlas/templates`, inserts
only the California section from the canonical template, and adds the supported
`ATLAS_TEMPLATES` override to the launcher. It rejects unrelated project-rule drift.
Run without `--apply` to preview; `--drive` and `--wheel` identify the targets.

The local bare CLI was upgraded to the same deployed 0.11.0 wheel, with the merged
agents-rules template installed by atomic replacement (preserving uv's cached
package). The user-level `ATLAS_TEMPLATES` setting also points to the shared
override; the installed copy covers already-open terminals. Future package upgrades
must refresh or deliberately retire that override so it does not mask new templates.
Do not downgrade the live application just to distribute a Markdown change.

Backfill through a bounded Atlas Plan targeting AGENTS.md. Preview the generated
change; copy the existing control file into `.agent/backups/` before applying.
Verify project-owned text outside the markers and PROJECT.md remain unchanged,
CLAUDE.md still imports AGENTS.md, and a second plan makes no further changes.
Do not run unrelated rename, relocation, sweep or project-fact operations for a
reference-library update. Preserve a run receipt and deployment manifest.

`scripts/verify-california-reference-routing.py --map <drive-map>` exercises real
new-project creation in a disposable local drive for Napa, Oakland and New York.
Run using the intended Atlas runtime, once with its packaged templates and once
with the launcher override. No test projects are created on the shared drive.
