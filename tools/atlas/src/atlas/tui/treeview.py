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

from rich.cells import cell_len
from rich.text import Text
from textual import work
from textual.widgets import Tree
from textual.widgets.tree import TreeNode as TreeNodeWidget

from ..core.conform import parent_key
from ..core.scan import READ, UNREADABLE
from ..core.tree import ProjectTree, TreeNode
from . import tokens


ELLIPSIS = "…"
# The fewest cells of a name a row keeps, however little room there is.
MIN_NAME = 3


def middle_ellipsis(text: str, width: int) -> str:
    """``text`` shortened to ``width`` cells by cutting its middle.

    The middle, not the end: studio names put what tells two things apart at
    the end (``YYMMDD_<ShortAddress>-<Description>``), and right-clipping is
    exactly what removes it. Measured in cells, not characters.
    """
    if width <= 0 or cell_len(text) <= width:
        return text
    if width == 1:
        return ELLIPSIS
    room = width - 1
    head_cells = (room + 1) // 2
    head = ""
    for char in text:
        if cell_len(head + char) > head_cells:
            break
        head += char
    tail = ""
    for char in reversed(text[len(head):]):
        if cell_len(head) + cell_len(char + tail) > room:
            break
        tail = char + tail
    return f"{head}{ELLIPSIS}{tail}"


def _detail(node: TreeNode, narrow: bool) -> str:
    """What follows the disclosure marker: a count, or why there is not one."""
    if node.load == READ:
        return tokens.child_count(node.folders, node.files, narrow=narrow)
    style = tokens.load_style(node.load)
    return style.short if narrow else style.label


def _suffix_width(node: TreeNode, narrow: bool, expanded: bool) -> int:
    """Everything a row draws after the name, in cells."""
    width = 0
    fault = _fault_word(node, narrow)
    if fault:
        width += 2 + cell_len(fault)
    if node.is_dir:
        width += 2 + cell_len(tokens.disclosure(node.load, expanded=expanded))
        width += 2 + cell_len(_detail(node, narrow))
    return width


def _fitted_name(node: TreeNode, narrow: bool, expanded: bool, room: int) -> str:
    """The name, shortened so what follows it stays inside ``room`` cells.

    The Fault Word and the Load State come after a name of any length. At 46
    columns a long name pushed them out of the viewport, leaving hue alone to
    tell Loose from Unfiled - ADR 0008 rules that out. So the suffix is
    reserved and the name gives way. ``room`` of 0 means unbounded.
    """
    if room <= 0:
        return node.name
    budget = max(MIN_NAME, room - 2 - _suffix_width(node, narrow, expanded))
    return middle_ellipsis(node.name, budget)


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


def node_label(node: TreeNode, *, narrow: bool = False, expanded: bool = False,
               room: int = 0) -> Text:
    """One tree row, as Text, fitted to ``room`` cells when that is given.

    Never a ``str``. ``Tree.process_label`` runs ``Text.from_markup`` on anything
    it is handed, so a folder genuinely named ``[2024] Survey`` would lose its
    prefix and ``[b] Basement`` would turn bold - silently, and only for the
    folders unlucky enough to be named that way.
    """
    filing = tokens.filing_style(node.filing)
    label = Text()
    label.append(filing.glyph, style=filing.colour)
    label.append(" ")
    label.append(_fitted_name(node, narrow, expanded, room), style=tokens.PALETTE.ink)
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


