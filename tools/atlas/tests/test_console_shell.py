"""The console shell as Atlas code (ticket 20, ADR 0005).

Rendered headless at the sizes ticket 03 measured off forty PTY resizes - 179,
153, 120, 87, 77 and 46 columns, 51, 30 and 24 rows - rather than at the 132x38
the effort had been assuming. Single-Region is the common case here, not the
degraded one.
"""

from __future__ import annotations

import asyncio

import pytest
from textual.widgets import Static

from atlas.tui.app import AtlasApp
from atlas.tui.treeview import ProjectTreeView

from conftest import make_project

SPLIT_WIDTHS = (179, 153, 120)
NARROW_WIDTHS = (87, 77, 46)


async def settle(app: AtlasApp, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def two_projects(drive):
    make_project(drive, "260501_Alpha", sections=["01 Model", "Meetings"],
                 files={"Meetings/k.md": "z"})
    make_project(drive, "260502_Bravo", sections=["01 Model"])


# ------------------------------------------------------------ Compositions


@pytest.mark.parametrize("width", SPLIT_WIDTHS)
async def test_split_composition_draws_the_list_beside_the_workspace(fixture_drive, width):
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(width, 51)) as pilot:
        await settle(app, pilot)
        assert app.query_one("#projects").display
        assert app.query_one("#workspace").display
        assert app.query_one("#tree").display
        assert app.query_one("#companion").display
        assert not app.query_one("#refusal").display


@pytest.mark.parametrize("width", NARROW_WIDTHS)
async def test_single_region_composition_draws_exactly_one(fixture_drive, width):
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(width, 51)) as pilot:
        await settle(app, pilot)
        assert app.query_one("#projects").display
        assert not app.query_one("#tree").display
        assert not app.query_one("#companion").display

        await pilot.press("tab")
        await pilot.pause()
        assert not app.query_one("#projects").display
        assert app.query_one("#tree").display


async def test_summary_and_operation_merge_at_twenty_four_rows(fixture_drive):
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 24)) as pilot:
        await settle(app, pilot)
        assert not app.query_one("#summary").display
        line = str(app.query_one("#operation", Static).content)
        assert "projects" in line and "ready" in line, line


@pytest.mark.parametrize("size", ((39, 51), (120, 15)))
async def test_too_small_draws_one_honest_line(fixture_drive, size):
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=size) as pilot:
        await settle(app, pilot)
        refusal = app.query_one("#refusal", Static)
        assert refusal.display
        assert "40 columns" in str(refusal.content)
        assert not app.query_one("#console").display
        assert not app.query_one("#mark").display
        assert not app.query_one("#operation").display
        assert not app.query_one("#summary").display
        assert not app.query_one("#keys").display


async def test_the_narrow_chrome_names_the_keys_that_move(fixture_drive):
    """46 columns is the single most common measured width. The full binding
    list does not fit and the keys still work - only the chrome shrinks."""
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(46, 51)) as pilot:
        await settle(app, pilot)
        keys = app.query_one("#keys", Static)
        assert keys.display
        assert str(keys.content) == "? Help  Tab Region  Enter Open"
        assert app.check_action("add_section", ()) is True, "still available"


# --------------------------------------------------------------- collapse


async def test_collapse_outranks_the_breakpoint_and_sticks(fixture_drive):
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(179, 51)) as pilot:
        await settle(app, pilot)
        assert app.query_one("#companion").display

        await pilot.press("right_square_bracket")
        await pilot.pause()
        assert not app.query_one("#companion").display, "collapsed at a wide width"

        await pilot.press("left_square_bracket")
        await pilot.pause()
        assert not app.query_one("#projects").display
        assert app.query_one("#tree").display, "focus moved off the collapsed Region"

        await pilot.press("left_square_bracket", "right_square_bracket")
        await pilot.pause()
        assert app.query_one("#projects").display
        assert app.query_one("#companion").display


async def test_zoom_is_single_region_at_any_width(fixture_drive):
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(179, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("z")
        await pilot.pause()
        assert app.query_one("#projects").display
        assert not app.query_one("#tree").display
        assert not app.query_one("#companion").display

        await pilot.press("escape")
        await pilot.pause()
        assert app.query_one("#tree").display


# -------------------------------------------------------- Companion Modes


async def test_the_companion_shows_real_unmet_expectations(fixture_drive):
    """The default mode is wired to the core seam, not to a placeholder: this is
    what the tree exists to be compared against."""
    make_project(fixture_drive, "260503_Sparse", sections=["01 Model"])
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(179, 51)) as pilot:
        await settle(app, pilot)
        assert "Unmet expectations" in str(app.query_one("#companion-title", Static).content)
        body = str(app.query_one("#companion-body", Static).content)
        assert "08 OUT" in body, body
        assert "CLAUDE.md" in body, body
        assert "(add folders)" in body, "a section is not a Backfill"


