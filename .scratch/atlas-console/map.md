# Map: Atlas console

Label: wayfinder:map
Effort: atlas-console
Started: 2026-09-02

## Destination

A shipped, installed Atlas that a studio principal and occasional studio staff both
want to open: the SOLID+VOID identity present on screen, a navigable per-project
folder tree that shows what is filed and what the drive map expects but disk lacks,
the project dossier readable in-app, drive-wide search, and file-level actions - all
still crossing `atlas.core` plans with preview and confirmation before any write.

Done means running against the real ARCHITECTURE drive, tests green, docs current.
Not a spec, not a mockup.

## Notes

**This map carries execution.** It overrides Wayfinder's plan-don't-do default: a
ticket here may ship code, not only a decision. Ticket types still hold - a grilling
ticket resolves a question, a task ticket does work that unblocks one.

Domain: Python 3, Textual 8.2.8, `tools/atlas`. A self-contained uv project and the
one code exception to this repo's content-is-Markdown rule (ADR 0002). Not covered
by `scripts/lint.sh`.

Skills every session should consult:

- `/impeccable` - any visual or interaction work. Terminal is the medium, so its
  web-specific bans (self-hosted display faces, drawn SVG icon sets, box-shadow
  depth) do not transfer; its craft floor - contrast, spacing rhythm, real states,
  product language, one authored moment - does. Unicode glyphs *are* the icon
  system here and monospace is not a costume.
- `/tdd` - changes to `atlas.core`.
- `/grilling` and `/domain-modeling` - any decision ticket. New vocabulary lands in
  `/CONTEXT.md`.
- `/codebase-design` - seam design, especially the tree seam.

Standing constraints:

- Every mutation crosses a plan built in `atlas.core`, previewed, and confirmed.
  The TUI never writes directly. CLI and TUI share the plan.
- The drive map (`_tools/<drive>-map.json`) is the only folder-structure brain.
  Atlas hard-codes zero canonical folder names.
- Never touch a production or shared drive during development. Build synthetic
  fixture drives, as `tests/conftest.py` and the prior smoke run did.
- Tree work is built on a plain Textual `Tree`, never `DirectoryTree`. Labels are
  always `rich.text.Text`, never `str`, or folder names containing square brackets
  are silently mangled. Selection is re-resolved from Atlas's own key after every
  refresh, because Textual restores the cursor by line number. Per-node load
  workers are never `exclusive`. All four are measured findings from ticket 05.
- Verification per session: `cd tools/atlas && uv run pytest`, plus headless
  Textual renders at the **measured** terminal widths - 179, 153, 120, 87, 77, 46
  - and at 51, 30 and 24 rows. State which ran. The old 132x38 and 80x24 were
  assumed, never measured, and ticket 03 found them wrong on both axes: rows are
  abundant and near-constant at 51, columns are scarce and trimodal, and the most
  common single width is 46.
- Google Drive File Stream latency is the performance reality, not local disk.
  Local timings are not a latency claim.

Continuity: `.agent/handoff/` per this repo's checkpoint rule.

## Decisions so far

<!-- one line per closed ticket: gist plus link -->

- Destination, tree model, operator, and capability scope settled at charting.
  Filesystem-mirror tree with a separate not-on-disk list; both operators served;
  dossier, search, and file actions in scope; portfolio dashboard out.
- [Land the outstanding Atlas working tree](issues/01-land-outstanding-working-tree.md)
  - landed as four commits, `c6d564a..7737de7`, tests and lint green before
  committing. `.agent/`, `.impeccable/`, and `.scratch/` are tracked, not ignored.
  Not pushed.
- [Lock the Atlas visual world](issues/02-lock-the-visual-world.md) - POCHE world
  with an EMBER wordmark, rendered in half-blocks so the header costs 6 rows
  instead of 9 while the gradient gets finer. Collapse rule: full mark at >= 115
  columns, compact at 82 - 114, single bar below 82. Retro register stops at the
  wordmark and the cursor - no scanlines on data. Field muted, selected row the
  only full-strength thing on screen. `SETUP` moved from steel blue into the ember
  family. Prototype token values recorded on the ticket.