def label_width(node: TreeNode, *, narrow: bool = False, expanded: bool = False,
                room: int = 0) -> int:
    """How wide that row will be, without building it.

    Ticket 05 measured the median rebuild at 5000 expanded nodes falling from
    25.4 ms to 6.4 ms by overriding ``get_label_width``, and the tree rebuilds on
    any mutation, resize or style change. Measuring by rendering would give the
    right number and none of the saving, so this adds the parts up instead - and
    a test holds the two in agreement.
    """
    name = _fitted_name(node, narrow, expanded, room)
    return 2 + cell_len(name) + _suffix_width(node, narrow, expanded)


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

    def action_toggle_expand_all(self) -> None:
        """Nothing: there is no expand-all.

        Tree's default bindings include shift+space -> toggle_expand_all, which
        posts one NodeExpanded per descendant - measured at 201 messages for 201
        nodes. On a streaming mount that is a load storm. Filtering BINDINGS
        cannot remove it, because Textual merges the base class's bindings back
        in, so the action itself is what goes.
        """

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
        self._filter = ""
        self._expanded_before: set[str] = set()
        self._drawn: dict[str, list[TreeNode]] = {}
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
        self._filter = ""
        self._expanded_before = set()
        self._drawn = {}
        self._reopen = set()
        self.reset("", data="")
        self._by_key[""] = self.root
        # The root level is a displayed node like any other, so it is read the
        # same way: off the UI thread. On the studio drive one enumeration is
        # 91 ms at p99, which is a visible stall to spend on a cursor move.
        self.loading = source is not None
        if source is not None:
            self._load("")

    def set_narrow(self, narrow: bool) -> None:
        """Abbreviate or spell out the rows, after a resize. Redraws, never reads."""
        if narrow == self.narrow:
            return
        self.narrow = narrow
        # Row widths are cached by the Tree; they depend on the words chosen.
        self._invalidate()

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
        if not key and not parent.children and self.source.load_state("") == UNREADABLE:
            # The root is hidden, so an unreadable project would draw nothing -
            # the same blank as an empty one (ADR 0004). A row says which it is.
            # No data and no facts: it is not a node, and nothing acts on it.
            parent.add_leaf(Text(f"{tokens.load_style(UNREADABLE).suffix}  "
                                 f"{tokens.load_style(UNREADABLE).label} - "
                                 "Atlas could not list this project folder",
                                 style=tokens.PALETTE.muted))
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

    # ---- the Tree Region's filter (ADR 0005: `/` filters the focused Region)

    @property
    def filter_text(self) -> str:
        return self._filter

    def set_filter(self, query: str) -> None:
        """Show only the loaded nodes whose names contain ``query``, with the
        folders that lead to them; an empty query restores the tree as it was.

        Never reads. It searches what Atlas has already opened - the nodes the
        widget holds facts for - because a filter that walked the project to
        find a name would be the enumeration ticket 06 rules out, one keystroke
        at a time. A name inside a folder nobody opened is not found, which is
        the honest answer for a lazy tree.
        """
        query = query.strip().casefold()
        if query == self._filter:
            return
        if not self._filter:
            # Snapshot what is drawn - every loaded node, open or closed - and
            # the operator's own expansion, to give both back on clear.
            self._drawn = {}
            self._expanded_before = set()

            def walk(node: TreeNodeWidget, key: str) -> None:
                for child in node.children:
                    child_key = str(child.data or "")
                    if child_key not in self._facts:
                        continue
                    self._drawn.setdefault(key, []).append(self._facts[child_key])
                    if child.is_expanded:
                        self._expanded_before.add(child_key)
                    walk(child, child_key)

            walk(self.root, "")
        self._filter = query

        children = self._drawn
        keep: set[str] | None = None
        if query:
            keep = set()
            for facts in (f for group in children.values() for f in group):
                if query in facts.name.casefold():
                    key = facts.key
                    while key and key not in keep:
                        keep.add(key)
                        key = parent_key(key)

        self.reset("", data="")
        self._by_key = {"": self.root}

        def add(parent: TreeNodeWidget, key: str) -> None:
            for facts in children.get(key, ()):
                if keep is not None and facts.key not in keep:
                    continue
                if facts.is_dir:
                    expand = (facts.key in children and
                              (keep is not None or facts.key in self._expanded_before))
                    node = parent.add(facts.name, data=facts.key, expand=expand)
                    self._by_key[facts.key] = node
                    add(node, facts.key)
                else:
                    self._by_key[facts.key] = parent.add_leaf(facts.name, data=facts.key)

        add(self.root, "")
        if not query:
            self._expanded_before = set()
            self._drawn = {}
        if self.root.children:
            self.cursor_line = 0

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
        source.children(key)
        self.app.call_from_thread(self._loaded, key, source)

    def _loaded(self, key: str, source: ProjectTree | None = None) -> None:
        # Tagged with the project it was started for. One that finishes after
        # the operator moved on would otherwise re-read the *current* project
        # on the UI thread and clear its loading state early.
        if source is not None and source is not self.source:
            return
        if not key:
            self.loading = False
        node = self._by_key.get(key)
        if node is not None:
            self._fill(node, key)

    # ---- rendering -------------------------------------------------------

    def render_label(self, node: TreeNodeWidget, base_style, style):
        facts = self._facts.get(str(node.data or ""))
        if facts is None:
            return super().render_label(node, base_style, style)
        label = node_label(facts, narrow=self.narrow, expanded=node.is_expanded,
                           room=self._room(node))
        # Textual delivers the cursor and hover highlight only through `style`.
        # Dropping it drew every row the same, so the operator could not see
        # which node `f` would repair. The row's own colours sit under it; the
        # cursor, laid over the top, is the one full-strength thing (ticket 02).
        if base_style:
            label.stylize_before(base_style)
        if style:
            label.stylize(style)
        return label

    def get_label_width(self, node: TreeNodeWidget) -> int:
        facts = self._facts.get(str(node.data or ""))
        if facts is None:
            return super().get_label_width(node)
        return label_width(facts, narrow=self.narrow, expanded=node.is_expanded,
                           room=self._room(node))

    def _room(self, node: TreeNodeWidget) -> int:
        """The cells a node's label may use: the viewport less its guides.

        With the root hidden, a top-level node draws no guide; each level below
        it adds one ``guide_depth``-wide column. 0 while the widget has no size,
        which leaves the label unbounded.
        """
        width = self.scrollable_content_region.width
        if width <= 0:
            return 0
        depth = 0
        parent = node.parent
        while parent is not None and parent is not self.root:
            depth += 1
            parent = parent.parent
        return max(1, width - depth * self.guide_depth)
