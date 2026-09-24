"""What the console draws, rendered headless rather than asked of a helper.

The audit that found these (2026-09) kept meeting the same gap: a pure function
was tested as a value - ``render_label(node, "", "")`` - and the widget that
called it drew something else. These tests read what reaches the screen.
"""

from __future__ import annotations

from rich.color import Color

from atlas.tui import tokens
from atlas.tui.app import AtlasApp
from atlas.tui.layout import TREE
from atlas.tui.treeview import ProjectTreeView

from conftest import make_project


async def settle(app: AtlasApp, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def line_styles(tree: ProjectTreeView, y: int) -> set:
    """The distinct (colour, background, bold) of the non-blank cells on line y."""
    strip = tree.render_line(y)
    return {
        (seg.style.color, seg.style.bgcolor, seg.style.bold)
        for seg in strip
        if seg.text.strip() and seg.style is not None
    }


# ------------------------------------------------------------ the cursor (#17)


async def test_the_tree_cursor_row_draws_differently_from_its_neighbours(fixture_drive):
    make_project(fixture_drive, "260813_Cursor",
                 sections=["01 Model", "06 Research", "08 OUT"])
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(87, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        assert app._focus_region == TREE
        tree = app.query_one(ProjectTreeView)
        await pilot.press("down")
        await settle(app, pilot)
        assert tree.cursor_line == 1

        cursor = line_styles(tree, 1)
        assert cursor != line_styles(tree, 0)
        assert cursor != line_styles(tree, 2)
        assert all(bg is not None for _, bg, _ in cursor), "the cursor paints its row"
        # Painted by the token layer, not by whatever the Textual theme picks.
        cursor_ground = {bg for _, bg, _ in cursor}
        assert cursor_ground == {Color.parse(tokens.PALETTE.ember[2])}
