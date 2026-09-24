<div align="center">

```
 █████╗ ██████╗  ██████╗██╗  ██╗    ███████╗████████╗██╗   ██╗██████╗ ██╗ ██████╗
██╔══██╗██╔══██╗██╔════╝██║  ██║    ██╔════╝╚══██╔══╝██║   ██║██╔══██╗██║██╔═══██╗
███████║██████╔╝██║     ███████║    ███████╗   ██║   ██║   ██║██║  ██║██║██║   ██║
██╔══██║██╔══██╗██║     ██╔══██║    ╚════██║   ██║   ██║   ██║██║  ██║██║██║   ██║
██║  ██║██║  ██║╚██████╗██║  ██║    ███████║   ██║   ╚██████╔╝██████╔╝██║╚██████╔╝
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝    ╚══════╝   ╚═╝    ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝
```

**Architecture Studio**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/tyler-figureground/skills-for-architects)](https://github.com/tyler-figureground/skills-for-architects/releases)

</div>

> Agents, skills, and rules for architects, designers, and AEC professionals — use with [Claude Desktop](https://claude.ai) or [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

**Architecture Studio** teaches Claude architecture-specific workflows — site analysis, zoning, space programming, specifications, materials research, sustainability, and presentations.

**7 agents**, **45 skills**, **7 rules**, and **3 hooks** across **11 plugins**. Built by [ALPA](https://alpa.llc).

## What's New in 1.2

- **Project dossier + decision records** — the new [Project Dossier plugin](./plugins/09-project-dossier) gives every project a persistent state: `/project-dossier` maintains `PROJECT.md` (sourced, dated facts — site, zoning, program, code), and `/decision` captures ADR-style decision records in `decisions/`. Analysis skills read the dossier before fetching, append their findings after, and propose `/decision` when an analysis forces a choice.
- **Agents are native subagents** — each agent now ships inside the plugin it orchestrates; installing the plugin registers it with Claude Code, so Claude can delegate to it automatically.
- **Hooks register themselves** — enable the [Dispatcher plugin](./plugins/08-dispatcher) and the three hooks are live. The manual settings merge is gone.

Full history in the [CHANGELOG](./CHANGELOG.md).

## Architecture

```
Architecture Studio
├── /studio                              ← entry point (08-dispatcher)
│
├── plugins/
│   ├── 00-due-diligence                 7 skills
│   ├── 01-site-planning                 4 skills · agent: site-planner
│   ├── 02-zoning-analysis               2 skills · agent: nyc-zoning-expert
│   ├── 03-programming                   2 skills · agent: workplace-strategist
│   ├── 04-specifications                1 skill
│   ├── 05-sustainability                4 skills · agent: sustainability-specialist
│   ├── 06-materials-research           12 skills · agents: researcher + ffe-designer
│   ├── 07-presentations                 3 skills · agent: brand-manager
│   ├── 08-dispatcher                    2 skills · hooks ship here
│   ├── 09-project-dossier               2 skills · PROJECT.md + decisions/
│   └── 10-norma                         6 skills · building-code analysis (norma engine)
│
├── rules/                               7 rules · 2 hook-enforced, 5 advisory
├── tools/atlas/                         studio drive TUI/CLI · Python, own tests, not a plugin
└── docs/adr/                            architecture decision records
```

**Agents** orchestrate skills across plugins — they assess your input, choose a path, and exercise judgment; each ships inside the plugin it orchestrates and registers as a native Claude Code subagent. **Skills** are single-purpose tools invoked with a slash command. **Rules** are cross-cutting conventions (two hook-enforced, five advisory). **Hooks** are event-driven automations that ship with the Dispatcher plugin and register automatically. Skills are grouped into **plugins** (installable bundles organized by project lifecycle).

## Quick Start

### Install

**Claude Desktop:** Open **Customize** → **Browse plugins** → **+** → **Add marketplace from GitHub** → enter `tyler-figureground/skills-for-architects`

**Claude Code:**
```bash
claude plugin marketplace add tyler-figureground/skills-for-architects
claude plugin install 01-site-planning@skills-for-architects
```

### Use

Type `/studio` followed by what you need. The router reads your request and hands off to the right agent or skill.

```
/studio task chair, mesh back, under $800
/studio 123 Main St, Brooklyn NY
/studio I need a space program for 200 people
/studio parse this EPD
```

Type `/skills` for the full menu. Or call any skill directly by name (e.g. `/environmental-analysis 123 Main St`).

## Agents

Agents are the orchestration layer. Describe your task — the agent decides which skills to call, in what order, and what judgment to apply.

| Agent | Domain | What it does |
|-------|--------|-------------|
| [site-planner](./plugins/01-site-planning/agents/site-planner.md) | Site Planning | Runs all site research in parallel, synthesizes a unified brief with opportunities and constraints |
| [nyc-zoning-expert](./plugins/02-zoning-analysis/agents/nyc-zoning-expert.md) | Due Diligence + Zoning | Full NYC property and zoning analysis — due diligence, buildable envelope, 3D visualization |
| [workplace-strategist](./plugins/03-programming/agents/workplace-strategist.md) | Programming | Translates headcount and work style into space programs — occupancy compliance, zone allocation, room schedules |
| [product-and-materials-researcher](./plugins/06-materials-research/agents/product-and-materials-researcher.md) | Materials Research | Finds products from a brief, extracts specs from URLs/PDFs, tags and classifies, finds alternatives |
| [ffe-designer](./plugins/06-materials-research/agents/ffe-designer.md) | FF&E Design | Builds clean schedules from messy inputs, composes room packages, runs QA, exports to dealer formats |
| [sustainability-specialist](./plugins/05-sustainability/agents/sustainability-specialist.md) | Sustainability | Evaluates environmental impact — finds EPDs, compares GWP, checks LEED eligibility, writes spec thresholds |
| [brand-manager](./plugins/07-presentations/agents/brand-manager.md) | Presentations | Owns visual identity — builds decks, creates palettes, QAs deliverables for presentation readiness |

See the [agents index](./agents/README.md) for full workflows and handoff logic.

## Plugins & Skills

Organized by project lifecycle — from due diligence through delivery.

| # | Plugin | Skills | Description |
|---|--------|--------|-------------|
| 0 | [Due Diligence](./plugins/00-due-diligence) | 7 | NYC property data: landmarks, DOB permits, violations, ACRIS, HPD, BSA. |
| 1 | [Site Planning](./plugins/01-site-planning) | 4 | Site research: environmental, mobility, demographics, history. |
| 2 | [Zoning Analysis](./plugins/02-zoning-analysis) | 2 | Zoning envelope analysis and 3D visualization for NYC. |
| 3 | [Programming](./plugins/03-programming) | 2 | Workplace strategy: space programs, occupancy loads, IBC compliance. |
| 4 | [Specifications](./plugins/04-specifications) | 1 | CSI outline specifications from a materials list. |
| 5 | [Sustainability](./plugins/05-sustainability) | 4 | EPD parsing, research, comparison, and GWP thresholds. |
| 6 | [Materials Research](./plugins/06-materials-research) | 12 | FF&E product research, spec extraction, cleanup, and image processing. Exports to SIF dealer formats and [Norma](https://norma.llc). |
| 7 | [Presentations](./plugins/07-presentations) | 3 | Slide deck generation, color palette creation, and image resizing for web, social, slides, and print. |
| 8 | [Dispatcher](./plugins/08-dispatcher) | 2 | Studio router (`/studio`), help menu (`/skills`), and the three hooks. |
| 9 | [Project Dossier](./plugins/09-project-dossier) | 2 | Persistent project facts (`PROJECT.md`) and ADR-style decision records. |
| 10 | [Norma](./plugins/10-norma) | 6 | Building-code analysis — code Q&A, egress, allowable area, compare, drawing review. Cited verbatim via the `norma` engine. |

<details>
<summary><strong>All 45 skills</strong></summary>

### Due Diligence

| Skill | Description |
|-------|-------------|
| [`/nyc-landmarks`](./plugins/00-due-diligence/skills/nyc-landmarks) | LPC landmark and historic district check |
| [`/nyc-dob-permits`](./plugins/00-due-diligence/skills/nyc-dob-permits) | DOB permit and filing history |
| [`/nyc-dob-violations`](./plugins/00-due-diligence/skills/nyc-dob-violations) | DOB and ECB violations |
| [`/nyc-acris`](./plugins/00-due-diligence/skills/nyc-acris) | ACRIS property transaction records |
| [`/nyc-hpd`](./plugins/00-due-diligence/skills/nyc-hpd) | HPD violations, complaints, and registration |
| [`/nyc-bsa`](./plugins/00-due-diligence/skills/nyc-bsa) | BSA variances and special permits |
| [`/nyc-property-report`](./plugins/00-due-diligence/skills/nyc-property-report) | Combined NYC property report — all 6 above |

### Site Planning

| Skill | Description |
|-------|-------------|
| [`/environmental-analysis`](./plugins/01-site-planning/skills/environmental-analysis) | Climate, precipitation, wind, sun angles, flood zones, seismic risk, soil |
| [`/mobility-analysis`](./plugins/01-site-planning/skills/mobility-analysis) | Transit, walk/bike/transit scores, pedestrian infrastructure |
| [`/demographics-analysis`](./plugins/01-site-planning/skills/demographics-analysis) | Population, income, age, housing market, employment |
| [`/history`](./plugins/01-site-planning/skills/history) | Neighborhood context, landmarks, commercial activity, planned development |

### Zoning Analysis

| Skill | Description |
|-------|-------------|
| [`/zoning-analysis-nyc`](./plugins/02-zoning-analysis/skills/zoning-analysis-nyc) | NYC buildable envelope — FAR, height, setbacks, use groups from PLUTO |
| [`/zoning-envelope`](./plugins/02-zoning-analysis/skills/zoning-envelope) | Interactive 3D zoning envelope viewer |

### Programming

| Skill | Description |
|-------|-------------|
| [`/workplace-programmer`](./plugins/03-programming/skills/workplace-programmer) | Space programs from headcount and work style |
| [`/occupancy-calculator`](./plugins/03-programming/skills/occupancy-calculator) | IBC occupancy loads, egress, plumbing fixture counts |

### Specifications

| Skill | Description |
|-------|-------------|
| [`/spec-writer`](./plugins/04-specifications/skills/spec-writer) | CSI outline specs — MasterFormat divisions, three-part sections |

### Sustainability

| Skill | Description |
|-------|-------------|
| [`/epd-parser`](./plugins/05-sustainability/skills/epd-parser) | Extract data from EPD PDFs — GWP, life cycle stages, certifications |
| [`/epd-research`](./plugins/05-sustainability/skills/epd-research) | Search EC3, UL, Environdec for EPDs by material or category |
| [`/epd-compare`](./plugins/05-sustainability/skills/epd-compare) | Side-by-side environmental impact comparison |
| [`/epd-to-spec`](./plugins/05-sustainability/skills/epd-to-spec) | CSI specs with EPD requirements and GWP thresholds |

### Materials Research

| Skill | Description |
|-------|-------------|
| [`/product-research`](./plugins/06-materials-research/skills/product-research) | Find products from a design brief |
| [`/product-spec-bulk-fetch`](./plugins/06-materials-research/skills/product-spec-bulk-fetch) | Extract specs from product URLs at scale |
| [`/product-data-cleanup`](./plugins/06-materials-research/skills/product-data-cleanup) | Normalize messy FF&E schedules |
| [`/product-spec-pdf-parser`](./plugins/06-materials-research/skills/product-spec-pdf-parser) | Extract specs from PDF catalogs |
| [`/product-image-processor`](./plugins/06-materials-research/skills/product-image-processor) | Batch download, resize, remove backgrounds |
| [`/product-data-import`](./plugins/06-materials-research/skills/product-data-import) | Import raw product data into the master schedule |
| [`/master-schedule`](./plugins/06-materials-research/skills/master-schedule) | Connect a product library sheet to the project |
| [`/product-enrich`](./plugins/06-materials-research/skills/product-enrich) | Auto-tag products with categories, colors, materials |
| [`/product-match`](./plugins/06-materials-research/skills/product-match) | Find similar products |
| [`/product-pair`](./plugins/06-materials-research/skills/product-pair) | Suggest complementary products |
| [`/csv-to-sif`](./plugins/06-materials-research/skills/csv-to-sif) | Convert CSV to SIF for dealer systems |
| [`/sif-to-csv`](./plugins/06-materials-research/skills/sif-to-csv) | Convert SIF to readable spreadsheets |

### Presentations

| Skill | Description |
|-------|-------------|
| [`/slide-deck-generator`](./plugins/07-presentations/skills/slide-deck-generator) | HTML slide decks — editorial layout, 22 slide types |
| [`/color-palette-generator`](./plugins/07-presentations/skills/color-palette-generator) | Color palettes from descriptions, images, or hex codes |
| [`/resize-images`](./plugins/07-presentations/skills/resize-images) | Batch-resize photos for web, social, slides, and print |

### Dispatcher

| Skill | Description |
|-------|-------------|
| [`/studio`](./plugins/08-dispatcher/skills/studio) | Smart router — describe a task and get routed to the right agent or skill |
| [`/skills`](./plugins/08-dispatcher/skills/skills-menu) | Help menu listing all available skills and agents |

### Project Dossier

| Skill | Description |
|-------|-------------|
| [`/project-dossier`](./plugins/09-project-dossier/skills/project-dossier) | Create or update `PROJECT.md` — sourced, dated project facts |
| [`/decision`](./plugins/09-project-dossier/skills/decision) | ADR-style decision records — context, options, the call, consequences |

### Norma (Building Code)

| Skill | Description |
|-------|-------------|
| [`/ibc`](./plugins/10-norma/skills/ibc) | Building-code Q&A — any provision, grounded in the local corpus and cited verbatim |
| [`/egress`](./plugins/10-norma/skills/egress) | Occupant load, required exits, egress width, travel distance, common path / dead-end |
| [`/allowable-area`](./plugins/10-norma/skills/allowable-area) | Allowable height / stories / area by occupancy + construction type + sprinkler |
| [`/code-analysis`](./plugins/10-norma/skills/code-analysis) | Full code-analysis cover sheet — occupancy + egress + allowable + ratings, all cited |
| [`/compare`](./plugins/10-norma/skills/compare) | Cross-jurisdiction provision diff — IBC 2009 vs NYC 2022 vs CA 2025 |
| [`/drawing-analysis`](./plugins/10-norma/skills/drawing-analysis) | Vision-grounded life-safety / egress review of a floor-plan PDF or image |

</details>

## Rules

Cross-cutting conventions every skill is written against. Two are hook-enforced (professional-disclaimer, csi-formatting); the other five are advisory references — see [rules/](./rules) for the honest breakdown.

| Rule | What it governs |
|------|-----------------|
| [units-and-measurements](./rules/units-and-measurements.md) | Imperial/metric, area types (GSF/USF/RSF), dimensions |
| [code-citations](./rules/code-citations.md) | Building code references, edition years, jurisdiction awareness |
| [professional-disclaimer](./rules/professional-disclaimer.md) | Disclaimer language, what AI outputs can and cannot claim |
| [csi-formatting](./rules/csi-formatting.md) | MasterFormat 2018 section numbers, three-part structure |
| [terminology](./rules/terminology.md) | AEC standard terms, abbreviations, material names |
| [output-formatting](./rules/output-formatting.md) | Tables, source attribution, file naming, list structure |
| [transparency](./rules/transparency.md) | Show your work — link sources, expose inputs, make outputs verifiable |

## Hooks

Event-driven automations — they ship with the [Dispatcher plugin](./plugins/08-dispatcher) and register automatically when it's enabled. No settings merge needed.

| Hook | Event | What it does |
|------|-------|-------------|
| [post-write-disclaimer-check](./plugins/08-dispatcher/hooks/post-write-disclaimer-check.sh) | After Write | Warns if regulatory output is missing the professional disclaimer |
| [post-output-metadata](./plugins/08-dispatcher/hooks/post-output-metadata.sh) | After Write | Stamps YAML front matter onto marked plugin reports; leaves other Markdown alone |
| [pre-commit-spec-lint](./plugins/08-dispatcher/hooks/pre-commit-spec-lint.sh) | Before git commit | Flags malformed CSI section numbers |

See the [hooks directory](./plugins/08-dispatcher/hooks) for details and customization.

## Contributing

Want to add a skill for the built environment?

1. **Fork** this repository
2. Create your skill in the appropriate plugin folder (or propose a new plugin)
3. Each skill needs a `SKILL.md` with instructions and domain knowledge, a `README.md`, and any supporting data files
4. Open a **pull request** — describe what the skill does, how you tested it, and sample output

For the full conventions we apply across all our plugins (naming, layout, dispatcher pattern, versioning, hard rules from real bugs), read [PATTERNS.md](./PATTERNS.md). Release history lives in the [CHANGELOG](./CHANGELOG.md).

For guidance on organizing skills across a team, read [Distributing Skills to Teams](https://alpa.llc/articles/distributing-skills-to-teams).

## License

MIT — see [LICENSE](LICENSE).

---

Built by [ALPA](https://alpa.llc) — research, strategy, and technology for the built environment.

**Read more:** [Claude Code Cheat Sheet for Architects](https://alpa.llc/articles/claude-code-cheat-sheet) · [Distributing Skills to Teams](https://alpa.llc/articles/distributing-skills-to-teams)
