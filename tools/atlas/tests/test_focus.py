"""Focus legibility everywhere (the last fog item from ticket 03).

With three Regions and a Tab that cycles them, which Region has focus must read
without moving the cursor - in Single-Region Composition too, where only one is
drawn. One token-layer rule covers every interactive surface: focused =
full-strength frame and title, unfocused = muted. The distinction is weight and
luminance - solid vs heavy, muted vs bold bone, rail vs ink - never hue alone
(ADR 0008), so it survives every colour vision. Tested by structure, never by
hex: the tokens behind the rules are free to be retuned.
"""

from __future__ import annotations

import pytest

from atlas.tui import tokens
from atlas.tui.app import AtlasApp
from atlas.tui.layout import COMPANION, PROJECT_LIST, TREE
from atlas.tui.tokens import contrast_ratio, stylesheet

from test_tokens import _hex, _rules

from conftest import make_project

PALETTE = tokens.PALETTE

# Every interactive surface that carries the Focus Rule: (rest selector, focus
# selector). Region frames, then the controls inside modals and overlays.
REGION_FRAMES = ("#projects", "#tree", "#companion", "#drives")
CONTROL_FRAMES = ("Input", "SelectCurrent")
FOCUS_VARIANTS = {
    "#projects": "#projects:focus-within",
    "#tree": "#tree:focus-within",
    "#companion": "#companion:focus-within",
    "#drives": "#drives:focus-within",
    "Input": "Input:focus",
    "SelectCurrent": "Select:focus > SelectCurrent",
}


def _border(rule: dict[str, str]) -> tuple[str, str]:
    """(style, colour) of a border declaration."""
    keyword, _, colour = (rule.get("border") or "").partition(" ")
    return keyword.strip(), _hex(colour) or ""


# ------------------------------------------------------- the token-layer rule


def test_every_interactive_surface_has_a_rest_and_a_focus_frame():
    rules = _rules()
    for selector in REGION_FRAMES + CONTROL_FRAMES:
        assert _border(rules.get(selector, {}))[0], f"{selector} has no rest frame"
        focused = rules.get(FOCUS_VARIANTS[selector], {})
        assert _border(focused)[0], f"{selector} has no focus frame"


def test_the_focus_distinction_is_weight_and_luminance_never_hue():
    """Colourblindness strips hue, not weight or brightness. The rest/focus
    frame pair must therefore differ in border weight (a shape) or clear a
    luminance gap with the hue removed - the tokens here do both, and the test
    holds whichever way a retune splits it."""
    rules = _rules()
    for selector in REGION_FRAMES + CONTROL_FRAMES:
        rest_style, rest_colour = _border(rules[selector])
        focus_style, focus_colour = _border(rules[FOCUS_VARIANTS[selector]])
        weight_differs = rest_style != focus_style
        luminance_gap = contrast_ratio(focus_colour, rest_colour)
        assert weight_differs or luminance_gap >= 2.0, (
            f"{selector}: rest and focus differ by hue alone "
            f"({rest_style}/{rest_colour} vs {focus_style}/{focus_colour})"
        )
        # The focused frame is always the full-strength one.
        assert contrast_ratio(focus_colour, PALETTE.ground) > contrast_ratio(
            rest_colour, PALETTE.ground), f"{selector}: the focused frame must out-read the rest"


def test_the_focused_region_frame_is_heavy_the_rest_is_solid():
    """solid vs heavy is the shape half of the rule: a monochrome terminal
    keeps it."""
    rules = _rules()
    for selector in REGION_FRAMES:
        assert _border(rules[selector])[0] == "solid"
        assert _border(rules[FOCUS_VARIANTS[selector]])[0] == "heavy"


def test_region_titles_follow_focus():
    """The Companion's title is muted at rest and full-strength - bone, bold -
    only while the Region holds focus. The Workspace title stays bone: it names
    the project, not a Region, and the Tree Region's frame carries its focus."""
    rules = _rules()
    assert rules["#companion-title"].get("color") and "bold" not in rules["#companion-title"].get("text-style", "")
    focused = rules["#companion:focus-within #companion-title"]
    assert "bold" in focused.get("text-style", "")
    rest = _hex(rules["#companion-title"]["color"])
    focus = _hex(focused["color"])
    assert contrast_ratio(focus, PALETTE.ground) > contrast_ratio(rest, PALETTE.ground)


