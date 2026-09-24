# The tree widget, as Atlas code

Type: task
Status: resolved
Blocked by: -
Parent: ../map.md

## Question

Ticket 07 settled the seam and built `atlas.core.tree`. Ticket 20 built the frame
the tree lands in and left the Tree Region holding a placeholder. What remains is
the widget itself, and it is the destination's centrepiece - "a navigable
per-project folder tree with not-on-disk awareness" is the first thing the map
promises.

Do, test-first:

- **A pure label function.** Glyph, name, disclosure marker and Child Count, built
  from `tui/tokens.py` and returning `rich.text.Text`. Never `str`: `Tree.process_label`
  runs `Text.from_markup`, so a real folder named `[2024] Survey` silently loses
  its prefix, and `[b] Basement` loses more than that. Testable with no widget.
- **The widget.** A plain `Tree`, never `DirectoryTree`. One `children()` call per
  expanded node, in a worker that is **not** `exclusive` - the widget's default
  worker group is shared, so an exclusive per-node worker cancels every other
  in-flight expansion.
- **Cursor restore by Node Key.** Textual restores the cursor by line number, so
  the widget must re-resolve a Node Key to a line after every rebuild, and
  `select_node` on a just-added node has to go through `call_after_refresh` or it
  lands on the root (issue 3547, still open on 8.2.8).
- **No expand-all.** `expand_all()` posts one `NodeExpanded` per descendant -
  measured at 201 messages for 201 nodes - which is a load storm on a streaming
  mount. The default `shift+space` binding has to go.
- **`get_label_width`.** Ticket 05 measured the median rebuild at 5000 expanded
  nodes falling from 25.4 ms to 6.4 ms by overriding it. Cheap, and the tree is
  rebuilt on any mutation, resize or style change.
- **Wire it into the Tree Region**, replacing ticket 20's placeholder, and let the
  Workspace's cursor-follow populate it.

Explicitly not here: **the repair keys and the undo stack.** ADR 0006 designed
them and ticket 21 built the core they sit on, but a tree that writes is a
different ticket from a tree that reads. That is ticket 23.

Verification: `cd tools/atlas && uv run pytest`, green, plus a headless render at
the measured widths showing a real project's folders. State what ran.

## Constraints already fixed

- ADR 0007 is the seam contract; ADR 0004 is the state model; ticket 05's Textual
  findings are binding and are listed above rather than left to be rediscovered.
- Colour and glyphs come from `tui/tokens.py`. Tree nodes are not DOM nodes and
  take no CSS at all, which is the whole reason the token layer owns them.
- Ticket 13 stands: Child Count is immediate children only, and only for a folder
  whose Load State is Read.
- An unreadable folder must never render as an empty one (ADR 0004).

## Resolution

Built. `tui/treeview.py`: a pure `node_label`, a matching `label_width`, and
`ProjectTreeView` over `core.tree`. 360 tests pass, up from 339. Repo lint green.
Rendered headless at 179 and 46 columns on a scratch fixture drive.

- **The label is a value, not a render.** `node_label` returns `Text` and is
  tested against three names that a `str` label would have corrupted -
  `[2024] Survey`, `[b] Basement Survey`, `[/] Odd`. Only the second would have
  looked wrong; the other two are why the bug was latent.
- **`label_width` adds the parts up** rather than measuring a rendered label,
  which is the entire saving ticket 05 measured. Two computations of one number
  is somewhere they can drift, so a test holds them in agreement across every
  Filing State, Load State, width mode and expansion state.
- **Lazy, in a worker that is not exclusive.** Expanding one folder reads that
  folder and no other, and two expansions in flight both finish - asserted,
  because an exclusive worker would have cancelled one and the tree would simply
  have looked slow.
- **`select_key`** re-resolves a Node Key after a rebuild and goes through
  `call_after_refresh` (issue 3547). A key whose node is not drawn yet waits for
  it, which is what the cursor needs after a repair moves something into a folder
  Atlas has not opened.
- **No expand-all**, and the root level is read in the same worker as everything
  else with `Widget.loading` while it runs.

### One bug the render found and the tests did not

At first paint several folders drew an open triangle while closed. The Companion's
unmet-Expectations pass reads every mapped section (ADR 0007 says so), so those
folders are genuinely Read before the operator touches one - and the token layer
was using one glyph for two different facts. **Readness and expansion are not the
same thing.** `tokens.disclosure(load, expanded=...)` now picks the marker: the
triangle follows the widget, and Unreadable and Partial override it because they
say something no triangle can.

That is an argument for rendering the thing. Sixteen widget tests passed while
every closed folder on screen was lying about itself.