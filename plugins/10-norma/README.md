# 10 — Norma (Building Code)

Building-code analysis for the architect of record. Every answer is grounded in a **local code corpus** and cited verbatim — no code answers from memory.

These skills are the **surface**; the calculators, corpus, and data are the **Norma engine**, installed editably and called as the `norma` CLI. Engine edits go live everywhere with no re-publish; only skill prose ships through the marketplace. See [`agents.md`](./agents.md) for the universal context (persona, source types, corpus routing, tool stack, known divergences); the full divergence list, dossier blocks and verdicts are in [`reference/norma-context.md`](./reference/norma-context.md).

## Prerequisite — the `norma` engine

These skills shell out to `norma`. Install the engine once (editable, so it stays live):

```bash
# from the Norma engine repo
pip install -e .
```

If `norma` isn't found at runtime, put the Python Scripts dir on PATH, or the skills fall back to `python -m norma.cli <verb>`.

## Scoping — the project's `PROJECT.md`

Norma scopes from the workspace `PROJECT.md` front-matter (the shared machine contract maintained by [`/project-dossier`](../09-project-dossier)). `norma project active` reads `jurisdiction`, `occupancy_group`, `construction_type`, `sprinklered`, etc.; written analyses land in `06 Research & Existing Conditions/Code/` via `norma project analysis-dir`.

## Skills

| Skill | What it does |
|-------|-------------|
| [`/ibc`](./skills/ibc) | Code Q&A — one question, any provision (occupancy, egress, heights/areas, ratings, accessibility), grounded + cited |
| [`/egress`](./skills/egress) | Occupant load, required exits, egress width, travel distance, common path / dead-end for a space or story |
| [`/allowable-area`](./skills/allowable-area) | Allowable height (ft) / stories / area by occupancy + construction type + sprinkler; allowable vs. actual |
| [`/code-analysis`](./skills/code-analysis) | Full code-analysis cover sheet (occupancy + egress + allowable + ratings, all cited) for a project |
| [`/compare`](./skills/compare) | Cross-jurisdiction diff of one provision — IBC 2009 vs NYC 2022 vs CA 2025, side by side |
| [`/drawing-analysis`](./skills/drawing-analysis) | Vision-grounded life-safety / egress review of a floor-plan PDF or image |

## Authority & posture

Norma answers the design professional of record as a peer — it does **not** emit the studio's professional-disclaimer marker (see [`agents.md`](./agents.md)). It cites only sections found in the corpus, runs `norma guard` on every draft, and abstains when retrieval is weak. Private reference use of lawfully-held code editions only.
