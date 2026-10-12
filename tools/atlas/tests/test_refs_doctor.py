"""Reference Sets: `atlas refs doctor` validation (plan 1.1).

`refs index` tests live in test_refs_index.py (ergonomics plan Phase 2).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.refsets import doctor_sets

TODAY = date(2026, 10, 10)

CARD_FULL = """---
type: code-analysis
title: Code Analysis Memo
status: approved
owner: Tyler
approved_by: Tyler
approved: 2026-10-05
reviewed: 2026-10-05
next_review: 2027-04-05
---

# Code Analysis Memo - reference set

## The exemplars

| ID | Project | Kind |
|---|---|---|
| E1 | Monte Vista | California residential |

## Near-miss

**N1 - McKean.** Debug notes up front.
"""

NOTES_FULL = """---
id: {id}
set: code-analysis
source_path: G:\\Shared drives\\ARCHITECTURE\\P1 Alpha\\06 Research\\memo.md
leak_list: ["Alpha House", "Lot 12"]
---

# {id}
"""

def _set(root: Path, name: str, card: str) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "SET.md").write_text(card, encoding="utf-8")
    return folder


def _exemplar(folder: Path, name: str, ex_id: str, notes: str | None = None) -> Path:
    child = folder / name
    child.mkdir()
    if notes is not None:
        (child / "NOTES.md").write_text(notes.format(id=ex_id), encoding="utf-8")
    return child


@pytest.fixture
def good_root(tmp_path: Path) -> Path:
    root = tmp_path / "Reference Sets"
    folder = _set(root, "Code Analysis", CARD_FULL)
    _exemplar(folder, "E1 Monte Vista - CRC", "E1", NOTES_FULL)
    _exemplar(folder, "N1 McKean - debug notes", "N1", NOTES_FULL)
    return root


# ---- doctor ---------------------------------------------------------------


def test_doctor_clean_set(good_root: Path):
    [report] = doctor_sets(good_root, TODAY)
    assert report.type == "code-analysis"
    assert report.status == "approved"
    assert report.problems == () and not report.stale
    assert main(["refs", "doctor", "--root", str(good_root)]) == 0


def test_doctor_card_front_matter_keys(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    _set(root, "Bad", "---\ntype: rfi\ntitle: RFI\nstatus: approved\n---\n# RFI\n")
    [report] = doctor_sets(root, TODAY)
    missing = {p.message for p in report.problems}
    assert "front matter missing owner" in missing
    assert "front matter missing next_review" in missing
    # approved with no approval fields is a governance breach (README step 3)
    assert "approved card has no approved_by" in missing


def test_doctor_card_status_vocabulary(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    _set(root, "Bad", CARD_FULL.replace("status: approved", "status: draft"))
    _exemplar(root / "Bad", "E1 A", "E1", NOTES_FULL)
    _exemplar(root / "Bad", "N1 B", "N1", NOTES_FULL)
    [report] = doctor_sets(root, TODAY)
    assert any("status" in p.message and "draft" in p.message for p in report.problems)


def test_doctor_no_front_matter(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    _set(root, "Bad", "# just a heading\n")
    [report] = doctor_sets(root, TODAY)
    assert any(p.message == "no front matter" for p in report.problems)


def test_doctor_card_names_folder_missing_on_disk(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    folder = _set(root, "Bad", CARD_FULL.replace("| E1 | Monte Vista | California residential |",
                                                 "| E1 | Monte Vista | California residential |\n"
                                                 "| E2 | Silverado | Code issue |"))
    _exemplar(folder, "E1 Monte Vista - CRC", "E1", NOTES_FULL)
    _exemplar(folder, "N1 McKean - debug notes", "N1", NOTES_FULL)
    [report] = doctor_sets(root, TODAY)
    assert any(p.message == "card names E2 but no such folder" for p in report.problems)


def test_doctor_folder_without_notes(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    folder = _set(root, "Bad", CARD_FULL)
    _exemplar(folder, "E1 Monte Vista - CRC", "E1", NOTES_FULL)
    _exemplar(folder, "N1 McKean - debug notes", "N1")  # no NOTES.md
    [report] = doctor_sets(root, TODAY)
    assert any(p.file == "N1 McKean - debug notes" and "NOTES.md" in p.message
               for p in report.problems)


def test_doctor_empty_leak_list(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    folder = _set(root, "Bad", CARD_FULL)
    _exemplar(folder, "E1 Monte Vista - CRC", "E1", NOTES_FULL.replace(
        'leak_list: ["Alpha House", "Lot 12"]', "leak_list: []"))
    _exemplar(folder, "N1 McKean - debug notes", "N1", NOTES_FULL)
    [report] = doctor_sets(root, TODAY)
    assert any(p.file.endswith("NOTES.md") and p.message == "empty leak_list"
               for p in report.problems)


def test_doctor_card_length_and_line_caps(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    long_card = CARD_FULL + "\n".join(f"filler line {n}" for n in range(160)) + "\n"
    wide_card = CARD_FULL + "x" * 2001 + "\n"
    for name, card in (("Long", long_card), ("Wide", wide_card)):
        folder = _set(root, name, card)
        _exemplar(folder, "E1 A", "E1", NOTES_FULL)
        _exemplar(folder, "N1 B", "N1", NOTES_FULL)
    reports = {r.folder.name: r for r in doctor_sets(root, TODAY)}
    assert any("lines" in p.message and "150" in p.message for p in reports["Long"].problems)
    assert any("line" in p.message and "2000" in p.message for p in reports["Wide"].problems)


def test_doctor_lnk_files(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    folder = _set(root, "Bad", CARD_FULL)
    e1 = _exemplar(folder, "E1 Monte Vista - CRC", "E1", NOTES_FULL)
    _exemplar(folder, "N1 McKean - debug notes", "N1", NOTES_FULL)
    (e1 / "original.lnk").write_bytes(b"")
    [report] = doctor_sets(root, TODAY)
    assert any(p.file.endswith(".lnk") for p in report.problems)


def test_doctor_stale_is_a_warning_not_a_problem(good_root: Path, capsys):
    card = (good_root / "Code Analysis" / "SET.md")
    card.write_text(CARD_FULL.replace("next_review: 2027-04-05", "next_review: 2026-01-01"),
                    encoding="utf-8")
    [report] = doctor_sets(good_root, TODAY)
    assert report.stale and report.problems == ()
    assert main(["refs", "doctor", "--root", str(good_root)]) == 0  # stale alone exits clean
    assert "STALE" in capsys.readouterr().out


def test_doctor_stray_folder_has_no_card(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    (root / "Loose Folder").mkdir(parents=True)
    [report] = doctor_sets(root, TODAY)
    assert any(p.message == "no SET.md" for p in report.problems)


def test_doctor_cli_exit_codes_and_json(tmp_path: Path, capsys):
    root = tmp_path / "Reference Sets"
    _set(root, "Bad", "# no front matter\n")
    assert main(["refs", "doctor", "--root", str(root), "--json"]) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["root"] == str(root)
    [entry] = out["sets"]
    assert entry["problems"][0]["file"] == "SET.md"
    assert {"type", "title", "status", "stale", "folder", "problems"} <= set(entry)


def test_doctor_missing_root_is_an_error(tmp_path: Path):
    assert main(["refs", "doctor", "--root", str(tmp_path / "nope")]) == 2

