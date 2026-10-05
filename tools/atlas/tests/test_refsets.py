"""Reference Sets: front matter, listing, and the leak check (ADR 0015)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.refsets import check_draft, front_matter, list_sets, parse_marker

CARD = """---
type: code-analysis
title: Code Analysis Memo
status: approved          # candidate | approved | retired
entity: shared
reviewed: 2026-10-10
next_review: 2026-01-01
applies_to: {phase: [SD, CD], use_case: [Addition]}
---

# Code Analysis Memo
"""


def _notes(ex_id: str, source: str, leaks: str) -> str:
    return f"""---
id: {ex_id}
set: code-analysis
source_path: {source}
leak_list: {leaks}
---

# {ex_id}
"""


@pytest.fixture
def sets_root(tmp_path: Path) -> Path:
    root = tmp_path / "Reference Sets"
    s = root / "Code Analysis"
    (s / "E1 Monte Vista - CRC").mkdir(parents=True)
    (s / "E3 Centre - NYC").mkdir()
    (s / "E2 Coleman - audit").mkdir()  # no NOTES.md: a problem, not a crash
    (s / "SET.md").write_text(CARD, encoding="utf-8")
    (s / "E1 Monte Vista - CRC" / "NOTES.md").write_text(_notes(
        "E1", r"G:\Shared drives\ARCHITECTURE\260203_262 Monte Vista Dr\06 Research\Code\memo.md",
        '["262 Monte Vista", "APN 052-123-004", "Smith"]'), encoding="utf-8")
    (s / "E3 Centre - NYC" / "NOTES.md").write_text(_notes(
        "E3", r"G:\Shared drives\ARCHITECTURE\260527_211 centre street\06 Research\Code\memo.md",
        '["211 Centre", "Montez", "B"]'), encoding="utf-8")
    return root


def test_front_matter_subset():
    fm = front_matter(CARD)
    assert fm["status"] == "approved"  # comment stripped
    assert fm["applies_to"] == "{phase: [SD, CD], use_case: [Addition]}"
    block = front_matter("---\nleak_list:\n  - one\n  - \"two, three\"\n---\n")
    assert block["leak_list"] == ["one", "two, three"]
    assert front_matter("no front matter") == {}
    assert front_matter("---\nkey: open\n") == {}


def test_inline_list_keeps_quoted_commas():
    fm = front_matter('---\nleak_list: ["Smith, Jane", \'#5 Lot\', plain]\n---\n')
    assert fm["leak_list"] == ["Smith, Jane", "#5 Lot", "plain"]


def test_list_sets_reports_problems_and_staleness(sets_root: Path):
    [refset] = list_sets(sets_root)
    assert refset.type == "code-analysis"
    assert [e.id for e in refset.exemplars] == ["E1", "E2", "E3"]
    assert refset.problems() == ["E2: no NOTES.md"]
    assert refset.stale(date(2026, 10, 4))


def test_check_finds_leaks_case_and_space_insensitive(sets_root: Path, tmp_path: Path):
    draft = tmp_path / "draft.md"
    draft.write_text("Site: 262  monte vista\nOwner smithson\nAPN 052-123-004\n", encoding="utf-8")
    leaks, checked = check_draft(draft, list_sets(sets_root))
    assert {(l.exemplar, l.string, l.line) for l in leaks} == {
        ("E1", "262 Monte Vista", 1), ("E1", "APN 052-123-004", 3)}
    assert "Smith" not in {l.string for l in leaks}  # word boundary: smithson is not Smith
    assert checked == ["code-analysis E1", "code-analysis E3"]


def test_short_leak_strings_ignored(sets_root: Path, tmp_path: Path):
    draft = tmp_path / "draft.md"
    draft.write_text("Occupancy B\n", encoding="utf-8")
    leaks, _ = check_draft(draft, list_sets(sets_root))
    assert leaks == []


def test_marker_scopes_the_check(sets_root: Path, tmp_path: Path):
    draft = tmp_path / "draft.md"
    draft.write_text("<!-- architecture-studio:reference: code-analysis E3 -->\n"
                     "262 Monte Vista and 211 Centre\n", encoding="utf-8")
    assert parse_marker(draft.read_text()) == ("code-analysis", ("E3",))
    leaks, checked = check_draft(draft, list_sets(sets_root))
    assert checked == ["code-analysis E3"]
    assert [l.string for l in leaks] == ["211 Centre"]


def test_own_project_exemplar_skipped(sets_root: Path, monkeypatch):
    from atlas.core import refsets
    monkeypatch.setattr(refsets, "_project_root", lambda p: (
        "architecture/260527_211 centre street" if ("211" in p or "draft" in p) else "other"))
    draft = sets_root.parent / "draft.md"
    draft.write_text("211 Centre, Montez\n", encoding="utf-8")
    leaks, checked = check_draft(draft, list_sets(sets_root))
    assert checked == ["code-analysis E1"] and leaks == []


def test_project_root_from_drive_path():
    from atlas.core.refsets import _project_root
    assert _project_root(r"G:\Shared drives\ARCHITECTURE\260203_262 Monte Vista\06 X\a.md") == \
        "architecture/260203_262 monte vista"
    assert _project_root("/tmp/x.md") == ""


def test_cli_check_exit_codes_and_json(sets_root: Path, tmp_path: Path, capsys):
    draft = tmp_path / "draft.md"
    draft.write_text("Montez Radio memo\n", encoding="utf-8")
    assert main(["refs", "check", str(draft), "--root", str(sets_root), "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["leaks"][0]["string"] == "Montez"
    draft.write_text("clean memo\n", encoding="utf-8")
    assert main(["refs", "--root", str(sets_root), "check", str(draft)]) == 0
    assert "0 leak(s)" in capsys.readouterr().out


def test_cli_list_and_unknown_type(sets_root: Path, tmp_path: Path, capsys):
    assert main(["refs", "--root", str(sets_root), "--json"]) == 1  # E2 problem + stale
    rows = json.loads(capsys.readouterr().out)["sets"]
    assert rows[0]["stale"] and rows[0]["problems"] == ["E2: no NOTES.md"]
    draft = tmp_path / "d.md"
    draft.write_text("x\n", encoding="utf-8")
    assert main(["refs", "check", str(draft), "--root", str(sets_root), "--type", "rfi"]) == 2


def test_cli_missing_root_is_an_error(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("ATLAS_REFERENCE_SETS", raising=False)
    assert main(["refs", "--root", str(tmp_path / "nope")]) == 2


def test_root_from_map_key(sets_root: Path, tmp_path: Path, monkeypatch, capsys):
    monkeypatch.delenv("ATLAS_REFERENCE_SETS", raising=False)
    drive = tmp_path / "drive"
    (drive / "_tools").mkdir(parents=True)
    (drive / "_tools" / "architecture-map.json").write_text(json.dumps(
        {"referenceSets": str(sets_root)}), encoding="utf-8")
    assert main(["refs", "--drive", str(drive), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["root"] == str(sets_root)


def test_single_word_leaks_keep_case(sets_root: Path, tmp_path: Path):
    draft = tmp_path / "draft.md"
    draft.write_text("the smith shop\nMontez said\nmontez lowercase\n", encoding="utf-8")
    leaks, _ = check_draft(draft, list_sets(sets_root))
    assert [(l.string, l.line) for l in leaks] == [("Montez", 2)]


def test_yaml_quote_escapes():
    fm = front_matter("---\n"
                      "leak_list: ['15''-7\"', \"45' - 4\\\"\", \"\\\"Mo\\\"\", O'Brien, plain # note]\n"
                      "block:\n  - '10''-11\"'\n  - \"48\\\" vs. 69\\\"\"\n"
                      "---\n")
    assert fm["leak_list"] == ["15'-7\"", "45' - 4\"", "\"Mo\"", "O'Brien", "plain"]
    assert fm["block"] == ["10'-11\"", "48\" vs. 69\""]


def test_short_words_and_cross_project_names_skipped(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    s = root / "Minutes"
    for name in ("E1 A", "E2 B"):
        (s / name).mkdir(parents=True)
    (s / "SET.md").write_text("---\ntype: meeting-minutes\n---\n", encoding="utf-8")
    (s / "E1 A" / "NOTES.md").write_text(_notes(
        "E1", r"G:\Shared drives\ARCHITECTURE\P1 Alpha\11 Meetings\m.md",
        '["Ron Cox", "Max", "Lot 12", "Alpha House"]'), encoding="utf-8")
    (s / "E2 B" / "NOTES.md").write_text(_notes(
        "E2", r"G:\Shared drives\ARCHITECTURE\P2 Beta\11 Meetings\m.md",
        '["Ron Cox", "Beta Loft"]'), encoding="utf-8")
    draft = tmp_path / "draft.md"
    draft.write_text("Ron Cox attended. Max. 35% coverage. Lot 12. Alpha House.\n", encoding="utf-8")
    leaks, _ = check_draft(draft, list_sets(root))
    assert sorted(l.string for l in leaks) == ["Alpha House", "Lot 12"]


def test_generic_strings_never_leak(tmp_path: Path):
    root = tmp_path / "Reference Sets"
    s = root / "Minutes"
    (s / "E1 A").mkdir(parents=True)
    (s / "SET.md").write_text("---\ntype: meeting-minutes\n---\n", encoding="utf-8")
    (s / "E1 A" / "NOTES.md").write_text(_notes(
        "E1", r"G:\Shared drives\ARCHITECTURE\P1 Alpha\11 Meetings\m.md",
        '["260916", "2026-09-16", "50:10", "$100", "DR-019", "15\'\'-7\\"", "873.30 sf", '
        '"052-123-004", "Alpha House"]'), encoding="utf-8")
    draft = tmp_path / "draft.md"
    draft.write_text("260916 2026-09-16 [50:10] $100 DR-019 15'-7\" 873.30 sf\n"
                     "APN 052-123-004, Alpha House\n", encoding="utf-8")
    leaks, _ = check_draft(draft, list_sets(root))
    assert sorted(l.string for l in leaks) == ["052-123-004", "Alpha House"]


def test_project_flag_and_studio_ignore(sets_root: Path, tmp_path: Path, capsys):
    (sets_root / "README.md").write_text("---\nleak_ignore: [Smith, OutKast]\n---\n# Sets\n",
                                         encoding="utf-8")
    draft = tmp_path / "draft.md"
    draft.write_text("211 Centre and Smith, surveyed by OutKast\n", encoding="utf-8")
    assert main(["refs", "check", str(draft), "--root", str(sets_root), "--json"]) == 1
    assert [l["string"] for l in json.loads(capsys.readouterr().out)["leaks"]] == ["211 Centre"]
    own = r"G:\Shared drives\ARCHITECTURE\260527_211 centre street"
    assert main(["refs", "check", str(draft), "--root", str(sets_root),
                 "--project", own]) == 0


def test_studio_ignore_covers_phrases_containing_the_name(sets_root: Path, tmp_path: Path):
    from atlas.core.refsets import studio_ignore
    e1 = sets_root / "Code Analysis" / "E1 Monte Vista - CRC" / "NOTES.md"
    e1.write_text(_notes("E1", r"G:\Shared drives\ARCHITECTURE\260203_262 Monte Vista Dr\x.md",
                         '["iGUIDE survey", "262 Monte Vista"]'), encoding="utf-8")
    (sets_root / "README.md").write_text("---\nleak_ignore: [iGUIDE]\n---\n", encoding="utf-8")
    draft = tmp_path / "d.md"
    draft.write_text("Per the iGUIDE survey of 262 Monte Vista.\n", encoding="utf-8")
    leaks, _ = check_draft(draft, list_sets(sets_root), ignore=studio_ignore(sets_root))
    assert [l.string for l in leaks] == ["262 Monte Vista"]


def test_retired_exemplar_is_listed_apart_and_never_checked(sets_root: Path, tmp_path: Path):
    x = sets_root / "Code Analysis" / "X1 Old"
    x.mkdir()
    (x / "NOTES.md").write_text("---\nid: X1\nstatus: retired\nleak_list: [\"Old Barn\"]\n---\n",
                                encoding="utf-8")
    [refset] = list_sets(sets_root)
    assert refset.retired == ("X1",) and "X1" not in [e.id for e in refset.exemplars]
    draft = tmp_path / "d.md"
    draft.write_text("Old Barn\n", encoding="utf-8")
    leaks, checked = check_draft(draft, [refset])
    assert leaks == [] and "code-analysis X1" not in checked