- [The wordmark and header, as Atlas code](issues/17-wordmark-and-header-in-atlas.md)
  - **shipped.** Half-block compositor, extrusion, ramp sampler and the three
  compositions, written fresh under test. Measured at 111 / 78 / 20 columns and
  4 / 4 / 1 rows. The width rule needed a correction the prototype hid: thresholds
  are the mark width plus the console's four columns of padding, which is exactly
  the published 115 and 82, and a test walks every width from 20 to 240 asserting
  the chosen composition fits. Replaces Textual's `Header`, refreshed on resize.
- [The token layer](issues/18-token-layer.md) - **built.** A Python module owns
  the palette and glyph table and generates the Textual CSS from it, because tree
  nodes take no CSS and `render_label` must read from Python. `MODAL_CSS` and
  `STATUS_STYLES` migrated; the app's CSS block is geometry only. Colour is tested
  by structure and contrast, never by hex literal - every text token must clear
  4.5:1, and the generated CSS is scanned so a hand-edited colour fails the suite.
  Tuning to pass that floor lightened four tokens. Flips ACTION to vermilion and
  REVIEW to ochre from the old yellow/red.
- [Do folders show a count, and of what](issues/13-folder-counts.md) -
  immediate-child counts only, folders and files counted separately, rendered only
  on Read folders and never as a zero on an Unread one. Recursive counts are out:
  they are a walk, and they are incompatible with lazy loading regardless of cost.
  Uncovered a live collision - `clean` removes folders with no file *anywhere
  beneath* while the tree calls a folder empty when it has no children *of its
  own*. Now named separately as **Fileless** and **Empty Folder** in `/CONTEXT.md`.
