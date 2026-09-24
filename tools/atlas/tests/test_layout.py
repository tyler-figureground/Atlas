"""The console's layout rules (ticket 20, ADR 0005).

Pure: which Composition a terminal size earns, which Regions are drawn, where
navigation goes. No Textual. The measured widths from ticket 03 - 179, 153, 120,
87, 77, 46 - and the measured rows - 51, 30, 24 - are the sizes under test,
because they are the sizes the operator actually works at.
"""

from __future__ import annotations

import pytest

from atlas.tui.layout import (
    COMPANION,
    DEFAULT_MODE,
    DOSSIER,
    EXPECTATIONS,
    HEALTH,
    MODE_LABELS,
    MODES,
    PROJECT_LIST,
    REFUSED,
    SINGLE,
    SPLIT,
    REGIONS,
    TREE,
    drill,
    footer_actions,
    layout_for,
    next_mode,
    next_region,
    summary_line,
    unwind,
)

MEASURED_WIDTHS = (179, 153, 120, 87, 77, 46)


@pytest.mark.parametrize("width", (179, 153, 120, 100))
def test_a_wide_terminal_earns_the_split_composition(width):
    layout = layout_for(width, 51)
    assert layout.composition == SPLIT
    assert layout.visible == (PROJECT_LIST, TREE, COMPANION)


@pytest.mark.parametrize("width", (99, 87, 77, 46, 40))
def test_a_narrow_terminal_draws_one_region(width):
    """Not a degraded fallback. Eight of the twelve widths ticket 03 measured
    cannot hold two columns of content, so this is the common case."""
    layout = layout_for(width, 51)
    assert layout.composition == SINGLE
    assert layout.visible == (PROJECT_LIST,)


@pytest.mark.parametrize("size", ((39, 51), (46, 15), (20, 10)))
def test_below_the_floor_atlas_asks_for_more_space(size):
    """Drawing something false is worse than drawing one honest line."""
    layout = layout_for(*size)
    assert layout.composition == REFUSED
    assert layout.visible == ()
    assert layout.refusal


def test_summary_and_operation_merge_when_rows_run_out():
    """Three fixed chrome rows plus a Workspace title cost four of about 44
    usable rows. Affordable at 51, not at 24."""
    assert not layout_for(120, 51).merge_status
    assert not layout_for(120, 30).merge_status
    assert layout_for(120, 29).merge_status
    assert layout_for(120, 24).merge_status


def test_an_explicit_collapse_outranks_the_breakpoint_default():
    """At a width that would show all three, a collapsed Region stays hidden."""
    layout = layout_for(179, 51, collapsed={COMPANION})
    assert layout.composition == SPLIT
    assert layout.visible == (PROJECT_LIST, TREE)


def test_zoom_is_single_region_at_any_width():
    layout = layout_for(179, 51, zoomed=TREE)
    assert layout.composition == SINGLE
    assert layout.visible == (TREE,)


def test_a_width_that_cannot_carry_the_collapse_takes_over_without_forgetting_it():
    """Sticky for the session: narrowing does not clear what was collapsed, it
    just stops being the thing that decides."""
    collapsed = {COMPANION}
    assert layout_for(87, 51, collapsed=collapsed).visible == (PROJECT_LIST,)
    assert layout_for(120, 51, collapsed=collapsed).visible == (PROJECT_LIST, TREE)


# ------------------------------------------------------------- navigation


def test_tab_cycles_the_regions():
    assert next_region(PROJECT_LIST) == TREE
    assert next_region(TREE) == COMPANION
    assert next_region(COMPANION) == PROJECT_LIST


def test_tab_skips_a_collapsed_region():
    assert next_region(PROJECT_LIST, collapsed={TREE}) == COMPANION
    assert next_region(TREE, collapsed={COMPANION}) == PROJECT_LIST


def test_enter_drills_toward_the_tree_and_escape_unwinds_to_the_drive_picker():
    assert drill(PROJECT_LIST) == TREE
    assert drill(TREE) == COMPANION
    assert drill(COMPANION) == COMPANION, "nothing deeper to drill into"

    assert unwind(COMPANION) == TREE
    assert unwind(TREE) == PROJECT_LIST
    assert unwind(PROJECT_LIST) is None, "out of the project, back to the drives"


def test_navigation_is_identical_in_both_compositions():
    """No key changes meaning with width. In Split the keys move focus; in
    Single-Region they move focus and also change what is drawn."""
    def walk(width):
        focus, seen = PROJECT_LIST, []
        for _ in range(len(REGIONS)):
            focus = next_region(focus)
            seen.append((focus, layout_for(width, 51, focus=focus).visible))
        return [f for f, _visible in seen]

    assert walk(179) == walk(46) == [TREE, COMPANION, PROJECT_LIST]
    assert layout_for(179, 51, focus=TREE).visible == REGIONS
    assert layout_for(46, 51, focus=TREE).visible == (TREE,)


# -------------------------------------------------------- Companion Modes


def test_the_companion_cycles_three_modes_and_starts_on_expectations():
    """Unmet Expectations is the default because it is the only one that has to
    be readable at the same time as the tree (ADR 0005)."""
    assert DEFAULT_MODE == EXPECTATIONS
    assert next_mode(EXPECTATIONS) == HEALTH
    assert next_mode(HEALTH) == DOSSIER
    assert next_mode(DOSSIER) == EXPECTATIONS


def test_every_mode_has_a_label():
    assert {mode: MODE_LABELS[mode] for mode in MODES} == {
        EXPECTATIONS: "Unmet expectations",
        HEALTH: "Project health",
        DOSSIER: "Dossier",
    }


# ------------------------------------------------------------ the footer


def test_a_narrow_footer_keeps_only_the_keys_that_move():
    """At 46 columns - the single most common measured width - there is room for
    navigation and nothing else. The full list stays one keypress away in help."""
    assert footer_actions(46) == ("show_help_panel", "next_region", "drill")
    assert footer_actions(87) == ("show_help_panel", "next_region", "drill")
    assert footer_actions(100)[:3] == ("show_help_panel", "next_region", "drill")
    assert footer_actions(120) is None
    assert footer_actions(179) is None


# ------------------------------------------------------- the summary line


def test_the_summary_line_answers_for_the_region_that_has_focus():
    parts = dict(drive_summary="14 projects | 9 ready",
                 project="260401_Demo", companion_mode=EXPECTATIONS,
                 companion_count=3)

    assert summary_line(PROJECT_LIST, **parts) == "14 projects | 9 ready"
    assert "260401_Demo" in summary_line(TREE, **parts)
    companion = summary_line(COMPANION, **parts)
    assert "Unmet expectations" in companion and "3" in companion


def test_the_summary_line_says_when_a_mode_has_nothing_to_show():
    """A zero is a fact worth reading - it is the difference between a project
    that meets the map and one Atlas has not looked at."""
    line = summary_line(COMPANION, drive_summary="", project="260401_Demo",
                        companion_mode=EXPECTATIONS, companion_count=0)
    assert "Unmet expectations" in line and "none" in line.casefold()
