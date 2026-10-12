"""Reference Sets: `atlas refs index` - the visual contents block.

Ergonomics plan Phase 2: the README's atlas:contents block is a Mermaid band
map plus one 3-column table per lifecycle band, both generated from the same
card front matter so they cannot drift (rules/visual-markdown.md). Doctor
tests live in test_refs_doctor.py.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.refsets import (
    CONTENTS_BEGIN,
    CONTENTS_END,
    RefSetError,
    band_for,
    contents_lines,
    list_sets,
    splice_contents,
)

TODAY = date(2026, 10, 10)


def _card(type_: str, status: str, next_review: str = "2027-04-05") -> str:
    return (f"---\ntype: {type_}\ntitle: {type_}\nstatus: {status}\n"
            f"reviewed: 2026-10-05\nnext_review: {next_review}\n---\n\n# {type_}\n")


def _set(root: Path, name: str, status: str = "candidate",
         next_review: str = "2027-04-05") -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    slug = name.split(None, 1)[1] if " " in name else name
    type_ = slug.lower().replace(" ", "-")
    (folder / "SET.md").write_text(_card(type_, status, next_review), encoding="utf-8")
    return folder


@pytest.fixture
def banded_root(tmp_path: Path) -> Path:
    """Sets in every band, boundary prefixes included."""
    root = tmp_path / "Reference Sets"
    _set(root, "03 Code Analysis", "approved")
    _set(root, "09 Research Reports")
    _set(root, "10 Client Briefs")
    _set(root, "14 AHJ Registers")
    _set(root, "16 Comment-Response Letters")
    _set(root, "19 Presentation Decks")
    _set(root, "21 Floor Plans")
    _set(root, "45 Punch Lists")
    _set(root, "90 Control File - BRIEF")
    return root


def _block(root: Path, today: date = TODAY) -> list[str]:
    return contents_lines(list_sets(root), today)


def _stripped(block: list[str]) -> list[str]:
    return [line.strip() for line in block]


# ---- banding --------------------------------------------------------------


@pytest.mark.parametrize("folder,band", [
    ("01 Research Reports", "Due diligence"),
    ("09 Late Study", "Due diligence"),
    ("10 Client Briefs", "Client & control"),
    ("13 Decision Records", "Client & control"),
    ("14 AHJ Registers", "Permitting"),
    ("16 Comment-Response Letters", "Permitting"),
    ("19 Presentation Decks", "Design"),
    ("20 G-Series Sheets", "Drawings"),
    ("29 Late Sheet Type", "Drawings"),
    ("40 Specs", "Construction"),
    ("45 Punch Lists", "Construction"),
    ("90 Control File - BRIEF", "Control files"),
    ("99 Late Control", "Control files"),
    ("17 Gap Number", "Other"),   # a deliberate gap in the numbering
    ("Code Analysis", "Other"),   # no numeric prefix
])
def test_band_for_boundaries(folder: str, band: str):
    assert band_for(folder)[0] == band


# ---- the map --------------------------------------------------------------


def test_map_is_one_flowchart_with_a_subgraph_per_present_band(banded_root: Path):
    block = _block(banded_root)
    assert block[0] == CONTENTS_BEGIN and block[-1] == CONTENTS_END
    assert "```mermaid" in block and "flowchart LR" in block and "```" in block
    subgraphs = [line.strip() for line in block if line.strip().startswith("subgraph")]
    for band, band_id in (("Due diligence", "DD"), ("Client & control", "CC"),
                          ("Permitting", "PER"), ("Design", "DES"), ("Drawings", "DW"),
                          ("Construction", "CON"), ("Control files", "CF")):
        assert f'subgraph {band_id}["{band}"]' in subgraphs
    # bands linked once, in lifecycle order; the legend subgraph is not linked
    chains = [line.strip() for line in block if " --> " in line]
    assert chains == ["DD --> CC --> PER --> DES --> DW --> CON --> CF"]


def test_map_nodes_keep_the_number_and_labels_stay_short(banded_root: Path):
    stripped = _stripped(_block(banded_root))
    assert 's03_Code_Analysis["03 Code Analysis"]' in stripped
    # over-long folder names drop whole trailing words; the number stays
    assert 's16_Comment_Response_Letters["16 Comment-Response"]' in stripped
    labels = []
    for line in stripped:
        match = re.fullmatch(r's\w+\["([^"]+)"\]', line)
        if match:
            labels.append(match.group(1))
    assert len(labels) == 9
    assert all(len(label) <= 25 for label in labels)
    assert all(label[:2].isdigit() for label in labels)  # it teaches the prefix


def test_map_status_is_a_classdef_and_a_word(banded_root: Path):
    block = _block(banded_root)
    stripped = _stripped(block)
    assert any(line.startswith("classDef approved") for line in stripped)
    assert any(line.startswith("classDef candidate") for line in stripped)
    assert not any(line.startswith("classDef retired") for line in stripped)
    assert "class s03_Code_Analysis approved" in stripped
    assert any(line.endswith(" candidate") and line.startswith("class s09")
               for line in stripped)
    # the legend states the statuses as words, coloured the same as the nodes
    assert 'subgraph KEY["Status"]' in stripped
    assert 'key_approved["approved"]' in stripped
    assert 'key_candidate["candidate"]' in stripped
    assert "class key_approved approved" in stripped


def test_map_retired_classdef_only_when_a_retired_set_exists(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    _set(root, "03 Code Analysis", "retired")
    stripped = _stripped(_block(root))
    assert any(line.startswith("classDef retired") for line in stripped)
    assert "class s03_Code_Analysis retired" in stripped
    assert 'key_retired["retired"]' in stripped


def test_map_has_no_click_links(banded_root: Path):
    # rules/visual-markdown.md: click links are unreliable across renderers
    assert not any(line.strip().startswith("click") for line in _block(banded_root))


# ---- the tables -----------------------------------------------------------


def test_tables_are_banded_three_columns_in_band_order(banded_root: Path):
    block = _block(banded_root)
    headings = [line for line in block if line.startswith("### ")]
    assert headings == ["### Due diligence", "### Client & control", "### Permitting",
                        "### Design", "### Drawings", "### Construction",
                        "### Control files"]
    assert block.count("| Set | Status | Card |") == 7


def test_table_rows_link_with_escaped_spaces_and_carry_status_words(banded_root: Path):
    block = _block(banded_root)
    assert ("| [03 Code Analysis](03%20Code%20Analysis/SET.md) | approved | "
            "[SET.md](03%20Code%20Analysis/SET.md) |") in block
    assert ("| [90 Control File - BRIEF](90%20Control%20File%20-%20BRIEF/SET.md) | "
            "candidate | [SET.md](90%20Control%20File%20-%20BRIEF/SET.md) |") in block


def test_stale_is_a_word_in_the_status_column(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    _set(root, "03 Code Analysis", "approved", next_review="2026-01-01")
    block = _block(root)
    assert ("| [03 Code Analysis](03%20Code%20Analysis/SET.md) | approved (STALE) | "
            "[SET.md](03%20Code%20Analysis/SET.md) |") in block


def test_every_set_in_the_map_is_also_a_table_row(banded_root: Path):
    """Words stand alone: a reader on Drive web (raw Mermaid) loses nothing."""
    block = _block(banded_root)
    rows = [line for line in block if line.startswith("| [")]
    folders = sorted(p.name for p in banded_root.iterdir() if p.is_dir())
    assert len(rows) == len(folders)
    for folder in folders:
        assert any(row.startswith(f"| [{folder}](") for row in rows)


def test_contents_lines_deterministic(banded_root: Path):
    assert _block(banded_root) == _block(banded_root)


# ---- splice and CLI -------------------------------------------------------


def _readme(block: str | None = None) -> str:
    inner = block if block is not None else "<!-- placeholder -->\n"
    return ("---\ntitle: Reference Sets\n---\n\n# Reference Sets\n\n## Sets\n\n"
            f"{CONTENTS_BEGIN}\n{inner}{CONTENTS_END}\n\n## Rules\n")


def test_splice_requires_exactly_one_marker_block():
    with pytest.raises(RefSetError):
        splice_contents(["# README", "no markers"], [CONTENTS_BEGIN, CONTENTS_END])
    doubled = [CONTENTS_BEGIN, CONTENTS_BEGIN, CONTENTS_END, CONTENTS_END]
    with pytest.raises(RefSetError):
        splice_contents(doubled, [CONTENTS_BEGIN, CONTENTS_END])


def test_index_dry_run_previews_without_writing(banded_root: Path, capsys):
    readme = banded_root / "README.md"
    readme.write_text(_readme(), encoding="utf-8")
    before = readme.read_bytes()
    assert main(["refs", "index", "--root", str(banded_root)]) == 1  # pending, like `runs`
    out = capsys.readouterr().out
    assert "-<!-- placeholder -->" in out
    assert "+flowchart LR" in out
    assert "+| [03 Code Analysis](03%20Code%20Analysis/SET.md)" in out
    assert "--apply" in out
    assert readme.read_bytes() == before


def test_index_apply_is_byte_idempotent(banded_root: Path, capsys):
    readme = banded_root / "README.md"
    readme.write_text(_readme(), encoding="utf-8")
    assert main(["refs", "index", "--root", str(banded_root), "--apply"]) == 0
    first = readme.read_bytes()
    assert CONTENTS_BEGIN.encode() in first
    assert b"flowchart LR" in first
    assert b"### Due diligence" in first
    assert b"## Rules" in first  # outside the markers untouched
    assert main(["refs", "index", "--root", str(banded_root), "--apply"]) == 0
    assert "up to date" in capsys.readouterr().out
    assert readme.read_bytes() == first


def test_index_regenerates_only_the_block(banded_root: Path):
    readme = banded_root / "README.md"
    readme.write_text(_readme("| hand edited |\n"), encoding="utf-8")
    assert main(["refs", "index", "--root", str(banded_root), "--apply"]) == 0
    text = readme.read_text(encoding="utf-8")
    assert "| hand edited |" not in text
    assert text.startswith("---\ntitle: Reference Sets\n---")


def test_index_keeps_crlf(banded_root: Path):
    readme = banded_root / "README.md"
    readme.write_bytes(_readme().replace("\n", "\r\n").encode("utf-8"))
    assert main(["refs", "index", "--root", str(banded_root), "--apply"]) == 0
    raw = readme.read_bytes()
    assert b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"")


def test_index_missing_readme_or_markers(tmp_path: Path, banded_root: Path):
    bare = tmp_path / "bare"
    bare.mkdir()
    assert main(["refs", "index", "--root", str(bare)]) == 2
    (banded_root / "README.md").write_text("# no markers\n", encoding="utf-8")
    assert main(["refs", "index", "--root", str(banded_root)]) == 2


def test_index_json(banded_root: Path, capsys):
    (banded_root / "README.md").write_text(_readme(), encoding="utf-8")
    assert main(["refs", "index", "--root", str(banded_root), "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["changed"] and not out["applied"]
    assert out["sets"] == ["code-analysis", "research-reports", "client-briefs",
                           "ahj-registers", "comment-response-letters",
                           "presentation-decks", "floor-plans", "punch-lists",
                           "control-file---brief"]
