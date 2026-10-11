"""Content search over the Content Index (ticket 35; tickets 08/33/34, ADR
0020).

Content matches join the Search Overlay below name matches, carrying the
matched line as a snippet; `atlas search --content` is the CLI form owed in
the same session (ADR 0008). Query-time freshness is revalidation by
path+size+mtime - a changed file is stale, counted and excluded, never
silently served on old text - and re-extraction is a top-up's job, not a
query's. The Indexed-At Stamp is visible in both surfaces; absent, building
and failed indexes are one honest line each, never a silent zero (ADR 0004).

Overlay states rendered headless at the measured widths: 179, 153, 120, 87,
77, 46 columns; 51, 30, 24 rows. The cache dir is always a test tmp path
(conftest `_local_cache`); the real machine cache is never touched.
"""

from __future__ import annotations

import json

from textual.widgets import Input, OptionList, Static

from atlas.cli import main
from atlas.core.contentindex import build_index, load_index, query_index
from atlas.core.search import build_name_index
from atlas.tui.app import AtlasApp
from atlas.tui.layout import search_overlay_cells
from atlas.tui.search import SearchOverlay
from atlas.tui.treeview import ProjectTreeView

from conftest import make_pdf, make_project

# The measured terminals (map.md): columns trimodal, rows near-constant at 51.
WIDTHS = (179, 153, 120, 87, 77, 46)
ROWS = (51, 30, 24)

MD = "260813_Alpha/06 Research/Code/zoning notes.md"
PDF = "260813_Alpha/PERMIT-set.pdf"


def _drive(drive):
    make_project(drive, "260813_Alpha",
                 sections=["01 Model", "06 Research/Code"],
                 files={"06 Research/Code/zoning notes.md": "Zoning  Variance\n\nAPPROVED",
                        "01 Model/model notes.txt": "grid lines and levels"})
    make_pdf(drive / "260813_Alpha" / "PERMIT-set.pdf",
             text="A-101 LEVEL ONE PLAN", title="ISSUED FOR PERMIT")
    make_project(drive, "260901_Beta", sections=["11 Meetings"],
                 files={"11 Meetings/minutes.markdown": "client approved the scheme"})