def test_textual_default_focus_colours_do_not_leak_in():
    """The defaults these rules replace ($border, a 5% tint) are theme colours,
    not tokens - an Input without a rule here draws a frame nothing else owns."""
    rules = _rules()
    assert _hex(rules["Input"]["border"]), "unfocused inputs draw an untracked theme frame"
    assert rules["Input"].get("background"), "inputs sit on an untracked theme ground"


# ------------------------------------------------- the rule on screen

REGION_WIDGET = {PROJECT_LIST: "#projects", TREE: "#tree", COMPANION: "#companion"}


def border_styles(app) -> dict[str, str]:
    """Each Region container's border edge style as currently drawn."""
    return {
        region: app.query_one(widget).styles.border_top[0]
        for region, widget in REGION_WIDGET.items()
    }


@pytest.mark.parametrize("width", [179, 153, 120, 87, 77, 46])
async def test_the_focused_region_reads_at_every_measured_width(fixture_drive, width):
    """Tab through the Regions at one measured width; the focused Region's
    frame is heavy and every other drawn Region's is solid. At 87, 77 and 46
    the Composition is Single-Region - the one drawn Region is the focused one,
    and it still carries the heavy frame."""
    make_project(fixture_drive, "260501_Alpha", sections=["01 Model", "Meetings"])
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(width, 51)) as pilot:
        for _ in range(3):
            await app.workers.wait_for_complete()
            await pilot.pause()
        for _press in range(3):
            focused = app._focus_region
            styles = border_styles(app)
            assert styles[focused] == "heavy", (
                f"{width} cols: {focused} has focus but a {styles[focused]} frame: {styles}")
            for region, style in styles.items():
                widget = app.query_one(REGION_WIDGET[region])
                if region != focused and widget.display:
                    assert style == "solid", (
                        f"{width} cols: unfocused {region} drew {style}: {styles}")
            await pilot.press("tab")
            for _ in range(3):
                await app.workers.wait_for_complete()
                await pilot.pause()


@pytest.mark.parametrize("height", [30, 24])
async def test_the_focused_region_reads_at_the_measured_short_heights(fixture_drive, height):
    """Rows are abundant but not infinite: below 30 the summary merges onto the
    operation line. The frame rule owes nothing to rows and must hold."""
    make_project(fixture_drive, "260501_Alpha", sections=["01 Model", "Meetings"])
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, height)) as pilot:
        for _ in range(3):
            await app.workers.wait_for_complete()
            await pilot.pause()
        await pilot.press("tab")
        for _ in range(3):
            await app.workers.wait_for_complete()
            await pilot.pause()
        assert app._focus_region == TREE
        assert app.query_one("#tree").styles.border_top[0] == "heavy"
        assert app.query_one("#projects").styles.border_top[0] == "solid"


async def test_the_search_overlay_input_carries_the_rule(fixture_drive):
    """Modals and overlays used to show default Textual focus. The overlay's
    input now draws the token frame: full-strength while focused, muted once
    the results take over."""
    make_project(fixture_drive, "260501_Alpha", sections=["01 Model"])
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        for _ in range(3):
            await app.workers.wait_for_complete()
            await pilot.pause()
        await pilot.press("g")
        await pilot.pause()
        overlay = app.screen
        search_input = overlay.query_one("#search-input")
        assert search_input.has_focus
        assert search_input.styles.border_top[1] != search_input.styles.border_top[1].__class__.parse(PALETTE.dim)
        await pilot.press(*"Alpha")
        for _ in range(3):
            await app.workers.wait_for_complete()
            await pilot.pause()
        await pilot.press("down")       # into the results
        await pilot.pause()
        assert not search_input.has_focus
        assert search_input.styles.border_top[1] == search_input.styles.border_top[1].__class__.parse(PALETTE.dim)
