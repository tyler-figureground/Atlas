"""The Tree Region's widget: a plain Textual Tree over ``atlas.core.tree``.

Every non-obvious choice here is a measurement from ticket 05 rather than a
preference, and each is commented where it lands: a plain ``Tree`` instead of
``DirectoryTree``, labels built as ``rich.text.Text``, per-node workers that are
not exclusive, no expand-all, and a ``get_label_width`` that does not build a
label to measure one.

Colour and glyphs come from ``tui.tokens``. Tree nodes are not DOM nodes and take
no CSS at all, which is the whole reason the token layer owns them.
"""

from __future__ import annotations

import threading

from rich.cells import cell_len
from rich.text import Text
from textual import work
from textual.widgets import Tree
from textual.widgets.tree import TreeNode as TreeNodeWidget

from ..core.conform import parent_key
from ..core.scan import READ
from ..core.tree import CONCURRENCY_CAP, LOADING_DELAY, ProjectTree, TreeNode
from . import tokens

# Node loads in flight at once, shared by every tree view (ticket 12).
LOAD_SLOTS = threading.BoundedSemaphore(CONCURRENCY_CAP)


def _detail(node: TreeNode, narrow: bool) -> str:
    """What follows the disclosure marker: a count, or why there is not one."""
    if node.load == READ:
        return tokens.child_count(node.folders, node.files, narrow=narrow)
    return tokens.load_style(node.load).label


def _fault_word(node: TreeNode, narrow: bool) -> str:
    """The glyph says something is wrong; this says what.

    Abbreviated when the width runs out, never dropped (ticket 10). Dropping it
    was the original behaviour and it left Drifted, Misplaced and Loose rendering
    the identical hatch in the identical colour - indistinguishable to anyone, at
    the width Atlas is most often opened at. The word is the only thing that ever
    separated them.
    """
    if node.filing == tokens.MAPPED:
        return ""
    style = tokens.filing_style(node.filing)
    return style.short if narrow else style.label


def node_label(node: TreeNode, *, narrow: bool = False, expanded: bool = False) -> Text:
    """One tree row, as Text.

    Never a ``str``. ``Tree.process_label`` runs ``Text.from_markup`` on anything
    it is handed, so a folder genuinely named ``[2024] Survey`` would lose its
    prefix and ``[b] Basement`` would turn bold - silently, and only for the
    folders unlucky enough to be named that way.
    """
    filing = tokens.filing_style(node.filing)
    label = Text()
    label.append(filing.glyph, style=filing.colour)
    label.append(" ")
    label.append(node.name, style=tokens.PALETTE.ink)
    # A file says what is wrong with it too. It has no disclosure marker and no
    # count, but a Loose file and an Unfiled file are otherwise the same hatch
    # in two hues, which is the whole thing ticket 10 rules out.
    fault = _fault_word(node, narrow)
    if fault:
        label.append("  ")
        label.append(fault, style=filing.colour)
    if not node.is_dir:
        return label
    label.append("  ")
    label.append(tokens.disclosure(node.load, expanded=expanded), style=tokens.PALETTE.dim)
    label.append("  ")
    label.append(_detail(node, narrow), style=tokens.PALETTE.muted)
    return label


def label_width(node: TreeNode, *, narrow: bool = False, expanded: bool = False) -> int:
    """How wide that row will be, without building it.

    Ticket 05 measured the median rebuild at 5000 expanded nodes falling from
    25.4 ms to 6.4 ms by overriding ``get_label_width``, and the tree rebuilds on
    any mutation, resize or style change. Measuring by rendering would give the
    right number and none of the saving, so this adds the parts up instead - and
    a test holds the two in agreement.
    """
    width = 2 + cell_len(node.name)
    fault = _fault_word(node, narrow)
    if fault:
        width += 2 + cell_len(fault)
    if not node.is_dir:
        return width
    width += 2 + cell_len(tokens.disclosure(node.load, expanded=expanded))
    width += 2 + cell_len(_detail(node, narrow))
    return width


