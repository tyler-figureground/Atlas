---
name: code-analysis
description: Generate a STANDARD CODE ANALYSIS cover-sheet for a building project. Activate when the user types /code-analysis, or asks to "run a code analysis", "produce a code summary / code review sheet", "build the code cover sheet", or wants occupant load + egress + allowable height/area assembled into one cited document for a project. Reads the project's PROJECT.md, runs deterministic norma calculators, quotes governing corpus sections, writes Markdown into the project's code dir, and offers a Google Docs export.
---

> **Norma engine.** This skill calls the `norma` CLI (an editable install of the Norma engine — calculators + corpus are live). If `norma` isn't on PATH, put the Python Scripts dir on PATH or use `python -m norma.cli <verb>`. Universal context — persona, source types, corpus routing, known divergences — is in the plugin's [`agents.md`](../../agents.md).
>
> **Hard rules:** ground every answer in the corpus (`norma search` / `norma grep`), never memory; quote the controlling text verbatim and cite `<edition> § <number>`; numbers come from `norma codecalc`, never by hand; run `norma guard -j <j>` on every draft; abstain over guessing. You answer the architect of record **as a peer** — never "consult a professional," and do not emit the marketplace disclaimer marker.

# Standard Code Analysis Generator

Assembles a single cited cover-sheet document from the deterministic calculators and the local code corpus - the thing that goes on the first sheet of a permit set.

This is the *generator* sibling of `/ibc`. `/ibc` answers one question; `/code-analysis` runs the whole battery for one project and writes a document.

## Document-specific rules

- **State the governing edition + jurisdiction up front and on every line.** Every value-bearing line cites `<edition> <section>`, e.g. `2022 NYC Building Code Table 1004.1.3`. A line with a number and no citation is a bug.
- **Flag every table-derived number** with a trailing ` - verify against published code`.
- **A cover sheet for a locality must carry the local layer.** In a California locality (`-j napa`, `napa-city`, `sonoma`, `calistoga`, `yountville`, `american-canyon`) the ordinance overrides the state base, and under `-j napa` the **adopted regulatory instruments** - Napa County Road & Street Standards (2023), Napa County Defensible Space Guidelines (May 2021) - are governing, citable law incorporated by county ordinance. A sheet built from `-j ca` for a Napa County project is wrong on its face. Values taken from an instrument carry a trailing ` - verify tables, charts, and plates against the published instrument`.
- **Never cite the advisory layers.** The DGS `dgs` block (state Title 24 guidance) and the AHPP `advisory` block inform the work; neither governs and neither belongs in the Code References list.
- **Run `norma guard` on the finished draft before presenting.** If any citation comes back UNVERIFIED, the document is not done - locate the real section in the corpus and fix it, then re-run until it passes.

## Inputs: the project profile

```bash
norma project active        # active project (from the workspace PROJECT.md front-matter)
norma project show          # full field set (jurisdiction, occupancy, construction, sprinklered, …)
```

`norma project show` prints the fields the analysis needs: `jurisdiction` (nyc|california|other), `_corpus` (e.g. `nyc/2022`), `occupancy_group`, `construction_type`, `sprinklered`, `stories`, `building_area_sf`, `frontage_ft`, plus `existing_co_occupant_load`, `existing_exits`, `place_of_assembly_strategy`, `tenancy`, `notes`. **Confirm scope** before adopting it: `norma project scope-check "<project name or address>"` - a `WARNING` means the active project doesn't match the building you were asked about.

### If fields are missing - interview, don't assume

If there is no active project, or required fields are blank, ask the architect directly in one batched message. Minimum set to run a full analysis:

- **Jurisdiction / location** (sets the governing edition)
- **Occupancy group(s)** - e.g. `B`, `A-2`; note mixed/separated vs. non-separated
- **Construction type** - e.g. `I-B`, `II-A`, `V-B`
- **Sprinklered?** - boolean or system (`NFPA 13` / `13R` / `13D` / none)
- **Stories** above grade plane and **building/fit-out area (sf)**
- **Frontage (ft)** and open-space details if a Chapter 5 frontage increase is claimed
- **Per-space breakdown** (function of space + area sf) for the occupant-load table

Offer to capture the answers via **`/project-dossier`** - it writes the `PROJECT.md` front-matter that `norma project active` reads, so the next run auto-scopes.

### If the input is a drawing or PDF

When the project arrives as a PDF/drawing rather than a profile, ingest it first with `norma drawing` (full workflow in the drawing-analysis skill): `norma drawing info` triages each page (vector vs scanned), `sheets` rosters them, `text --region br` pulls the title block (address → jurisdiction, scale), and `render --for-vision` yields legible tiles. Feed extracted space areas into `occupant-load` - do not retype numbers the tool already extracted.

When the architect has the **CAD/BIM source** (DWG/DXF/IFC) rather than only a plot, prefer `norma ingest <file>` - it returns one structured `extract` (IFC: `spaces[].area` + `doors[].width` semantically; DXF/DWG: exact `geometry`). Feed `spaces[].area` into `occupant-load` and `geometry` into `plancheck` with no eyeballing. Fidelity order: IFC > DXF/DWG > vector-PDF > vision.

