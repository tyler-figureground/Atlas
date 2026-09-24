# The console shell, as Atlas code

Type: task
Status: resolved
Blocked by: -
Parent: ../map.md

## Question

Ticket 03 decided the console's Regions, Compositions, breakpoints, keys, and
first paint. ADR 0005 records it. Nothing of it exists in `tools/atlas` yet:
`compose()` is still mark, drives, filter, `#workspace` as a flat `Horizontal` of
`#projects` and `#detail`, summary, operation, footer.

Build the shell, with the Tree Region and the Companion Region holding
placeholders. This is deliberately the frame without the tree - ticket 07 fills
the Tree Region, ticket 09 fills the dossier Companion Mode. Building them in that
order means the tree lands into a layout that already works, at every width,
rather than into one being invented around it.

Do:

- Three Regions and the Workspace container, per ADR 0005. `#detail` is replaced,
  not kept alongside.
- `HORIZONTAL_BREAKPOINTS` at 100 and 40, with Single-Region Composition below
  100 and the too-narrow line below 40. Vertical rules at 30 rows (merge summary
  and operation) and 16 rows (refuse).
- Collapse: `[`, `]`, `z`, with an explicit collapse outranking the breakpoint
  default and sticky for the session.
- Navigation: Enter drills, Escape unwinds, Tab moves to the next Region, `/`
  filters the focused Region. Identical semantics in both Compositions.
- `action_inspect` stops pushing `ResultModal`; project health becomes a Companion
  Mode, `d` cycles the modes, and the Companion snaps back to unmet Expectations
  when the Selected Project changes.
- Workspace title carrying the Project Name, permanently.
- Cursor-follow: debounced at ~150 ms, cache hits exempt. With no tree yet the
  placeholder can still exercise the debounce and the cancellation path.
- Context-sensitive summary line.
- Footer at 46 columns shows `?`, `Tab`, `Enter`.

Verification, per the map's constraint as ticket 03 revised it: headless renders
at the measured widths - 179, 153, 120, 87, 77, 46 - and at 51, 30, and 24 rows.
`uv run pytest` green. State which ran.

## Constraints already fixed

- ADR 0005 is the contract. Deviating from it is a decision, not an
  implementation detail, and belongs back on ticket 03.
- Colour comes from `tui/tokens.py`, never a hex literal; the app's CSS block is
  geometry only. The contrast test in the token suite must stay green.
- The wordmark's own thresholds (115 / 82) are independent of the layout
  breakpoints (100 / 40) and stay independent. Do not unify them.
- Textual-side traps from ticket 05 apply to anything tree-shaped built here.

## Resolution

Built. The layout rules are a pure module, `tui/layout.py`, tested without
Textual; `app.py` applies them and owns none of the rule. 339 tests pass, up from
294. Repo lint green. Rendered headless at 179, 120, 87, 46 and 39 columns and at
51 and 24 rows on a scratch fixture drive - Split, Single-Region, the merged
status line and the refusal all confirmed on screen, not only in assertions.

- **Three Regions and the Workspace.** `#console` holds the Project List beside
  the Workspace, which is a title over the Tree Region over the Companion Region.
  `#detail` is gone.
- **Breakpoints.** `HORIZONTAL_BREAKPOINTS` now `[(0, "-tiny"), (40, "-narrow"),
  (100, "-wide")]`. Split at 100+, Single-Region from 40 to 99, one honest line
  below 40 columns or 16 rows. Summary and operation merge below 30 rows onto the
  operation line.
- **Collapse.** `[` the Project List, `]` the Companion, `z` zooms the focused
  Region. Sticky for the session; a width that cannot carry the collapse takes
  over without forgetting it. Collapsing the focused Region moves focus off it.
- **Navigation.** Tab cycles and skips what is collapsed, Enter drills, Escape
  unwinds through the Regions and then to the drive picker. None of the three
  functions takes a width, which is what makes "identical in both Compositions"
  structural rather than a promise.
- **Companion Modes.** `d` cycles unmet Expectations, project health and the
  dossier placeholder; the Companion snaps back to Expectations when the Selected
  Project changes. The health modal is gone - `action_inspect` is deleted and the
  palette entry switches the mode instead.
- **Unmet Expectations is real, not a placeholder.** It reads
  `ProjectTree.expectations()` from ticket 07, and it marks the ones conform
  cannot backfill.
- **Cursor-follow.** Title moves at once, the Companion waits out a 150 ms rest,
  cache hits are exempt, and a cursor passing over a project never opens it.
- **Footer.** Below 100 columns Textual's footer gives way to a three-key line -
  `? Help  Tab Region  Enter Open`.

### One thing worth carrying forward

The first attempt sized the footer through `check_action`, returning `None` to
hide a binding. That also **disables** it, so at 80 columns every action key
stopped working and twenty-three tests went red at once. The chrome now has its
own widget and `check_action` is back to being only about state. Hiding and
disabling are the same return value in Textual, and they are not the same thing.
