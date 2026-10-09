# Do File Rules reach below the project root

Type: grilling
Status: closed (2026-10-07)
Blocked by: -
Parent: ../map.md

## Question

Ticket 25 deliberately stopped at the project root. A permit set sitting in
`01 Model` instead of `08 OUT/Transmittals` is the same mistake as one sitting at the
root, and Atlas cannot see it.

Three things stand in the way, and this ticket is to decide whether they are worth
paying:

- **Containment says it is already filed.** ADR 0007: a node under a canonical path is
  Mapped. A rule that overrode that would make Filing State depend on which rule ran
  last, which is exactly what the first-match order exists to prevent. Does a rule
  outrank containment, or only apply where containment has no opinion?
- **`doctor` does not descend, on purpose.** Its 4.24-second drive-wide cost (ticket
  12) is bounded precisely because it reads project roots only. A rule that reaches
  deeper turns one enumeration per project into a walk - and with a content filter, a
  download per candidate. Is this a `doctor` fact at all, or a tree-only one, computed
  for the folder actually on screen?
- **Moving a file someone filed by hand is a different act** from filing one nobody
  filed. The first overrules a person; the second helps them. Does it need a
  different confirmation, or a rule flag that opts in?

A defensible answer is "no, roots only" - in which case record why, and the studio
gets a `misfiled` finding some other way or not at all.

## Constraints

- ADR 0004, 0006, 0007, 0009 all bear on this. None may be quietly amended.
- Whatever is decided, it emits a Sweep or it emits nothing.

## Decision

**Rules never outrank containment, because below the root they do not produce
Filing States at all.** A rule that fires below the root is a distinct, opt-in
rule class - a **Receipt Rule**, a new map key `receiptRules` - whose match is a
doctor finding with a Sweep Offer, orthogonal to Filing State the way an unmet
Expectation is. Containment (ADR 0007) still decides every deep node's Filing
State, first-match order is untouched, and the "which rule ran last" failure
cannot arise because the Filing State pipeline never sees these rules.

**It is a doctor fact, in an opt-in deep pass - never the default pass.** The
default `doctor` / `conform` report stays root-only; its cost bound depends on
it. Receipt Rules evaluate only in an explicitly scoped run, `atlas doctor
--deep PROJECT` (apply leg: `atlas conform PROJECT --deep`). One project's walk
is bounded by that project; `--all --deep` pays the measured 4.24 s-class drive
walk deliberately, by flag, never by default. Content filters are banned below
the root: at depth a `pdfText` test is a download per candidate with no
enumeration gate in front of it. Receipt Rules carry name filters only
(`extensions`, `names`, `nameRegex`) - which is exactly the vocabulary that
identifies agent receipts (research 1.1: machine files are an extension list).

**Moving a hand-filed file gets no new confirmation mechanism; it gets three
fences.** (a) A Receipt Rule's target must be inside the agent workspace
(`runsDir`, `backupsDir`), so the class can only move machine receipts out of
the numbered tree, never reorder a person's filing between sections. (b) A
matched file stays Mapped in the tree and earns no repair key - deep findings
surface only through doctor and conform plans, never the inline confirm. (c)
The malformed-rule rule of ADR 0009 holds: a bad Receipt Rule refuses the whole
map. The operator's check is the existing modal - a deep conform is a
multi-action Plan, and confirmation weight already follows plan size (ADR 0006).

Reasoning, three lines:

1. The studio's need (plan Phase 1.3/1.7) is *detection* of machine files in
   numbered sections; tree-only findings fail it because nobody expands every
   folder, and always-deep doctor fails the cost discipline - the scoped deep
   pass is the only option that serves both.
2. The mechanism already holds: SWEEP, the Guard, the Move Manifest, undo and
   `conform --revert` all handle a nested `src` unchanged, so the constraint
   "emits a Sweep or nothing" costs no new action kind (ADR 0006 stands).
3. Restricting targets to the agent workspace is what makes the class safe to
   opt into: it can enforce the filing contract's "scratch never lives in the
   numbered tree" rule and is structurally incapable of overruling hand filing.

Consequences:

- Becomes build ticket **31** (receipt rules below the root). Vocabulary
  (Receipt Rule, Deep Pass) lands in `/CONTEXT.md` with that build.
- **ADR 0009 needs a line.** Drafted amendment, to be added by ticket 31 (not
  created here):

  > **Amendment (ticket 26, 2026-10-07): "Root files only" holds for
  > `fileRules`; a second rule class, `receiptRules`, fires below the root.** A
  > Receipt Rule uses name filters only (`extensions`, `names`, `nameRegex` -
  > never `pdfText`), targets only the agent workspace (`runsDir`,
  > `backupsDir`), and is evaluated only in an explicitly requested deep pass
  > (`doctor --deep`, `conform --deep`), never in the default root-only report.
  > Its match is not a Filing State - containment (ADR 0007) decides those at
  > every depth - it is a doctor finding that emits a SWEEP and nothing else.
  > A malformed Receipt Rule refuses the whole map, as File Rules do.

- **ADR 0007 needs no amendment**: containment is untouched, and this decision
  should be recorded as confirming it rather than qualifying it. ADR 0004 and
  ADR 0006 are likewise untouched.
- The research backlog row (`atlas-file-management-oss.md` item 2) moves to
  decided; ticket 28 (content filters) stays parked - this decision bans content
  filters at depth rather than creating a second home for them.
- Rejected alternatives, recorded: "roots only forever" (leaves the top live
  drift - agent receipts in numbered sections - with no teeth); tree-only
  findings (detection is the point; nobody expands every folder); content
  filters at depth (an unbounded download per candidate on the streaming
  mount).
