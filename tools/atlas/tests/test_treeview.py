"""The tree widget (ticket 22).

The label is pure and is tested as a value, not as a render: it is the one place
a folder's real name meets Rich markup, and ticket 05 found that meeting to be
silently destructive.
"""

from __future__ import annotations

import os

from conftest import make_project
from textual.app import App

from atlas.core.doctor import report_project
from atlas.core.scan import PARTIAL, READ, UNREAD, UNREADABLE, scan_drive
from atlas.core.tree import (
    DRIFTED,
    LOOSE,
    MAPPED,
    MISPLACED,
    UNFILED,
    TreeNode,
    open_project_tree,
)
from atlas.tui.treeview import ProjectTreeView, node_label


def folder(name, **kwargs):
    return TreeNode(key=kwargs.pop("key", name), name=name, is_dir=True, **kwargs)


def test_a_read_folder_shows_its_glyph_and_its_own_children():
    node = folder("01 Model", filing=MAPPED, load=READ, folders=2, files=3)

    assert str(node_label(node, expanded=True)) == "█ 01 Model  ▾  2 folders, 3 files"
    assert str(node_label(node)) == "█ 01 Model  ▸  2 folders, 3 files"


def test_a_filed_file_carries_a_glyph_and_nothing_else():
    """No disclosure marker and no count: a file has no children to describe.
    A file with something wrong with it still names it - see below."""
    node = TreeNode(key="CLAUDE.md", name="CLAUDE.md", is_dir=False, filing=MAPPED)

    assert str(node_label(node)) == "█ CLAUDE.md"


def test_a_folder_named_like_markup_keeps_its_name():
    """Ticket 05's latent bug. Tree.process_label runs Text.from_markup on a str,
    so these two names are exactly the ones a str label would corrupt - and the
    first would look fine while the second silently lost its prefix."""
    for name in ("[2024] Survey", "[b] Basement Survey", "[/] Odd"):
        node = folder(name, filing=MAPPED, load=READ)
        assert node_label(node).plain.startswith(f"█ {name}"), name


def test_an_unreadable_folder_never_reads_as_empty():
    """Both return zero children. Only one of them is a fact (ADR 0004)."""
    empty = folder("01 Model", filing=MAPPED, load=READ)
    denied = folder("10 Legal", filing=MAPPED, load=UNREADABLE)

    assert "empty" in str(node_label(empty))
    assert "cannot read" in str(node_label(denied))
    assert "empty" not in str(node_label(denied))


def test_an_unopened_folder_claims_no_count():
    """A zero here would be the same false negative as an unreadable folder
    rendering as empty."""
    node = folder("06 Research", filing=MAPPED)

    rendered = str(node_label(node))
    assert rendered.endswith("not opened yet")
    for claim in ("file", "folder", "empty"):
        assert claim not in rendered.removeprefix("█ 06 Research"), claim


def test_a_partial_listing_says_so():
    node = folder("01 Model", filing=MAPPED, load=PARTIAL, folders=1, files=2)

    assert "partial" in str(node_label(node))


def test_a_repairable_folder_abbreviates_what_is_wrong_rather_than_dropping_it():
    node = folder("Meetings", filing=DRIFTED, load=READ, files=1)

    assert "wrong name" in str(node_label(node))
    narrow = str(node_label(node, narrow=True))
    assert "wrong name" not in narrow, "the long form does not fit"
    assert "NAME" in narrow, "but the row must still say what is wrong"
    assert "0F 1" in narrow


def test_a_file_says_what_is_wrong_with_it_too():
    """Found by rendering, not by the suite. A file returns early - no disclosure
    marker, no count - and used to return before the word as well, which left a
    Loose file and an Unfiled file identical but for hue at every width."""
    loose = TreeNode(key="HANDOFF.md", name="HANDOFF.md", is_dir=False, filing=LOOSE)
    unfiled = TreeNode(key="scratch.txt", name="scratch.txt", is_dir=False, filing=UNFILED)

    for narrow in (False, True):
        rendered = {str(node_label(n, narrow=narrow)) for n in (loose, unfiled)}
        assert len(rendered) == 2, rendered
        for node, text in zip((loose, unfiled), sorted(rendered)):
            assert text.rstrip() != f"▚ {node.name}", (
                f"a {node.filing} file says nothing at "
                f"{'narrow' if narrow else 'full'} width"
            )

    assert "not filed yet" in str(node_label(loose))
    assert "LOOSE" in str(node_label(loose, narrow=True))
    assert "UNMAPPED" in str(node_label(unfiled, narrow=True))


