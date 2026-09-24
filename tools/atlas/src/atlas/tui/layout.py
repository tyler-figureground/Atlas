"""The console's layout rules: Regions, Compositions, and where keys go.

Pure. Given a terminal size and what the operator has collapsed, this decides
which Composition is in force and which Regions are drawn; given a Region, it
decides where Tab, Enter and Escape lead. ``app.py`` applies the answer and owns
nothing of the rule.

The sizes are measured, not assumed: ticket 03 read forty PTY resizes off the
agent runtime and found rows abundant and near-constant at 51, columns scarce and
trimodal, and eight of twelve distinct widths too narrow to hold two columns of
content. See ADR 0005.
"""

from __future__ import annotations

from dataclasses import dataclass

# The three Regions, in drill order: outermost first.
PROJECT_LIST = "projects"
TREE = "tree"
COMPANION = "companion"
REGIONS = (PROJECT_LIST, TREE, COMPANION)

# Compositions.
SPLIT = "split"
SINGLE = "single"
REFUSED = "refused"

# Breakpoints. The horizontal 100 is the one already declared in the app's
# HORIZONTAL_BREAKPOINTS and is reused deliberately; the wordmark's own 115 and 82
# are a different measurement of a different thing and stay independent.
SPLIT_COLUMNS = 100
MIN_COLUMNS = 40
MERGE_ROWS = 30
MIN_ROWS = 16

# Below this, a tree row abbreviates what is wrong with a folder instead of
# spelling it out (ticket 10). It approximates the Tree Region's own width, which
# the Composition decides: in Split the tree gets roughly half the terminal, in
# Single-Region nearly all of it, so no single number is right for both. 60 is
# the value that keeps the measured 87- and 77-column terminals spelling the word
# out - they are Single-Region, so the tree owns the width - while the 46-column
# case, the most common of all, abbreviates. Reusing SPLIT_COLUMNS here was the
# original bug: it stripped labels at 87 as though the tree were cramped.
ABBREVIATE_COLUMNS = 60

REFUSAL = "Atlas needs at least 40 columns and 16 rows."


@dataclass(frozen=True)
class Layout:
    """What to draw at one terminal size."""

    composition: str
    visible: tuple[str, ...]
    merge_status: bool = False
    refusal: str = ""


def layout_for(width: int, height: int, *, focus: str = PROJECT_LIST,
               collapsed: frozenset[str] | set[str] = frozenset(),
               zoomed: str | None = None) -> Layout:
    """The Composition a terminal of this size earns, and what it shows.

    An explicit collapse outranks the breakpoint default and is honoured until
    the width cannot carry it, at which point Single-Region takes over and the
    collapse is remembered rather than discarded.
    """
    if width < MIN_COLUMNS or height < MIN_ROWS:
        return Layout(composition=REFUSED, visible=(), refusal=REFUSAL)

    merge = height < MERGE_ROWS
    if zoomed is not None:
        return Layout(composition=SINGLE, visible=(zoomed,), merge_status=merge)
    if width < SPLIT_COLUMNS:
        return Layout(composition=SINGLE, visible=(focus,), merge_status=merge)
    shown = tuple(region for region in REGIONS if region not in collapsed)
    return Layout(composition=SPLIT, visible=shown or (focus,), merge_status=merge)


# ----------------------------------------------------------------- navigation
#
# The navigation model is identical in both Compositions, which is why none of
# these take a width. In Split Composition they move focus; in Single-Region they
# move focus and, because only the focused Region is drawn, also change what is
# on screen. No key changes meaning with width.


def next_region(current: str, *,
                collapsed: frozenset[str] | set[str] = frozenset()) -> str:
    """Where Tab goes from ``current``, skipping anything collapsed."""
    available = [region for region in REGIONS if region not in collapsed]
    if current not in available:
        return available[0] if available else current
    return available[(available.index(current) + 1) % len(available)]


def drill(current: str) -> str:
    """Where Enter goes: one Region deeper, stopping at the innermost."""
    index = REGIONS.index(current)
    return REGIONS[min(index + 1, len(REGIONS) - 1)]


