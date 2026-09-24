"""What the console draws, rendered headless rather than asked of a helper.

The audit that found these (2026-09) kept meeting the same gap: a pure function
was tested as a value - ``render_label(node, "", "")`` - and the widget that
called it drew something else. These tests read what reaches the screen.
"""

from __future__ import annotations

from rich.color import Color
from textual.widgets import DataTable, Label, Static

from atlas.tui import tokens
from atlas.tui.app import OPERATION_MARGIN, AtlasApp, ConfirmListModal
from atlas.tui.wordmark import composition_for, render_mark
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


# ------------------------------------------------ words stay on screen (#19)


def visible_lines(tree: ProjectTreeView) -> list[str]:
    return ["".join(seg.text for seg in tree.render_line(y))
            for y in range(len(tree.root.children))]


async def test_the_fault_word_and_load_state_survive_a_long_name_at_46_columns(fixture_drive):
    """ADR 0008: colour may reinforce a distinction, never carry it alone. The
    word came after an unbounded name, so at 46 columns it was scrolled out of
    view and the hue was all that told Loose from Unfiled."""
    make_project(
        fixture_drive, "260813_Long", sections=["01 Model", "Random Stuff From The Old Server"],
        files={
            "HANDOFF-2026-08-13-client-kickoff-notes.md": "x",
            "HANDOFF_2026-08-13-client-kickoff-notes.md": "x",
        },
    )
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(46, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        tree = app.query_one(ProjectTreeView)
        lines = visible_lines(tree)
        random = next(line for line in lines if "Random" in line)

        assert "UNMAPPED" in random and "unread" in random, lines
        loose = next(line for line in lines if "HANDOFF-" in line or "LOOSE" in line)
        unfiled = next(line for line in lines if line is not loose and "HANDOFF" in line)
        assert "LOOSE" in loose, lines
        assert "UNMAPPED" in unfiled, lines
        for line in lines:
            assert len(line.rstrip()) <= tree.scrollable_content_region.width
        # Names shorten in the middle, so both ends survive.
        assert "notes" in loose and "HANDOFF" in loose


def test_unread_has_a_short_form_and_cannot_read_never_shortens():
    from atlas.core.tree import TreeNode
    from atlas.core.scan import UNREADABLE
    from atlas.tui.treeview import node_label

    unread = TreeNode(key="a", name="a", is_dir=True)
    assert str(node_label(unread, narrow=True)).endswith("unread")
    denied = TreeNode(key="b", name="b", is_dir=True, load=UNREADABLE)
    assert str(node_label(denied, narrow=True)).endswith("!  cannot read")


# ------------------------------------------------ names are never markup (#37)


def rendered(widget) -> str:
    """What a Label, Static or cell shows, as plain text."""
    value = widget.render()
    return getattr(value, "plain", str(value))


async def test_a_bracketed_project_name_survives_the_list_modals_and_toasts(fixture_drive):
    """`clean_name_part` allows brackets, so Atlas's own New project form can
    make `260813_Loft [draft]`. Rich markup ate `[draft]`, and the destructive
    Clean confirm named the wrong project."""
    make_project(fixture_drive, "260813_Loft [draft]", sections=["01 Model", "08 OUT"])
    make_project(fixture_drive, "260813_Loft", sections=["01 Model"])
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        table = app.query_one("#projects", DataTable)
        names = [table.get_row_at(index)[2] for index in range(table.row_count)]
        assert any(getattr(name, "plain", name) == "260813_Loft [draft]" for name in names)
        assert all(not isinstance(name, str) for name in names), "a str cell is parsed as markup"

        draft = next(index for index, row in enumerate(app._visible_rows)
                     if row.key == "260813_Loft [draft]")
        table.move_cursor(row=draft)
        await settle(app, pilot)
        await pilot.press("c")
        await settle(app, pilot)
        assert isinstance(app.screen, ConfirmListModal)
        title = app.screen.query_one(".dialog-title", Label)
        assert "260813_Loft [draft]" in rendered(title)
        await pilot.press("escape")
        await settle(app, pilot)

        app.notify("[draft] kept", title="t")
        await pilot.pause()
        assert all(not n.markup for n in app._notifications), "a toast parsed markup"


def test_option_lists_do_not_parse_markup():
    from atlas.tui.app import AddSectionModal

    assert not isinstance(AddSectionModal._option_label("[old] Archive"), str)


# ------------------------------------------------------------- resize (#18)


def drifted(drive):
    make_project(drive, "260813_Fixit", sections=["01 Model", "Meetings"],
                 files={"Meetings/kickoff.md": "x"})


def mark_plain(app: AtlasApp) -> str:
    return app.query_one("#mark", Static).content.plain


async def test_a_snap_resize_redraws_for_the_new_size_not_the_old_one(fixture_drive):
    """Atlas's resize handler runs before Textual stores the new size, so
    anything reading self.size there is one resize behind."""
    drifted(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        tree = app.query_one(ProjectTreeView)
        assert app.query_one("#workspace").display
        assert not tree.narrow

        await pilot.resize_terminal(46, 51)
        await settle(app, pilot)
        assert app.query_one("#projects").display
        assert not app.query_one("#workspace").display, "stayed Split at 46 columns"
        assert mark_plain(app).startswith(render_mark(composition_for(46)).plain)
        assert tree.narrow, "the tree kept its wide words at 46 columns"

        await pilot.resize_terminal(120, 51)
        await settle(app, pilot)
        assert app.query_one("#workspace").display, "stayed Single-Region at 120"
        assert mark_plain(app).startswith(render_mark(composition_for(120)).plain)
        assert not tree.narrow


async def test_an_armed_confirm_is_rebuilt_for_the_new_width(fixture_drive):
    drifted(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        app.query_one(ProjectTreeView).select_key("Meetings")
        await settle(app, pilot)
        await pilot.press("f")
        await pilot.pause()
        assert app._armed is not None

        await pilot.resize_terminal(46, 51)
        await settle(app, pilot)
        line = app._operation_text
        assert line.endswith("Enter confirm  Esc cancel")
        assert len(line) <= 46 - OPERATION_MARGIN