async def test_d_cycles_the_modes_and_a_new_project_snaps_back(fixture_drive):
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(179, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("d")
        await pilot.pause()
        assert "Project health" in str(app.query_one("#companion-title", Static).content)

        await pilot.press("d")
        await pilot.pause()
        assert "Dossier" in str(app.query_one("#companion-title", Static).content)

        await pilot.press("down")
        await pilot.pause()
        assert "Unmet expectations" in str(app.query_one("#companion-title", Static).content)


async def test_the_workspace_title_carries_the_project_name(fixture_drive):
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(179, 51)) as pilot:
        await settle(app, pilot)
        assert str(app.query_one("#workspace-title", Static).content) == "260501_Alpha"
        await pilot.press("down")
        await pilot.pause()
        assert str(app.query_one("#workspace-title", Static).content) == "260502_Bravo"


# ------------------------------------------------------------ cursor follow


async def test_the_workspace_waits_out_a_moving_cursor_but_not_a_cached_one(fixture_drive):
    """Debounced so that holding a key down does not enumerate every project it
    passes over; exempt on a cache hit, because there is nothing to wait for."""
    # The two must differ in what the map expects of them, or "did the Companion
    # update" is unanswerable.
    make_project(fixture_drive, "260501_Alpha", sections=["01 Model"])
    make_project(fixture_drive, "260502_Bravo",
                 sections=["01 Model/01 Site Model", "01 Model/02 Design",
                           "06 Research/Zoning", "06 Research/Code", "08 OUT",
                           "10 Legal", "11 Meetings"],
                 files={"CLAUDE.md": "x"})
    app = AtlasApp(fixture_drive, follow_debounce=0.5)

    async with app.run_test(size=(179, 51)) as pilot:
        await settle(app, pilot)
        await asyncio.sleep(0.6)
        await pilot.pause()
        first = str(app.query_one("#companion-body", Static).content)

        await pilot.press("down")
        await pilot.pause()
        assert str(app.query_one("#companion-body", Static).content) == first, "still pending"
        await asyncio.sleep(0.6)
        await pilot.pause()
        second = str(app.query_one("#companion-body", Static).content)
        assert second != first

        await pilot.press("up")
        await pilot.pause()
        assert str(app.query_one("#companion-body", Static).content) == first, "cache hit"


async def test_the_palette_switches_the_companion_instead_of_pushing_a_modal(fixture_drive):
    """The command that used to open a project-health modal now switches a
    Companion Mode. It is also the one place a deleted action would have gone
    unnoticed: the palette only builds its entries when Atlas is not busy."""
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(179, 51)) as pilot:
        await settle(app, pilot)
        commands = {command.title for command in app.get_system_commands(app.screen)}
        assert "Project health" in commands

        app.action_show_health()
        await pilot.pause()
        assert app.screen is app.screen_stack[0], "no modal"
        assert "Project health" in str(app.query_one("#companion-title", Static).content)
        assert "ATLAS CAN FIX" in str(app.query_one("#companion-body", Static).content)


async def test_the_palette_names_the_key_for_every_console_verb(fixture_drive):
    """The palette is where an operator who opens Atlas twice a month finds a key
    (#43). Each console verb has an entry, the entry names its key, and the entry
    runs the same action the key does."""
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(179, 51)) as pilot:
        await settle(app, pilot)
        commands = {command.title: command for command in app.get_system_commands(app.screen)}
        keys = {command.help.split(" - ", 1)[0] for command in commands.values()}
        assert {"/", "d", "[", "]", "z", "f", "u", "o", "y", "c"} <= keys

        before = app._companion_mode
        commands["Switch Companion mode"].callback()
        await pilot.pause()
        assert app._companion_mode != before


async def test_a_cursor_passing_through_never_enumerates_what_it_passed(fixture_drive):
    """The cancellation path. Holding the cursor key down walks the list; only
    where it comes to rest is worth an enumeration."""
    make_project(fixture_drive, "260504_One", sections=["01 Model"])
    make_project(fixture_drive, "260505_Two", sections=["01 Model", "06 Research"])
    make_project(fixture_drive, "260506_Three",
                 sections=["01 Model", "06 Research", "08 OUT", "10 Legal"])
    app = AtlasApp(fixture_drive, follow_debounce=0.5)

    async with app.run_test(size=(179, 51)) as pilot:
        await settle(app, pilot)
        await asyncio.sleep(0.6)
        await pilot.pause()

        await pilot.press("down")
        await pilot.press("down")
        await pilot.pause()
        assert app._workspace_project == "260506_Three"
        # Passed straight over the middle project, so it was never opened.
        assert "260505_Two" not in app._trees

        await asyncio.sleep(0.6)
        await pilot.pause()
        assert "260506_Three" in app._trees
        assert "260505_Two" not in app._trees