## Calculators

```bash
norma codecalc occupant-load --function "Business areas" --area 18500 -j nyc --json
norma codecalc min-exits     --load 185 --occupancy B                 -j nyc --json
norma codecalc egress-width  --load 185 --component stairways --sprinklered -j nyc --json
norma codecalc egress-width  --load 185 --component other     --sprinklered -j nyc --json
norma codecalc travel        --occupancy B --sprinklered               -j nyc --json
norma codecalc allowable     --occupancy B --construction I-B --sprinklered -j nyc --json
```

Rules:
- Use the returned `section`/`sections` verbatim as the citation.
- If a result has `"error"`, print the message and `options` to the architect and ask which to use.
- If a result has `"verify"`, carry that text into the sheet as a `verify` note on that line.
- For `min-exits` above the first story, pass `--story N` (1 = first story above grade plane). The single-exit allowance is first-story-only; without `--story` the result carries a `verify` caveat and may understate exits on an upper floor. E.g. `norma codecalc min-exits --load 36 --occupancy B --story 5 -j nyc` → 2 exits.

## Pulling governing sections from the corpus

For each computed value, open the corpus and quote the controlling section so the sheet is self-supporting:

```bash
norma grep "1016\.2\.1" -j nyc
norma grep -i "occupant load factor|travel distance|allowable area" -j nyc
```

For any cover-sheet item whose section you don't already know (fire-resistance ratings, special inspections, accessibility scoping), run concept search first, then quote the hit:

```bash
norma search "fire-resistance rating exterior bearing wall" -j nyc
norma search "accessible route entrance"                    -j ca
```

Read the matched chapter file around the hit (include exceptions). Resolve cross-references before citing.

### The local and adopted layers

For a project in one of the six California localities, run the dossier and read every governing block, not just the code candidates:

```bash
norma answer --q "fire apparatus access road width" -j napa
```

- `candidates` - code and local-ordinance hits. Governing.
- `adopted` - the county-adopted instruments. **Governing and citable**, with `publication`, `edition` and `adopted_by` on every entry. Cite as `Napa County Road & Street Standards 2023 § 15 "Design Criteria"`.
- `dgs` / `advisory` - context only, never cited.

Read the three verdicts alongside them. `confidence` scores the code candidates and is the only one that drives `abstain`; `standards_confidence` and `adopted_confidence` score their own blocks and move nothing else. A LOW on a block means thin retrieval evidence, not that the block is wrong, and `null` means no verdict was possible rather than LOW. When a sheet line rests on a LOW block, say so on the line instead of presenting it as settled.

## Output document

Write Markdown into the project's code dir. Get the destination with **`norma project analysis-dir`** (it prints/creates `<workspace>/06 Research & Existing Conditions/Code/`), then write **`06 …/Code/<project>-code-analysis.md`**. Its first line is the `<!-- architecture-studio:report -->` marker, so the marketplace's metadata hook recognises it as a report. Use exactly these sections, every value-line ending in a `<edition> <section>` citation:

1. **Project & Jurisdiction** - name, address, jurisdiction, governing edition (one line explicitly), corpus path.
2. **Occupancy Classification** - group(s), mixed-use treatment (separated/non-separated), cite Chapter 3 sections.
3. **Construction Type** - Chapter 6 type, cite Table 601 element ratings as relevant.
4. **Allowable vs. Actual** - table: Height (ft), Stories, Area (sf) with allowable (from `allowable`, incl. frontage increase if claimed) vs. actual (from the profile), pass/fail per row. Cite Chapter 5 (Tables 503/504/506 per edition) + the section returned by the calculator.
5. **Occupant Load** - per-space table: Function | Area (sf) | Factor | Basis | OL | Section; total. Cite the occupant-load-factor table (`Table 1004.x`).
6. **Means of Egress** - exits required vs. provided; required egress width (stairways + other); max travel distance; common-path-of-travel limit. Each line cited.
7. **Fire-Resistance Ratings** - structural elements, separations, shaft/corridor ratings; cite Table 601 / Chapter 7 sections.
8. **Accessibility scope** - applicable chapter: IBC/NYC Ch. 11; **California splits 11A (housing) vs 11B (public/commercial)** - pick the right one and say which. Cite the governing section.
9. **Code References** - consolidated list of every `<edition> <section>` cited above, deduped.

### Dwellings: the residential code variant

When the work is a detached one- or two-family dwelling, a townhouse, or an accessory structure inside the residential code's scope (CRC / IRC § R101.2), the commercial battery does not apply. Confirm scope first and cite it in section 1. Keep the same nine headings, in order, so the sheet reads like every other code analysis. A heading whose subject the residential code does not regulate stays in place with one line saying why, cited. Never drop it and never compute it anyway.

