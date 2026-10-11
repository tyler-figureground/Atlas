"""The Search Overlay: drive-wide name search over the session Name Index.

Not a Region - ADR 0005's three stand (amendment, ticket 33). The overlay is
episodic: opened with `g`, answered, dismissed with Escape, and the Regions
underneath keep their focus, their collapse and their cursor. It reads the
warm in-memory Name Index built at session start and on `r`; it never
enumerates or reads content at keystroke time, which is what makes
live-as-you-type affordable over the Drive mount (ticket 08).

The geometry rules live in ``tui.layout`` (``search_overlay_width``); this
widget applies them. Result rows carry the kind as a word - colour may
reinforce the distinction between a folder and a file and never carries it
alone (ADR 0008).
"""

from __future__ import annotations

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from ..core.search import RESULT_CAP, NameHit, NameIndex, search_names
from . import tokens
from .layout import search_overlay_cells, search_overlay_width
from .treeview import middle_ellipsis

# What the overlay hands back to the app: (REVEAL, hit) selects the project
# and opens the tree to the node; (OPEN, hit) opens the file or folder with
# the OS. None is an Escape - nothing to do, nothing disturbed.
REVEAL = "reveal"
OPEN = "open"


def result_text(hit: NameHit, cells: int) -> Text:
    """One result row, fitted to ``cells``.

    Never a ``str`` - a folder named ``[2024] Survey`` would be parsed as
    markup (ticket 05). The kind is spelled out at every width: hue alone
    telling a folder from a file is exactly what ADR 0008 rules out.
    """
    kind = hit.kind
    path = middle_ellipsis(hit.path, max(8, cells - len(kind) - 2))
    row = Text()
    row.append(kind, style=tokens.PALETTE.muted)
    row.append("  ")
    row.append(path, style=tokens.PALETTE.ink)
    return row


class SearchOverlay(ModalScreen[tuple[str, NameHit] | None]):
    """The overlay itself: one input, one status line, the capped results."""

    BINDINGS = [
        Binding("escape", "cancel", "Close", show=False),
        Binding("o", "open_hit", "Open", show=False),
        # From the input, down moves into the results. The OptionList's own
        # binding wins once it has focus, so this only ever fires in the input.
        Binding("down", "focus_results", "Results", show=False),
    ]

    def __init__(self, index: NameIndex | None, *, cap: int = RESULT_CAP) -> None:
        super().__init__()
        self._index = index
        self._cap = cap
        # The hits as currently drawn, aligned with the OptionList's order.
        self._hits: tuple[NameHit, ...] = ()

    def compose(self) -> ComposeResult:
        with Vertical(id="search-dialog"):
            yield Static("Search the drive", id="search-title", markup=False)
            yield Input(placeholder="Folder, file or project name", id="search-input")
            yield Static("", id="search-status", markup=False)
            yield OptionList(id="search-results")
            # `o` lives on the list, not the input - in the input it is a
            # letter. Saying so is cheaper than an operator discovering it.
            yield Static("Enter reveal   o open   Esc close", id="search-keys",
                         markup=False)

    def on_mount(self) -> None:
        self._fit()
        self.query_one("#search-input", Input).focus()
        self._refresh_results()

    def on_resize(self, event: events.Resize) -> None:
        # The dialog follows the terminal (layout.search_overlay_width), and
        # the rows are fitted to what it leaves, so a resize re-fits both.
        self._fit()
        self._refresh_results()

    def _fit(self) -> None:
        self.query_one("#search-dialog").styles.width = (
            search_overlay_width(self.size.width or 80))

    # ---- content ---------------------------------------------------------

    def set_index(self, index: NameIndex) -> None:
        """Hand over the index when its build lands while the overlay is open.

        The loading line is what a not-yet-built index shows; the operator
        watching it should see it warm up, not have to reopen the overlay.
        """
        self._index = index
        self._refresh_results()

    def _refresh_results(self) -> None:
        status = self.query_one("#search-status", Static)
        options = self.query_one("#search-results", OptionList)
        options.clear_options()
        self._hits = ()
        if self._index is None:
            status.update("Indexing drive names - one moment.")
            return
        query = self.query_one("#search-input", Input).value.strip()
        if not query:
            status.update("Type to search every folder, file and project name.")
            return
        result = search_names(self._index, query, cap=self._cap)
        self._hits = result.hits
        if not result.hits:
            status.update(f"No matches for '{query}'.")
            return
        cells = search_overlay_cells(self.size.width or 80)
        options.add_options(Option(result_text(hit, cells)) for hit in result.hits)
        options.highlighted = 0
        noun = "match" if result.total == 1 else "matches"
        # Short enough to hold at 46 columns, where the dialog has 34 cells.
        overflow = f" - {result.overflow} more" if result.overflow else ""
        status.update(f"{result.total} {noun}{overflow}")
        if self._index.unreadable:
            status.update(
                f"{result.total} {noun}{overflow} - "
                f"{len(self._index.unreadable)} folder(s) unreadable, "
                "results may be incomplete")

    # ---- keys ------------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self._refresh_results()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter in the input activates the highlighted result."""
        if event.input.id == "search-input":
            self._activate()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if 0 <= event.option_index < len(self._hits):
            self.dismiss((REVEAL, self._hits[event.option_index]))

    def action_focus_results(self) -> None:
        if self._hits:
            self.query_one("#search-results", OptionList).focus()

    def action_open_hit(self) -> None:
        hit = self._highlighted()
        if hit is not None:
            self.dismiss((OPEN, hit))

    def _activate(self) -> None:
        hit = self._highlighted()
        if hit is not None:
            self.dismiss((REVEAL, hit))

    def _highlighted(self) -> NameHit | None:
        if not self._hits:
            return None
        highlighted = self.query_one("#search-results", OptionList).highlighted
        return self._hits[highlighted or 0]

    def action_cancel(self) -> None:
        self.dismiss(None)