def test_the_narrow_row_still_tells_the_repairable_states_apart():
    """The defect ticket 10 was opened for. Drifted, Misplaced and Loose share a
    glyph and a colour by design - the word is the only thing between them, so
    the narrow row cannot be allowed to drop it."""
    rendered = {
        filing: str(node_label(folder("Meetings", filing=filing, load=READ), narrow=True))
        for filing in (DRIFTED, MISPLACED, LOOSE, UNFILED)
    }

    assert len(set(rendered.values())) == len(rendered), rendered


# ------------------------------------------------------------- the widget


class Harness(App):
    """Just the tree, so a widget test is about the widget."""

    def __init__(self, source):
        super().__init__()
        self._source = source

    def compose(self):
        yield ProjectTreeView(id="tree")

    def on_mount(self):
        self.query_one(ProjectTreeView).set_source(self._source)


def source_for(drive, name):
    inventory = scan_drive(drive)
    m = inventory.map
    inv = next(p for p in inventory.projects if p.name == name)
    return open_project_tree(inv, m, report_project(inv, m))


async def settle(app, pilot):
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def rows(tree):
    return [str(tree.render_label(node, "", "")) for node in tree.root.children]


async def test_the_tree_shows_the_project_root_and_nothing_deeper(fixture_drive):
    """Lazy. One enumeration for what is on screen, and none for what is not."""
    make_project(fixture_drive, "260601_Tree",
                 sections=["01 Model/01 Site Model", "Meetings"],
                 files={"CLAUDE.md": "x"})
    source = source_for(fixture_drive, "260601_Tree")
    app = Harness(source)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        tree = app.query_one(ProjectTreeView)

        assert [n.data for n in tree.root.children] == ["01 Model", "Meetings", "CLAUDE.md"]
        assert source.load_state("01 Model") == UNREAD, "not opened, so not read"
        assert any("not opened yet" in row for row in rows(tree))
        assert any("wrong name" in row for row in rows(tree)), "Meetings is Drifted"


def test_the_width_and_the_label_agree():
    """label_width adds the parts up instead of rendering, which is the whole
    saving. Two ways of computing one number is a place they can drift, so they
    are held together here rather than trusted."""
    from atlas.core.scan import UNREAD
    from atlas.tui.treeview import label_width

    for filing in (MAPPED, DRIFTED, MISPLACED, LOOSE, UNFILED):
        for load in (UNREAD, READ, UNREADABLE, PARTIAL):
            for narrow in (False, True):
                for expanded in (False, True):
                    node = folder("06 Research", filing=filing, load=load,
                                  folders=2, files=11)
                    assert label_width(node, narrow=narrow, expanded=expanded) == \
                        node_label(node, narrow=narrow, expanded=expanded).cell_len, \
                        (filing, load, narrow, expanded)
        leaf = TreeNode(key="a.md", name="a.md", is_dir=False, filing=filing)
        assert label_width(leaf) == node_label(leaf).cell_len, filing


async def test_there_is_no_expand_all(fixture_drive):
    """expand_all posts one NodeExpanded per descendant - 201 messages for 201
    nodes, measured. On a streaming mount that is a load storm.

    Pressed, not read off BINDINGS: Textual merges inherited bindings, and the
    action is `toggle_expand_all`, so the old filter removed nothing and its
    test passed whether or not the key worked (#50)."""
    make_project(fixture_drive, "260605_All",
                 sections=["01 Model/01 Site Model", "06 Research/Zoning", "08 OUT/RFI"])
    source = source_for(fixture_drive, "260605_All")
    app = Harness(source)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        tree = app.query_one(ProjectTreeView)
        tree.focus()
        tree.cursor_line = 0
        await pilot.pause()
        before = [node.is_expanded for node in tree.root.children]

        await pilot.press("shift+space")
        await settle(app, pilot)

        assert [node.is_expanded for node in tree.root.children] == before
        assert source.load_state("06 Research") == UNREAD, "nothing was walked"



async def test_expanding_a_folder_reads_that_folder_and_no_other(fixture_drive):
    make_project(fixture_drive, "260602_Lazy",
                 sections=["01 Model/01 Site Model", "06 Research"],
                 files={"01 Model/a.rvt": "x"})
    source = source_for(fixture_drive, "260602_Lazy")
    app = Harness(source)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        tree = app.query_one(ProjectTreeView)
        assert source.load_state("01 Model") == UNREAD

        tree.node_for("01 Model").expand()
        await settle(app, pilot)

        assert source.load_state("01 Model") == READ
        assert source.load_state("06 Research") == UNREAD, "never touched"
        assert [n.data for n in tree.node_for("01 Model").children] == [
            "01 Model/01 Site Model", "01 Model/a.rvt"]
        # Reading a folder changes how its own row draws.
        assert "1 folder, 1 file" in str(
            tree.render_label(tree.node_for("01 Model"), "", ""))


