# Dossier panel

Type: grilling
Status: closed (2026-10-08)
Blocked by: -
Parent: ../map.md

## Question

Reading `PROJECT.md` inside Atlas is in scope. The machine contract stands: ADR
0001 covers the shared front matter, `core/projectmd.py` reads and writes it,
and `core/project_data.py::load_project_record` exposes the record.

What changed since this ticket opened - **the layout question is settled.** The
dossier is a Companion Mode: `MODES = (EXPECTATIONS, HEALTH, DOSSIER)` in
`tui/layout.py`, cycled on `d`. The slot is a stub today -
`_render_companion` in `tui/app.py` renders the literal string "The dossier
lands here." So the remaining questions are about content and behaviour, not
placement.

Resolve:

- Which facts surface: identity, site address, use case, billing and client
  contact snapshots, decisions index, code edition. All of them, or a chosen
  subset?
- Read-only, or editable in place? Atlas already has a full edit path behind
  `e` (`action_edit_project`) with rename preview and confirmation - does the
  dossier panel duplicate an entry point into that, or become a second way to
  write?
- What renders when `PROJECT.md` is missing, malformed, or legacy? Core
  deliberately refuses to silently rewrite malformed dossier data - the panel
  must say so usefully rather than showing blanks.
- Does the decisions index link through to `decisions/NNNN-slug.md`, and can
  those be read in Atlas too, or is that a different surface?
- CLI form: ADR 0008 obliges every fact-producing surface. `atlas dossier
  PROJECT [--json]` over `load_project_record`, or is `cat PROJECT.md` the
  answer? If the latter, record why.

## Acceptance

- Each question above answered; decision recorded in `docs/adr/` and one line
  on `../map.md`; new vocabulary in `/CONTEXT.md`.
- The stub string in `_render_companion` is gone - the mode renders real
  dossier facts or a deliberate decision not to build it is on record.
- Missing/malformed/legacy rendering verified headless at the measured widths
  (179, 153, 120, 87, 77, 46 columns; 51, 30, 24 rows).

## Decision

The DOSSIER Companion Mode renders the dossier's **facts contract, not its
prose** - and it is **read-only**, with its errors spoken aloud.

**Rendered facts, not raw Markdown.** The mode draws a facts table from
`core/project_data.py::load_project_record`: identity (name, address, use
case, description, created) and the billing/client Contact Snapshots, plus
the decisions summary (count and latest titles) that the digest already
computes. The twelve ADR 0001 governing keys are Norma's scope contract; the
panel shows the Atlas intake record, which is what Atlas owns and validates.
Raw Markdown is rejected: PROJECT.md is two artifacts - a machine contract
and prose - and the Companion Region has rows to spend on the contract, not
a prose reader. The prose already has the best renderer available: `o` opens
the file in the editor.

**Read-only, and this is architecture, not caution.** Every dossier write
already has exactly one home, and both carry what an in-panel edit cannot:
`project edit` (the `e` key) owns intake corrections and can rename the
folder - a write that must cross a previewed Plan with the rename shown and
the contacts and index updated together; conform/backfill owns the control
plane. A second write path in a narrow Region would duplicate the rename
preview, the Guard, and the digest checks, or silently skip them - and the
standing constraint (every mutation crosses a Plan) forbids the skip. The
panel's footer line advertises `e` instead of becoming a second way to
write. The ticket's "almost certainly read-only" is confirmed, not refuted:
no dossier fact exists that a person legitimately edits outside those two
paths.

**Missing, malformed, and legacy render the reason, never blanks.** Core
deliberately refuses to silently rewrite malformed dossier data
(`ProjectDataError`); the panel inherits that honesty by rendering the
error's reason in the mode's style - `PROJECT.md: invalid Atlas intake data:
<reason>` - rather than an empty table. A missing PROJECT.md is the unmet
control-plane Expectation the EXPECTATIONS mode already lists one `d` away;
the dossier mode says so in one line and offers nothing, because backfill
lives there, not here. A legacy dossier (Norma-era front matter without the
Atlas intake keys) renders as malformed-for-Atlas with the same honesty -
blank means unknown (ADR 0001), and a panel that guessed would mis-scope the
same facts Norma trusts.

**Decisions do not link through.** Reading `decisions/NNNN-slug.md` in Atlas
is a different surface and is deliberately not built here: the mode shows
the count and titles, and `o` opens the folder. Recorded as a scope cut, not
an oversight - a Markdown reader inside the Companion Region is the prose
trap again.

**The CLI form is `atlas dossier PROJECT [--json]` over `load_project_record`
- not `cat PROJECT.md`.** The fact this surface produces is the *validated
contract*: parsed intake, resolved snapshots, and the malformed-data error
when the file cannot be read safely. `cat` emits bytes and can neither
surface the validation failure nor give an agent the record as data. ADR
0008 obliges the subcommand in the same session as the mode.

Reasoning, three lines:

1. The Companion slot serves the contract half of PROJECT.md; the prose half
   already has a better surface behind `o`, so rendering raw Markdown in-app
   buys nothing and costs a reader widget.
2. Read-only follows from the write architecture: the two existing write
   paths carry rename preview, Guard, and index/contact co-update, and a
   third path either duplicates them or bypasses the Plan - both forbidden
   outcomes.
3. Core's refusal to silently rewrite malformed dossiers is the product's
   honesty rule; a panel showing blanks would launder that refusal into
   something that looks like an empty project.

Consequences:

- Becomes build ticket **36** (the dossier Companion Mode plus `atlas
  dossier`). Vocabulary (Dossier Facts Table) lands in `/CONTEXT.md` with
  that build.
- **ADR 0005 needs a line.** Drafted amendment, to be added by ticket 36 (not
  created here):

  > **Amendment (ticket 09, 2026-10-08): the DOSSIER Companion Mode is
  > rendered facts, read-only.** It draws the intake record's identity and
  > contact snapshots plus the decisions summary, never raw Markdown and
  > never an editor - dossier writes stay in `project edit` and conform,
  > which carry the rename preview and Plan the panel cannot. A missing or
  > malformed PROJECT.md renders the reason in the mode; it never renders
  > blanks.

- ADR 0001 is untouched: the panel reads the contract and changes nothing
  about who writes it.
- Rejected alternatives, recorded: raw Markdown rendering (prose trap; `o`
  is the better surface); in-place editing (third write path, violates the
  Plan constraint or duplicates it); `cat PROJECT.md` as the CLI form (bytes
  are not the fact; the validated record is); in-Atlas decision reading
  (scope cut, recorded).
