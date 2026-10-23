---
name: compare
description: Cross-jurisdiction code diff. Activate when the user types /compare, or asks how a provision differs between the 2009 IBC, 2022 NYC Building Code, and 2025 California Building Code (e.g. "how does multiple-tenant egress differ in NYC vs CA?", "business occupant-load factor across editions"). Pulls the provision from all three corpora and presents a side-by-side with each jurisdiction's section number and the material differences.
---

> **Norma engine.** This skill calls the `norma` CLI (an editable install of the Norma engine — calculators + corpus are live). If `norma` isn't on PATH, put the Python Scripts dir on PATH or use `python -m norma.cli <verb>`. Universal context — persona, source types, corpus routing, known divergences — is in the plugin's [`agents.md`](../../agents.md); full divergences, dossier blocks and verdicts in [`reference/norma-context.md`](../../reference/norma-context.md).
>
> **Hard rules:** ground every answer in the corpus (`norma search` / `norma grep`), never memory; quote the controlling text verbatim and cite `<edition> § <number>`; numbers come from `norma codecalc`, never by hand; run `norma guard -j <j>` on every draft; abstain over guessing. You answer the architect of record **as a peer** — never "consult a professional," and do not emit the marketplace disclaimer marker.

# Cross-Jurisdiction Compare

Diffs one provision across all three corpora - base **2009 IBC** (`-j ibc`), **2022 NYC Building Code** (`-j nyc`), and **2025 California Building Code** (`-j ca`) - and presents a side-by-side table: each jurisdiction's **section number**, the **controlling value/rule** quoted verbatim, and the **material difference**.

## Finding the matching section in each corpus

Section numbers diverge across editions - map by **topic**, not by reusing one number:

1. If given a **section number**, treat it as belonging to its source edition. For the other two, search by the defined term / topic phrase: `norma grep -i "multiple tenants|intervening spaces" -j nyc`
2. If given a **topic**, grep each corpus for the topic phrase, then **Read** the matched chapter file for the controlling text and exceptions in each.
3. Run `norma xref <section> -j <j>` per jurisdiction to confirm you have the right section and resolve referenced sub-sections before quoting.

## Workflow

1. **Identify** the provision (topic or section) and any qualifiers (occupancy, sprinkler, construction type).
2. **Locate** the equivalent section in each corpus by topic search; **Read** each for controlling text + exceptions.
3. **Compute** (if the provision is a numeric value) with `norma codecalc ... -j ibc|nyc|ca --json` for each; capture each `section`.
4. **Cross-check** each side with `norma xref`; **guard** the draft with `norma guard` once per jurisdiction.
5. **Present** a side-by-side table:

   | Jurisdiction | Section | Controlling rule / value (verbatim) | Material difference |
   |---|---|---|---|
   | IBC 2009 | § 1014.2.1 | "...same or similar occupancy..." | allowed |
   | 2022 NYC | § 1016.2.1 | "...shall not pass through..." | forbidden (Group M larger-tenant exception only) |
   | 2025 CBC | § 1016.2.1 | "...same or similar occupancy..." | allowed (kept model language) |

   Then a 1-3 sentence **bottom line** on the practical difference, and an **edition note** (sources + verify-against-published-code reminder). If a project is active, flag which row governs it.
