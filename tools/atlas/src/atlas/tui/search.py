"""The Search Overlay: drive-wide search over the session Name Index and the
per-machine Content Index.

Not a Region - ADR 0005's three stand (amendment, ticket 33). The overlay is
episodic: opened with `g`, answered, dismissed with Escape, and the Regions
underneath keep their focus, their collapse and their cursor. It reads the
warm in-memory Name Index built at session start and on `r`, and the Content
Index from the local cache; it never enumerates or reads content at keystroke
time, which is what makes live-as-you-type affordable over the Drive mount
(ticket 08).

Content matches (ticket 35) rank below name matches and carry the matched
line as a snippet from the stored text - a query never re-reads a file to
show one. The Indexed-At Stamp is always visible while an index is loaded;
absent, building and failed states are one honest line each, never a silent
zero (ADR 0004). Result rows keep the colour-alone rule (ADR 0008): the kind
is a word at every width.

The geometry rules live in ``tui.layout`` (``search_overlay_width``); this
widget applies them.
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

from ..core.contentindex import ContentHit, ContentIndex, query_index
from ..core.search import RESULT_CAP, NameHit, NameIndex, search_names
from . import tokens
from .layout import search_overlay_cells, search_overlay_width
from .treeview import middle_ellipsis

# What the overlay hands back to the app: (REVEAL, hit) selects the project
# and opens the tree to the node; (OPEN, hit) opens the file or folder with
# the OS. None is an Escape - nothing to do, nothing disturbed.
REVEAL = "reveal"
OPEN = "open"

Hit = NameHit | ContentHit


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


def content_result_text(hit: ContentHit, cells: int) -> Text:
    """One content match: the kind word, the path, then the matched line.

    The snippet is what separates a content hit from a name hit at a glance -
    the kind word (``pdf``/``markdown``/``text``) already says it is not a
    ``file``/``folder`` name match, so the distinction never rides on colour.
    """
    kind = hit.kind
    snippet = hit.snippet
    room = cells - len(kind) - 2
    if snippet:
        # The path keeps enough to be identified; the snippet gets the rest.
        path = middle_ellipsis(hit.path, max(8, room * 2 // 5))
        snippet = middle_ellipsis(snippet, max(0, room - len(path) - 2))
    else:
        path = middle_ellipsis(hit.path, max(8, room))
    row = Text()
    row.append(kind, style=tokens.PALETTE.muted)
    row.append("  ")
    row.append(path, style=tokens.PALETTE.ink)
    if snippet:
        row.append("  ")
        row.append(snippet, style=tokens.PALETTE.muted)
    return row


def _stamp_short(stamp: str, *, date_only: bool = False) -> str:
    """The Indexed-At Stamp for a status line: '2026-10-09 07:31'."""
    date, _, time = stamp.partition("T")
    if date_only or not time:
        return date
    return f"{date} {time[:5]}"


def _fit_line(candidates: list[str], cells: int) -> str:
    """The first candidate that fits; the last, ellipsised, if none does.

    The content line is fitted, never clipped mid-word by the widget - the
    pointer at `atlas index build` is only useful whole.
    """
    for line in candidates:
        if len(line) <= cells:
            return line
    return middle_ellipsis(candidates[-1], cells)


class SearchOverlay(ModalScreen[tuple[str, Hit] | None]):
    """The overlay itself: one input, one status line, the capped results."""

    BINDINGS = [
        Binding("escape", "cancel", "Close", show=False),
        Binding("o", "open_hit", "Open", show=False),
        # From the input, down moves into the results. The OptionList's own
        # binding wins once it has focus, so this only ever fires in the input.
        Binding("down", "focus_results", "Results", show=False),
    ]

    def __init__(self, index: NameIndex | None, *,
                 content_index: ContentIndex | None = None,
                 content_building: bool = False,
                 content_progress: tuple[int, int] | None = None,
                 content_error: str | None = None,
                 cap: int = RESULT_CAP) -> None:
        super().__init__()
        self._index = index
        self._content_index = content_index
        self._content_building = content_building
        self._content_progress = content_progress
        self._content_error = content_error
        self._cap = cap
        # The hits as currently drawn, aligned with the OptionList's order.
        self._hits: tuple[Hit, ...] = ()
        # The last content query, so the stamp line can carry its counts.
        self._content_total = 0
        self._content_stale = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="search-dialog"):
            yield Static("Search the drive", id="search-title", markup=False)
            yield Input(placeholder="Folder, file or project name", id="search-input")
            yield Static("", id="search-status", markup=False)
            yield OptionList(id="search-results")
            yield Static("", id="search-content", markup=False)
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

    def set_content_index(self, index: ContentIndex) -> None:
        """The Content Index landed (loaded from cache, or a build finished)."""
        self._content_index = index
        self._content_building = False
        self._content_progress = None
        self._content_error = None
        self._refresh_results()

    def set_content_building(self, progress: tuple[int, int] | None = None) -> None:
        """The background first build is running; the overlay never blocks on
        it, it says so."""
        self._content_building = True
        self._content_progress = progress
        self._refresh_results()

    def set_content_error(self, message: str) -> None:
        """A failed build is not an absent index - say which (ADR 0004)."""
        self._content_building = False
        self._content_error = message
        self._refresh_results()

    def _content_line(self, cells: int) -> str:
        """The Content Index's one honest line: stamp, building, absent or
        failed - never a silent nothing (ADR 0004). Fitted to the dialog."""
        if self._content_error is not None:
            return _fit_line([
                f"content index failed: {self._content_error} - name matches only",
                f"content index failed: {self._content_error}",
            ], cells)
        if self._content_building:
            progress = ""
            if self._content_progress is not None:
                done, total = self._content_progress
                progress = f" {done}/{total} files" if total else ""
            return _fit_line([
                f"content index building{progress} - name matches for now",
                f"content index building{progress}",
                "content index building",
            ], cells)
        if self._content_index is None:
            return _fit_line([
                "no content index - `atlas index build` builds one",
                "no content index - run `atlas index build`",
                "no content index - atlas index build",
            ], cells)
        stamp = _stamp_short(self._content_index.indexed_at)
        date = _stamp_short(self._content_index.indexed_at, date_only=True)
        if not self.query_one("#search-input", Input).value.strip():
            return _fit_line([f"content: indexed {stamp}", f"content: indexed {date}"],
                             cells)
        found = f"{self._content_total} content match" + (
            "es" if self._content_total != 1 else "")
        if self._content_stale:
            found += f", {self._content_stale} stale"
        return _fit_line([
            f"{found} - indexed {stamp}",
            f"{found} - {date}",
            found,
        ], cells)

    def _refresh_results(self) -> None:
        status = self.query_one("#search-status", Static)
        options = self.query_one("#search-results", OptionList)
        cells = search_overlay_cells(self.size.width or 80)
        content_line = self.query_one("#search-content", Static)
        options.clear_options()
        self._hits = ()
        self._content_total = 0
        self._content_stale = 0
        if self._index is None:
            status.update("Indexing drive names - one moment.")
            content_line.update(self._content_line(cells))
            return
        query = self.query_one("#search-input", Input).value.strip()
        if not query:
            status.update("Type to search every folder, file and project name.")
            content_line.update(self._content_line(cells))
            return
        result = search_names(self._index, query, cap=self._cap)
        content_result = None
        if self._content_index is not None:
            content_result = query_index(self._content_index, query, cap=self._cap)
            self._content_total = content_result.total
            self._content_stale = content_result.stale
        content_hits = content_result.hits if content_result is not None else ()
        # Name matches rank first (ticket 35); the two kinds never mix.
        self._hits = (*result.hits, *content_hits)
        if not self._hits:
            status.update(f"No matches for '{query}'.")
            content_line.update(self._content_line(cells))
            return
        options.add_options(
            Option(result_text(hit, cells)) for hit in result.hits)
        options.add_options(
            Option(content_result_text(hit, cells)) for hit in content_hits)
        options.highlighted = 0
        noun = "match" if result.total == 1 else "matches"
        # Short enough to hold at 46 columns, where the dialog has 34 cells.
        overflow = f" - {result.overflow} more" if result.overflow else ""
        if result.hits:
            status.update(f"{result.total} {noun}{overflow}")
        else:
            # Content matched where no name did; that is not "no matches".
            status.update(f"No name matches - {self._content_total} in contents")
        if self._index.unreadable:
            status.update(
                f"{result.total} {noun}{overflow} - "
                f"{len(self._index.unreadable)} folder(s) unreadable, "
                "results may be incomplete")
        content_line.update(self._content_line(cells))

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

    def _highlighted(self) -> Hit | None:
        if not self._hits:
            return None
        highlighted = self.query_one("#search-results", OptionList).highlighted
        return self._hits[highlighted or 0]

    def action_cancel(self) -> None:
        self.dismiss(None)
