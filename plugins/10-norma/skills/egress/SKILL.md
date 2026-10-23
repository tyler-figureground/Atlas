---
name: egress
description: Means-of-egress calculator for a space or story. Activate when the user types /egress, or asks for occupant load, required number of exits, egress (capacity) width, exit-access travel distance, or common path of egress travel. Computes the numbers deterministically via the norma engine (never by hand) and quotes the controlling section verbatim from the local corpus.
---

> **Norma engine.** This skill calls the `norma` CLI (an editable install of the Norma engine — calculators + corpus are live). If `norma` isn't on PATH, put the Python Scripts dir on PATH or use `python -m norma.cli <verb>`. Universal context — persona, source types, corpus routing, known divergences — is in the plugin's [`agents.md`](../../agents.md); full divergences, dossier blocks and verdicts in [`reference/norma-context.md`](../../reference/norma-context.md).
>
> **Hard rules:** ground every answer in the corpus (`norma search` / `norma grep`), never memory; quote the controlling text verbatim and cite `<edition> § <number>`; numbers come from `norma codecalc`, never by hand; run `norma guard -j <j>` on every draft; abstain over guessing. You answer the architect of record **as a peer** — never "consult a professional," and do not emit the marketplace disclaimer marker.

# Egress Calculator

## Inputs to gather

- **Function of space** - the Table 1004.5 label, e.g. "Business areas", "Assembly, concentrated".
- **Floor area** in square feet (gross/net per the factor's basis).
- **Occupancy group** (e.g. `B`, `A-1`) - drives required exits, travel distance, common path.
- **Sprinklered?** - drives egress width, travel distance, common path.
- **Component** for width - `stairways` vs `other` (doors/corridors/ramps).

If the active project supplies any of these, default to it and say so. If the space comes from a PDF/drawing, extract its areas, scale, and title block first with `norma drawing` (see the drawing-analysis skill), then feed the extracted areas here rather than retyping them. **Better still, if the architect has the CAD/BIM source** (DWG/DXF/IFC), run `norma ingest <file>`: an IFC returns each `spaces[].area` semantically and a DXF/DWG returns exact `geometry` - feed those straight into `--area` instead of measuring or retyping. Fidelity order: IFC > DXF/DWG > vector-PDF > vision.

## Calculators

```bash
norma codecalc occupant-load --function "Business areas" --area 5000 -j ca
norma codecalc min-exits     --load 120 --occupancy B          -j ibc
norma codecalc egress-width  --load 120 --component stairways --sprinklered -j ca
norma codecalc travel        --occupancy A --sprinklered       -j nyc
```

Add `--json` for the raw result dict. Every result names the `section` it was derived from - use it verbatim as the citation anchor.

For a space **above the first story**, pass `--story N` to `min-exits` (1 = first story above grade plane). The single-exit allowance is first-story-only, so without `--story` the result carries a `verify` caveat and can understate required exits on an upper floor. E.g. `norma codecalc min-exits --load 36 --occupancy B --story 5 -j nyc` → 2 exits (single exit not permitted on story 5).

## Localities: check the layer above the state code

In a California locality (`-j napa`, `napa-city`, `sonoma`, `calistoga`, `yountville`, `american-canyon`) the ordinance amends the state base, so pass the locality key rather than `-j ca` - `-j ca` returns the unamended state text.

Egress rarely stops at the building line, and **site access is where the adopted instruments bite**. For unincorporated Napa County, fire apparatus access road width, dead-end road length, turnaround geometry and driveway grade are governed by the **Napa County Road & Street Standards (2023)**, incorporated by Napa County Code § 15.32.070; defensible space by the **Napa County Defensible Space Guidelines (May 2021)** via § 8.36.030. Both are governing, citable law. Run `norma answer --q "<question>" -j napa`, read the `adopted` block, and cite as `Napa County Road & Street Standards 2023 § 15 "Design Criteria"` with `verify tables, charts, and plates against the published instrument` on any value read from a chart or plate.

`adopted_confidence` scores that block alone and never moves the code answer's `abstain`. A LOW there means thin retrieval evidence, not that the instrument is wrong, and `null` means no verdict was possible rather than LOW.

## Exit separation & dead-end (deterministic)

`norma plancheck` handles geometry, reading the same per-jurisdiction corpora:

```bash
norma plancheck diagonal --width 120 --length 90
norma plancheck exit-sep --diagonal 150 --separation 60 --sprinklered -j nyc
norma plancheck dead-end --length 34 --occupancy B --sprinklered      -j ca
```

For the **2009 IBC** route, `plancheck` flags the sprinklered 1/3-diagonal and 50-ft dead-end values as known-code-but-not-in-corpus (OCR dropped those exception blocks); repeat that `verify` flag. NYC/CA carry them verbatim.

## Common path & dead-end

`codecalc` covers occupant load, exits, width, and travel distance directly. **Common path of egress travel** and **dead-end corridor** limits are conditional table/section limits - resolve them from the corpus:

1. Find the egress travel section family (Ch. 10). Section numbers differ by edition: **§ 1014.2** in 2009 IBC, **§ 1016.2** in NYC 2022 and CA 2025. If unsure where a limit lives, run `norma search "common path of egress travel" -j <j>` for candidate subsections.
2. Run `norma xref <travel-distance-section> -j <j>` to pull related common-path/dead-end sections, then **Read** the chapter file for the limit and its conditions (sprinklered, occupant-load <= 30, occupancy).
3. Quote the limit row verbatim with its section number.

## Workflow

1. **Scope.** Run `norma project active`; adopt its jurisdiction/occupancy/sprinkler. State the assumptions.
2. **Compute.** Call `norma codecalc` subcommands with the right `-j`. Capture the returned `section`.
3. **Quote.** Search the governing corpus for that section (`norma grep`) and **Read** it for the verbatim controlling text + exceptions.
4. **Cross-check.** Run `norma xref` on the controlling section.
5. **Guard.** Pipe the draft through `norma guard -j <j>`; fix or flag any UNVERIFIED citation.
6. **Answer** in this shape:
   - **Direct answer** with the value(s): occupant load, required exits, required width (in), max travel distance (ft), common path / dead-end limit.
   - **Controlling text:** verbatim quote(s) cited as `<edition> § <number>`, with the table row shown verbatim where table-derived.
   - **Conditions/exceptions** (sprinklered, occupant-load caps, single-exit threshold).
   - **Edition note:** source + verify-against-governing-edition reminder.

## Sanity checks

- CA 2025 business-area occupant-load factor = **150 gross**; 2009 IBC and NYC 2022 = **100 gross**.
- Group B single-exit max occupant load = **49** on the *first story above grade* (2009 IBC and NYC); NYC also allows **29** on the second story; single exit is **not permitted on upper stories** - pass `--story` to `min-exits` so it applies the right story limit.
