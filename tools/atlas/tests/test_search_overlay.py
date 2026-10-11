"""The Search Overlay (ticket 33; the ADR 0005 amendment: an overlay, not a Region).

Opened with `g`, live over the session Name Index, dismissed with Escape leaving
Region focus and collapse exactly as they were. Enter reveals the hit - the node
in the tree, the project in the list - and `o` opens the file. Rendered headless
at the measured widths: 179, 153, 120, 87, 77, 46 columns; 51, 30, 24 rows.
"""

from __future__ import annotations

from textual.widgets import DataTable, Input, OptionList, Static

from atlas.core.search import build_name_index
from atlas.tui.app import AtlasApp
from atlas.tui.layout import PROJECT_LIST, TREE, search_overlay_cells, search_overlay_width
from atlas.tui.search import SearchOverlay
from atlas.tui.treeview import ProjectTreeView

from conftest import make_project

# The measured terminals (map.md): columns trimodal, rows near-constant at 51.
WIDTHS = (179, 153, 120, 87, 77, 46)
ROWS = (51, 30, 24)


async def settle(app, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def _drive(drive):
    make_project(drive, "260813_Alpha",
                 sections=["01 Model", "06 Research/Code"],
                 files={"01 Model/site model.rvt": "x",
                        "06 Research/Code/zoning notes.md": "z"})
    make_project(drive, "260901_Beta", sections=["01 Model"],
                 files={"01 Model/model notes.txt": "n"})


def _overlay(app) -> SearchOverlay:
    assert isinstance(app.screen, SearchOverlay), f"overlay not open: {app.screen!r}"
    return app.screen


def _result_rows(overlay: SearchOverlay) -> list[str]:
    options = overlay.query_one("#search-results", OptionList)
    return [options.get_option_at_index(i).prompt.plain for i in range(options.option_count)]


def _status(overlay: SearchOverlay) -> str:
    return str(overlay.query_one("#search-status", Static).content)


def _drawn_results(overlay: SearchOverlay) -> list[str]:
    """The result rows as they actually reach the screen."""
    options = overlay.query_one("#search-results", OptionList)
    return ["".join(seg.text for seg in options.render_line(y))
            for y in range(options.size.height)]


# ------------------------------------------------------------- open and close


async def test_g_opens_the_overlay_and_escape_hands_the_screen_back_untouched(fixture_drive):
    """The overlay is episodic: it takes the screen while open and disturbs
    nothing underneath - not the Region focus, not a collapse, not the cursor."""
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")          # drill to the tree
        await settle(app, pilot)
        await pilot.press("right_square_bracket")   # collapse the Companion
        await settle(app, pilot)
        assert app._focus_region == TREE and app._collapsed == {"companion"}

        await pilot.press("g")
        await settle(app, pilot)
        overlay = _overlay(app)
        assert overlay.query_one("#search-input", Input).has_focus

        await pilot.press("escape")
        await settle(app, pilot)
        assert not isinstance(app.screen, SearchOverlay)
        assert app._focus_region == TREE
        assert app._collapsed == {"companion"}


async def test_g_is_not_offered_before_a_drive_is_open(tmp_path):
    app = AtlasApp(tmp_path, follow_debounce=0)
    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("g")
        await settle(app, pilot)
        assert not isinstance(app.screen, SearchOverlay)


# ------------------------------------------------------------- live narrowing


async def test_typing_narrows_live_against_the_warm_index(fixture_drive):
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        assert app._name_index is not None, "the walk ran at session start"
        await pilot.press("g")
        await settle(app, pilot)
        overlay = _overlay(app)

        await pilot.press(*"model")
        await settle(app, pilot)
        rows = _result_rows(overlay)
        assert any("site model.rvt" in row for row in rows), rows
        assert any("model notes.txt" in row for row in rows), rows

        await pilot.press(*" notes")
        await settle(app, pilot)
        rows = _result_rows(overlay)
        assert len(rows) == 1 and "model notes.txt" in rows[0], rows
        assert "1 match" in _status(overlay)


async def test_no_results_is_one_honest_line(fixture_drive):
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(87, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("g")
        await pilot.press(*"zzz nothing")
        await settle(app, pilot)
        overlay = _overlay(app)
        assert _status(overlay) == "No matches for 'zzz nothing'."
        assert overlay.query_one("#search-results", OptionList).option_count == 0


async def test_an_index_still_building_says_so(fixture_drive):
    """The loading state: the overlay never blocks on the walk, so while the
    index is being built it says so instead of pretending there are no hits."""
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        app.push_screen(SearchOverlay(None))
        await settle(app, pilot)
        overlay = _overlay(app)
        assert "indexing" in _status(overlay).casefold()

        # An index landing while the overlay is open warms it in place.
        overlay.set_index(build_name_index(fixture_drive))
        await pilot.press("x")
        await settle(app, pilot)
        assert "indexing" not in _status(overlay).casefold()


# ------------------------------------------------------------- the actions


async def test_enter_reveals_a_deep_hit_in_the_tree(fixture_drive):
    """Enter on a result selects the project, opens the folders leading to the
    hit - never opened before - and lands the tree cursor on the node."""
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("g")
        await pilot.press(*"zoning")
        await settle(app, pilot)
        await pilot.press("enter")      # from the input: the highlighted hit
        await settle(app, pilot)

        assert not isinstance(app.screen, SearchOverlay)
        assert app._workspace_project == "260813_Alpha"
        assert app._focus_region == TREE
        tree = app.query_one(ProjectTreeView)
        facts = tree.selected_facts()
        assert facts is not None
        assert facts.key == "06 Research/Code/zoning notes.md"
        # The folders leading to it were opened to get there.
        assert tree.node_for("06 Research").is_expanded
        assert tree.node_for("06 Research/Code").is_expanded


async def test_enter_from_the_results_list_reveals_too(fixture_drive):
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("g")
        await pilot.press(*"zoning")
        await settle(app, pilot)
        await pilot.press("down", "enter")      # into the list, then pick
        await settle(app, pilot)
        assert not isinstance(app.screen, SearchOverlay)
        facts = app.query_one(ProjectTreeView).selected_facts()
        assert facts is not None and facts.key.endswith("zoning notes.md")


async def test_enter_on_a_project_hit_selects_the_project_in_the_list(fixture_drive):
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("g")
        await pilot.press(*"beta")
        await settle(app, pilot)
        overlay = _overlay(app)
        # The path is searchable, so "beta" names everything inside Beta too;
        # the project itself is the first, highlighted hit.
        rows = _result_rows(overlay)
        assert rows[0] == "folder  260901_Beta" and len(rows) == 3, rows
        await pilot.press("enter")
        await settle(app, pilot)

        assert not isinstance(app.screen, SearchOverlay)
        assert app._focus_region == PROJECT_LIST
        row = app._selected_row()
        assert row is not None and row.key == "260901_Beta"
        table = app.query_one("#projects", DataTable)
        assert app._visible_rows[table.cursor_row].key == "260901_Beta"


async def test_reveal_finds_a_project_the_list_filter_hid(fixture_drive):
    """A hit is in a project whether or not the list is filtered to show it."""
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("slash")
        await pilot.press(*"alpha")     # the list now hides Beta
        await settle(app, pilot)
        await pilot.press("escape")     # filter kept, focus back on the list
        await settle(app, pilot)

        await pilot.press("g")
        await pilot.press(*"model notes")
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        row = app._selected_row()
        assert row is not None and row.key == "260901_Beta"
        assert app.query_one("#filter", Input).value == ""


async def test_o_opens_the_hit_without_touching_the_tree(fixture_drive, monkeypatch):
    opened = []
    monkeypatch.setattr("atlas.tui.app.open_path", opened.append)
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("g")
        await pilot.press(*"zoning")
        await settle(app, pilot)
        await pilot.press("down")     # out of the input, into the results
        await pilot.press("o")
        await settle(app, pilot)

        assert not isinstance(app.screen, SearchOverlay)
        assert len(opened) == 1
        assert opened[0].name == "zoning notes.md"
        assert app._focus_region == PROJECT_LIST, "open disturbs no focus"


# ------------------------------------------------------------- the cap


async def test_the_overflow_is_counted(fixture_drive):
    _drive(fixture_drive)
    index = build_name_index(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        app.push_screen(SearchOverlay(index, cap=2))
        await settle(app, pilot)
        overlay = _overlay(app)
        await pilot.press(*"model")
        await settle(app, pilot)
        assert overlay.query_one("#search-results", OptionList).option_count == 2
        status = _status(overlay)
        assert "4 matches" in status and "2 more" in status, status


# ------------------------------------------------------------- headless renders


async def test_the_overlay_is_legible_at_the_measured_widths(fixture_drive):
    """Every state, every measured width: the kind word (colour never carries a
    distinction alone, ADR 0008), the match count, and no line past the edge."""
    _drive(fixture_drive)
    index = build_name_index(fixture_drive)

    for width in WIDTHS:
        app = AtlasApp(fixture_drive, follow_debounce=0)
        async with app.run_test(size=(width, 51)) as pilot:
            await settle(app, pilot)
            app.push_screen(SearchOverlay(index, cap=3))
            await settle(app, pilot)
            overlay = _overlay(app)
            dialog = overlay.query_one("#search-dialog")
            assert dialog.outer_size.width == search_overlay_width(width), width

            await pilot.press(*"model")
            await settle(app, pilot)
            rows = _result_rows(overlay)
            assert any(row.startswith("folder") for row in rows), (width, rows)
            assert any(row.startswith("file") for row in rows), (width, rows)
            # The kind word survives at every width; the path is fitted, not
            # clipped past the dialog's edge.
            for line in _drawn_results(overlay):
                assert len(line.rstrip()) <= overlay.query_one("#search-results").size.width, (width, line)
            assert "more" in _status(overlay), (width, _status(overlay))
            assert len(_status(overlay)) <= search_overlay_cells(width), (width, _status(overlay))

            # Empty state at the same width.
            input_ = overlay.query_one("#search-input", Input)
            input_.value = "zzz"
            await settle(app, pilot)
            assert _status(overlay).startswith("No matches"), (width, _status(overlay))


async def test_the_overlay_holds_at_30_and_24_rows(fixture_drive):
    _drive(fixture_drive)
    index = build_name_index(fixture_drive)

    for width, rows in ((120, 30), (87, 24), (46, 24)):
        app = AtlasApp(fixture_drive, follow_debounce=0)
        async with app.run_test(size=(width, rows)) as pilot:
            await settle(app, pilot)
            app.push_screen(SearchOverlay(index))
            await settle(app, pilot)
            overlay = _overlay(app)
            await pilot.press(*"zoning")
            await settle(app, pilot)
            dialog = overlay.query_one("#search-dialog")
            assert dialog.size.height <= rows, (width, rows)
            # The row is fitted to the dialog, so its distinguishing tail survives.
            assert "notes.md" in "\n".join(_drawn_results(overlay))
            assert "1 match" in _status(overlay)
