---
name: allowable-area
description: Allowable building height, stories and area calculator. Activate when the user types /allowable-area, or asks about allowable height (feet), number of stories, allowable floor area, height/area increases, or whether a proposed building fits its construction type. Computes via the norma engine (Tables 504/506) and quotes the controlling table rows verbatim; compares allowable vs actual when a project is active.
---

> **Norma engine.** This skill calls the `norma` CLI (an editable install of the Norma engine — calculators + corpus are live). If `norma` isn't on PATH, put the Python Scripts dir on PATH or use `python -m norma.cli <verb>`. Universal context — persona, source types, corpus routing, known divergences — is in the plugin's [`agents.md`](../../agents.md); full divergences, dossier blocks and verdicts in [`reference/norma-context.md`](../../reference/norma-context.md).
>
> **Hard rules:** ground every answer in the corpus (`norma search` / `norma grep`), never memory; quote the controlling text verbatim and cite `<edition> § <number>`; numbers come from `norma codecalc`, never by hand; run `norma guard -j <j>` on every draft; abstain over guessing. You answer the architect of record **as a peer** — never "consult a professional," and do not emit the marketplace disclaimer marker.

# Allowable Height / Stories / Area

Reports **allowable building height (ft), number of stories, and allowable floor area (sf)** by occupancy group + construction type + sprinkler status, optionally applying a frontage/open-perimeter area increase, and shows **allowable vs. actual** when a project is active.

## Inputs to gather

- **Occupancy group** (e.g. `B`, `A-2`, `R-2`).
- **Construction type** (e.g. `IIA` / `II-A` / `VB`).
- **Sprinklered?** (NFPA 13 throughout assumed unless stated).
- **Frontage / open perimeter** (optional) - `frontage_ft` and building perimeter for the § 506.3 frontage area increase.
- **Actual** proposed height, stories, area - to compare against allowable (the active project carries these as `building_area_sf`, `stories`, `frontage_ft`).

## Calculator

```bash
norma codecalc allowable --occupancy B --construction IIA --sprinklered -j ibc
norma codecalc allowable --occupancy A-2 --construction II-A           -j ca --json
```

Construction-type spelling is normalized (`IIA`, `II-A`, `ii a` all match). `Unlimited` surfaces IBC `null` / CA `"UL"` - report it as unlimited, not missing.

The `--json` result gives `height_ft`, `stories`, `area_sf`, contributing `sections`, plus `note`/`verify`.

**Frontage increase.** `codecalc` returns the *base* tabular area only - it does not compute the frontage/open-perimeter increase. If frontage is provided, apply the code formula from the controlling section text:
- IBC 2009 § 506.2: `Aa = At + (At × If) + (At × Is)`
- NYC/CA (2015/2024-based): § 506.2 / 506.3

Show each term step-by-step and quote that section verbatim - read it from the corpus before applying, do not use a remembered formula.

## Workflow

1. **Scope.** Run `norma project active`; adopt occupancy/construction/sprinkler and capture `building_area_sf`, `stories`, `frontage_ft` for the comparison. State the assumptions.
2. **Compute base.** `norma codecalc allowable ... --json`. Capture `sections`.
3. **Apply frontage increase** (only if provided): read the controlling 506 section in the governing corpus (`norma grep`), apply the formula term-by-term.
4. **Quote.** Read the governing corpus for the returned `sections` (Tables 504/506) and quote the base row(s) verbatim.
5. **Cross-check & guard.** Run `norma xref` on the controlling sections; pipe the draft through `norma guard -j <j>` and fix/flag any UNVERIFIED citation.
6. **Answer** in this shape:
   - **Direct answer:** allowable height (ft) / stories / area (sf); if a project is active, an **allowable vs. actual** line for each with pass/fail.
   - **Controlling text:** verbatim table row(s) cited as `<edition> Table 504.x / 506.2`, plus the frontage-increase math and its section if applied.
   - **Conditions/exceptions:** sprinkler increase basis, mixed-occupancy caveats, `Unlimited` where applicable.
   - **Edition note:** source + verify-against-governing-edition reminder. Note: base-IBC Tables are 2009 (§ 503 / Table 503); NYC/CA use the 2015/2024 renumbering (Tables 504.3, 504.4, 506.2).
