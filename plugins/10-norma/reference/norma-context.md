# Norma - Reference Context

Fuller reference for the three subjects `agents.md` summarizes in one line each: the
five dossier blocks, the three confidence verdicts, and the known per-edition
divergences. Moved here verbatim from `agents.md` on 2026-09-10 so the plugin context
stays under 150 lines. Read the relevant section when a skill lands on it.

---

## The dossier: five blocks, and only two of them govern

`norma answer --q "<question>" -j <j>` returns the full retrieval dossier as JSON. It carries **five** result blocks, and confusing their authority is the single most consequential mistake available here.

| Block | Authority | What to do with it |
|---|---|---|
| `candidates` | **Governing** - the code and local-ordinance hits | Quote verbatim, cite, guard |
| `adopted` | **Governing and citable** - regulatory instruments incorporated by local ordinance | Quote verbatim and cite. Stamp `verify tables, charts, and plates against the published instrument` |
| `standards` | Incorporated by reference; edition-routed | Cite only when the resolver reports `matched` |
| `dgs` | **Never governs** - state advisory | Orientation only. Never cite as authority |
| `advisory` | **Never governs** - professional practice (AHPP) | Judgment and process, not requirements |

**The `adopted` block is the one most likely to be missed, and it is governing law.** For a Napa County question about road width, driveway grade, turnarounds, cross sections, parcel-map improvements, defensible space, or fuel treatment, the controlling text is very often the **Napa County Road & Street Standards (2023)** or the **Napa County Defensible Space Guidelines (May 2021)**, not the CBC. Napa County Code § 15.32.070 and § 8.36.030 incorporate them, which makes them enforceable. Answering such a question from the state code alone is wrong even when the state code has something to say.

Both blocks are **present-and-empty rather than absent** when the jurisdiction does not search them, so read `dossier["adopted"]` unconditionally. `adopted` is populated for `-j napa` only.

---

## The three confidence verdicts

The dossier carries three verdicts, on three different questions. They are deliberately separate, and **only the code verdict decides whether to abstain.**

| Field | Scores | Reads |
|---|---|---|
| `confidence` / `abstain` (+ `confidence_basis`) | `candidates` **only** | HIGH / MEDIUM / LOW |
| `standards_confidence` (+ `standards_basis`) | the `standards` block | HIGH / MEDIUM / LOW, or `null` |
| `adopted_confidence` (+ `adopted_basis`) | the `adopted` block | HIGH / MEDIUM / LOW, or `null` |

**The invariant: a strong `adopted` or `standards` block never makes the code answer more confident, and a weak one never makes it abstain.** They are parallel authorities, not stronger or weaker readings of the same one. So when the code corpus abstains and the adopted block answers, report both plainly - "the CBC does not address this; Napa County's adopted Road & Street Standards do, at § 15" - rather than letting one verdict speak for the other.

How to use them:

- **LOW on a block** means the retrieval evidence is weak, not that the block is wrong. Read the text before dismissing it, and say the evidence is thin rather than presenting it as settled.
- **`null` is not LOW.** It means no verdict was possible - an empty block, or lexical-only retrieval on a corpus whose verdict is calibrated on the neural signal. Do not translate a `null` into a confidence claim in either direction.
- Each verdict is calibrated **per corpus**. Never carry a threshold or a reading from one block to another.

---

## Known divergences (pitfalls by edition)

Always cite the value from the corpus you actually searched - these are the provisions that differ most:

| Provision | IBC 2009 | NYC 2022 | CA 2025 |
|---|---|---|---|
| Business occupant-load factor | 100 gross | 100 gross | **150 gross** |
| Multiple-tenant egress through intervening space | § 1014.2.1 - **allowed** | § 1016.2.1 - **forbidden** (Group M larger-tenant exception only) | § 1016.2.1 - **allowed** |
| Intervening-spaces section number | § 1014.2 | § 1016.2 | § 1016.2 |
| Accessibility chapter(s) | Ch. 11 | Ch. 11 | **11A (housing) + 11B (public/commercial)** - pick the right one |
| CA amendment marking | n/a | n/a | Italics in published code = CA amendment; **distinction lost in PDF extraction** |
| Table extraction quality | OCR-derived (2009 scan) - watch `I`/`1`, `l`/`1` artifacts | `pdftotext -layout` - page breaks can split a table | `pdftotext -layout` - same page-break risk |
| NFPA 13 / 72 adopted edition | **2007** (hold 2025 -> mismatch, directional only) | **2016** (hold 2025 -> mismatch, directional only) | **2025** (held -> citable) |
| ICC/ANSI A117.1 | adopts **2003** (held -> citable) | adopts **2009** (held -> citable) | **not adopted** - use CBC Ch 11B / 11A |

**A117.1 editions are both held now.** The engine holds 2003 and 2009, so cite the edition your jurisdiction adopts - `ICC A117.1-2003 § 308.2.1` under IBC, `ICC A117.1-2009 § 308.2.1` under NYC. Never cite an A117.1 number in a California answer.

**Flag all table-derived values** (occupant-load factors, fire-resistance ratings, allowable height/area, egress width factors, travel distance) with `verify against published code`.