# ------------------------------------------------------------- the Tree Region


async def test_the_tree_region_draws_the_selected_project(fixture_drive):
    """Ticket 20 left a placeholder here. Ticket 22 fills it, and the Workspace's
    cursor-follow is what points it at a project."""
    make_project(fixture_drive, "260507_Alpha", sections=["01 Model", "Meetings"],
                 files={"CLAUDE.md": "x"})
    make_project(fixture_drive, "260508_Bravo", sections=["06 Research"])
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(179, 51)) as pilot:
        await settle(app, pilot)
        tree = app.query_one(ProjectTreeView)
        assert [n.data for n in tree.root.children] == ["01 Model", "Meetings", "CLAUDE.md"]

        await pilot.press("down")
        await settle(app, pilot)
        assert [n.data for n in tree.root.children] == ["06 Research"]


async def test_the_tree_drops_the_wording_when_the_width_runs_out(fixture_drive):
    """Same tree, same facts, two Compositions. The glyph and its colour carry
    the state in both; only the words go."""
    make_project(fixture_drive, "260509_Narrow", sections=["01 Model", "Meetings"],
                 files={"Meetings/k.md": "z"})

    async def drifted_row(width):
        app = AtlasApp(fixture_drive, follow_debounce=0)
        async with app.run_test(size=(width, 51)) as pilot:
            await settle(app, pilot)
            tree = app.query_one(ProjectTreeView)
            node = tree.node_for("Meetings")
            return str(tree.render_label(node, "", ""))

    assert "wrong name" in await drifted_row(179)
    assert "wrong name" not in await drifted_row(46)


# ------------------------------------------------- focus, not just intent


async def test_drilling_into_the_tree_actually_moves_keyboard_focus(fixture_drive):
    """Ticket 23 found this by rendering. `_focus_current_region` focused the
    Region's container - `#tree` is a Vertical, and a Vertical cannot take focus,
    so `focus()` was a no-op. The app believed it had drilled, the arrow keys
    still drove the project list, and the tree cursor never existed.

    Asserting on `_focus_region` or on `display` cannot catch it. Only asserting
    on which widget the keyboard is actually talking to can.
    """
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        assert app.focused is app.query_one("#projects")

        await pilot.press("enter")
        await settle(app, pilot)

        assert app.focused is app.query_one(ProjectTreeView)


async def test_arrow_keys_move_the_tree_cursor_once_drilled(fixture_drive):
    """The consequence, stated as behaviour: after Enter, down belongs to the
    tree. It was moving the project list, which also changed what the tree was
    showing underneath the operator."""
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        before = app._workspace_project

        await pilot.press("enter")
        await settle(app, pilot)
        await pilot.press("down")
        await settle(app, pilot)

        assert app._workspace_project == before, "down must not change the project"
        assert app.query_one(ProjectTreeView).selected_facts() is not None


async def test_unwinding_returns_focus_to_the_project_list(fixture_drive):
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        await pilot.press("escape")
        await settle(app, pilot)

        assert app.focused is app.query_one("#projects")


async def test_enter_stays_atlas_key_when_the_tree_has_focus(fixture_drive):
    """ADR 0005: Enter drills, identically in both Compositions and in every
    Region. Textual's Tree binds enter to select_cursor, and a widget binding
    beats an App one - so once the focus bug was fixed and the tree could
    actually hold focus, the tree quietly took Atlas's key. Enter is priority
    for the same reason Tab already is."""
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        assert app.focused is app.query_one(ProjectTreeView)

        await pilot.press("enter")
        await settle(app, pilot)

        # The Companion Region, or the Expectations list inside it (#42).
        companion = app.query_one("#companion")
        assert app.focused is companion or companion in app.focused.ancestors, \
            "Enter drilled onward"


async def test_space_toggles_a_folder_once_the_tree_has_focus(fixture_drive):
    """The other half of the same finding: with focus real, each Region's own
    space does the right thing. Marking is a project-list idea; in the tree,
    space opens a folder - which was unreachable by keyboard until now."""
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)
        tree = app.query_one(ProjectTreeView)
        assert tree.cursor_node is not None and not tree.cursor_node.is_expanded

        await pilot.press("space")
        await settle(app, pilot)

        assert tree.cursor_node.is_expanded
        assert not app._marked, "space in the tree must not mark a project"


async def test_drilling_into_the_tree_lands_the_cursor_on_a_node(fixture_drive):
    """Textual leaves cursor_line at -1 until an arrow key moves it, so a freshly
    drilled tree had focus, rows, and no cursor - and the repair key was silently
    inert until the operator pressed down. A key that does nothing and says
    nothing is the one failure mode this whole ticket is trying to avoid."""
    two_projects(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)

        tree = app.query_one(ProjectTreeView)
        assert tree.cursor_node is not None
        assert tree.selected_facts() is not None
