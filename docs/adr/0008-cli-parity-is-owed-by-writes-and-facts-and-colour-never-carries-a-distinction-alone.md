# 8. CLI parity is owed by writes and facts, and colour never carries a distinction alone

Date: 2026-09-04

## Status

Accepted

Supersedes nothing. Constrains ADR 0004 (Filing State, which the tree renders),
ADR 0005 (the Regions), and ADR 0006 (the writes the tree offers). Every
implementation ticket for the console inherits both rules.

## Context

Atlas has kept CLI parity for every capability since the beginning. `cli.py`
states it as a docstring - *"every TUI capability as a subcommand; `--json` is the
agent interface"* - and the reason recorded for it was accessibility: a persona
critique named CLI parity as the accessible fallback because Textual's
screen-reader support is unresolved upstream ([textual#2425]).

The console effort then added three natively spatial capabilities - a folder tree,
a search overlay, a dossier panel - and the question of what parity means for them
was deferred through sessions 6, 7 and 8. Each of those sessions shipped surface
that inherited the unanswered question: a wordmark, five keybindings, three
Regions, two Compositions, an undo stack, an inline confirm, and a tree with its
own glyph vocabulary.

Two facts, both established when the question was finally taken up, reframe it.

**There is no screen-reader operator.** The accessibility justification traces to
one synthetic persona and one upstream issue, not to a person waiting on Atlas.
The operator profile settled at charting is the principal daily and studio staff
occasionally. Keeping a commitment nobody owns, worded as though someone does, is
the kind of claim that is never tested and never true.

**There is no `--json` consumer either.** Nothing under `plugins/`, `agents/` or
`rules/` shells out to Atlas. The agent interface has zero current callers. So the
contract is free to change, and any rule written here is a bet on near-future use
rather than a response to a live consumer. Worth saying plainly rather than
implying otherwise.

Meanwhile the deferred question had produced a live defect. `treeview` dropped a
node's Filing State word when width ran out, on the reasoning that "the glyph and
its colour still carry it". They do not:

- Drifted, Misplaced and Loose deliberately share one glyph (`▚`) and one colour,
  per ADR 0004 - colour answers *whose problem is this*, not *which problem*. The
  word was the only thing between them. Dropping it made three states render
  identically to **everyone**, not only to someone who cannot separate hues.
- What remained was Atlas-fixable vermilion against Unfiled ochre: measured at
  **1.82:1** against each other, under the 3:1 floor for non-text, and on the
  red/green confusion axis besides. Every token clears 4.5:1 against the ground;
  nothing had ever tested a token against another token.
- The trigger fired at the wrong width. It keyed on terminal width below the
  100-column Composition breakpoint - but below 100 the console is Single-Region,
  where the tree is the only Region drawn and owns nearly the whole terminal. At
  87 columns the tree stripped its labels while holding ~85 columns.
- Rendering it found a second instance the suite could not: a file returned from
  `node_label` before the word was appended, so a Loose file and an Unfiled file
  were separated by hue alone at *every* width.

The effort's own research had already ruled on this - `docs/research/atlas-tui-ux-evidence.md`,
HIGH/Primary: *"avoid color-only status."* It was accepted, deferred to this
ticket, and then contradicted by shipped code.

## Decision

**A CLI form is owed by every capability that writes, and by every capability that
produces a fact. Navigation is exempt.**

An agent wants the facts and the writes; it never wants the cursor. So walking a
tree owes nothing, and the Filing State of every node in it owes a subcommand.
This is narrower than "every capability" and wider than "every write", and it is
falsifiable: given a new surface, you can say whether it produces a fact.

The obligation is discharged **in the same session as the surface, in either
order** - not before the TUI code is written, and never in a later ticket.
Deferring parity to a follow-up is exactly how this decision slipped three times,
and the tracker is local Markdown with nothing enforcing it.

`--json` stays the agent interface. `doctor`'s output shape stays as it is: it is
drive-wide, and its 4.24-second cost is bounded precisely because it does not
descend below a project root. The tree's facts get their own subcommand,
`atlas tree PROJECT [--json] [--depth N]`, a thin wrapper over the seam ADR 0007
already built, with `--depth` giving a caller the cost control the TUI gets from
lazy expansion.

**Colour may reinforce a distinction. It may never be the only thing carrying
one.** Concretely, in the tree:

- Every Filing State that is not Mapped carries a word, at every width. When the
  width runs out the word abbreviates - `NAME`, `PLACE`, `LOOSE`, `UNMAPPED` -
  and is never dropped.
- The rule applies to files as well as folders. A file has no disclosure marker
  and no child count; it still says what is wrong with it.
- The abbreviation threshold is `layout.ABBREVIATE_COLUMNS`, 60, named and
  commented as the approximation it is. It cannot reuse `SPLIT_COLUMNS`, because
  the Tree Region's share of the terminal depends on the Composition: roughly half
  in Split, nearly all in Single-Region. 60 keeps the measured 87- and 77-column
  terminals spelling the word out and abbreviates at 46, the most common width of
  all.
- A test asserts the invariant directly rather than pinning a colour: no two
  Filing States may render identically once colour is stripped, at either width.

**The accessibility claim is stated, and it is a negative.** Atlas has not been
validated with assistive technology and claims no conformance. The CLI is
described by what is true of it - plain text, the automation path - not as a
fallback nobody has tested.

## Consequences

The tree is the only surface this changed. The project list already renders
`Text(row.health, ...)` with the word as the cell and colour as style, so it was
correct before this ADR and is unaffected by it.

`FilingStyle` gains a `short` field, so the token layer owns both forms and a
future state cannot be added with only one. The colour-alone test fails loudly if
someone adds a state that collides with an existing glyph-and-word pair.

Two CLI surfaces are now owed and tracked: `conform --node` plus undo, inside the
ticket that adds the tree's write keys, and `atlas tree`, which is ticket 22's
retroactive debt and is charted as its own ticket rather than folded into
another's commit.

The rule costs something real. Every future console surface - search, the dossier
- now has to answer what fact it produces and expose it. That is the intended
cost: it is what "CLI parity" was always claiming, and it had never once been
priced.

What this does **not** do is make Atlas accessible. It makes the console legible
without colour and gives automation a documented path. A screen-reader claim would
need assistive technology and an operator, and Atlas has neither.

[textual#2425]: https://github.com/Textualize/textual/issues/2425
