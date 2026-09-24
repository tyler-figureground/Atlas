# 7. The project tree is a lazily-expanding handle, Filing State below the root is containment, and a write reconciles by its manifest

Date: 2026-09-04

## Status

Accepted

Supersedes nothing. Consumes ADR 0004 (Filing State and Load State), ADR 0005
(the Regions the tree lives in), and ADR 0006 (the writes it offers).

## Context

Atlas's console needs a per-project folder tree. The TUI owns interaction and the
Textual widget; `atlas.core` owns filesystem facts. Nothing has connected the two,
and three earlier tickets constrain what the connection can be.

**Ticket 06 measured the read cost.** The whole studio drive is 7,956 folders and
walks in 4.24 seconds, so throughput is not the problem; the tail is. Cold p99 is
91 ms per enumeration and the worst observed is 314 ms. It also ruled out
filesystem watching over the Drive redirector, leaving TTL plus explicit refresh
plus invalidation on Atlas's own writes as the only honest staleness model.

**Ticket 05 measured the widget.** The TUI side is a plain `Tree`, because
`DirectoryTree` destroys injected nodes on reload and costs two `is_dir` stats per
entry that `os.scandir` gives away free. Critically, **Textual restores the tree
cursor by line number, not by node identity**, so any rebuild that changes the
child list silently moves the selection. And `TreeNode` has no re-parent API -
Textual discussion 6133 is open on exactly that - so a node cannot be moved from
one parent to another once built, which is a problem for a tool whose whole job is
moving folders.

**`doctor.report_project` only judges the project root.** It reads
`inv.root_entries` and nothing deeper. A tree that draws four levels needs a Filing
State for nodes the report has never seen, and ADR 0004 says a Tree Node has
exactly one.

## Decision

### Core hands the TUI a lazily-expanding handle

`atlas.core.tree.ProjectTree`. The TUI asks it for the children of one Node Key at
a time; it enumerates that one folder and caches the result. Immutable `TreeNode`
values come out, a mutable cache sits behind them - the division
`tui.model.ProjectRow` already makes between a stable value and the scan that
produced it, with a cache added because the tree is read repeatedly and the list is
not.

Not a whole node tree, which forces an eager walk that ticket 06 ruled out. Not a
flat list with depth, which bakes expansion state - TUI state - into a core
structure and turns every expand into a core round trip.

Nodes are regenerated on every read rather than mutated, so a folder that has since
been opened reports its Load State and Child Count the next time the TUI asks,
without anyone holding a stale value.

**The Node Key is the project-relative path**, forward-slashed, and it is the
stable identity the TUI re-resolves against after every rebuild. Listings come back
in a deterministic order - folders first, then files, each case-insensitively by
name - because with a line-number cursor an unstable order is a moved selection.

**Cancellation lives in the TUI.** Core is synchronous and every call is
side-effect free, so a worker abandoned mid-flight costs the read and nothing else.
Per ticket 05 those workers must not be `exclusive`, or one node's expansion
cancels every other in flight.

### Filing State below the root is decided by containment

A path the drive map names explicitly keeps its own verdict at any depth - that
covers nested relocation sources, which `report_project` already resolves. Below
that, containment decides: a node at or under a canonical path is **Mapped**, and a
node under an **Unfiled** one stays Unfiled.

The alternative readings both fail. Calling everything below the root Unfiled is
literal to ADR 0004's wording and would paint most of a real project as needing a
filing decision. Giving deep nodes no Filing State at all contradicts ADR 0004
outright. Containment needs no amendment to ADR 0004 and keeps the one property
that matters: a node nobody can explain never renders as accounted for.

The tree reads doctor's verdict rather than deriving one. One brain, the same rule
ADR 0006 applied to writes.

### Unmet Expectations are computed beside the tree, and only some are repairable

The not-on-disk list comes from the drive map and the root listing, never from the
tree structure - the tree is a filesystem mirror and an unmet Expectation is not a
node (ADR 0004). Computing it reads each mapped section that is present, which is
bounded by the number of sections in the map and is exactly the set of folders the
operator is about to expand.

ADR 0006 said an unmet Expectation is a BACKFILL. **That holds only for the control
plane.** Conform backfills `PROJECT.md`, `decisions`, `CLAUDE.md` and the analysis
directory; it has never created a mapped section, and `_apply_backfill` would
report an unknown control-plane item and skip. An Expectation therefore carries its
kind, and only a control-plane one offers a Repair. Missing sections keep the
existing add-folders path. Offering a repair Atlas will silently skip is worse than
offering none.

### Staleness is a 60-second TTL, explicit refresh, and invalidation by manifest

