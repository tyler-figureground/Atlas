# The token layer

Type: grilling
Status: resolved
Blocked by: - (14, resolved)
Parent: ../map.md

## Question

Graduated from the map's fog now that the visual world is settled.

Ticket 02 produced a working palette as prototype constants. Ticket 05 proved tree
nodes take no CSS at all - `render_label` is the only route - so whatever holds
these values must be readable from Python, not only from a Textual stylesheet.
Meanwhile `app.py` already carries a `MODAL_CSS` string and a `STATUS_STYLES` dict,
which are two token systems that do not know about each other.

Resolve:

- What is the layer? A Textual theme, a CSS variable block, a Python module of
  constants, or a Python module that also generates the CSS?
- How do the existing `MODAL_CSS` and `STATUS_STYLES` migrate onto it, and does
  anything in the modal CSS need to stop being a literal?
- Does it carry glyphs as well as colours? Ticket 14's node kinds each need a
  glyph and a colour, and keeping them apart invites drift.
- Does it support more than one theme? Option C - PAPER, a light ground - was
  rejected as the default, not proven impossible. Is a light theme a real future
  or explicitly never?
- Do the CLI's colours come from here too, or does the CLI stay uncoloured?
- How does a test assert a colour without hard-coding the hex in the test?

Ticket 02 recorded the prototype values. This ticket decides where they live and
is the last thing standing between the design and the implementation tickets.

## Answer

Built. `src/atlas/tui/tokens.py`, 26 tests, 237 passing overall.

**It is a Python module, and the CSS is generated from it.** That direction is
forced rather than chosen: ticket 05 proved tree nodes are not DOM nodes and take
no CSS at all, so `render_label` has to read colours and glyphs from Python. If
the stylesheet also owned them there would be two sources of truth and the tree
would drift from everything around it. `tokens.stylesheet()` returns the Textual
CSS.

**Migration done, not deferred.** `MODAL_CSS` is now `tokens.stylesheet()`.
`STATUS_STYLES` derives from `PALETTE.status` instead of naming terminal colours.
The app's own CSS block is geometry only, with a comment saying why.

**This flips two status colours.** The old literals were `ACTION: bold yellow` and
`REVIEW: bold red`. They are now vermilion and ochre, because colour answers "can
Atlas fix this or is it yours" - vermilion marks where Atlas has work, ochre marks
where a person must decide. Worth knowing before the first run looks wrong.

**Yes, it carries glyphs.** `filing_style()` returns glyph, colour, human label and
a `solid` flag together. Keeping the glyph table elsewhere would invite exactly the
drift this layer exists to prevent.

**Two themes: structured for, not shipped.** `Palette` is a frozen dataclass rather
than module constants, so the rejected PAPER light world is another instance and
not a refactor. One palette ships.

**CLI stays uncoloured.** It is the agent and accessibility interface and `--json`
is its contract. Ticket 10 owns the accessibility claim.

### Testing colour without pinning hex

The question the ticket asked. Assert on structure and contrast, never literals.

- **Coverage** - every Filing State has a glyph, colour and label; every Load State
  has a disclosure marker; an unknown state raises rather than rendering blank.
- **Meaning** - only `Mapped` is solid, and the three Atlas-fixable states share
  exactly one colour that neither `Unfiled` nor `Mapped` shares. ADR 0004's
  rendering rule as a test rather than a paragraph.
- **Legibility** - a real contrast-ratio implementation. Every text token must
  clear 4.5:1 against the ground; structural tokens must sit between 1.2 and 4.5 so
  they recede without vanishing; the cursor must be the brightest thing on screen.
- **Provenance** - the generated CSS is scanned for hex literals and every one must
  be a palette value, so a hand-edited colour fails the suite.

These survive retuning. A test pinning `#E2452A` would not, and would prove nothing.

### Measured result

| token | | contrast |
|---|---|---|
| bone (cursor) | `#F4F0E6` | 17.18:1 |
| ink | `#B5AFA4` | 8.97:1 |
| muted | `#96907F` | 6.14:1 |
| dim | `#5A554D` | 2.65:1 |
| rail | `#302C27` | 1.41:1 |
| READY | `#8AA37A` | 7.08:1 |
| ACTION | `#E2452A` | 4.77:1 |
| REVIEW | `#D9A441` | 8.69:1 |
| SETUP | `#C79A6B` | 7.69:1 |

The prototype's `ink`, `muted`, `dim` and `rail` were all darker and failed the
floor. They were lightened until it passed - the design survived measurement,
slightly adjusted.

Verified by headless render of the real app at 148x40 and 80x24 against a synthetic
drive: palette applied, narrow layout drops the detail pane as designed, selected
row carries the ember cursor background.

`child_count()` lands here rather than in the tree, since ticket 13's format
decision is presentation.
