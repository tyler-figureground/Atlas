# The wordmark and header, as Atlas code

Type: task
Status: resolved
Blocked by: - (14, resolved)
Parent: ../map.md

## Question

Ticket 02 settled what the header looks like and proved it renders. This ships it
into `tools/atlas` as real code, under test. The prototype renderer is throwaway
and must not be lifted.

Build:

- **Glyph table.** Capitals plus `+` and space, six pixel rows tall, five columns
  wide, two-column gaps. Only the characters `SOLID+VOID ATLAS` needs, unless a
  second drive name makes a wider set worth it.
- **Half-block compositor.** Packs pixel-row pairs into one character row as
  U+2580 with foreground as the top pixel and background as the bottom. This is the
  whole height saving; it needs its own test.
- **Extrusion.** Darkened offset copies composited behind the face, depth in pixel
  rows, so depth 2 costs one character row.
- **Ramp sampler.** Multi-stop interpolation, sampled per pixel row.
- **Three compositions** and the width rule that picks between them: full at
  >= 115 columns, compact at 82 - 114, bar below 82. Atlas already declares Textual
  horizontal breakpoints; this may or may not want to use them.

Verification, all of which must actually run:

- `uv run pytest` green, with new tests for the compositor, the ramp, the width
  rule, and each composition's exact column count.
- Headless Textual renders at 148x40, 104x34, and 80x24 confirming the right
  composition is chosen at each width.
- The mark is decorative, so it must not be announced as content. Decide what a
  screen reader gets, in line with ticket 10.

Blocked by ticket 14 only for the colour tokens the header shares with node kinds;
the geometry can start before that lands if it is kept separate.

## Answer

Shipped. `src/atlas/tui/wordmark.py`, 24 tests, 261 passing overall. Written
fresh; nothing was lifted from the prototype.

**Half-block compositor.** Every cell is U+2580, foreground painting the top pixel
row and background the bottom. A six-pixel glyph occupies three character rows and
the extrusion adds a fourth. There is a test asserting every cell in the rendered
mark is that one character - any other glyph means the packing broke and the mark
is silently at half resolution.

**Measured, not assumed:**

| composition | width | rows |
|---|---|---|
| full | 111 | 4 |
| compact | 78 | 4 |
| bar | 20 | 1 |

**The width rule needed a correction the prototype hid.** The published rule is
full at >= 115 columns, compact at 82-114, bar below. The marks are 111 and 78
wide, so a naive "widest that fits" would have chosen the full mark at 111 columns
and rendered it flush against both terminal edges. The thresholds are the mark
width *plus the console's four columns of padding*, which is exactly 115 and 82.
`MARGIN` is now a named constant and `composition_for` takes it, so the rule and
the layout cannot drift apart. A test walks every width from 20 to 240 and asserts
the chosen composition always fits.

**Wired in place of Textual's `Header`.** A `#mark` Static, refreshed on mount, on
resize, and whenever the inventory changes, so the mark collapses as the window
narrows rather than clipping. The identity line beneath it carries drive, map
version, project count, and how many need attention - and at bar width it sits on
the same row, making the whole header one line.

**Always `rich.text.Text`, never `str`.** Ticket 05's markup-injection trap. A mark
carrying 24 distinct colour spans has no business going through `Text.from_markup`,
and there is a test pinning the type.

**Regression guard for the prototype's own bug.** An early build had VOID and ATLAS
running together because the word space was two columns and took no gaps. The space
glyph is four columns and still takes the gaps either side; a test asserts the
separation exceeds a plain letter gap.

### Verification

- `uv run pytest` - 261 passed, up from 237.
- Headless render of the real app at 148x40, 100x32 and 80x24, each producing the
  expected composition: full mark, compact with the ATLAS caption, and the
  single-row bar.
- All six ember stops confirmed present in the rendered SVG, so the gradient is
  reaching the terminal rather than collapsing to a flat colour.

### Not done here

Accessibility. The mark is decorative and should not be announced as content, and
the ticket asked what a screen reader gets. Textual's screen-reader story is
unresolved (ticket 05 research), and ticket 10 owns the honest accessibility claim
for the whole surface, so this is deliberately left there rather than guessed at.
