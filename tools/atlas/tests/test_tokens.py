"""The token layer is the single source of truth for how Atlas looks.

Tests assert on structure, coverage and contrast - never on a literal hex. A test
that pins `#E2452A` breaks every time the palette is tuned and proves nothing; a
test that pins "every state a node can be in has a legible colour" survives
retuning and is the thing that actually matters.
"""

from __future__ import annotations

import pytest

from atlas.core.scan import PARTIAL, READ, UNREADABLE
from atlas.tui import tokens
from atlas.tui.tokens import (
    DRIFTED,
    FILING_STATES,
    LOAD_STATES,
    LOOSE,
    MAPPED,
    MISPLACED,
    UNFILED,
    contrast_ratio,
    filing_style,
    load_style,
    stylesheet,
)

PALETTE = tokens.PALETTE


# --------------------------------------------------------------- coverage


def test_every_filing_state_has_a_style():
    for state in FILING_STATES:
        style = filing_style(state)
        assert style.glyph, f"{state} has no glyph"
        assert style.colour.startswith("#"), f"{state} has no colour"
        assert style.label, f"{state} has no human label"


def test_every_load_state_has_a_disclosure_marker():
    for state in LOAD_STATES:
        assert load_style(state).suffix, f"{state} has no marker"


def test_only_a_fully_read_folder_goes_unannotated():
    """Read is the normal case and needs no words. Every other state says why."""
    assert load_style(READ).label == ""
    for state in (tokens.UNREAD, UNREADABLE, PARTIAL):
        assert load_style(state).label, f"{state} must explain itself"


def test_load_states_match_the_core_constants():
    """The token layer must not invent a second vocabulary for Load State."""
    assert set(LOAD_STATES) == {READ, UNREADABLE, PARTIAL, tokens.UNREAD}


def test_unknown_state_raises_rather_than_rendering_blank():
    with pytest.raises(KeyError):
        filing_style("not-a-state")


# ------------------------------------------------------------- the reading


def test_only_mapped_is_solid():
    """Solid versus hatched is what answers 'is anything wrong here'. ADR 0004."""
    assert filing_style(MAPPED).solid
    for state in (DRIFTED, MISPLACED, LOOSE, UNFILED):
        assert not filing_style(state).solid, f"{state} must not read as filed"


def test_atlas_fixable_states_share_one_colour():
    """Colour answers 'can Atlas fix it, or is it mine'."""
    fixable = {filing_style(s).colour for s in (DRIFTED, MISPLACED, LOOSE)}
    assert len(fixable) == 1
    assert filing_style(UNFILED).colour not in fixable
    assert filing_style(MAPPED).colour not in fixable


def test_unreadable_never_reads_as_empty():
    """The bug this whole model exists to prevent."""
    assert load_style(UNREADABLE).label.strip()
    assert load_style(UNREADABLE).label != load_style(READ).label


def test_no_two_filing_states_are_told_apart_by_colour_alone():
    """Ticket 10, and the reason it existed.

    Colour is allowed to reinforce a distinction. It is never allowed to be the
    only thing carrying one. Both widths are checked because the narrow row is
    where this failed: the word was dropped, and Drifted, Misplaced and Loose all
    collapsed onto one hatch in one hue - unreadable to anyone, not only to
    someone who cannot separate vermilion from ochre.
    """
    for wide, short in ((True, False), (False, True)):
        assert wide is not short
        seen: dict[tuple[str, str], str] = {}
        for state in FILING_STATES:
            style = filing_style(state)
            key = (style.glyph, style.short if short else style.label)
            assert key not in seen, (
                f"{state} and {seen[key]} render identically without colour "
                f"at {'narrow' if short else 'full'} width: {key}"
            )
            seen[key] = state


def test_every_state_that_needs_a_word_has_a_short_one():
    """Abbreviated, never dropped. Mapped is the exception and says nothing at
    either width, because 'nothing is wrong' is what a solid glyph already
    means."""
    assert filing_style(MAPPED).short == ""
    for state in (DRIFTED, MISPLACED, LOOSE, UNFILED):
        style = filing_style(state)
        assert style.short, f"{state} has no short form"
        assert len(style.short) < len(style.label), f"{state} does not abbreviate"


# ----------------------------------------------------------------- legible


def _text_tokens():
    return {
        "bone": PALETTE.bone,
        "ink": PALETTE.ink,
        "muted": PALETTE.muted,
        **{s: filing_style(s).colour for s in FILING_STATES},
        **{s: PALETTE.status[s] for s in PALETTE.status},
    }


@pytest.mark.parametrize("name", sorted(_text_tokens()))
def test_text_tokens_are_legible_on_the_ground(name):
    ratio = contrast_ratio(_text_tokens()[name], PALETTE.ground)
    assert ratio >= 4.5, f"{name} is {ratio:.2f}:1 against the ground, needs 4.5"


def test_structural_tokens_are_visible_but_recede():
    for name in ("rail", "dim"):
        ratio = contrast_ratio(getattr(PALETTE, name), PALETTE.ground)
        assert ratio >= 1.2, f"{name} is invisible at {ratio:.2f}:1"
        assert ratio < 4.5, f"{name} is structural and should not compete with text"


