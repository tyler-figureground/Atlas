"""Reference Sets: `atlas refs gallery` - the human-facing HTML page.

One self-contained page beside the sets README: a tile per set under the same
lifecycle bands as `refs index`, status as word plus colour, exemplar quick
links, drawing-set thumbnails from Pages/ exports. Doctor tests live in
test_refs_doctor.py, index tests in test_refs_index.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.refsets import list_sets
from atlas.core.refsgallery import (
    FOOTER,
    GALLERY_NAME,
    gallery_html,
    when_to_use,
    write_gallery,
)
from test_refs_doctor import NOTES_FULL, _exemplar

CARD_GALLERY = """---
type: {type}
title: {title}
status: {status}
---

# {title} - reference set
> **Use when:** {when}.
> **Start from:** a blank file.

## When to use / when not

- **Use:** {when}.
"""


def _set(root: Path, name: str, status: str = "candidate",
         when: str = "a deliverable of this kind") -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    slug = name.split(None, 1)[1] if " " in name else name
    type_ = slug.lower().replace(" ", "-")
    (folder / "SET.md").write_text(
        CARD_GALLERY.format(type=type_, title=slug, status=status, when=when),
        encoding="utf-8")
    return folder


@pytest.fixture
def gallery_root(tmp_path: Path) -> Path:
    """Sets across bands: a drawing set with Pages/ thumbnails, a set whose
    exemplar is a frozen PDF, a bare set with none of either."""
    root = tmp_path / "Reference Sets"
    code = _set(root, "03 Code Analysis", "approved", "the governing-code analysis")
    _exemplar(code, "E1 Monte Vista - CRC", "E1", NOTES_FULL)
    plans = _set(root, "21 Floor Plans", "approved", "a dimensioned floor plan")
    e1 = _exemplar(plans, "E1 Monte Vista - Napa bedroom addition", "E1", NOTES_FULL)
    pages = e1 / "Pages"
    pages.mkdir()
    (pages / "01-a101-full-sheet.png").write_bytes(b"\x89PNG")
    (pages / "02-a101-strings.png").write_bytes(b"\x89PNG")
    cds = _set(root, "26 CD Sets", "candidate", "assembling the issued PDF set")
    cde1 = _exemplar(cds, "E1 Coleman - 23-Sheet Construction Set", "E1", NOTES_FULL)
    (cde1 / "2026-10-08 - 1757 Coleman A - Construction Set.pdf").write_bytes(b"%PDF")
    _set(root, "90 Control File - BRIEF", "retired", "every project, always")
    return root


def _html(root: Path) -> str:
    return gallery_html(root, list_sets(root))


# ---- the page -------------------------------------------------------------


def test_tile_per_set_with_name_number_chip_and_badge(gallery_root: Path):
    page = _html(gallery_root)
    assert page.count('<article class="tile"') == 4
    # the name drops the numeric prefix; the number survives as a chip
    assert "<h3>Code Analysis <span class=\"chip\">03</span>" in page
    assert "<h3>Floor Plans <span class=\"chip\">21</span>" in page
    # status is a word AND a colour class - never colour alone (ADR 0008)
    assert '<span class="badge approved">approved</span>' in page
    assert '<span class="badge candidate">candidate</span>' in page
    assert '<span class="badge retired">retired</span>' in page


def test_band_grouping_in_lifecycle_order_with_nav(gallery_root: Path):
    page = _html(gallery_root)
    headings = [line for line in page.splitlines() if line.startswith("<h2>")]
    assert headings == ["<h2>Due diligence</h2>", "<h2>Drawings</h2>",
                        "<h2>Control files</h2>"]
    nav = [line for line in page.splitlines() if line.startswith('<nav class="bands">')]
    assert len(nav) == 1
    assert '<a href="#dd">Due diligence</a>' in nav[0]
    assert '<a href="#dw">Drawings</a>' in nav[0]
    assert '<a href="#cf">Control files</a>' in nav[0]
    assert '<section class="band" id="dd">' in page
    # sections appear in band order
    assert page.index('id="dd"') < page.index('id="dw"') < page.index('id="cf"')


def test_when_to_use_from_the_card_strip_with_title_fallback(gallery_root: Path):
    page = _html(gallery_root)
    assert '<p class="when">the governing-code analysis</p>' in page
    card = gallery_root / "03 Code Analysis" / "SET.md"
    card.write_text("---\ntype: code-analysis\ntitle: Code Analysis Memo\n"
                    "status: approved\n---\n\n# Code Analysis Memo\n", encoding="utf-8")
    page = _html(gallery_root)
    assert '<p class="when">Code Analysis Memo</p>' in page


def test_when_to_use_parser_variants():
    strip = "# Card\n> **Use when:** a meeting transcript exists.\n"
    assert when_to_use(strip, "fallback") == "a meeting transcript exists"
    bullet = "# Card\n\n## When to use / when not\n\n- **Use:** outline specs.\n"
    assert when_to_use(bullet, "fallback") == "outline specs"
    assert when_to_use("# bare card\n", "fallback") == "fallback"


def test_thumbnail_only_when_pages_pngs_exist(gallery_root: Path):
    page = _html(gallery_root)
    thumb = ("21%20Floor%20Plans/E1%20Monte%20Vista%20-%20Napa%20bedroom%20addition/"
             "Pages/01-a101-full-sheet.png")
    assert f'<img src="{thumb}"' in page
    assert 'loading="lazy"' in page
    assert page.count("<img ") == 1  # the other three sets stay plain tiles
    # a Pages folder with no PNGs is no thumbnail either
    bare = gallery_root / "26 CD Sets" / "E1 Coleman - 23-Sheet Construction Set" / "Pages"
    bare.mkdir()
    assert _html(gallery_root).count("<img ") == 1


def test_exemplar_links_pdf_direct_else_folder(gallery_root: Path):
    page = _html(gallery_root)
    # a frozen PDF opens natively in the browser - link straight to the file
    assert ('<a href="26%20CD%20Sets/E1%20Coleman%20-%2023-Sheet%20Construction%20Set/'
            '2026-10-08%20-%201757%20Coleman%20A%20-%20Construction%20Set.pdf">E1</a>') in page
    # no PDF: the link is the folder, trailing slash
    assert '<a href="03%20Code%20Analysis/E1%20Monte%20Vista%20-%20CRC/">E1</a>' in page


def test_card_folder_and_junior_links_escaped_and_relative(gallery_root: Path):
    page = _html(gallery_root)
    assert '<a href="03%20Code%20Analysis/SET.md">Card</a>' in page
    assert '<a href="03%20Code%20Analysis/">Folder</a>' in page
    assert '<a href="90%20Control%20File%20-%20BRIEF/">Folder</a>' in page
    # the junior quick start lives one level up, prominent in the header
    assert '<a href="../Reference%20Sets%20-%20Junior%20Quick%20Start.md">' in page


def test_filter_box_and_footer_present(gallery_root: Path):
    page = _html(gallery_root)
    assert '<input id="filter"' in page
    assert 'data-search="' in page  # every tile carries its filter haystack
    assert "the governing-code analysis" in page.split('data-search="', 1)[1]
    assert f"<footer>{FOOTER}</footer>" in page


def test_self_contained_no_network(gallery_root: Path):
    page = _html(gallery_root).lower()
    assert "http" not in page  # no external fonts, libs, images or anchors
    assert "<style>" in page and "</style>" in page
    assert "<script>" in page and "</script>" in page
    assert "@import" not in page and "<link" not in page


def test_no_emojis_or_em_dashes_in_copy(gallery_root: Path):
    page = _html(gallery_root)
    assert "\u2014" not in page  # em dash
    assert "\u2013" not in page  # en dash


def test_gallery_is_byte_idempotent(gallery_root: Path):
    sets = list_sets(gallery_root)
    assert gallery_html(gallery_root, sets) == gallery_html(gallery_root, sets)
    path = write_gallery(gallery_root, sets)
    first = path.read_bytes()
    write_gallery(gallery_root, list_sets(gallery_root))
    assert path.read_bytes() == first


# ---- the CLI --------------------------------------------------------------


def test_gallery_cli_writes_beside_the_readme(gallery_root: Path, capsys):
    (gallery_root / "README.md").write_text("# Reference Sets\n", encoding="utf-8")
    assert main(["refs", "gallery", "--root", str(gallery_root)]) == 0
    out = capsys.readouterr().out
    path = gallery_root / GALLERY_NAME
    assert str(path) in out
    assert path.is_file()
    head = path.read_text(encoding="utf-8").splitlines()[0]
    assert head == "<!DOCTYPE html>"


def test_gallery_cli_json(gallery_root: Path, capsys):
    assert main(["refs", "gallery", "--root", str(gallery_root), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["gallery"] == str(gallery_root / GALLERY_NAME)
    assert out["tiles"] == 4
    assert out["thumbnails"] == 1
    assert out["sets"] == ["code-analysis", "floor-plans", "cd-sets",
                           "control-file---brief"]


def test_gallery_missing_root_is_an_error(tmp_path: Path):
    assert main(["refs", "gallery", "--root", str(tmp_path / "nope")]) == 2