- [Enumeration failure as a core fact](issues/16-enumeration-error-as-a-core-fact.md)
  and [Extended-length paths](issues/19-extended-length-paths.md) - **built, not
  just decided.** `list_entries` returns a `Listing` carrying Load State; it
  iterates like the tuple it replaced so all six consumers were untouched, and is
  unconditionally truthy so `if listing:` cannot silently regress. `long_path()`
  applies the `\\?\` prefix on demand at the three read chokepoints. An
  unreadable project root is recorded, reported as REVIEW rather than READY or
  SETUP, and shown in its own detail block. `--json` gains `unreadable`. 211 tests
  pass; both live over-MAX_PATH folders verified fixed on the real drive.
- [Node kind vocabulary](issues/14-node-kind-vocabulary.md) - a node is a thing
  that exists on disk; an unmet map Expectation is not a node and is listed beside
  the tree, which means the prototype renders showing missing folders inline were
  wrong and the renderer drops those rows. Every node carries two orthogonal
  values: **Filing State** (Mapped / Drifted / Misplaced / Loose / Unfiled, first
  matching map rule wins) and **Load State** (Unread / Read / Unreadable /
  Partial). Emptiness is derived, never stored. Solid vs hatched answers "is
  anything wrong", colour answers "mine or Atlas's". Terms in `/CONTEXT.md`,
  decision in `docs/adr/0004`.
- [A latency number for the tree](issues/12-latency-budget.md) - measured on the
  live drive with the user's authorisation, read-only. The **whole studio drive is
  7,956 folders and 18,536 files, walked in 4.24 seconds**, so throughput is a
  non-issue at this size and a drive-wide index is affordable. The cost is all in
  the tail: cold p99 91 ms, worst 314 ms, nothing over a second. Budgets set -
  loading state at 120 ms, prefetch one level capped at 50, concurrency cap 4,
  count cap 500, cache TTL 60 s. Found two live `MAX_PATH` failures, one of which
  Atlas reports as an empty folder that is not empty. Report:
  `docs/research/atlas-drive-latency-measurement.md`.
- [What the folder tree is allowed to write](issues/04-tree-write-contract.md) -
  **the tree invents no new action kinds.** Every write it offers is a one-action
  slice of the Plan conform already builds: Drifted earns RENAME, Misplaced
  RELOCATE, Loose SWEEP, an unmet Expectation BACKFILL from the Companion. Unfiled
  earns nothing but reveal. Every write crosses a Plan, previews, and confirms with
  no exceptions - but confirmation weight follows plan size, so one action confirms
  inline on the operation line and only longer plans get the modal. **A full undo
  stack, one per Project**, in memory, no redo - undo restores the precondition
  that offered the action, so re-pressing the repair key *is* redo. Undo needs
  `Action.moved`, a manifest of what each apply actually moved, because a merge
  cannot otherwise be inverted without guessing and a wrong guess is data loss.
  **Revalidation scopes to the action:** the existing guard is a full 4.24-second
  `scan_drive` and `_project_token` only covers the project root, so a one-action
  Plan re-reads the map and re-enumerates two parent folders instead. The same
  guard runs on every undo pop, which is what lets the stack be optimistic. Path
  length **warns and obeys**, computed in `build_plan`, and `long_path()` is never
  applied on the write side - a warning is only honest if Atlas cannot silently
  exceed the limit. No CLI equivalents; ticket 10 settles parity for all three new
  surfaces at once. Vocabulary in `/CONTEXT.md`, decision in `docs/adr/0006`.
- [The core write surface for the tree](issues/21-core-write-surface.md) -
  **built.** `Move` and `Action.moved` give every applied action a manifest;
  `build_repair_plan` slices one Action out of the Plan conform already builds;
  `invert_plan` reverses it and refuses outright when a Backfill, a file-empty
  removal, or a Conflict leaves nothing to reverse; `Guard` exists at two scopes
  and three tests run them side by side; path length warns from `build_plan` and
  reaches `--json`, which now names its own fields instead of shipping `__dict__`.
  281 tests, up from 261.
- [The ProjectTree core seam](issues/07-project-tree-core-seam.md) and
  [What the tree does when conform moves things](issues/15-relocation-and-the-tree.md)
  - **decided and built.** Core hands the TUI a **lazily-expanding handle**, not a
  node tree and not a flat list: immutable nodes out, cache inside, one enumeration
  per displayed folder. Below the root, where `report_project` has no opinion,
  **containment** decides Filing State - Mapped under a canonical path, Unfiled
  under an Unfiled one - which needs no amendment to ADR 0004. The **Node Key** is
  the project-relative path and it is what the line-number cursor re-resolves
  against. Staleness is a 60-second shelf life plus explicit refresh; after Atlas's
  own write the tree **reconciles by Move Manifest**, forgetting the two folders
  the scoped Guard already watched, and the cursor follows what it repaired. One
  correction to ADR 0006: **only control-plane Expectations are repairable** -
  conform has never created a mapped section and would skip it. `docs/adr/0007`.
- [The console shell, as Atlas code](issues/20-console-shell-in-atlas.md) -
  **built.** The layout rules are a pure module the tests cross without Textual;
  `app.py` applies them and owns none of the rule. Three Regions, two
  Compositions, breakpoints at 100 and 40, summary and operation merged below 30
  rows, one honest line below the floor. Collapse on `[` `]` `z`, sticky and
  outranking the breakpoint. Tab, Enter and Escape take no width argument, which
  is what makes identical-in-both-Compositions structural. The health modal is
  gone: `d` cycles Companion Modes and unmet Expectations reads the real seam from
  ticket 07. Below 100 columns Textual's footer gives way to `? Help  Tab Region
  Enter Open`. Rendered headless at 179/120/87/46/39 columns and 51/24 rows.
- [The tree widget, as Atlas code](issues/22-tree-widget.md) - **built.** A plain
  `Tree` over `core.tree`: labels as `Text` so a folder named `[2024] Survey` keeps
  its name, `label_width` adding the parts up instead of rendering to measure,
  per-node workers that are deliberately not exclusive, no expand-all, and
  `select_key` re-resolving the cursor through `call_after_refresh`. Rendering it
  found a bug sixteen passing tests had not: readness and expansion were sharing
  one glyph, so every folder the Companion had prefetched drew an open triangle
  while closed. `tokens.disclosure` now separates them.
- [Console layout and navigation model](issues/03-console-layout-and-navigation.md)
  - **the console is three Regions in two Compositions.** Project List opposite a
  Workspace that stacks the Tree Region over a Companion Region - rows spent to
  save columns. Split Composition at >= 100 columns, Single-Region below, refusal
  under 40 columns or 16 rows. Settled by measuring Herdr's PTY resize log rather
  than assuming: rows are near-constant at 51, columns trimodal at ~179/153,
  ~87/77 and 46, and **eight of twelve measured widths are Single-Region** - the
  narrow arrangement is the common case, not the degraded one. Navigation is
  identical in both: Enter drills, Escape unwinds, Tab is next-Region, `/` filters
  the focused Region. Explicit collapse outranks the breakpoint default. The
  Workspace follows the list cursor, debounced 150 ms, cache hits exempt, so the
  tree is populated at first paint. `#detail` and the health modal are both
  replaced by Companion Modes; unmet Expectations is the privileged default
  because it is the only one that must be simultaneous with the tree. Vocabulary
  in `/CONTEXT.md`, decision in `docs/adr/0005`.