Ticket 06 ruled out watching, and ticket 12's budget already set 60 seconds. An
external change - someone else moving a folder on the shared drive - reaches the
tree when a listing's shelf life expires or when the operator refreshes, and never
any sooner. That is a real limitation and it is stated rather than hidden.

**After Atlas's own write, the tree reconciles by the Move Manifest.** ADR 0006
made every applied Action record every pair it moved; `reconcile` invalidates the
parent of each source and each destination and reports which. For a one-node repair
that is two enumerations - the same two directories the scoped Guard watched, so
the write and the rebuild cost the same pair twice rather than a subtree walk.

A project-wide conform invalidates the whole project instead. Its manifest can span
everything, and at that width rebuilding wholesale is the cheaper honest answer.
Invalidation strength scales with action scope, exactly as guard strength does.

Reconciliation also takes the freshly built `ProjectReport`, because a repair
changes what the map says about what is left. A tree still serving the pre-write
verdict would keep offering a repair that has already happened.

**The cursor follows what it repaired.** `follow(key, applied)` maps a pre-write
Node Key to its post-write one from the manifest - and, for a merge, from the
Action, since a merge moves children one at a time and nothing in the manifest
names the vanished folder itself. Without it, a rebuild lands the cursor on
whatever now occupies that line number.

### A failed or conflicted write gets no state of its own

Ticket 15 asked what the tree shows for a node whose plan came back Conflict or
Failed. Nothing new. A conflicted merge leaves the source in place with its
colliding children still in it, and the tree draws that truthfully because it is a
filesystem mirror. The outcome of a write is reported where ADR 0005 already put
write outcomes - the operation line and the Companion Region - not baked into a
Filing State, which is what the map says rather than what happened.

### No `atlas tree` command here

The seam is pure core and a CLI could sit on it without new logic. Whether one
should is ticket 10's question, along with search and the dossier, and this
decision does not pre-empt it.

## Consequences

The tree can serve a stale listing for up to 60 seconds, and a change made by
someone else on the shared drive is invisible until then. That is the cost of the
redirector ruling out watching, and the refresh key is the escape hatch.

Containment means a deep node's Filing State depends on an ancestor's, so a wrong
verdict at the root propagates down a whole subtree. It also means the verdict is
only as good as `report_project`, which still checks the project root only - the
deep-unreadable gap ticket 16 recorded is inherited here and stays open.

`expectations()` reads every present mapped section. On a project whose sections
are all cold that is up to one p99 enumeration each, paid the first time the
Companion draws. It is bounded by the map and it warms exactly what gets expanded
next, but it is not free and it is not lazy.

The Expectation-kind split means the Companion has two repair paths rather than
one, which is more surface than ADR 0006 anticipated. The alternative was a Backfill
that skips, which is worse.

`reconcile` trusts the manifest. An Action that changed the drive without recording
what it moved would leave the tree confidently wrong - which is the same property
that makes such an Action uninvertible, and `invert_plan` already refuses those.

## Corrections

Found by building the tree's write keys on top of this seam (ticket 23, session 9).
Both were found by rendering the flow, not by the suite.

**Reconcile missed the folder a merge consumed.** `reconcile` invalidated the
parent of every `Move` in the manifest. A merge moves children one at a time, so
every Move names a child and their parents are the two merged folders - never the
folder that just lost the source from its own listing. That folder's cached
listing kept an entry for a directory that no longer exists, and the tree drew a
row for it, as Mapped, because a fresh report has no complaint about a name that
is gone. A node that is not on disk is exactly what ADR 0004 rules out.

`follow` had the insight already and says so in its own comment - *nothing in the
manifest names the folder itself, which is now gone; the Action does*. `reconcile`
now invalidates the Action's own endpoints as well as its manifest's. For a plain
rename those are the same folders, so the cost is unchanged.

The suite could not have caught it: the TDD fixture had no pre-existing
`11 Meetings`, so its rename was never a merge.

**The Tree Region could not take keyboard focus at all.** Not a seam defect, but
it hid the one above. `_focus_current_region` focused the Region's container, and
`#tree` is a `Vertical` - which cannot take focus, so `focus()` silently did
nothing and the keyboard stayed on the project list. Arrow keys drove the project
list while the operator believed they were in the tree, and no binding the tree
widget declares was ever reachable by keyboard. Asserting on `_focus_region` or on
`display` cannot catch that; only asserting on which widget the keyboard is
actually talking to can.

Fixing it exposed two things the bug had been masking. Textual's `Tree` binds
`enter` to `select_cursor`, and a widget binding beats an App one, so the tree took
Atlas's drill key the moment it could hold focus - `enter` is `priority=True` now,
for the same reason `tab` already was. And Textual leaves `cursor_line` at -1 until
an arrow key moves it, so a freshly drilled tree had focus, rows, and no cursor,
which made the repair key silently inert on arrival.