def test_the_cursor_is_the_brightest_thing_on_screen():
    ground = PALETTE.ground
    cursor = contrast_ratio(PALETTE.bone, ground)
    for name in ("ink", "muted"):
        assert cursor > contrast_ratio(getattr(PALETTE, name), ground)


# ------------------------------------------ every pair the console draws (#39)


def _rules() -> dict[str, dict[str, str]]:
    """The generated stylesheet as {selector: {property: value}}."""
    import re

    rules: dict[str, dict[str, str]] = {}
    css = re.sub(r"/\*.*?\*/", "", stylesheet(), flags=re.S)
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        props = {}
        for decl in body.split(";"):
            if ":" in decl:
                name, value = decl.split(":", 1)
                props[name.strip()] = value.strip()
        for selector in selectors.split(","):
            rules.setdefault(" ".join(selector.split()), {}).update(props)
    return rules


def _hex(value: str | None) -> str | None:
    import re

    found = re.search(r"#[0-9A-Fa-f]{6}", value or "")
    return found.group(0) if found else None


def _ground_of(selector: str, rules: dict[str, dict[str, str]]) -> str | None:
    """The background a selector's text is drawn on: its own, or the one it
    sits inside. Never assumed to be `ground` - that assumption is the bug.
    None when the container leaves it to the Textual theme."""
    own = _hex(rules.get(selector, {}).get("background"))
    if own:
        return own
    for container in ("#operation", "#dialog", "DataTable", "Tree", "#keys"):
        if selector.startswith(container) and selector != container:
            return _hex(rules.get(container, {}).get("background"))
    return _hex(rules["Screen"]["background"])


def _drawn_pairs():
    rules = _rules()
    pairs = []
    for selector, props in rules.items():
        colour = _hex(props.get("color"))
        if colour:
            pairs.append((selector, colour, _ground_of(selector, rules)))
    # Colours the tree and list set from Python, on the grounds the stylesheet
    # gives those widgets.
    for widget in ("Tree", "DataTable"):
        ground = _ground_of(widget + " >", rules)
        for state in FILING_STATES:
            pairs.append((f"{widget} {state}", filing_style(state).colour, ground))
        for name in ("ink", "muted"):
            pairs.append((f"{widget} {name}", getattr(PALETTE, name), ground))
        for status, colour in PALETTE.status.items():
            pairs.append((f"{widget} {status}", colour, ground))
    return pairs


def test_the_tree_and_list_are_painted_on_token_grounds():
    rules = _rules()
    for widget in ("Tree", "DataTable", "DataTable > .datatable--header", "#operation"):
        assert _hex(rules.get(widget, {}).get("background")), f"{widget} has no token ground"


@pytest.mark.parametrize("pair", _drawn_pairs(), ids=lambda p: p[0])
def test_every_text_pair_the_console_draws_is_legible(pair):
    """Ticket 18: every text token clears 4.5:1 - on what it is actually drawn
    on. ACTION passed against `ground` and measured 3.64:1 on the tree's theme
    surface."""
    name, fg, bg = pair
    assert bg, f"{name} is drawn on a Textual theme colour, not a token ground"
    ratio = contrast_ratio(fg, bg)
    assert ratio >= 4.5, f"{name}: {fg} on {bg} is {ratio:.2f}:1, needs 4.5"


def test_contrast_ratio_is_symmetric_and_bounded():
    assert contrast_ratio("#FFFFFF", "#000000") == pytest.approx(21.0, abs=0.05)
    assert contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.05)
    assert contrast_ratio("#777777", "#777777") == pytest.approx(1.0, abs=0.01)


# --------------------------------------------------------------- stylesheet


def test_stylesheet_is_generated_from_the_palette_not_written_twice():
    css = stylesheet()
    assert PALETTE.ground in css
    assert PALETTE.bone in css
    assert PALETTE.rail in css


def test_stylesheet_has_no_stray_colour_literals():
    """Every colour in the CSS must come from the palette."""
    import re

    known = {v.lower() for v in vars(PALETTE).values() if isinstance(v, str)}
    known |= {c.lower() for c in PALETTE.status.values()}
    known |= {filing_style(s).colour.lower() for s in FILING_STATES}
    known |= {c.lower() for c in PALETTE.ember}
    for found in re.findall(r"#[0-9A-Fa-f]{6}", stylesheet()):
        assert found.lower() in known, f"{found} is not a palette token"


def test_ember_ramp_runs_light_to_dark():
    lums = [tokens.relative_luminance(c) for c in PALETTE.ember]
    assert lums == sorted(lums, reverse=True), "the ramp must descend"


def test_the_disclosure_marker_follows_expansion_not_readness():
    """A folder can be Read and still closed - the Companion's Expectations pass
    reads every mapped section before the operator touches one. A triangle
    pointing down at a closed folder is a lie about the widget, not about Atlas."""
    assert tokens.disclosure(tokens.READ, expanded=False) == "\u25b8"
    assert tokens.disclosure(tokens.READ, expanded=True) == "\u25be"
    assert tokens.disclosure(tokens.UNREAD, expanded=False) == "\u25b8"


def test_a_folder_atlas_cannot_open_overrides_the_triangle():
    """Unreadable and Partial say something no triangle can, so they win."""
    assert tokens.disclosure(tokens.UNREADABLE, expanded=True) == "!"
    assert tokens.disclosure(tokens.PARTIAL, expanded=True) == "\u2026"