class ProjectTreeView(Tree):
    """The Tree Region's widget.

    A plain ``Tree``, never ``DirectoryTree``: that subclass destroys injected
    nodes on reload, its one hook can subtract paths but never add them, and it
    costs about two ``is_dir`` stats per entry per load where ``os.scandir``
    gives the type away free (ticket 05).
    """

    # The disclosure marker comes from the token layer along with everything else
    # a row is made of, so Textual's own icons are turned off rather than drawn
    # beside them.
    ICON_NODE = ""
    ICON_NODE_EXPANDED = ""

    # Tree's default bindings include shift+space -> expand_all, which posts one
    # NodeExpanded per descendant - measured at 201 messages for 201 nodes. On a
    # streaming mount that is a load storm, and the binding is unreachable in
    # practice anyway, so it does not survive here.
    BINDINGS = [b for b in Tree.BINDINGS if getattr(b, "action", "") != "expand_all"]

    def __init__(self, **kwargs) -> None:
        super().__init__("", data="", **kwargs)
        # Before any reactive: setting show_root rebuilds the tree, which calls
        # get_label_width, which reads these.
        self.source: ProjectTree | None = None
        self.narrow = False
        self._facts: dict[str, TreeNode] = {}
        self._by_key: dict[str, TreeNodeWidget] = {}
        self._opened: set[str] = set()
        self._pending_key: str | None = None
        self._reopen: set[str] = set()
        self.show_root = False
        self.guide_depth = 2

    # ---- content ---------------------------------------------------------

    def set_source(self, source: ProjectTree | None, *, narrow: bool = False) -> None:
        """Point the widget at one project, from the top."""
        self.source = source
        self.narrow = narrow
        self._facts = {}
        self._by_key = {}
        self._opened = set()
        self._pending_key = None
        self._reopen = set()
        self.reset("", data="")
        self._by_key[""] = self.root
        # The root level is a displayed node like any other, so it is read the
        # same way: off the UI thread. On the studio drive one enumeration is
        # 91 ms at p99, which is a visible stall to spend on a cursor move.
        # The loading state waits LOADING_DELAY (120 ms, ticket 12): above the
        # cold p99, so a warm read never flickers it on and off.
        self._cancel_loading_timer()
        self.loading = False
        if source is not None:
            self._loading_timer = self.set_timer(LOADING_DELAY, self._show_loading)
            self._load("")

    def _show_loading(self) -> None:
        self._loading_timer = None
        self.loading = True

    def _cancel_loading_timer(self) -> None:
        timer = getattr(self, "_loading_timer", None)
        if timer is not None:
            timer.stop()
        self._loading_timer = None

    def reload(self, *, narrow: bool | None = None) -> None:
        """Rebuild from the seam, keeping what was open and where the cursor was.

        For when the source's facts changed under the widget - a refresh, a
        project-wide conform. Textual restores the cursor by line number, so both
        are carried across by Node Key instead: folders re-open as they are drawn
        and the cursor lands on its key once that key exists (#40).
        """
        expanded = {key for key, node in self._by_key.items() if key and node.is_expanded}
        cursor = self.cursor_node
        cursor_key = str(cursor.data) if cursor is not None and cursor.data else None
        self.set_source(self.source, narrow=self.narrow if narrow is None else narrow)
        self._reopen = expanded
        if cursor_key:
            self._pending_key = cursor_key

    def _fill(self, parent: TreeNodeWidget, key: str) -> None:
        """Draw one folder's children from the seam, and remember their facts."""
        if self.source is None:
            return
        parent.remove_children()
        for child in self.source.children(key):
            self._facts[child.key] = child
            node = (parent.add(child.name, data=child.key) if child.is_dir
                    else parent.add_leaf(child.name, data=child.key))
            self._by_key[child.key] = node
            if child.is_dir and child.key in self._reopen:
                node.expand()   # posts NodeExpanded, which loads it off-thread
        self._refresh_facts(key)
        if self._pending_key is not None and self._pending_key in self._by_key:
            self.select_key(self._pending_key)

    def _refresh_facts(self, key: str) -> None:
        """Re-read one node's own facts after its children were enumerated.

        Its Load State and Child Count live on the node, not on its listing, so
        reading a folder changes how its own row draws. The parent's listing is
        already cached, so this costs a dictionary write, not an enumeration.
        """
        if not key or self.source is None:
            return
        for sibling in self.source.children(parent_key(key)):
            if sibling.key == key:
                self._facts[key] = sibling
                return

    def node_for(self, key: str) -> TreeNodeWidget | None:
        """The widget node for a Node Key, or None if it is not drawn."""
        return self._by_key.get(key)

    def on_focus(self) -> None:
        """Land the cursor on the first node when the Region takes focus.

        Textual leaves ``cursor_line`` at -1 until an arrow key moves it, so a
        freshly drilled tree has focus and rows and no cursor. Every key that
        acts on the selected node - the repair key above all - is then silently
        inert until the operator happens to press down. Silently is the problem:
        the key looks broken rather than inapplicable.
        """
        if self.cursor_line < 0 and self.root.children:
            self.cursor_line = 0

    def selected_facts(self) -> TreeNode | None:
        """The Tree Node under the cursor, as core last described it.

        The widget's own node carries only a Node Key in ``data``; everything a
        repair needs to decide - the Filing State above all - lives on the
        immutable record core handed over. The cursor can also sit on the root,
        which is not a node at all.
        """
        node = self.cursor_node
        if node is None:
            return None
        return self._facts.get(str(node.data or ""))

    def select_key(self, key: str) -> None:
        """Put the cursor on a Node Key, now or as soon as it is drawn.

        Two Textual facts make this more than a one-liner. The cursor is restored
        by line number, so a rebuild moves it unless something re-resolves an
        identity; and ``select_node`` on a node added in the same cycle lands on
        the root instead (issue 3547, open, reproduces on 8.2.8) - hence
        ``call_after_refresh``. A key whose node is not drawn yet waits: after a
        repair, the place the cursor should follow to may be inside a folder
        Atlas has not opened.
        """
        node = self._by_key.get(key)
        if node is None:
            self._pending_key = key
            return
        self._pending_key = None
        self.call_after_refresh(self.select_node, node)

    # ---- lazy loading ----------------------------------------------------

    def on_tree_node_expanded(self, event) -> None:
        key = str(event.node.data or "")
        if not key or key in self._opened:
            return
        self._opened.add(key)
        self._load(key)

    @work(thread=True, exclusive=False, group="tree-load")
    def _load(self, key: str) -> None:
        """One enumeration, off the UI thread.

        Deliberately not exclusive. Tree shares one default worker group, so an
        exclusive per-node loader would cancel every other expansion in flight -
        which on a streaming mount is precisely the case that has several.
        """
        source = self.source
        if source is None:
            return
        # Not exclusive, but not unbounded either: ticket 12's cap on loads in
        # flight against the Drive redirector (#46).
        with LOAD_SLOTS:
            source.children(key)
        self.app.call_from_thread(self._loaded, key)

    def _loaded(self, key: str) -> None:
        if not key:
            self._cancel_loading_timer()
            self.loading = False
        node = self._by_key.get(key)
        if node is not None:
            self._fill(node, key)

    # ---- rendering -------------------------------------------------------

    def render_label(self, node: TreeNodeWidget, base_style, style):
        facts = self._facts.get(str(node.data or ""))
        if facts is None:
            return super().render_label(node, base_style, style)
        return node_label(facts, narrow=self.narrow, expanded=node.is_expanded)

    def get_label_width(self, node: TreeNodeWidget) -> int:
        facts = self._facts.get(str(node.data or ""))
        if facts is None:
            return super().get_label_width(node)
        return label_width(facts, narrow=self.narrow, expanded=node.is_expanded)