| # | Heading | What goes under it for a dwelling |
|---|---|---|
| 1 | Project & Jurisdiction | As above, plus the scope finding (`<edition> § R101.2`) and, in California, a per-part table: CRC, Energy Code, CALGreen, CFC / WUI, each with its edition and local amending section. |
| 2 | Occupancy Classification | `R-3` dwelling and `U` garage or accessory, stated for reference. Note that the residential code governs in place of the building code's Chapter 3. |
| 3 | Construction Type | One line: the residential code does not assign a Chapter 6 type. Then state the construction method and the prescriptive path relied on, with its limits (`R301`). Say whether an engineer is required. |
| 4 | Allowable vs. Actual | Replace the Chapter 5 table with the scope limits: stories above grade plane, height, and the prescriptive-path conditions (wind, seismic design category, snow, flood). Each row gets the limit, the actual and pass/fail. Do not run `allowable`. |
| 5 | Occupant Load | One line: not computed, because the residential code has no occupant-load provisions. Do not run `occupant-load`. |
| 6 | Means of Egress | Emergency escape and rescue openings (`R310`), egress door, hallways, stairs and handrails (`R311`), guards and window-fall protection (`R312`). Flag any EERO an addition makes non-compliant; it is often the item that moves walls. |
| 7 | Fire-Resistance Ratings | Fire separation distance and exterior walls (`R302.1`), dwelling-to-garage separation (`R302.6`), two-family or townhouse separation, sprinklers (`R313` plus any local trigger, with the arithmetic shown), smoke and CO alarms (`R314`, `R315`), and wildland-urban interface (`R337` / CWUIC) where mapped. |
| 8 | Accessibility scope | Usually not applicable: say why and cite the scoping section. California 11A reaches covered multifamily, not a private single-family dwelling. Say what would change that: a public or commercial use brings in 11B, a covered multifamily building 11A. |
| 9 | Code References | As above. |

Energy, CALGreen and flood findings go under 7 or as a short item after 8, cited like any other line. If a dwelling sheet runs `allowable`, `occupant-load` or `egress-width`, the scope test was skipped. Studio users: the Code Analysis reference set shows this variant on real projects (E1, E2, and N1 section 12).

Formatting conventions:
- Header line: `Governing code: <edition> (<jurisdiction>). All citations are to this edition unless noted.`
- Every table-derived line: trailing ` - verify against published code`.
- Where a calculator returned `verify`, append `verify: <text>`.
- No em dashes; use a spaced hyphen.

## Citation guard (mandatory final gate)

```bash
norma guard -j nyc --text "$(cat "$(norma project analysis-dir)/<project>-code-analysis.md")"
```

Exit `0` = all citations traceable. Exit `1` = UNVERIFIED citations present - **do not present**; find the real section and fix, then re-run. Report the guard result (verified/total) to the architect as evidence the sheet is clean.

## Export to Google Docs (offer after the sheet passes)

After the Markdown is written and the guard passes, offer to export via the **google-workspace** MCP. Do NOT call MCP during skill setup - only if the architect says yes.

Steps at use-time:
1. `ToolSearch` with `select:mcp__google-workspace__import_to_google_doc` to load its schema.
2. Prefer **`import_to_google_doc`** - imports the Markdown file directly, preserving heading/table structure. Pass the absolute path and a doc title like `Code Analysis - <Project> (<edition>)`.
3. Fallback **`create_doc`** + `batch_update_doc` / `insert_doc_elements` only if `import_to_google_doc` is unavailable.
4. If the MCP returns an auth/consent error, tell the architect the exact tool and that it needs Google authorization (`start_google_auth`), and stop.

The local Markdown in `06 …/Code/` is the source of truth; the Doc is a convenience copy.

## Worked example

`/code-analysis` with an active project (NYC, Group B, Type I-B, NFPA 13, 22 stories, 18500 sf fit-out, 200 ft frontage):

```bash
norma project active
# FiDi Office Fit-Out  [2022 NYC Building Code]

norma codecalc occupant-load --function "Business areas" --area 18500 -j nyc --json
# -> occupants 185, factor 100 gross, section "Table 1004.1.3"

norma codecalc min-exits --load 185 --occupancy B -j nyc --json
norma codecalc egress-width --load 185 --component stairways --sprinklered -j nyc --json
norma codecalc egress-width --load 185 --component other --sprinklered -j nyc --json
norma codecalc travel --occupancy B --sprinklered -j nyc --json
norma codecalc allowable --occupancy B --construction I-B --sprinklered -j nyc --json

norma grep -i "business areas|occupant load factor" -j nyc
norma grep "1016\.2\.1|common path" -j nyc

# Assemble 06 …/Code/fidi-office-fit-out-code-analysis.md (9 sections, every line cited)

norma guard -j nyc --text "$(cat "$(norma project analysis-dir)/fidi-office-fit-out-code-analysis.md")"
# -> expect "PASS: all citations traceable to corpus."
```

Present to the architect: the path to the written sheet, the guard result (e.g. `12 verified, 0 unverified`), and the export offer.
