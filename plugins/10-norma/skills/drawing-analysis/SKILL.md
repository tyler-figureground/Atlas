---
name: drawing-analysis
description: Vision-grounded life-safety / egress review of a floor plan. Activate when the user types /drawing-analysis (or /plan-review), drops in a PDF or image of a floor plan, life-safety plan, or egress diagram, or asks you to "check this plan", "review the egress on this drawing", "do a life-safety review", or find exit-separation / dead-end / travel-distance / occupant-load issues on a drawing. Reads the drawing with vision, then runs every number through the deterministic norma calculators and quotes the controlling corpus section verbatim.
---

> **Norma engine.** This skill calls the `norma` CLI (an editable install of the Norma engine — calculators + corpus are live). If `norma` isn't on PATH, put the Python Scripts dir on PATH or use `python -m norma.cli <verb>`. Universal context — persona, source types, corpus routing, known divergences — is in the plugin's [`agents.md`](../../agents.md).
>
> **Hard rules:** ground every answer in the corpus (`norma search` / `norma grep`), never memory; quote the controlling text verbatim and cite `<edition> § <number>`; numbers come from `norma codecalc` / `norma plancheck`, never by hand; run `norma guard -j <j>` on every draft; abstain over guessing. You answer the architect of record **as a peer** — never "consult a professional," and do not emit the marketplace disclaimer marker.

# Drawing Analysis (life-safety / egress plan review)

Reviews an actual **drawing** - a floor plan, life-safety plan, or egress diagram supplied as a PDF or image. Vision reads the drawing (spaces, areas, exits, corridors, dimensions, scale); the deterministic tools compute every code conclusion. The drawing is the input; the code math is never done by eye.

> Vision measures. The tools compute. The corpus is cited. Keep those three jobs separate in every answer.

## What to extract from the drawing

Build a structured inventory, tagging each item's source/confidence:

- **Sheet identity & scale** - sheet title, level/floor, drawing scale, north arrow. Note the scale source (title block vs scale bar).
- **Rooms / spaces** - name, apparent use/function-of-space, and area. Prefer an **area tag** or **dimension string** on the drawing; only scale off the plan if neither is present (and flag it).
- **Occupancy & sprinkler** - from a code-plan note if present, else from the active project, else ask.
- **Means of egress** - each exit / exit-access doorway / stair, its location, and the straight-line distance between the two most-remote required exits (for the separation check). The overall diagonal of the area served.
- **Corridors** - widths; any dead-end corridor and its length.
- **Travel paths** - the most-remote occupied point to the nearest exit (travel distance), and the point where two independent paths first become available (common path).
- **Doors** - egress doors, swing direction (matters where a door serves >= 50 occupants), clear width.

For anything you cannot read, put it on an explicit **"could not determine"** list rather than estimating silently.

## Tools

**Ingest the PDF first - before vision.** `norma drawing` triages the file, pulls the text layer (room tags, dimension strings, title block) with no vision, rosters the sheets, and renders legible tiles. A 36" sheet read whole is downsampled to ~1500 px (≈ 42 px/inch, so 3/32" text ≈ 4 px) - read its tiles instead.

```bash
# Ingest (run BEFORE looking at the drawing)
norma drawing info   plans.pdf                       # per-page: size, vector/scanned, tiles needed
norma drawing sheets plans.pdf                       # sheet numbers/titles + drawing-index page
norma drawing text   plans.pdf --page 3 --region br  # title block / tags as TEXT, with coords
norma drawing render plans.pdf --page 3 --for-vision # legible PNG tiles -> Read each one

# Exact source - a DWG/DXF/IFC beats eyeballing a PDF (use it whenever the architect has it)
norma ingest existing-conditions.dxf   # DXF/DWG: exact model-space extents -> plancheck, layers, placed text
norma ingest "Montez Radio.ifc"        # IFC: IfcSpace name/number/area + IfcDoor widths, semantic (no vision)

# Geometry
norma plancheck scale    --measured 3.5 --scale "1/8\"=1'-0\""
norma plancheck diagonal --width 120 --length 90
norma plancheck exit-sep --diagonal 150 --separation 60 --sprinklered -j nyc
norma plancheck dead-end --length 34 --occupancy B --sprinklered      -j ca

# Loads / exits / width / travel
norma codecalc occupant-load --function "Business areas" --area 5000 -j ca
norma codecalc min-exits     --load 120 --occupancy B               -j nyc
norma codecalc egress-width  --load 120 --component other --sprinklered -j ca
norma codecalc travel        --occupancy B --sprinklered            -j nyc

# Find a provision by concept when you don't know the section number
norma search "emergency lighting in corridors" -j nyc
```

Add `--json` for the raw result dict. Both tools return `section`, `edition`, and any `note`/`verify`.

**Prefer the source file over the plot.** A PDF is flattened; the exact data lives one layer down. Fidelity order is **IFC > DXF/DWG > vector-PDF text > rendered tiles > whole-sheet vision**. If the architect has the CAD/BIM file, `norma ingest <file>` returns one structured `extract` (it routes by extension): DXF/DWG give exact overall dimensions and stair/exit coordinates - feed `geometry.width`/`height` straight into `norma plancheck` for a *measured* exit-separation result instead of "by inspection"; IFC gives each `IfcSpace` area and `IfcDoor` width semantically - feed `spaces[].area` into `norma codecalc occupant-load` and `doors[].width` into the egress-width check, no tagging by eye. Only fall back to vision when no source file exists.

**Establish the scale before measuring anything.** Read it from the title block / scale bar. If illegible or absent, ask the architect for the scale or one known dimension to calibrate - do not guess a scale. All paper measurements go through `norma plancheck scale`.

