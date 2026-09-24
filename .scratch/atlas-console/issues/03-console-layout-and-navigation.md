# Console layout and navigation model

Type: grilling
Status: resolved
Blocked by: -
Parent: ../map.md

## Question

The portfolio dashboard is out of scope, so the project list stays the landing
surface. That leaves the relationship between the list and the tree undecided.

The prototypes show both panes at once. That reads well at 132 columns and breaks
below roughly 100 - the current app already declares breakpoints at 100 and hides
its detail pane below that.

Resolve:

- Does the tree sit permanently beside the project list, or does Enter push into a
  full-width tree for one project with Escape returning?
- If responsive: what happens at each breakpoint, and does the model change or only
  the composition? A layout that changes navigation model by width is harder to
  build muscle memory against.
- Where do the dossier panel and search results live in whichever model wins - a
  third pane, a mode of the right pane, or an overlay?
- What is on screen at first paint, before a project is selected?
- Which pane holds focus on entry, and what does Tab cycle through?
- The current app has a filter input, a summary line, an operation line, and a
  footer. Which of those survive, and does the operation line stay a persistent row
  or become transient?

Both operators must be served: fast for daily portfolio work, legible for someone
who opens Atlas twice a month.

## Answer

### The measurement that reframed the ticket

The ticket assumed the console lives at 132x38, with 80x24 as the floor. That is
wrong on both axes.

Herdr (`herdr.dev`, the agent runtime the user now works in daily) records every
PTY resize. `~/AppData/Roaming/herdr/herdr-server.log` held 40 resize events on
this machine:

- **Columns, by frequency:** 46 (9), 77 (8), 153 (7), 179 (3), 87/88 (3), 120 (2),
  then single instances of 80, 57, 48, 39.
- **Rows:** 51 in 33 of 40 samples, 52 in 3, then one each of 40, 30, 24.

Windows Terminal contributes 120x30, its default, with no `initialCols` or
`initialRows` override in `settings.json`.

**Rows are abundant and nearly constant. Columns are scarce and trimodal** -
roughly 179/153 full or wide, 87/77 half, 46 quarter. Vertical space is the
resource Atlas has; horizontal space is the one it does not. Every decision below
follows from that inversion.

A consequence worth stating plainly, because it contradicts how the effort has
been drawing itself: **the single-region composition is the common case, not the
degraded one.** Eight of the twelve distinct measured widths fall below the
two-column threshold.

### The model

**Beside, not drill.** The tree is present by default alongside the project list,
and either side can be collapsed by hand. This overrides the recommendation made
during the grill, which argued for drill-in on the grounds that tree plus NOT ON
DISK is already two panes.

**The model is constant at every width. Only the composition responds.** Enter and
Escape mean the same thing at 46 columns and at 179. Panes stack, collapse, or
become one-at-a-time; nothing changes what a key does.

### Regions

Three regions, arranged as **two columns where the outer one splits horizontally**:

```
+----------------+------------------------------+
|                | <project name>               |   workspace title, 1 row
|  project list  +------------------------------+
|                |                              |
|   (DataTable)  |   tree region                |
|                |                              |
|                +------------------------------+
|                |   companion region           |
+----------------+------------------------------+
```

The companion sits **under** the tree, not beside it. That spends rows, of which
there are 51, to save columns, of which there are 46. A three-column arrangement
would need ~150 columns to breathe and is dead at 77.

At 51 rows the budget is: header 1-4, workspace title 1, chrome 3, leaving roughly
44 - about 30 for the tree and 12 for the companion, both real.

The existing `#detail` pane is **replaced** by the companion. It does not survive
as a separate region.

### Breakpoints

Two breakpoints, three states. The `100` is the one already in
`HORIZONTAL_BREAKPOINTS`, deliberately reused rather than inventing a third set of
magic numbers alongside the wordmark's 115 and 82.

| Width | Composition | Measured panes landing here |
|---|---|---|
| `>= 100` | Two columns. List `2fr`, workspace `3fr`. | 120, 153, 179 |
| `40 - 99` | Single region, one visible at a time. | 46, 48, 57, 76, 77, 80, 87, 88 |
| `< 40` | One line: widen to 40 columns. | 39 |

One ratio at every two-column width. The workspace takes the larger share because
the tree is the point of the screen.

Height rules: at `>= 30` rows the summary and operation lines stay separate; below
30 they merge into one line; below 16 rows Atlas refuses the same way it does
below 40 columns.

### Collapse

**Manual wins until physically impossible.** Breakpoints set the default collapse
state for a width, but an explicit collapse is sticky for the session and is only
overridden when the width genuinely cannot honour it. Losing a deliberate choice
to a window drag makes an app feel like it is arguing with the operator, and under
Herdr pane resizes are frequent and not always intentional.

Keys:

- `[` toggles the project list.
- `]` toggles the companion.
- `z` maximizes the focused region, restoring on a second press. This is the
  one-keystroke path to the tree at full width.

### Navigation

**Enter drills rightward, Escape walks leftward, at every level.**

- Enter on a project row moves focus into the workspace.
- Enter on a folder node toggles it.
- Enter on a file opens it.
- Escape unwinds one step: tree to list, list to drive picker, clearing an open
  filter first.