async def settle(app, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def _overlay(app) -> SearchOverlay:
    assert isinstance(app.screen, SearchOverlay), f"overlay not open: {app.screen!r}"
    return app.screen


def _rows(overlay: SearchOverlay) -> list[str]:
    options = overlay.query_one("#search-results", OptionList)
    return [options.get_option_at_index(i).prompt.plain for i in range(options.option_count)]


def _status(overlay: SearchOverlay) -> str:
    return str(overlay.query_one("#search-status", Static).content)


def _content_line(overlay: SearchOverlay) -> str:
    return str(overlay.query_one("#search-content", Static).content)


# ------------------------------------------------------------- the core seam


def test_a_hit_carries_the_matched_line(fixture_drive):
    _drive(fixture_drive)
    index = build_index(fixture_drive)

    hit = query_index(index, "zoning variance").hits[0]

    assert hit.path == MD
    assert "zoning variance" in hit.snippet
    # The NameHit parity the overlay's reveal/open actions are written against.
    assert hit.project == "260813_Alpha"
    assert hit.name == "zoning notes.md"
    assert hit.node_key == "06 Research/Code/zoning notes.md"


def test_pdf_text_and_markdown_both_match(fixture_drive):
    """The ticket's done-when: a PDF-text phrase and a Markdown phrase, one
    index, one query seam."""
    _drive(fixture_drive)
    index = build_index(fixture_drive)

    assert [h.path for h in query_index(index, "issued for permit").hits] == [PDF]
    assert [h.path for h in query_index(index, "zoning variance").hits] == [MD]


def test_an_edited_file_is_stale_until_a_topup_reindexes_it(fixture_drive):
    """A file edited after indexing is never silently matched on old text:
    the query counts it stale, and the next build re-extracts it so the new
    text matches."""
    _drive(fixture_drive)
    index = build_index(fixture_drive)
    (fixture_drive / MD).write_text("board approved the rooftop deck", encoding="utf-8")

    stale = query_index(index, "zoning variance")
    assert stale.hits == () and stale.stale == 1
    assert query_index(index, "rooftop deck").hits == ()

    topped_up = build_index(fixture_drive)
    result = query_index(topped_up, "rooftop deck")
    assert [h.path for h in result.hits] == [MD]
    assert result.stale == 0
    assert "rooftop deck" in result.hits[0].snippet


def test_a_deleted_files_match_disappears(fixture_drive):
    _drive(fixture_drive)
    index = build_index(fixture_drive)
    (fixture_drive / MD).unlink()

    result = query_index(index, "zoning variance")
    assert result.hits == () and result.stale == 1


# ------------------------------------------------------------- the CLI


def _search(drive, capsys, *args):
    status = main(["search", *args, "--drive", str(drive)])
    return status, capsys.readouterr()


def test_search_content_finds_pdf_and_markdown_text(fixture_drive, capsys):
    _drive(fixture_drive)
    build_index(fixture_drive)

    status, out = _search(fixture_drive, capsys, "issued for permit", "--content")
    assert status == 0
    assert f"pdf  {PDF}" in out.out
    assert "indexed at" in out.out

    status, out = _search(fixture_drive, capsys, "zoning variance", "--content")
    assert status == 0
    assert f"markdown  {MD}" in out.out
    assert "zoning variance" in out.out  # the snippet


def test_search_content_without_an_index_says_so_and_serves_names(fixture_drive, capsys):
    """Never a silent zero: no index is said aloud, with the build named, and
    name matches are still served."""
    _drive(fixture_drive)

    status, out = _search(fixture_drive, capsys, "zoning", "--content")
    assert status == 0   # the name match stands on its own
    assert "no content index" in out.out
    assert "atlas index build" in out.out
    assert f"file  {MD}" in out.out

    status, out = _search(fixture_drive, capsys, "zzz nothing", "--content")
    assert status == 1
    assert "no matches" in out.out.casefold()
    assert "no content index" in out.out


def test_search_content_json_names_its_fields(fixture_drive, capsys):
    _drive(fixture_drive)
    index = build_index(fixture_drive)

    status = main(["search", "zoning variance", "--content", "--json",
                   "--drive", str(fixture_drive)])
    payload = json.loads(capsys.readouterr().out)

    assert status == 0
    content = payload["content"]
    assert content["indexed_at"] == index.indexed_at
    assert content["total"] == content["shown"] == 1
    assert content["stale"] == 0
    hit = content["results"][0]
    assert hit["path"] == MD and hit["kind"] == "markdown"
    assert hit["project"] == "260813_Alpha"
    assert "zoning variance" in hit["snippet"]


def test_search_content_json_is_null_without_an_index(fixture_drive, capsys):
    _drive(fixture_drive)
    status = main(["search", "zoning", "--content", "--json",
                   "--drive", str(fixture_drive)])
    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["content"] is None
    # The ticket-33 shape is untouched: no flag, no key.
    status = main(["search", "zoning", "--json", "--drive", str(fixture_drive)])
    payload = json.loads(capsys.readouterr().out)
    assert "content" not in payload


def test_search_content_json_counts_the_stale(fixture_drive, capsys):
    _drive(fixture_drive)
    build_index(fixture_drive)
    (fixture_drive / MD).write_text("board approved the rooftop deck", encoding="utf-8")

    status = main(["search", "zoning variance", "--content", "--json",
                   "--drive", str(fixture_drive)])
    payload = json.loads(capsys.readouterr().out)
    assert payload["content"]["stale"] == 1
    assert payload["content"]["results"] == []
    assert status == 1   # nothing valid matched


# ------------------------------------------------------------- the overlay


async def test_content_matches_join_below_name_matches(fixture_drive):
    """A phrase that hits a name and file contents lists the name first; the
    content row carries its kind word and the matched line (ADR 0008: never
    colour alone)."""
    _drive(fixture_drive)
    index = build_index(fixture_drive)

    app = AtlasApp(fixture_drive, follow_debounce=0)
    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        app.push_screen(SearchOverlay(build_name_index(fixture_drive),
                                      content_index=index))
        await settle(app, pilot)
        overlay = _overlay(app)
        await pilot.press(*"zoning")
        await settle(app, pilot)

        rows = _rows(overlay)
        assert rows[0].startswith("file"), rows        # the name match first
        content_rows = [r for r in rows if r.startswith("markdown")]
        assert len(content_rows) == 1, rows
        # The path is fitted (ellipsised) at this width; the name survives,
        # and the snippet is the matched line from the stored text.
        assert "zoning notes.md" in content_rows[0]
        assert "zoning variance approved" in content_rows[0]
        assert "1 content match" in _content_line(overlay)
        assert index.indexed_at.partition("T")[0] in _content_line(overlay)


async def test_the_stamp_is_visible_before_any_query(fixture_drive):
    _drive(fixture_drive)
    index = build_index(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        app.push_screen(SearchOverlay(build_name_index(fixture_drive),
                                      content_index=index))
        await settle(app, pilot)
        overlay = _overlay(app)
        line = _content_line(overlay)
        assert "content: indexed" in line
        assert index.indexed_at.partition("T")[0] in line


async def test_a_content_only_match_is_not_no_matches(fixture_drive):
    """Contents matched where no name did: the status must not read 'No
    matches' (ADR 0004)."""
    _drive(fixture_drive)
    index = build_index(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        app.push_screen(SearchOverlay(build_name_index(fixture_drive),
                                      content_index=index))
        await settle(app, pilot)
        overlay = _overlay(app)
        await pilot.press(*"rooftop variance phrase")   # matches nothing
        await settle(app, pilot)
        assert _status(overlay).startswith("No matches")

        input_ = overlay.query_one("#search-input", Input)
        input_.value = "level one plan"                  # PDF text only
        await settle(app, pilot)
        assert "No name matches" in _status(overlay)
        assert "1 in contents" in _status(overlay)
        rows = _rows(overlay)
        assert len(rows) == 1 and rows[0].startswith("pdf"), rows


async def test_the_stale_count_is_shown(fixture_drive):
    _drive(fixture_drive)
    index = build_index(fixture_drive)
    (fixture_drive / MD).write_text("board approved the rooftop deck", encoding="utf-8")
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        app.push_screen(SearchOverlay(build_name_index(fixture_drive),
                                      content_index=index))
        await settle(app, pilot)
        overlay = _overlay(app)
        await pilot.press(*"zoning variance")
        await settle(app, pilot)
        assert "1 stale" in _content_line(overlay)
        # The stale hit is excluded and counted, never served on old text.
        assert _rows(overlay) == []


async def test_a_cold_index_is_one_honest_line_and_names_still_search(fixture_drive):
    """No index: said so, `atlas index build` named, name search unaffected."""
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        app.push_screen(SearchOverlay(build_name_index(fixture_drive)))
        await settle(app, pilot)
        overlay = _overlay(app)
        line = _content_line(overlay)
        assert "no content index" in line and "atlas index build" in line

        await pilot.press(*"zoning")
        await settle(app, pilot)
        assert any(MD in row for row in _rows(overlay))
        assert "1 match" in _status(overlay)


async def test_a_building_index_is_one_honest_line(fixture_drive):
    """Still building: said so, with progress when known, and the overlay
    never blocks waiting."""
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        app.push_screen(SearchOverlay(build_name_index(fixture_drive),
                                      content_building=True,
                                      content_progress=(12, 40)))
        await settle(app, pilot)
        overlay = _overlay(app)
        line = _content_line(overlay)
        assert "building" in line and "12/40" in line

        await pilot.press(*"zoning")
        await settle(app, pilot)
        assert any(MD in row for row in _rows(overlay))  # names still search

        # The build landing warms the open overlay in place.
        overlay.set_content_index(build_index(fixture_drive))
        await settle(app, pilot)
        assert "indexed" in _content_line(overlay)


async def test_a_failed_build_is_not_an_absent_index(fixture_drive):
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        app.push_screen(SearchOverlay(build_name_index(fixture_drive),
                                      content_error="mount vanished"))
        await settle(app, pilot)
        line = _content_line(_overlay(app))
        assert "failed" in line and "mount vanished" in line


async def test_the_app_first_builds_an_absent_index_in_the_background(fixture_drive):
    """The console's first-build worker (ADR 0020 #5): a drive with no index
    gets one, off the UI thread, and an open overlay warms in place."""
    _drive(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        assert app._content_index is not None
        assert not app._content_building
        assert load_index(fixture_drive) is not None

        await pilot.press("g")
        await settle(app, pilot)
        overlay = _overlay(app)
        assert "indexed" in _content_line(overlay)
        await pilot.press(*"issued for permit")
        await settle(app, pilot)
        assert any(row.startswith("pdf") for row in _rows(overlay))


async def test_an_enter_on_a_content_hit_reveals_the_file_in_the_tree(fixture_drive):
    _drive(fixture_drive)
    build_index(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        await settle(app, pilot)
        await pilot.press("g")
        await pilot.press(*"level one plan")
        await settle(app, pilot)
        await pilot.press("enter")
        await settle(app, pilot)

        assert not isinstance(app.screen, SearchOverlay)
        assert app._workspace_project == "260813_Alpha"
        facts = app.query_one(ProjectTreeView).selected_facts()
        assert facts is not None and facts.key == "PERMIT-set.pdf"


# ------------------------------------------------------------- headless renders


async def test_content_states_at_the_measured_widths(fixture_drive):
    """Cold, building and warm states, every measured width: the stamp (or the
    honest state line) fits the dialog, rows keep their kind word, and no
    drawn line passes the list's edge."""
    _drive(fixture_drive)
    index = build_index(fixture_drive)
    name_index = build_name_index(fixture_drive)

    for width in WIDTHS:
        for content_kwargs in (
            {},                                              # cold
            {"content_building": True, "content_progress": (3, 9)},
            {"content_index": index},                        # warm
        ):
            app = AtlasApp(fixture_drive, follow_debounce=0)
            async with app.run_test(size=(width, 51)) as pilot:
                await settle(app, pilot)
                app.push_screen(SearchOverlay(name_index, **content_kwargs))
                await settle(app, pilot)
                overlay = _overlay(app)
                cells = search_overlay_cells(width)

                line = _content_line(overlay)
                assert line and len(line) <= cells, (width, content_kwargs, line)
                if "content_index" in content_kwargs:
                    assert "indexed" in line
                elif "content_building" in content_kwargs:
                    assert "building" in line
                else:
                    assert "no content index" in line

                await pilot.press(*"zoning")
                await settle(app, pilot)
                assert len(_content_line(overlay)) <= cells, (width, _content_line(overlay))
                assert len(_status(overlay)) <= cells, (width, _status(overlay))
                for row in _rows(overlay):
                    assert len(row) <= cells + 2, (width, row)


async def test_content_rows_hold_at_30_and_24_rows(fixture_drive):
    _drive(fixture_drive)
    index = build_index(fixture_drive)
    name_index = build_name_index(fixture_drive)

    for width, rows in ((120, 30), (87, 24), (46, 24)):
        app = AtlasApp(fixture_drive, follow_debounce=0)
        async with app.run_test(size=(width, rows)) as pilot:
            await settle(app, pilot)
            app.push_screen(SearchOverlay(name_index, content_index=index))
            await settle(app, pilot)
            overlay = _overlay(app)
            await pilot.press(*"variance")
            await settle(app, pilot)
            dialog = overlay.query_one("#search-dialog")
            assert dialog.size.height <= rows, (width, rows)
            # The stamp survives at every width (the date, when the full word
            # and timestamp no longer fit).
            assert index.indexed_at.partition("T")[0] in _content_line(overlay)
            assert any(row.startswith("markdown") for row in _rows(overlay))
