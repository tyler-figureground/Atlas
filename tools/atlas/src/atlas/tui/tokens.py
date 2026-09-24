"""The single source of truth for how Atlas looks.

Python owns the palette and the CSS is generated from it, not the other way
round. That direction is forced: Textual tree nodes are not DOM nodes and take no
CSS at all, so ``render_label`` has to read colours and glyphs from Python. Having
the stylesheet own them too would guarantee drift between the tree and everything
around it.

The world is POCHE with an EMBER ramp (ticket 02). Solid mass is a folder filed
correctly; hatched is a folder with something wrong. Colour then answers whether
Atlas can fix it or a person has to decide. See ADR 0004 for the state model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.scan import PARTIAL, READ, UNREADABLE

# ------------------------------------------------------------- Filing State
# Per ADR 0004. Resolved by the first map rule that matches, in the order
# conform applies them, with UNFILED as the fallthrough.

MAPPED = "mapped"
DRIFTED = "drifted"
MISPLACED = "misplaced"
LOOSE = "loose"
UNFILED = "unfiled"

FILING_STATES = (MAPPED, DRIFTED, MISPLACED, LOOSE, UNFILED)

# Load State. READ / UNREADABLE / PARTIAL come from core so there is exactly one
# vocabulary; UNREAD is presentation-only, since core never hands back a folder
# it has not looked at.
UNREAD = "unread"
LOAD_STATES = (UNREAD, READ, UNREADABLE, PARTIAL)


# ------------------------------------------------------------------ palette


@dataclass(frozen=True)
class Palette:
    """One visual world. A second (the rejected PAPER light ground) would be
    another instance of this, which is why it is a dataclass and not module
    constants."""

    name: str

    ground: str
    surface: str
    rail: str

    bone: str   # the cursor, and nothing else
    ink: str    # field text
    muted: str  # secondary text
    dim: str    # structure that must recede

    # crown to base; the wordmark samples this and the accents are drawn from it
    ember: tuple[str, ...]

    # project-level statuses, unchanged by ADR 0004
    status: dict[str, str] = field(default_factory=dict)


POCHE = Palette(
    name="poche",
    ground="#0C0C0D",
    surface="#141414",
    rail="#302C27",
    bone="#F4F0E6",
    ink="#B5AFA4",
    muted="#96907F",
    dim="#5A554D",
    ember=("#FFE7BC", "#F6C25A", "#EE8A2B", "#E2452A", "#A8250F", "#5E1206"),
    status={
        "READY": "#8AA37A",
        "ACTION": "#E2452A",
        "REVIEW": "#D9A441",
        "SETUP": "#C79A6B",
    },
)

PALETTE = POCHE


# ------------------------------------------------------------------ styles


@dataclass(frozen=True)
class FilingStyle:
    glyph: str
    colour: str
    label: str
    short: str
    solid: bool


@dataclass(frozen=True)
class LoadStyle:
    label: str
    suffix: str
    # What the row says when the width runs out. Never shortened into
    # ambiguity: "cannot read" keeps every word, because unreadable must never
    # read as empty (ticket 16).
    short: str = ""


_SOLID = "█"
_HATCH = "▚"

# Atlas-fixable states deliberately share one colour and one glyph. The specific
# state name lives in the node label, so someone who opens Atlas twice a month
# reads "something is wrong and Atlas can handle it" without a legend.
_FIXABLE = PALETTE.status["ACTION"]

# Every state carries a short form as well as a long one (ticket 10). The row
# abbreviates when the width runs out; it never goes silent. Dropping the word
# left four of five states rendering the identical hatch, separated only by hue -
# vermilion against ochre, which measures 1.82:1 and is the red/green confusion
# axis besides. Colour reinforces the word here. It never carries it alone.
#
# Caps because these read as tokens rather than as clipped prose, and because the
# project list already names its statuses that way.
_FILING: dict[str, FilingStyle] = {
    MAPPED: FilingStyle(_SOLID, PALETTE.status["READY"], "filed", "", solid=True),
    DRIFTED: FilingStyle(_HATCH, _FIXABLE, "wrong name", "NAME", solid=False),
    MISPLACED: FilingStyle(_HATCH, _FIXABLE, "wrong place", "PLACE", solid=False),
    LOOSE: FilingStyle(_HATCH, _FIXABLE, "not filed yet", "LOOSE", solid=False),
    UNFILED: FilingStyle(_HATCH, PALETTE.status["REVIEW"], "not in the map", "UNMAPPED",
                         solid=False),
}

# Never blank, and never a zero: an Unread folder showing "0 files" would be the
# same false negative as an unreadable folder showing as empty.
_LOAD: dict[str, LoadStyle] = {
    UNREAD: LoadStyle("not opened yet", "▸", "unread"),
    READ: LoadStyle("", "▾", ""),
    UNREADABLE: LoadStyle("cannot read", "!", "cannot read"),
    PARTIAL: LoadStyle("partial", "…", "partial"),
}


def filing_style(state: str) -> FilingStyle:
    return _FILING[state]


def load_style(state: str) -> LoadStyle:
    return _LOAD[state]


def disclosure(state: str, *, expanded: bool) -> str:
    """The marker at the head of a folder's detail.

    Readness and expansion are different facts and they were sharing one glyph.
    A folder can be Read and still closed - the Companion reads every mapped
    section before the operator opens one - so the triangle follows the widget.
    Unreadable and Partial override it, because they say something no triangle
    can and the direction is the less useful of the two.
    """
    if state in (UNREADABLE, PARTIAL):
        return _LOAD[state].suffix
    return _LOAD[READ].suffix if expanded else _LOAD[UNREAD].suffix


def child_count(folders: int, files: int, *, narrow: bool = False) -> str:
    """Immediate children only, folders and files apart (ticket 13).

    Callers pass this only for a folder whose Load State is READ; there is no
    count to render for one Atlas has not opened.
    """
    if narrow:
        return f"{folders}F {files}"
    parts = []
    if folders:
        parts.append(f"{folders} folder" + ("s" if folders != 1 else ""))
    if files:
        parts.append(f"{files} file" + ("s" if files != 1 else ""))
    return ", ".join(parts) if parts else "empty"


# ----------------------------------------------------------------- contrast


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(colour: str) -> float:
    h = colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# --------------------------------------------------------------- stylesheet


def stylesheet(palette: Palette = PALETTE) -> str:
    """Textual CSS generated from the palette. Never hand-edit colours here."""
    p = palette
    return f"""
    Screen {{ background: {p.ground}; color: {p.ink}; }}
    Header {{ background: {p.surface}; color: {p.bone}; }}
    Footer {{ background: {p.surface}; color: {p.muted}; }}

    ModalScreen {{ align: center middle; }}
    #dialog {{
        width: 76; max-width: 94%; max-height: 88%; padding: 1 2;
        background: {p.surface}; border: thick {p.ember[3]};
    }}
    #dialog .dialog-title {{ text-style: bold; color: {p.bone}; }}
    #dialog .field-label {{ color: {p.muted}; }}
    #dialog Input {{ margin-bottom: 1; }}
    #dialog.intake-dialog Input {{ margin-bottom: 0; }}
    #dialog.intake-dialog .field-label {{ height: 1; }}
    #dialog SelectionList {{ max-height: 18; margin-bottom: 1; }}
    #dialog.selection-dialog {{ height: 80%; min-height: 12; }}
    #dialog.selection-dialog SelectionList {{ height: 1fr; max-height: 1fr; }}
    #dialog #plan {{ max-height: 22; margin-bottom: 1; }}
    #dialog .actions {{ height: 3; align-horizontal: right; }}
    #dialog Button {{ margin-left: 2; }}
    #dialog #preview, #dialog .supporting {{ color: {p.muted}; margin-bottom: 1; }}

    #workspace {{ border-left: solid {p.rail}; }}
    #workspace-title {{ color: {p.bone}; text-style: bold; }}
    #companion {{ border-top: solid {p.rail}; }}
    #companion-title {{ color: {p.bone}; text-style: bold; }}
    #refusal {{ color: {p.muted}; }}
    #keys {{ background: {p.surface}; color: {p.muted}; }}
    #summary {{ color: {p.muted}; }}
    #operation {{ background: {p.surface}; color: {p.ink}; }}
    #operation.-warning {{ color: {p.status["REVIEW"]}; }}
    /* ACTION measures 4.49:1 on surface - under the floor by a hair. The ramp's
       next step up is the same warm family and clears it. */
    #operation.-error {{ color: {p.ember[2]}; }}

    /* The tree and list draw their text in token colours from Python, so they
       sit on a token ground too. Left to the Textual theme they drew on its
       surface (and a 5% focus tint), where ACTION fell to 3.64:1. Hover is
       painted the same, because a hover band is one more ground under the
       same text. */
    Tree {{ background: {p.ground}; color: {p.ink}; }}
    Tree:focus {{ background-tint: {p.ground} 0%; }}
    Tree > .tree--highlight-line {{ background: {p.ground}; }}
    DataTable {{ background: {p.ground}; color: {p.ink}; }}
    DataTable:focus {{ background-tint: {p.ground} 0%; }}
    DataTable > .datatable--header {{ background: {p.ground}; color: {p.muted}; }}
    DataTable > .datatable--header-hover {{ background: {p.ground}; }}
    DataTable > .datatable--hover {{ background: {p.ground}; }}
    DataTable > .datatable--even-row {{ background: {p.ground}; }}
    DataTable > .datatable--odd-row {{ background: {p.ground}; }}
    DataTable > .datatable--cursor {{ background: {p.ember[2]}; color: {p.ground}; }}
    Tree > .tree--cursor {{ background: {p.ember[2]}; color: {p.ground}; text-style: bold; }}
    DataTable > .datatable--header {{ color: {p.muted}; }}
    """