def unwind(current: str) -> str | None:
    """Where Escape goes: one Region out, and ``None`` to leave the project."""
    index = REGIONS.index(current)
    return REGIONS[index - 1] if index else None


# ----------------------------------------------------------- Companion Modes

EXPECTATIONS = "expectations"
HEALTH = "health"
DOSSIER = "dossier"
MODES = (EXPECTATIONS, HEALTH, DOSSIER)

# Unmet Expectations is the default because it is the only mode that has to be
# readable at the same time as the tree - what is filed against what the map
# expects is the comparison the screen exists to make. Project health and the
# dossier are answers to questions the operator asks one at a time, which is what
# makes them modes rather than Regions (ADR 0005).
DEFAULT_MODE = EXPECTATIONS

MODE_LABELS = {
    EXPECTATIONS: "Unmet expectations",
    HEALTH: "Project health",
    DOSSIER: "Dossier",
}


def next_mode(current: str) -> str:
    """Where `d` goes."""
    return MODES[(MODES.index(current) + 1) % len(MODES)]


# ------------------------------------------------------------- the chrome

# What the footer keeps when there is no room for the rest: the keys that move.
# Everything else stays one `?` away, which is why `?` is one of the three.
NAVIGATION_ACTIONS = ("show_help_panel", "next_region", "drill")


def footer_actions(width: int) -> tuple[str, ...] | None:
    """Which bindings the footer may show; ``None`` means all of them.

    Reuses the Split breakpoint rather than introducing a third width constant.
    The cost is real - at 87 columns the action keys drop out of the footer even
    though the terminal is not tiny - and it is the price of not having a third
    set of numbers to keep in agreement.
    """
    return NAVIGATION_ACTIONS if width < SPLIT_COLUMNS else None


# ------------------------------------------------------ the Project List

# (key, header, content width). The project name's width is whatever is left.
LIST_COLUMNS = (
    ("mark", "Mark", 4),
    ("health", "Health", 6),
    ("project", "Project", 0),
    ("sections", "Sections", 8),
    ("fixes", "Fixes", 5),
    ("review", "Review", 6),
)
# What a narrowing list gives up, in order. Sections first - Health already says
# whether anything is missing - then the two counts, which the Companion's
# Project health mode spells out in full. Mark, Health and the name stay.
LIST_DROP_ORDER = (("sections",), ("fixes", "review"))
# The fewest cells a project name gets before another column is given up.
MIN_PROJECT_CELLS = 24
# DataTable's cell padding, both sides, and its vertical scrollbar.
_CELL_PADDING = 2
_SCROLLBAR = 2


def list_columns(width: int) -> tuple[tuple[str, ...], int]:
    """Which Project List columns fit ``width`` cells, and the name's share.

    Columns that do not fit are dropped rather than left to sit past the right
    edge, where the list clipped `Fixes` and `Review` at 120 columns and the
    header to `Revie` at 153.
    """
    keys = [key for key, _, _ in LIST_COLUMNS]
    content = {key: cells for key, _, cells in LIST_COLUMNS}

    def room(shown: list[str]) -> int:
        others = sum(content[k] + _CELL_PADDING for k in shown if k != "project")
        return width - _SCROLLBAR - others - _CELL_PADDING

    for dropped in LIST_DROP_ORDER:
        if room(keys) >= MIN_PROJECT_CELLS:
            break
        keys = [key for key in keys if key not in dropped]
    return tuple(keys), max(1, room(keys))


def list_width(width: int, layout: Layout) -> int:
    """How wide the Project List is drawn in ``layout``: its 2fr of Split, or
    all of it when it stands alone."""
    if layout.composition == SPLIT and len(layout.visible) > 1 and PROJECT_LIST in layout.visible:
        return width * 2 // 5
    return width


def summary_line(region: str, *, drive_summary: str, project: str,
                 companion_mode: str, companion_count: int) -> str:
    """One line answering for whichever Region has focus."""
    if region == COMPANION:
        label = MODE_LABELS.get(companion_mode, companion_mode)
        count = str(companion_count) if companion_count else "none"
        return f"{project} | {label}: {count}"
    if region == TREE:
        return f"{project} | tree"
    return drive_summary
