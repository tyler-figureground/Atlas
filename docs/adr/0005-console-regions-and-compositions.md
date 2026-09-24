---
title: "5. The console is three Regions in two Compositions, and the narrow one is the common case"
date: 2026-09-03
generated_by: skills-for-architects
---

# 5. The console is three Regions in two Compositions, and the narrow one is the common case

Date: 2026-09-03

## Status

Accepted

## Context

Atlas is growing a per-project folder tree alongside the project list it already
has, plus a dossier panel and a drive-wide search. The question was where each of
those lives on screen and how the arrangement responds to terminal size.

The effort had been designing against 132x38, with 80x24 as the floor. Those
numbers were assumed, never measured. They are wrong.

Herdr - the agent runtime the studio now works in daily - records every PTY resize
it performs. Forty resize events on the development machine give this
distribution:

- **Columns:** 46 (9 events), 77 (8), 153 (7), 179 (3), 87/88 (3), 120 (2), then
  one each of 80, 57, 48, 39.
- **Rows:** 51 in 33 of 40 events, 52 in 3, then one each of 40, 30, 24.

Windows Terminal contributes 120x30, its default, with no size override in
`settings.json`.

Two facts fall out, and both invert the assumption the design was built on.

**Rows are abundant and nearly constant; columns are scarce and trimodal.** The
console reliably has around 51 rows and unreliably has anywhere from 39 to 179
columns. Vertical space is the resource Atlas has. Horizontal space is the one it
does not.

**Eight of the twelve distinct measured widths cannot hold two columns of
content.** A useful tree needs roughly 44 columns for indentation, a status glyph,
a name, and a child count; a useful project list needs roughly 40. Side by side
that is ~90 before either is being served. The narrow arrangement is therefore not
a degraded fallback for an unusual terminal - it is the arrangement in force most
of the time.

A third pressure came from ADR 0004, which ruled that an unmet map Expectation is
not a Tree Node and must be listed beside the tree rather than drawn inside it. A
project view is consequently already two areas, not one, before the project list
is considered at all.

## Decision

The console is **three Regions** - Project List, Tree Region, Companion Region -
arranged in **two Compositions**, with a refusal below a floor.

**The Companion Region sits under the Tree Region, not beside it.** The two of
them plus a title form the Workspace, which occupies one column opposite the
Project List. This spends rows, of which there are 51, to save columns, of which
there are often 46. A three-column arrangement was the obvious reading of ADR 0004
and is rejected: it needs ~150 columns to breathe and is unusable at 77.

The rejected alternative worth remembering is making unmet Expectations a *mode*
of a single right-hand Region. That fits any width, but it hides the one
comparison the screen exists to make - what is filed against what the map expects
- behind a keystroke. Simultaneity with the tree is the requirement that
distinguishes unmet Expectations from project health and the dossier, and it is
why those two are modes and this one is not.

**Split Composition** at 100 columns and above: Project List and Workspace side by
side, `2fr` to `3fr`. **Single-Region Composition** from 40 to 99: exactly one
Region visible, the others hidden rather than shrunk. Below 40 columns, or below
16 rows, Atlas draws one line asking for more space rather than drawing something
false.

The 100 is the breakpoint already declared in `HORIZONTAL_BREAKPOINTS`, reused
deliberately. The wordmark already owns 115 and 82 from ADR-adjacent work on
ticket 02; a third set of width constants was not worth the confusion.

**The navigation model is identical in both Compositions.** Enter drills toward
the tree, Escape unwinds toward the drive picker, Tab moves to the next Region,
and `/` filters whichever Region has focus. In Split Composition those keys move
focus. In Single-Region Composition they move focus and also change what is drawn.
No key changes meaning with width.

**An explicit collapse outranks the breakpoint default** and is sticky for the
session, overridden only when the width cannot honour it.

**The Workspace tracks the Project List cursor**, debounced, with cache hits
exempt, so the tree is populated at first paint and after every cursor rest rather
than on a keystroke.

## Consequences

Every surface added after this inherits the Region model, which is why the
decision is recorded rather than left in the ticket. The tree seam and the dossier
panel both land inside it.

The existing `#detail` pane is replaced by the Companion Region, and
`action_inspect`'s health modal becomes a Companion Mode. That reclaims Enter,
which the tree needs, and removes a modal that was standing in for a panel.

Single-Region Composition is a real arrangement to build and test, not a
degradation to tolerate. Treating it as the primary case is the point of this ADR;
a verification pass that only exercises Split Composition is testing the minority
of actual sessions. The verification widths for this effort become the measured
ones - 179, 153, 120, 87, 77, 46 - rather than 132x38 and 80x24.

Three fixed chrome rows plus a Workspace title cost four of roughly 44 usable
rows. That is affordable at 51 rows and is not at 24, which is why summary and
operation merge below 30 rows.

The measured distribution is one machine over one period, and Herdr is new to the
studio's workflow. If the pane habits change materially, the breakpoints are cheap
to move; the Region model and the constant-navigation rule are not.

## Note, 2026-09-23: what `/` filters in each Region

Built in #41. `/` filters the Project List by project name or health, and the Tree
Region by the names of the nodes Atlas has already opened - never by reading
further, because a filter that walked the project to find a name would be the
enumeration ticket 06 rules out, one keystroke at a time.

In the Companion Region `/` does not filter. It says, on the operation line, that
it filters the list or the tree. The Companion's lists are a handful of lines, and
acting on a Region the operator is not looking at - the old behaviour, which
filtered the hidden Project List - is the failure this ADR's navigation rule
exists to prevent. This is a deliberate narrowing of "`/` filters whichever Region
has focus", not an oversight; revisit it if a Companion Mode grows long enough to
need one.
