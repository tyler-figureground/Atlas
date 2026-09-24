# Lock the Atlas visual world

Type: prototype
Status: resolved
Blocked by: -
Parent: ../map.md

> **2026-09-23:** the design sheet this ticket cites no longer resolves (found in
> session 9; audit #61). It was already out of date - it drew missing folders
> inline, which ticket 14 ruled out, and rendered only at 132x38, a width ticket 03
> showed is not used. The decisions below stand; the renders are gone. Re-render
> from `tools/atlas` if they are needed.

## Question

Three visual worlds were built as real Textual renders, headless at 132x38, and
published for comparison:

https://claude.ai/code/artifact/4a9756ec-d166-44d0-b76d-ddd9979fbbc6 (gone - see the note above)

- **A - POCHE.** Solid is mass, void is space; the firm's name is the interface
  metaphor. Filled blocks for folders on disk, hatched void for folders the map
  expects and disk lacks. Five-row block wordmark, the plus cut in vermilion.
  Ink on near-black, one red. Seven header rows.
- **B - TITLE BLOCK.** Everything is line, nothing is fill. Double-rule box-drawing
  letterforms sharing strokes with the tree, a bordered DRIVE / MAP / PROJECTS /
  ATTENTION strip. Blueprint cyan on charcoal. Seven header rows, three of wordmark.
- **C - PAPER.** Inverted: bone ground, ink text, wordmark knocked out of a solid
  ink bar. Three header rows. Fights a dark terminal theme.

Resolve:

1. Which world ships.
2. The header footprint rule. A costs seven rows before the first project appears -
   a quarter of a thirty-row terminal. Proposed: full wordmark on first paint and
   when the terminal is tall, collapsing to a single identity line once work starts.
   Accept, reject, or replace.
3. The glyph vocabulary for folder state: present, absent, drifted, unfiled, empty.
   The prototypes propose fill weight (A, C) versus struck labels on standard
   branches (B). This is what a first-time user must read without a legend.
4. Whether the locked world becomes a written visual authority (DESIGN.md, or a
   token module) or stays as reference renders.

Prototype source: the throwaway renderer used for the artifact. Rebuild rather than
extend it if further variants are needed - it is not Atlas code and must not become
Atlas code.

## Progress

**World locked: A - POCHE.** Solid is mass, void is space; fill weight carries
folder state. The console body is settled and is not reopened by anything below.

**Wordmark reopened by the user:** retro-cyberpunk 3D extruded gradient lettering,
which the original A did not have. Five treatments built and published on the same
sheet:

https://claude.ai/code/artifact/4a9756ec-d166-44d0-b76d-ddd9979fbbc6 (gone - see the note above)

- H1 OUTRUN - yellow through orange, magenta, violet. Vertical ramp, depth 2.
- H2 CHROME - cyan, forced white specular row, steel, magenta, violet.
- H3 EMBER - bone-gold through amber into the console's own vermilion. The only
  treatment that adds no colour the console does not already mean something by.
- H4 SCANLINE - diagonal ramp, depth 3, alternate rows dimmed to 62%. 195 colours.
- H5 COMPACT - H1's ramp, but SOLID+VOID in the 3D face with ATLAS captioned
  beside it. 82 columns instead of 111.

Construction: 5x5 block glyphs, two-column gaps, extrusion composited as darkened
offset copies *behind* the face, gradient sampled per cell from a multi-stop ramp.
Full mark measures 111 columns by 7 rows; H5 measures 82.

Three questions still open, on the sheet:

1. Which treatment - and is a second colour system in the header acceptable, given
   vermilion, ochre, sage and steel already carry meaning in the console below?
2. Nine rows before the first project. Where does the header collapse?
3. Does the retro register stop at the wordmark, or does the whole console go
   further (scanline dimming on rows, glow on selection, neon rules)?

Ticket stays claimed until those three are answered. Prototype source is throwaway
and lives in the session scratchpad only - it is not Atlas code.

## Answer

**World: A - POCHE.** Solid is mass, void is space. Fill weight carries folder
state. Settled and not reopened.

**Wordmark: EMBER,** rendered in half-blocks. Bone-gold at the crown through amber
and orange into the vermilion the console already uses for ACTION, then oxblood at
the base. Chosen over the neon ramps because it introduces no colour the console
does not already mean something by, and it survives a colourblind check the magenta
ramps do not.

**Height: solved by half-block rendering,** not by shrinking the letterforms. A
terminal cell is about twice as tall as it is wide, and U+2580 UPPER HALF BLOCK
splits it: foreground paints the top half, background the bottom. Every character
row therefore carries two pixel rows of letterform. Glyphs are drawn six pixels
tall, packed into three character rows, with extrusion adding a fourth.

| | before | after |
|---|---|---|
| wordmark rows | 7 | **4** |
| whole header | 9 | **6** |
| gradient bands | 5 | **6** |

The gradient got *finer* while the mark got shorter - more pixel rows to sample
across. Nothing was traded.

**Collapse rule, three steps by terminal width:**

- **>= 115 columns** - full mark, `SOLID+VOID ATLAS` at 111 columns. 6 header rows.
- **82 - 114 columns** - compact mark: `SOLID+VOID` in the 3D face with `ATLAS` set
  beside it in ember caps, 78 columns. Still 6 header rows.
- **< 82 columns** - collapsed: the name knocked out of a single ember bar, drive
  identity beneath. 3 header rows.

**Retro register stops at the wordmark and the cursor.** No scanline dimming on
table rows, no glow, no neon pane rules. One loud moment.

**Cursor and field.** The selected row is the only full-strength thing on screen:
a solid ember rail in the gutter, bone text, saturated status colour. Every
unselected row drops to muted ink with its status colour mixed 42% toward the
ground. The alternative - status knocked out as an inverse chip - was built and
rejected: it reads faster down a long list but competes with the wordmark.

**One palette change made without being asked:** `SETUP` was a steel blue, the only
colour on screen from outside the ember family. It is now a warm bronze
(`#A8845C`). `READY` warmed slightly to `#8AA37A`. `ACTION` and `REVIEW` were
already ember and did not move. Called out here because it is a semantic colour,
not decoration - ticket 14 should confirm it when it writes the kind table.

**Tokens as built** (prototype values, to be confirmed by the token-layer ticket):

- ground `#0C0C0D` &middot; surface `#141414` &middot; rail `#282622`
- bone `#F4F0E6` (cursor only) &middot; ink `#A9A399` &middot; muted `#7A746A` &middot; dim `#48453F`
- ember ramp `#FFE7BC` `#F6C25A` `#EE8A2B` `#E2452A` `#A8250F` `#5E1206`
- extrusion shade `#1E0803`, lightened 30% toward `#E2452A` on the near layer
- ACTION `#E2452A` &middot; REVIEW `#D9A441` &middot; READY `#8AA37A` &middot; SETUP `#A8845C`

Sheet: https://claude.ai/code/artifact/4a9756ec-d166-44d0-b76d-ddd9979fbbc6 (gone - see the note above)

The prototype renderer stays throwaway. Ticket 17 writes this into Atlas properly,
under test.