## Workflow

1. **Ingest first.** Run `norma drawing info` then `sheets` to classify each page (vector vs scanned) and roster the set - this auto-answers most sheet/level/scale-source questions. On a **vector** page pull tags/dimensions/title block with `norma drawing text` (no vision); on a **scanned** page or any page `info` flags 'too small' to read whole, run `norma drawing render --for-vision` and Read the legible tiles. Only then look at the drawing. If multiple sheets, review the life-safety/floor-plan sheets (or ask which) in order.
2. **Scope, and check it.** Run `norma project active`; adopt its jurisdiction/occupancy/sprinkler unless the drawing's code notes override. State what you adopted. **Confirm the drawing is this project:** run `norma project scope-check "<sheet title-block project / address>"` - a `WARNING` means the active project doesn't match the drawing, so confirm scope before analyzing (don't silently apply the wrong project's jurisdiction/occupancy).
3. **Calibrate scale.** Read it; if unreadable, ask for it or for one known dimension.
4. **Extract the inventory** (section above), tagging each value: *drawing-tagged*, *scaled (approx)*, or *could-not-determine*.
5. **Compute, never eyeball:** occupant load → `norma codecalc occupant-load`; required exits → `norma codecalc min-exits`; required egress width vs. provided → `norma codecalc egress-width`; overall diagonal → `norma plancheck diagonal`; exit separation → `norma plancheck exit-sep`; dead-end → `norma plancheck dead-end`; travel distance → `norma codecalc travel`.
6. **Quote the controlling text.** For each finding, search the governing corpus for the returned section (`norma grep`) and **Read** it verbatim including exceptions. Run `norma xref` on key sections.
7. **Check the local and adopted layers.** For a California locality use the locality key (`-j napa`, `napa-city`, `sonoma`, `calistoga`, `yountville`, `american-canyon`), never `-j ca`. Then run `norma answer --q "<finding>" -j <j>` and read the `adopted` block: for unincorporated Napa County the **Napa County Road & Street Standards (2023)** and **Defensible Space Guidelines (May 2021)** are governing, citable law incorporated by county ordinance, and they control exactly the site-plan items a life-safety review turns up - access road width, dead-end length, turnaround geometry, driveway grade, defensible space. Cite them like any other governing text and stamp instrument values `verify tables, charts, and plates against the published instrument`. The `dgs` and `advisory` blocks never govern and never appear as citations. `adopted_confidence` scores only its own block: it never moves the code answer's `abstain`, and `null` there means no verdict was possible, not LOW.
8. **Guard.** Pipe the drafted report through `norma guard -j <j>`; resolve any UNVERIFIED citation.
9. **Report.** Write the review to the project's code dir - get it with `norma project analysis-dir` (creates `<workspace>/06 Research & Existing Conditions/Code/`) and save `06 …/Code/<project-or-sheet>-drawing-review.md`. Offer a Google Doc export (Workspace MCP `create_doc` / `import_to_google_doc`).

## Report shape

The first line is the `<!-- architecture-studio:report -->` marker, so the marketplace's metadata hook recognises the file as a report.

```
<!-- architecture-studio:report -->
# Drawing Review - <sheet / project>
Jurisdiction/edition · Occupancy · Sprinklered · Scale (source)

## Findings
| Check | Measured (source) | Code limit | Result | Section |
|---|---|---|---|---|
| Occupant load (Suite A) | 3,000 sf (tagged) | 100 gross | 30 occ | NYC § 1004.5 |
| Min exits | 30 occ | <= 49 single-exit | 1 OK | NYC § 1006.x |
| Exit separation | 60 ft provided (scaled) | 50 ft (1/3 diag, spr) | PASS (verify) | NYC § 1007.1.1 |
| Dead-end corridor | 34 ft (scaled) | 50 ft (spr, Grp B) | PASS | NYC § 1020.4 |
| Travel distance | ~180 ft (scaled) | 300 ft (spr) | PASS | NYC § 1017.x |

## Detail (per finding)
- Direct call + measured vs. limit.
- Controlling text: verbatim quote cited `<edition> § <number>` (+ table row if table-derived).
- Conditions/exceptions that apply.

## Could not determine
- <items the drawing did not let you read>

## Verify before relying
- Scale-derived dimensions (list which findings depend on them).
- Any not-in-corpus (2009 IBC sprinklered-exception) flags.
- Confirm against the jurisdiction's adopted edition.
```

## Vision limits (state these when they bite)

- Reading a full architectural sheet at once is unreliable - it is downsampled to ~1500 px on the long edge (a 36" sheet ≈ 42 px/inch, so 3/32" text ≈ 4 px tall). Use `norma drawing render --for-vision` tiles; trust a whole-sheet read only for gestalt (where things are), never for numbers or small text.
- A scaled measurement is approximate; a near-margin PASS/FAIL is provisional until checked against a dimensioned drawing or model file.
- Travel distance and common path follow the actual walkable path around walls/furniture; a straight-line read understates them - treat it as a lower bound and say so.
- An L-shaped or irregular area's "overall diagonal" is the longest straight corner-to-corner line, not the bounding-box diagonal - confirm you measured the right one.
- You cannot read what is not drawn (door swings, rated assemblies, ceiling conditions) - put those on the "could not determine" list.

## Sanity checks

- `norma plancheck diagonal --width 120 --length 90` → **150 ft**; `exit-sep --diagonal 150 --sprinklered -j ca` → **50 ft** (1/3).
- Non-sprinklered or ineligible occupancy dead-end limit = **20 ft**; sprinklered eligible group = **50 ft**.
- `norma plancheck scale --measured 3.5 --scale 1/8"=1'-0"` → **28 ft**.
