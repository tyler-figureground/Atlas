# California reference routing

Atlas's bundled `agents-rules.md` carries the California permit-reference workflow
in its `## California permit requirements` section. New projects inherit it through
their generated AGENTS.md; CLAUDE.md remains the one-line import. Existing
project-owned notes stay outside the Atlas markers.

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
actually relied on, and file project-specific reviews in the existing mapped folders
(`07 Correspondence/AHJ/01 Requirements & Pre-Application/` under ADR 0021).

## Distribution and maintenance

Edit [the canonical template](../tools/atlas/src/atlas/templates/project/agents-rules.md).
The drive map must name `agents-rules.md` in `controlPlane.agentsRules`, as the
ARCHITECTURE map does. `tools/atlas/tests/test_project_templates.py` asserts the
section is present, placed after `## Code work`, and uses current folder paths.

Distribution is the ordinary Atlas path: release a wheel, repin `_tools\Atlas.bat`,
then `atlas conform --all --only backfill` (dry run, then `--apply`) rewrites the
Atlas block in every project's AGENTS.md. No template override is used.

### History

On 2026-10-06 the section was first deployed through an `ATLAS_TEMPLATES` override
(a drive copy of the templates plus a launcher line) and a direct AGENTS.md backfill
to 15 projects, while the repo change stayed on one PC's local `main`. On 2026-10-07
the override was found masking newer templates and retired (robustness plan
progress log); the following conform rewrite removed the California section from
every project. Measured 2026-10-30: 0 of 11 active projects carried it. The section
now lives in the packaged template, so the next release and conform restore it and
no override can drift from it again.