In single-region composition, Enter and Escape additionally swap which region is
drawn. The meaning is unchanged; only what is visible differs.

**Enter does not load.** By the time it is pressed the tree is already present or
already in flight - see cursor-follow below.

**Tab means "next region"** in both compositions: list, tree, companion, list. At
`>= 100` it moves focus. Below 100 it moves focus and swaps the visible region.

**`/` filters the focused region** rather than always the project list - the list
by name and health as today, the tree by node name. One key, one meaning, follows
focus.

The health `ResultModal` that `action_inspect` pushes today **stops being a
modal**. Its content becomes a companion mode. That reclaims Enter and removes a
modal that was standing in for a panel.

### Cursor-follow

**The workspace tracks the project list cursor, debounced at ~150 ms, with cache
hits exempt.** A TTL-warm project renders with no debounce at all.

Without the debounce, arrowing through 40 projects fires 40 enumerations; ticket
12 measured cold p99 at 91 ms and worst case at 314 ms. With it, the tree is
populated at first paint and after every cursor rest, without a keystroke. That is
what makes "on by default" true rather than nominal.

### The companion

Three things want the companion slot: unmet Expectations (NOT ON DISK), project
health, and later the dossier from ticket 09.

Only NOT ON DISK needs to be **simultaneous** with the tree. Comparing what is
filed against what the map expects is the comparison the screen exists to make.
Health and the dossier are consulted and left; nobody reads a dossier while
scanning folder names.

So: **modes, with NOT ON DISK privileged.**

- `d` cycles: NOT ON DISK, health, dossier.
- NOT ON DISK is the default.
- The companion **snaps back to NOT ON DISK whenever the selected project
  changes**, so a consultation never persists silently into the next project and
  hides missing folders.

### Search

**A full-width overlay, not a fourth region.** There is no column budget for one,
and search is momentary.

Enter on a result **navigates the layout to it** - selects the project in the
list, expands the tree to the node, dismisses the overlay. Search is a way of
moving through the layout, not a fourth place to live.

Bound to `g`, for go-to. `/` is the filter and `s` is sort. Ticket 08 still owns
what search searches.

### First paint

Focus lands on the **project list**, always. It is the landing surface settled at
charting, and the workspace is downstream of what the list cursor is on.

- **Drive picker** unchanged, and unchanged in status: a pre-screen outside the
  list/workspace model, auto-skipped when exactly one drive is mapped.
- **During the scan:** the list keeps its existing `loading` state; the workspace
  draws a placeholder. An empty tree and an unscanned one are different facts -
  the same principle that separates Unreadable from Empty Folder in `CONTEXT.md`.
- **Scan complete:** cursor on row 0 under the current health sort, and the
  debounced follow fires immediately for that row. The tree is populated at first
  paint.
- **Below 100 columns:** the list is the visible region on entry.
- **Empty drive:** the list shows its empty state and the workspace shows a
  matching one, rather than a blank frame.

### Chrome

All four survive: transient filter input, summary line, operation line, footer.

- The **operation line stays a persistent row, not a toast.** It is the surface
  that reports live-drive mutations, and a notification that scrolls away is not
  honest about a write.
- The **summary line becomes context-sensitive** - portfolio counts in the list,
  project counts in the workspace.
- The **footer stays** because it is the only discoverability surface for the
  operator who opens Atlas twice a month. At 46 columns it can show roughly three
  bindings; the three that earn it are `?`, `Tab`, and `Enter`.
- The workspace gets a **permanent one-line title carrying the project name**, not
  only when the list is collapsed. It costs 1 row of 44 and means the region
  identifies itself under `z`, under `[`, and in single-region composition without
  a special case for each.

### Key map, consolidated

New in this ticket: `[`, `]`, `z`, `d`, `g`. Changed: `enter`, `escape`, `/`.
Retired: none - `action_inspect` survives as the companion's health mode.

Existing bindings untouched: `q r n e m a c f o s l x space ?`.

### What this does to the map

- The verification-sizes constraint naming 132x38 and 80x24 is replaced by the
  measured widths.
- The **80x24 composition** fog patch is resolved and cleared.
- Ticket 09 is unblocked.
- Ticket 20 graduates: the console shell as Atlas code.

Vocabulary in `/CONTEXT.md`. Decision in `docs/adr/0005`.

## Deviation, 2026-09-23: what Enter and space do in the tree

Built differently from the Navigation section above, and never recorded until the
2026-09 audit (#61):

- **Enter drills Regions, not nodes.** Enter on a project row moves focus into the
  tree; Enter in the tree moves focus to the Companion. It never toggles a folder or
  opens a file. While a repair is armed, Enter confirms it instead (ticket 23).
- **`space` toggles a folder** when the tree has focus - Textual's own Tree binding -
  and marks a project when the list does.
- **`o` opens a file or folder** under the tree cursor, and reveals an Unfiled node
  in Explorer rather than opening it (#45).

No session recorded why Enter stopped short of the node. What holds today: Enter
is a priority App binding, so it reaches the console before the Tree's own
`select_cursor`, and it is also the inline confirm for an armed repair. The `space`
meaning was never argued either - the session 9 handoff flags it - and is left
open to revisit in use. `g` from the key map above was not built; it belongs to
ticket 08 (global search), still open.
