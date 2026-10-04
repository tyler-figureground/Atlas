# Every deliverable type has a reference set, and agents look before they make

Date: 2026-10-04

## Status

Accepted. Pilot (Phases 0-3 of `docs/research/reference-sets.md`) in progress.

Builds on ADR 0012 (templates live in the repo), ADR 0014 (agents read before they ask).
Evidence: `docs/research/reference-sets.md`.

## Context

Instruction alone - a skill, an AGENTS.md rule, a chat prompt - produces bad deliverables,
from agents and from junior designers. The learning-science and prompting literatures agree
that a curated example is the most reliable way to transmit a quality standard, and that
criteria alone cannot carry it.

Examples also do damage when unmanaged. On this drive Solid Void template content - NYC
survey coordinates among it - bled into a Figure Ground project in Napa (Monte Vista
`PROJECT.md`), and Monticello content traced to a reference model open beside it (Monte
Vista `AGENTS.md`). The library's only `Reference Sets` folder held other firms' drawing
sets marked "precedent only", plus one house sheet list. No AGENTS.md pointed at an example.

## Decision

**Each deliverable type gets one Reference Set, approved by Tyler, and every agent reads it
before making that type.**

- Sets live in `G:\Shared drives\LIBRARY - Reference\00 Office Standards and Administration\Reference Sets\`,
  one folder per deliverable type, indexed by that folder's `README.md`. House standard,
  shared across entities.
- A set is a card (`SET.md`), at most three exemplars and one near-miss. Each exemplar is a
  frozen copy with a `NOTES.md` holding why it was chosen, callouts, and a leak list.
- Exemplars within a set differ on purpose: one California residential, one code-issue
  project, one commercial.
- Drawing-type sets are split by entity only for Solid Void, whose title block and template
  differ; every other set is shared.
- Tyler alone promotes, approves and retires. Agents nominate into `_candidates\`.
- The third-party folder `04 Design Process by Phase\04 Construction Documents\Reference Sets\`
  is renamed `Precedent Sets`, so "Reference Set" means only the studio's own approved
  exemplars. `REF-` precedent is never copied into a deliverable.
- Agents: facts from the project's own files, form from the exemplar, process from the
  skill; a skill's hard rule beats an exemplar. Every draft is checked against the card's
  review checklist and grepped for the opened exemplars' leak lists. The run receipt names
  the set used. No set for a type: the agent says so and may always ask Tyler for one
  example.

## Consequences

- AGENTS.md gains a "Look before you make" section through `agents-rules.md`, after the
  pilot sets are approved; deliverable-making skills gain a Reference step.
- Sets go stale like any standard. Each card carries `next_review:`; code adoption and
  skill rule changes trigger a review; retired sets move to `_retired\`, never deleted.
- Studio exemplars never enter the public repo. Skills bundle fictional examples for
  outside users.
- Whether a set helps is measured per type (with and without, on projects that are not
  exemplar sources) before more types are built.
