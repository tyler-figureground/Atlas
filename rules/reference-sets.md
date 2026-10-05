# Reference Sets

Before a skill drafts a deliverable, it looks at a good one. ADR 0015.

## The rule

1. **Find the set.** A studio with reference sets keeps one folder per deliverable type,
   each with a card (`SET.md`) and up to three exemplars. `atlas refs` lists them. Read the
   card, then the 1-2 exemplars nearest the project.
2. **Start from the skeleton, never from an exemplar.** Form comes from the exemplar. Facts
   come only from the project's own files (`BRIEF.md`, `PROJECT.md`, `decisions/`) and cited
   sources. A skill's hard rules beat an exemplar.
3. **Mark the draft** with the set and exemplars opened:

   ```
   <!-- architecture-studio:reference: code-analysis E1,E3 -->
   ```

4. **Check before handing back.** Run the card's Review checklist. The Dispatcher hook
   `post-write-reference-check` runs `atlas refs check` on every marked file and reports
   any exemplar fact found in the draft. A copied fact is a defect: replace it with the
   project's own. A hit on a fact that is genuinely this project's too stays, named in the
   receipt - never reword or drop a true fact to clear the check.
5. **No set, say so.** Name the nearest set used and ask for one example.

## Outside the studio

No `atlas`, or no reference sets configured: skip steps 1, 3 and 4. Use the examples bundled
with the skill, if any, the same way - structure, never content.

## Why

Instruction alone produces poor deliverables from agents and from people; a curated example
is the most reliable way to carry a quality standard. Examples also leak their facts into
new work - a past project's address, code edition or client - so every exemplar carries a
leak list and every marked draft is checked against it. Evidence:
`docs/research/reference-sets.md`.
