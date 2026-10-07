# Baseline rules are classified, and carry Revit, drawing and code sections

Date: 2026-10-06

## Status

Accepted. Decided by Tyler on 2026-10-06.

## Context

`agents-rules.md` is the rule set Atlas writes into every project's `AGENTS.md` block
(ADR 0010, 0012). Until now it covered process (finish the job, read first, look before
you make, meetings, filing, research) and said nothing about the Revit model, the
drawings or code work. Those rules lived in three other places:

- Pyvoid's S+V standards, policy and the `jdp` / `maestro` skills - tool-centred, not on
  the drive, so a project-level agent never sees them unless a skill loads.
- Hand-written blocks in individual project `AGENTS.md` files (Beitz, Monte Vista,
  Coleman) and handoffs (64th Lane, Montez, Silverado). About a dozen rules recur across
  them; they have drifted, and Monte Vista's "sync at natural checkpoints" contradicts
  every other project.
- Paste-in headers in the drive's prompt vault (`_tools\Architecture-Prompts`), which an
  agent that starts from `AGENTS.md` never reads.

The evidence (`docs/research/agent-baseline-rules-evidence.md`) is a mining pass over
~430 Claude Code sessions on the drive and in Pyvoid, 31 Codex sessions, the Beitz
post-mortem, every project's `AGENTS.md`, handoffs and run receipts, and the Norma repo.
Tyler's most repeated corrections are drafting-form (leaders, alignment, overlap), drawn
imitations of native objects (text tags, text schedules, drafting-view plans, hard-typed
references, text view titles), scope over-reach on "proceed", and agents auditing the
office template instead of drawing. The worst single failures are model-hygiene (lost
unsaved work, wrong document, unrequested sync, internal codes on a County set) and code
basis (wrong energy-code edition, City vs County, 2022 vs 1968 NYC code of record).

The other cost is the opposite failure: gates applied so hard that Tyler could not get
his own drawings out (Beitz: "this is taking way too long"). Rules without a class read
as uniformly absolute, so agents either ask about everything or refuse things Tyler is
entitled to direct.

## Decision

1. **Every rule has one of four kinds**, stated at the top of the block:
   - **Hard line** - nothing crosses it: fabrication, another user's borrowed elements,
     a second live writer, sending out of the studio.
   - **Tyler's call** - needs his current-conversation words naming the thing (sync,
     issue, transmit, delete, design change, code-bearing choice, template or library
     edit). When given, the agent complies with no second prompt.
   - **House default** - done without asking; a project rule or Tyler overrides, and
     the override is recorded.
   - **Project input** - values that vary by job live in `PROJECT.md`; never inferred;
     asked once by name with a default.
   Precedence: Tyler's current words > project rules > baseline > S+V skill standards >
   reference-set exemplars.
2. **The baseline gains four sections**: *Do the task asked* (scope), *Working in the
   Revit model* (one writer, pass shape, sync, reconcile, parameters not names, phases,
   template, overrides, deletes, issue state, JDP billing), *Drawings - native over
   drawn* (one native object per drawn thing, the agreed keynote fallback, Tyler's
   drafting form, paper is the done-test), and *Code work* (code basis first, code of
   record, scope document, local layer, calculator discipline, studio rulings).
3. **Tool detail stays in the skills.** The baseline names the rule; API traps, MCP tool
   names and defect tables stay in `maestro`, `jdp` and Pyvoid's `PATTERNS_REVIT.md`.
   Project-specific traps go in `PROJECT.md` "Model traps".
4. **10-norma never routes a project to `-j ibc`.** The 2009 IBC is reference-only for
   generic questions; an unresolved project jurisdiction is a stop.

## Consequences

- Every mapped project's block goes stale on Atlas 0.11.0; `atlas conform --all --apply`
  rewrites it. Lines outside the block are untouched.
- A standing rule in a project's own section counts as Tyler's words. Monte Vista's "sync
  at natural checkpoints" stays: Tyler is building trust with the system (2026-10-06).
- The block grows from ~75 to ~175 lines, read at every session start. Accepted: the
  cost of reading is smaller than one re-drawn sheet.
- Studio defaults set by Tyler, 2026-10-06, and written into the S+V standards:
  - Sheet numbers `A101`, no hyphen (S+V-RS-005; D10's NCS `A-101` default reversed).
  - Dimensions 1/4" display precision, face of stud. Centerline allowed in Concept and
    Schematic Design; Construction Documents are face of stud (S+V-DS-002 v1.5, Rule
    5.2.11). Shipped to JDP through the firm config `%PROGRAMDATA%\Pyvoid\jdp\jdp.yaml`.
- The original S+V conflict list on Pyvoid #769 is partly superseded by Tyler's later
  2026-10-06 rulings, already carried in Atlas 0.11.1. Preserve those drafting rules;
  standard-header naming and the isolated eighth-inch precision answer remain open.
  See the research reconciliation for source/status distinctions.

## Reconciliation with Pyvoid (2026-10-06)

The baseline's original "Exactly one Revit.exe" wording was broader than the
accepted Pyvoid safety contract. Replace the machine-wide process ban with **one
writer per model**, including different locals of the same central. Separate
project instances require positive target identity; failed Fleet pinning never
falls back to an arbitrary active document. Never close another session to make a
check pass. This preserves the hard line, not an exception to it.

Pyvoid ADR-029 and `user-authority.md` already settle that boundary; no new user
ruling was needed. Fleet's three-instance acceptance (#3100) was still open when
checked. Rules must not certify acceptance or launch extra seats by implication.

Carry the inherited workset-completeness rule at its actual boundary: every open,
reopen, local creation, migration and restart, before inventories or writes as well
as exports. Check actual printed backgrounds, not only text and fonts. Preserve
project-specific standing sync rulings outside Atlas's generated block. Tool
availability must be checked in the connected runtime, not inferred from a merge.
Evidence and the distinction between policy and shipped capability are recorded in
`docs/research/agent-baseline-rules-evidence.md`.