async def test_two_folders_can_load_at_once(fixture_drive):
    """The per-node worker must not be exclusive. Tree shares one default worker
    group, so an exclusive loader would cancel every other expansion in flight."""
    make_project(fixture_drive, "260603_Both",
                 sections=["01 Model/01 Site Model", "06 Research/Zoning"])
    source = source_for(fixture_drive, "260603_Both")
    app = Harness(source)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        tree = app.query_one(ProjectTreeView)

        tree.node_for("01 Model").expand()
        tree.node_for("06 Research").expand()
        await settle(app, pilot)

        assert source.load_state("01 Model") == READ
        assert source.load_state("06 Research") == READ


async def test_a_folder_atlas_cannot_open_expands_to_a_reason(fixture_drive, monkeypatch):
    """Never an empty folder. The row says so and there is nothing under it."""
    project = make_project(fixture_drive, "260604_Denied", sections=["01 Model", "10 Legal"])
    source = source_for(fixture_drive, "260604_Denied")
    app = Harness(source)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        tree = app.query_one(ProjectTreeView)

        real = os.scandir

        def deny(path, *a, **kw):
            if os.fspath(path) == os.fspath(project / "10 Legal"):
                raise PermissionError(13, "denied")
            return real(path, *a, **kw)

        monkeypatch.setattr(os, "scandir", deny)
        tree.node_for("10 Legal").expand()
        tree.node_for("01 Model").expand()
        await settle(app, pilot)

        denied = str(tree.render_label(tree.node_for("10 Legal"), "", ""))
        assert "cannot read" in denied and "empty" not in denied
        assert list(tree.node_for("10 Legal").children) == []
        assert "empty" in str(tree.render_label(tree.node_for("01 Model"), "", ""))


# ------------------------------------------------------- the cursor and the key


async def test_the_cursor_is_restored_by_node_key(fixture_drive):
    """Textual restores the cursor by line number, so any rebuild that changes
    the child list moves the selection somewhere else. The Node Key is what the
    widget re-resolves against instead."""
    make_project(fixture_drive, "260605_Cursor",
                 sections=["01 Model/01 Site Model", "06 Research", "Meetings"])
    source = source_for(fixture_drive, "260605_Cursor")
    app = Harness(source)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        tree = app.query_one(ProjectTreeView)

        tree.select_key("Meetings")
        await settle(app, pilot)
        assert tree.cursor_node.data == "Meetings"

        # Expanding above it shifts every line below. The key does not move.
        tree.node_for("01 Model").expand()
        await settle(app, pilot)
        tree.select_key("Meetings")
        await settle(app, pilot)
        assert tree.cursor_node.data == "Meetings"


async def test_the_cursor_can_be_sent_to_a_node_that_does_not_exist_yet(fixture_drive):
    """Issue 3547 still reproduces on 8.2.8: select_node on a just-added node
    lands on the root. And after a repair the destination may be inside a folder
    Atlas has not opened, so the key has to be able to wait for its node."""
    make_project(fixture_drive, "260606_Pending",
                 sections=["01 Model/01 Site Model", "06 Research"])
    source = source_for(fixture_drive, "260606_Pending")
    app = Harness(source)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        tree = app.query_one(ProjectTreeView)

        tree.select_key("01 Model/01 Site Model")
        assert tree.node_for("01 Model/01 Site Model") is None, "not drawn yet"

        tree.node_for("01 Model").expand()
        await settle(app, pilot)

        assert tree.cursor_node.data == "01 Model/01 Site Model"


def test_a_read_but_closed_folder_still_points_right():
    """Found by rendering, not by reasoning. The Companion's Expectations pass
    reads every mapped section, so by first paint several folders are Read and
    all of them are closed - and every one of them was drawing an open triangle."""
    node = folder("01 Model", filing=MAPPED, load=READ, folders=1, files=1)

    closed = str(node_label(node, expanded=False))
    assert "\u25b8" in closed and "\u25be" not in closed
    assert "1 folder, 1 file" in closed, "it still says what Atlas knows"
    assert "\u25be" in str(node_label(node, expanded=True))
