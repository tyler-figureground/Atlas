# Agent baseline rules - evidence

Date: 2026-10-06. Feeds ADR 0017 and `tools/atlas/src/atlas/templates/project/agents-rules.md`.

## Question

What should every studio project's `AGENTS.md` carry so that JDP (Junior Design Partner,
the ledgered production runtime), Maestro (live Revit through the Pyvoid MCP bridge) and
Norma (building code) work accurately, without friction, from the first session?

## Corpus

| Source | Volume |
|---|---|
| Claude Code sessions run from studio-drive project folders and the prompt vault | 17 folders, 167 real user messages |
| Claude Code sessions with 3+ Revit MCP calls (Pyvoid and worktrees) | 263 sessions, ~46 on live studio projects |
| Codex sessions calling the Revit MCP | 31 (development only, no production corrections) |
| Beitz post-mortem | `Pyvoid\docs\plans\beitz-postmortem-2026-10-02\evidence.md` |
| Project `AGENTS.md`, `PROJECT.md`, handoffs, run receipts | all 15 mapped projects |
| Pyvoid standards, policy, ADR-022, `PATTERNS_REVIT.md`, feedback memories | full read |
| Norma repo, 10-norma plugin, Code Analysis reference set, Norma issues | full read |

Not covered: pi agent sessions (`C:\Users\YOLOTRON\.pi\agent\sessions\`), which hold most
of the Beitz production run; quoted here only through the post-mortem.

## Findings, ranked by frequency x severity

Confidence: **High** = direct Tyler words in 3+ sessions or a documented incident;
**Medium** = 1-2 direct instances or Tyler's own prompt-vault rule; **Inferred** = from
what Tyler asked for, no direct correction.

### Drawings

1. **Native objects, not drawn imitations** - High. 5 corrections across 3 projects
   (07-31 to 09-27): "do not write the view titles with text ... use north arrow and grid
   scales as symbols not details and text" (Beitz 09-27); "I want the site plan to be a
   real floor plan" (09-26); "take a view of the actual geometry ... fix it for real in the
   model" (Montez 09-20). 25 hard-typed cross-references blocked renumbering at Montez
   A100. Monte Vista fans existed "only as text on A120". 64th Lane A401 had 1,098 leaders
   drawn as detail lines.
2. **Leader form** - High, Tyler's most repeated drafting correction: ~9 messages in 8
   sessions (08-01 to 09-23). "JDP/Maestro is doing stupid things like not using leader
   lines for text notes ... the elbows are not horizontal, the text justification is not
   correct etc. I could go on and on" (09-20). Root cause: `create_text_note` had no leader
   fields until Pyvoid #1486/#1487.
3. **Check the printed sheet** - High, ~12 messages in 11 sessions. A room schedule
   returned every row through `GetCellText` and printed blank in an issued PDF (Monte
   Vista). Beitz G-002 passed 30 PDF checks with its model backgrounds missing (closed
   workset).
4. **No internal text on sheets** - High. 43 of 50 Beitz PDFs, including the one sent to
   the County, carried hold codes and agent notes. "Dont include any internal notes on the
   sheets" (09-28).
5. **Composition and text standard** - High, ~19 messages across 14 sessions (alignment,
   grid, standard scales, `00-Standard`, no underlining). Composition took 39% of Beitz run
   time.
6. **Keynote fallback** - Medium. Native keynote tags cannot be created through the API
   (`IndependentTag.Create` leaves Key Source null). Tyler accepted numbered markers plus a
   numbered legend list with a match check on 10-03 (Pyvoid #2921).
7. **Filters and templates, not per-element overrides** - Inferred from 4 requests to
   change view templates or V/G rather than elements.

### Model hygiene

8. **One writer, right document** - High, ~7 instances. Old model pointed at (Montez
   09-20), reference model open in the same Revit (Monte Vista), template-shared GUID
   attached the bridge to the wrong project (Silverado), sync race destroyed a title-block
   rebrand (Monte Vista 07-30).
9. **Save local, never sync unasked** - High. An evening of writes lost unsaved (08-02).
   `ExitRevit` synced central unasked (Beitz). "I synced, credit JDP" is Tyler's
   acceptance in 23 messages across 17 sessions. 6 projects carry the rule; Monte Vista
   contradicts it.
10. **Reconcile after timeout, never replay** - High, 4 projects. A replayed deletion probe
   removed hundreds of elements (64th Lane).
11. **Parameters, not names** - High, 5 instances; Tyler: "add the rule" (Monte Vista
   08-01, a `30" x 60"` window 36" tall hid an EERO failure).
12. **Phase and workset on creation** - High. Silverado #908: 140 elements on New
   Construction. Shower pan placed on Existing (Monte Vista).
13. **Office template is the baseline** - Medium. "models are wasting time auditing and
   verifying my basic things inside the model and not doing real work" (09-22).

### Process

14. **Scope: "proceed" is not wider scope** - High. Rendering session, after four
   "proceed"s the agent had added 13 cameras and materials to Tyler's unsaved local: "you
   are over reaching. just supply the prompts" (09-18).
15. **Invent nothing; work inside Tyler's system** - High. "there is no T100 folder or
   whatever you are making up ... you are working inside of my system, not yours"
   (10-06). Invented package folder deleted (64th Lane); "SOLID VOIDD" on a title block.
16. **Questions up front with defaults** - High. 54 of Tyler's 166 Beitz messages were
   "proceed". "all the questions the model asked me could have been answered if they just
   opened the virtual tour for 2 minutes" (09-22).
17. **Drawing changes are progress, audits are not** - High. "stop all academic resarch
   and actually start updating the drawings" (64th Lane).
18. **Over-applied gates** - High, one long incident. Beitz: "can we just overide or skip
   the safety lock, I need to get these drawings done" -> refused -> "ok screw it".

### Code (Norma)

19. **Code basis first** - High. Wrong Energy Code edition advised at Monticello, overruled
   by Tyler 10-05 (2025 governs, Napa County included). City of Napa text on a Napa County
   job (Silverado carried Monte Vista's). 64th Lane analysed against 2022 NYC when filed
   under 1968.
20. **Scope document** - Medium. A dwelling memo headed CBC instead of CRC (McKean near-miss).
21. **Calculator discipline** - High. Open Norma defects #137, #138, #139, #141, #151, #166;
   silent fallback to 2009 IBC (#53 closed, #78 open); plugin routing still listed
   "Elsewhere -> 2009 IBC" (fixed in 10-norma 1.4.2).
22. **Close what sources can close** - High. Tyler's blind grade: "I would need to resolve
   all of the unverified, assumed etc." Seismic sheet showed 3 of 11 required items
   (Monticello plan-check comment).

## Negative evidence

- No direct Tyler correction of a per-element graphic override was found (finding 7 is
  inferred).
- Codex Revit sessions held no production corrections.
- Tyler rarely scolds on the drive; severity was judged by consequence, not tone.

## Settled 2026-10-06 (Tyler)

- Sheet numbering `A101`, no hyphen (Monte Vista and Silverado form; vault and RS-005 D10
  said `A-101`).
- Dimensions 1/4" display precision, face of stud; centerline in Concept and Schematic
  Design only.
- Monte Vista's project-level "sync at natural checkpoints" stays.

At the original mining pass, S+V vs Tyler-ruling conflicts remained on Pyvoid #769.
The later 2026-10-06 rulings settle most of them; see the reconciliation below.

## Pyvoid reconciliation (2026-10-06)

Follow-up requested after the decision-register update. Read the local checkout,
then fetched remote refs without pulling, resetting or editing Pyvoid's dirty work.
Local and remote history had diverged; local handoffs were not treated as proof of
current remote release state. Policy snapshot: Pyvoid `3d14c191b5139e71de3d1b4a4c0f3a19a801ea1c`.

- **High confidence: one writer is per model, not per machine.** Accepted ADR-029
  defines separate project-key-pinned instances; `user-authority.md` hard line 2
  forbids a second live writer on the same model. Thus the original Atlas rule
  "Exactly one Revit.exe" over-constrained safe isolation. Different local paths
  do not prove different central models. Title/GUID/process count alone is not identity.
- **High confidence: ambiguous targeting refuses.** ADR-029 requires zero/multiple
  matches and identity drift to refuse; a configured Fleet pin must never silently
  degrade to unpinned discovery. Non-active documents need the operation's supported
  explicit target contract (ADR-028), not a blanket assumption about every handler.
- **Acceptance remains separate.** Live GitHub readback showed #3100 OPEN. Neither
  this reconciliation nor merged multi-instance code establishes three-instance
  operational acceptance. No Revit instance was launched, closed, repinned or edited.
- **Workset evidence precedes model conclusions.** Inherited studio rule and Beitz
  evidence require recorded IsOpen states before inventories, calculations, edits
  and exports after any document-opening lifecycle event; loaded links and category
  visibility are insufficient. Printed backgrounds must match accepted content.
- **Capability vs policy.** Native symbol placement, scale-bar placement/checking
  and line-style operations have merged. Their installed/live availability is not
  proven by that merge. Shared rules retain native-over-drawn requirements and
  route tool detail to the JDP/Maestro skills rather than duplicating command tables.
- **Newer drafting rulings already landed in Atlas 0.11.1 (`a06652d`).** Live #769
  comment readback confirms sheet-only clockwise clouds, clear fixed witness lines,
  D01 door marks, parameter-driven ceiling-height labels, ALL CAPS, no drawing-set
  pricing, one schedule-splitting strategy per set, casework as dimension subject
  only, and provisional bottom-right/up/left view numbering except standard details.
  Preserve these concurrent changes, not the older open-question list. Standard
  header/firm naming and the isolated eighth-inch precision answer remain unresolved;
  do not guess either. Standards/engine changes are tracked in #3195, not certified
  by this Atlas patch. Issued-number exceptions remain project-specific.
- **Deliberately unchanged:** A101 numbering, face-of-stud/quarter-inch defaults,
  no autonomous sync, foreign-borrow protection, project-specific standing rulings.
  Product launch/branding and unmerged visual work are not studio-project rules;
  no Atlas rebrand or product-roadmap work is implied by this synchronization.

The reusable Atlas template and generation tests carry these changes. Existing drive
projects are not silently conformed by this repository edit. No Pyvoid worktree edits,
issue closure, runtime deployment or live-model verification were performed.

Source pointers (pinned where available):
- [Instance/project pinning, ADR-029](https://github.com/tyler-figureground/Pyvoid/blob/3d14c191b5139e71de3d1b4a4c0f3a19a801ea1c/.agent/ADR/ADR-029-instance-registry-project-key-pinning.md)
- [User authority and the per-model hard line](https://github.com/tyler-figureground/Pyvoid/blob/3d14c191b5139e71de3d1b4a4c0f3a19a801ea1c/.agent/policy/user-authority.md)
- [Non-active document handles, ADR-028](https://github.com/tyler-figureground/Pyvoid/blob/3d14c191b5139e71de3d1b4a4c0f3a19a801ea1c/.agent/ADR/ADR-028-document-handle-registry.md)
- [Three-instance acceptance, #3100](https://github.com/tyler-figureground/Pyvoid/issues/3100)
- [Latest drafting rulings, #769](https://github.com/tyler-figureground/Pyvoid/issues/769)
- [Standards/engine follow-through, #3195](https://github.com/tyler-figureground/Pyvoid/pull/3195)

## Sources

- `C:\Users\YOLOTRON\Documents\GitHub\Pyvoid\.agent\ADR\ADR-022-agentic-production-apparatus.md`
- `C:\Users\YOLOTRON\Documents\GitHub\Pyvoid\.agent\policy\user-authority.md`, `irreversible-actions.md`
- `C:\Users\YOLOTRON\Documents\GitHub\Pyvoid\docs\standards\` (AS-001, DS-002, TS-003, GN-004, RS-005)
- `C:\Users\YOLOTRON\Documents\GitHub\Pyvoid\docs\research\beitz\2885-drafting-primitive-gap-audit.md`
- `C:\Users\YOLOTRON\Documents\GitHub\Pyvoid\docs\plans\jdp-maestro-recurrence-implementation-plan-2026-09-27.md`
- `G:\Shared drives\ARCHITECTURE\_tools\Architecture-Prompts\02 Architecture Projects\01 Revit Prompt Library\`
- `G:\Shared drives\LIBRARY - Reference\00 Office Standards and Administration\Reference Sets\Code Analysis\SET.md`
- Project `AGENTS.md` and `.agent\` folders under `G:\Shared drives\ARCHITECTURE\`