- [The tree's write keys, the inline confirm, and the undo stack](issues/23-tree-write-keys.md)
  - **built.** `tui/repair.py` is pure like `tui/layout.py`: what the key offers,
  what the confirm reads, and a per-Project undo stack that refuses an
  uninvertible Plan **at push rather than at pop**. `f` means "conform what has
  focus" - the whole project from the list, one node from the tree - and arms an
  inline confirm on the operation line that Enter commits and Escape abandons.
  `u` undoes. `conform --node PATH` and `conform --revert FILE` are the CLI forms
  ADR 0008 obliges; `--revert` needed `plan_from_dict`, because `action_to_dict`
  had no inverse and the Move Manifest was write-only. **Five bugs, two of them
  design errors in shipped ADRs.** `Guard.for_action` cannot guard an undo - it
  re-derives the Plan from the map and an undo reverses the map, so it refused
  every undo on an unchanged drive. `reconcile` missed the folder a merge
  consumed, because every Move in a merge names a *child*, and the tree drew a row
  for a directory that no longer existed. And **the Tree Region could not take
  keyboard focus at all** - `#tree` is a `Vertical` and `Vertical.focus()` is a
  no-op, so the widget shipped unreachable by keyboard while sixteen widget tests
  passed; fixing it exposed Textual's `Tree` taking Atlas's Enter and a drilled
  tree having no cursor. Corrections on `docs/adr/0006` and `0007`. 405 tests, up
  from 364.
- [CLI parity and the accessible fallback](issues/10-cli-parity-and-accessibility.md) -
  **a CLI form is owed by every capability that writes and every capability that
  produces a fact; navigation is exempt, and the obligation is discharged in the
  same session as the surface.** Parity is kept but re-founded: the accessibility
  justification traced to one synthetic persona and Textual's unresolved #2425,
  not to an operator, and `--json` has zero consumers in this repo today - both
  recorded rather than glossed. The README now states the negative first and
  claims no conformance. The second rule is the one with a live victim: **colour
  may reinforce a distinction and never carry one alone.** Dropping the Filing
  State word at narrow width left Drifted, Misplaced and Loose rendering
  identically *to everyone*, because ADR 0004 has them share a glyph and a colour
  by design and the word was the only separator; what remained measured **1.82:1**,
  vermilion against ochre, on the red/green axis. The word now abbreviates -
  `NAME` `PLACE` `LOOSE` `UNMAPPED` - and is never dropped, on files as well as
  folders. The trigger was measuring the wrong thing too: `SPLIT_COLUMNS` stripped
  labels at 87 columns where the tree owns nearly the whole terminal, so
  `ABBREVIATE_COLUMNS` is its own named 60. Colour is tested by asserting no two
  Filing States survive having it stripped, never by a hex. Vocabulary in
  `/CONTEXT.md`, decision in `docs/adr/0008`. Tickets 23 and 24 graduated.
- [Textual 8.2.8 tree widgets and lazy loading](issues/05-research-textual-tree-widgets.md)
  - build on plain `Tree`; `DirectoryTree` destroys injected nodes on reload, can
  only subtract paths, and costs ~2 stats per entry. Copy its lazy-load machinery,
  do not inherit it. Scrolling is virtualized but `_build()` is linear in expanded
  nodes - 20-30ms at 5000. Two measured silent-corruption traps: markup injection
  via `str` labels, and cursor restore by line number. Report:
  `docs/research/atlas-tree-widget-evidence.md`.
- [Reading a project tree over Google Drive File Stream](issues/06-research-drive-tree-cost.md)
  - shared drives are streaming-only; enumeration is the unit of cost, not `stat`;
  no official latency figure exists from anyone; recursive counts have no cheap
  primitive; stock Textual `DirectoryTree` is the wrong loader; filesystem watching
  is not a dependable staleness signal; `Path.rglob` swallows every `OSError` and
  must never be used here. Report: `docs/research/atlas-drive-tree-read-cost.md`.
- [File Rules](issues/25-file-rules.md) - **built.** The map can file a loose root file
  by extension, glob, name regex, or the words inside a PDF. The design is organize's
  (MIT); its code is not, because the map is the only brain and every write crosses a
  Plan. A rule emits the SWEEP that Loose already earned, so ADR 0006 held and the
  tree, the repair key, the Guard and undo were untouched. A malformed rule refuses
  the whole map rather than being skipped - a widened rule moves more. Content is read
  last, only for `*.pdf`, never past 64 MB, cached by path+size+mtime, and silent on a
  damaged file. Decision in `docs/adr/0009`, vocabulary in `/CONTEXT.md`, survey in
  `docs/research/atlas-file-management-oss.md`. Tickets 26, 27, 28 graduated.

## Not yet specified

Fog toward the destination. Graduates into tickets as the frontier clears it.

- **File-level action set.** Which actions the tree offers, what core plan each
  builds, and how each previews. Depends on the write contract. *Partly cleared:*
  ticket 25 gave the map a way to make a root file Loose by name or content, and the
  tree already offers its Sweep. Ticket 04's non-writes are built (#45): `o` opens
  the node under the cursor (an Unfiled node is revealed in Explorer instead), `y`
  copies its path. What is still fog is rename, delete, and whether a file the
  operator picks can be moved anywhere the map has not named. Ticket 26 asks the
  narrowest version of the last one.
- **Load State labels do not abbreviate.** Ticket 10 gave the Fault Word a short
  form; the Load State label beside it kept its long one, so `not opened yet` runs
  past the viewport at 46 columns and the row scrolls. Same principle, different
  vocabulary, and `cannot read` is the one that must not be shortened into
  ambiguity - ticket 16's rule is that an unreadable folder never reads as empty.
  Deliberately out of scope at ticket 10; small, and visible on screen.
- **Selection and focus rendering everywhere else.** Ticket 02 settled the cursor
  for the project list and the tree. Modals, the filter input, the command palette,
  and the search overlay all still show default Textual focus, which no longer
  matches. Ticket 03 adds one to the list: with three Regions and a Tab that
  cycles them, **which Region has focus has to be legible without moving the
  cursor**, and in Single-Region Composition it has to be legible when only one is
  drawn. Small, and easy to forget until it looks wrong.
- **A `doctor` finding for over-long paths.** Ticket 04 put the length warning on
  the Action at plan-building time, which covers what Atlas is about to create. It
  does not surface paths already over the limit that nobody is currently moving.
  Considered and deferred once already as a new finding type; still deferred, now
  for a narrower reason.
- **Deep unreadable detection.** `doctor` checks the project root only, because
  that is all `scan_drive` enumerates. A folder three levels down that cannot be
  read is invisible until the tree lands. Ticket 07 inherits it.
- **Tree states.** Loading, empty project, permission error, a folder too large to
  walk, a stale tree after an external change. Ticket 06 adds two that must be
  designed distinctly: **enumeration error**, which must never look like empty, and
  **truncated or partial**, because a count cap can be hit and because CPython
  issue 102993 shows `os.listdir` returning a partial result on a synced mount
  while Explorer reads it fine.
- **Test strategy for the new surface.** The current three-happy-path TUI coverage
  will not hold a tree, a search overlay, and a dossier panel. Ticket 05 shows the
  shape that works: probe scripts driving real widgets through `App.run_test()`
  against the pinned venv, asserting on measured syscall and message counts rather
  than on rendered output.
- **Rebuild cost at depth.** `Tree._build()` is linear in expanded nodes and calls
  `render_label` once per line, and it fires on any mutation, resize or style
  change. Ticket 05 measured 20-30ms at 5000 expanded nodes and cut the median from
  25.4ms to 6.4ms by overriding `get_label_width`. Whether Atlas needs that, and
  what caps expansion depth, is unspecified.
- **Docs and release.** README, CHANGELOG, any ADR the seam decisions earn, and the
  `uv tool install --editable` redeploy.
- **Cache and invalidation layer.** Ticket 06 prescribes TTL plus explicit refresh
  plus subtree invalidation on Atlas's own mutations, in the shape rclone uses.
  Where that layer lives, what it keys on, and how conform and clean signal it.

## Out of scope

- **Portfolio dashboard.** A drive-wide home screen with health rollup, recent
  activity, and staleness. Ruled out at charting: the project list stays the
  landing surface.
- **Template copying.** Revit, Word, and spreadsheet template population at project
  creation. Already deferred by the intake work and not revisited here.
