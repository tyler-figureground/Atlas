"""File Rules: organize-style filing for Loose files at a project root (ADR 0009).

A File Rule is the map saying "a root file that looks like this belongs there".
It produces the Sweep conform already knows how to apply, preview, guard and
undo, so almost everything here is about which files match - and, above all,
which files must never match.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys

import pytest
from pypdf import PdfWriter

from atlas.cli import main
from atlas.core import content
from atlas.core.conform import (
    SWEEP,
    Guard,
    apply_plan,
    build_plan,
    build_repair_plan,
    invert_plan,
)
from atlas.core.doctor import report_drive, report_project, report_to_dict
from atlas.core.lintmap import lint_map
from atlas.core.mapfile import FileRule, MapError, find_map, load_map
from atlas.core.scan import scan_drive
from atlas.core.tree import LOOSE, UNFILED, open_project_tree

from conftest import FIXTURE_MAP, make_pdf, make_project, write_map

ISSUED = {
    "name": "Issued sets",
    "target": "08 OUT/Transmittals",
    "match": {"extensions": ["pdf"], "pdfText": ["issued for permit"]},
}
FEES = {"name": "Fee sheets", "target": "10 Legal/Invoices", "match": {"extensions": ["xlsx"]}}

SECTIONS = ["01 Model", "06 Research", "08 OUT", "11 Meetings"]
CONTROL_PLANE = {
    "PROJECT.md": "---\nproject: x\nrevit:\n---\n",
    "CLAUDE.md": "# workspace\n",
    "decisions/README.md": "# Decisions\n",
    "06 Research/Code/.keep": "",
}


@pytest.fixture(autouse=True)
def _fresh_pdf_cache():
    # The content cache is process-wide by design; tests must not share it.
    content.clear_cache()
    yield
    content.clear_cache()


def with_rules(drive, *rules, extra=None):
    data = copy.deepcopy(FIXTURE_MAP)
    data["fileRules"] = list(rules)
    data.update(extra or {})
    write_map(drive, data)
    return load_map(find_map(drive))


def project_with(drive, name, files=None):
    return make_project(drive, name, sections=SECTIONS, files={**CONTROL_PLANE, **(files or {})})


def report_for(drive, name):
    inventory = scan_drive(drive)
    inv = next(p for p in inventory.projects if p.name == name)
    return report_project(inv, inventory.map), inv, inventory.map


# ------------------------------------------------------------------ the map


def test_file_rules_load_in_order_and_normalise_extensions(fixture_drive):
    m = with_rules(
        fixture_drive,
        {"name": "Drawings", "target": "01 Model",
         "match": {"extensions": [".PDF", "Dwg"], "names": "A-*"}},
        FEES,
    )

    assert m.file_rules == (
        FileRule(name="Drawings", target="01 Model", extensions=("pdf", "dwg"), names=("A-*",)),
        FileRule(name="Fee sheets", target="10 Legal/Invoices", extensions=("xlsx",)),
    )


def test_a_map_without_file_rules_has_none(fixture_drive):
    assert load_map(find_map(fixture_drive)).file_rules == ()


@pytest.mark.parametrize(
    ("rules", "complaint"),
    [
        ({"not": "a list"}, "fileRules"),
        ([{"target": "01 Model", "match": {"extensions": ["pdf"]}}], "name"),
        ([{"name": "No home", "match": {"extensions": ["pdf"]}}], "target"),
        ([{"name": "Everything", "target": "01 Model", "match": {}}], "match"),
        ([{"name": "Typo", "target": "01 Model", "match": {"extension": ["pdf"]}}], "extension"),
        ([{"name": "Bad regex", "target": "01 Model", "match": {"nameRegex": "("}}], "nameRegex"),
        ([{"name": "Escape", "target": "../Elsewhere", "match": {"extensions": ["pdf"]}}], "target"),
        ([{"name": "Absolute", "target": "C:/Windows", "match": {"extensions": ["pdf"]}}], "target"),
        ([{"name": "Rooted", "target": "/etc", "match": {"extensions": ["pdf"]}}], "target"),
        ([{"name": "Numbers", "target": "01 Model", "match": {"extensions": [1]}}], "extensions"),
        ([{"name": "Nothing", "target": "01 Model", "match": {"names": []}}], "names"),
        ([{"name": "Blank", "target": "01 Model", "match": {"pdfText": [" "]}}], "pdfText"),
    ],
)
def test_a_malformed_rule_refuses_to_load(fixture_drive, rules, complaint):
    """Fail closed. A typo'd filter key that was silently ignored would leave a
    rule matching more than its author meant - and a rule that matches more moves
    more. Refusing the whole map is the only safe reading."""
    data = copy.deepcopy(FIXTURE_MAP)
    data["fileRules"] = rules
    write_map(fixture_drive, data)

    with pytest.raises(MapError, match=complaint):
        load_map(find_map(fixture_drive))


# ------------------------------------------------------- which files match


def test_a_root_file_matching_a_rule_is_swept_to_its_target(fixture_drive):
    with_rules(fixture_drive, FEES)
    project_with(fixture_drive, "260901_Fees", {"fee proposal.xlsx": "x"})

    report, _inv, _m = report_for(fixture_drive, "260901_Fees")

    assert ("fee proposal.xlsx", "10 Legal/Invoices") in report.sweeps
    assert report.sweep_rules == (("fee proposal.xlsx", "Fee sheets"),)
    assert "fee proposal.xlsx" not in report.unfiled
    assert report.status == "drift"


def test_every_filter_given_must_match(fixture_drive):
    with_rules(fixture_drive, {"name": "Invoices", "target": "10 Legal/Invoices",
                               "match": {"extensions": ["pdf"], "names": ["INV-*"]}})
    project_with(fixture_drive, "260902_And", {
        "INV-001.pdf": "x", "INV-001.docx": "x", "notes.pdf": "x",
    })

    report, _inv, _m = report_for(fixture_drive, "260902_And")

    assert [name for name, _t in report.sweeps] == ["INV-001.pdf"]
    assert set(report.unfiled) == {"INV-001.docx", "notes.pdf"}


def test_names_and_extensions_ignore_case(fixture_drive):
    """The drive is case-insensitive, so a rule that cared would be a rule that
    worked on one person's export settings and not another's."""
    with_rules(fixture_drive, {"name": "Invoices", "target": "10 Legal/Invoices",
                               "match": {"extensions": ["pdf"], "names": ["INV-*"]}})
    project_with(fixture_drive, "260903_Case", {"inv-002.PDF": "x"})

    report, _inv, _m = report_for(fixture_drive, "260903_Case")

    assert ("inv-002.PDF", "10 Legal/Invoices") in report.sweeps


def test_a_name_regex_is_searched_ignoring_case(fixture_drive):
    with_rules(fixture_drive, {"name": "RFIs", "target": "08 OUT/RFI",
                               "match": {"nameRegex": r"^\d{6}_rfi-\d+"}})
    project_with(fixture_drive, "260904_Regex", {"260901_RFI-004.pdf": "x", "RFI-004.pdf": "x"})

    report, _inv, _m = report_for(fixture_drive, "260904_Regex")

    assert [name for name, _t in report.sweeps] == ["260901_RFI-004.pdf"]


def test_the_first_matching_rule_wins(fixture_drive):
    with_rules(
        fixture_drive,
        {"name": "Invoices", "target": "10 Legal/Invoices", "match": {"names": ["INV-*"]}},
        {"name": "Any PDF", "target": "08 OUT/Transmittals", "match": {"extensions": ["pdf"]}},
    )
    project_with(fixture_drive, "260905_Order", {"INV-003.pdf": "x"})

    report, _inv, _m = report_for(fixture_drive, "260905_Order")

    assert report.sweeps == (("INV-003.pdf", "10 Legal/Invoices"),)
    assert report.sweep_rules == (("INV-003.pdf", "Invoices"),)


def test_a_glob_relocation_outranks_a_file_rule(fixture_drive):
    """Relocations were here first and their meaning must not shift under an
    operator's feet because someone added a broader rule below them."""
    with_rules(fixture_drive, {"name": "Notes", "target": "06 Research", "match": {"extensions": ["md"]}})
    project_with(fixture_drive, "260906_Glob", {"HANDOFF-x.md": "h"})

    report, _inv, _m = report_for(fixture_drive, "260906_Glob")

    assert report.sweeps == (("HANDOFF-x.md", ".agent/handoff/"),)
    assert report.sweep_rules == ()


def test_control_plane_and_tolerated_files_are_never_ruled(fixture_drive):
    """A rule for `*.md` must not file the project's own dossier away."""
    with_rules(fixture_drive, {"name": "Text", "target": "06 Research", "match": {"extensions": ["md", "ini"]}})
    project_with(fixture_drive, "260907_Dossier", {"desktop.ini": "x", "notes.md": "n"})

    report, _inv, _m = report_for(fixture_drive, "260907_Dossier")

    assert report.sweeps == (("notes.md", "06 Research"),)


def test_folders_are_never_ruled(fixture_drive):
    """Loose is a Filing State of files. A folder that happens to be named like
    one is a folder, and moving it is a relocation the map has to name."""
    with_rules(fixture_drive, {"name": "PDFs", "target": "08 OUT", "match": {"extensions": ["pdf"]}})
    project = project_with(fixture_drive, "260908_Folder")
    (project / "set.pdf").mkdir()

    report, _inv, _m = report_for(fixture_drive, "260908_Folder")

    assert report.sweeps == ()
    assert "set.pdf" in report.unfiled


# ------------------------------------------------------------- PDF content


def test_pdf_text_matches_words_on_the_first_page(fixture_drive):
    with_rules(fixture_drive, ISSUED)
    project = project_with(fixture_drive, "260909_Page")
    make_pdf(project / "A-101.pdf", text="ISSUED FOR PERMIT  Sheet A-101")

    report, _inv, _m = report_for(fixture_drive, "260909_Page")

    assert report.sweeps == (("A-101.pdf", "08 OUT/Transmittals"),)


def test_pdf_text_matches_the_document_title(fixture_drive):
    with_rules(fixture_drive, ISSUED)
    project = project_with(fixture_drive, "260910_Title")
    make_pdf(project / "set.pdf", title="Issued for Permit - 2026-09-01")

    report, _inv, _m = report_for(fixture_drive, "260910_Title")

    assert ("set.pdf", "08 OUT/Transmittals") in report.sweeps


def test_pdf_text_ignores_case_and_spacing(fixture_drive):
    """Title blocks set words in columns; extraction returns them with whatever
    spacing the layout left. The phrase has to survive that."""
    rule = copy.deepcopy(ISSUED)
    rule["match"]["pdfText"] = ["  ISSUED   For\tPERMIT "]
    with_rules(fixture_drive, rule)
    project = project_with(fixture_drive, "260911_Space")
    make_pdf(project / "A-102.pdf", text="issued  for permit")

    report, _inv, _m = report_for(fixture_drive, "260911_Space")

    assert ("A-102.pdf", "08 OUT/Transmittals") in report.sweeps


def test_a_pdf_without_the_phrase_stays_unfiled(fixture_drive):
    with_rules(fixture_drive, ISSUED)
    project = project_with(fixture_drive, "260912_Other")
    make_pdf(project / "A-103.pdf", text="ISSUED FOR BID", title="Bid Set")

    report, _inv, _m = report_for(fixture_drive, "260912_Other")

    assert report.sweeps == ()
    assert "A-103.pdf" in report.unfiled


def _encrypted(path):
    make_pdf(path, text="ISSUED FOR PERMIT")
    writer = PdfWriter(clone_from=str(path))
    writer.encrypt(user_password="secret", owner_password="owner", algorithm="RC4-128")
    writer.write(str(path))


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda p: p.write_bytes(b"%PDF-1.4\nthis is not really a pdf\n"), id="malformed"),
        pytest.param(lambda p: p.write_bytes(b"hello, I am a text file"), id="not-a-pdf"),
        pytest.param(lambda p: p.write_bytes(make_pdf(p, text="ISSUED FOR PERMIT").read_bytes()[:200]),
                     id="truncated"),
        pytest.param(_encrypted, id="encrypted"),
    ],
)
def test_a_pdf_atlas_cannot_read_never_matches(fixture_drive, build):
    """Uncertainty never moves a file."""
    with_rules(fixture_drive, ISSUED)
    project = project_with(fixture_drive, "260913_Broken")
    build(project / "A-104.pdf")

    report, _inv, _m = report_for(fixture_drive, "260913_Broken")

    assert report.sweeps == ()
    assert "A-104.pdf" in report.unfiled


@pytest.mark.parametrize(
    "setup",
    [
        pytest.param("", id="no-handler"),
        pytest.param("import logging; logging.basicConfig(); ", id="root-handler"),
    ],
)
def test_a_damaged_pdf_prints_nothing_to_a_real_terminal(tmp_path, setup):
    """pypdf's complaints about a broken file must not reach the terminal, where
    under the console they would draw over the screen. Two paths lead there:
    Python's last-resort stderr handler when nothing is configured, and any root
    handler when something is.

    Run in a subprocess because pytest cannot see this. It attaches its capture
    handlers to non-propagating loggers too, so inside pytest the damage is
    captured whether or not Atlas prevented it."""
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4\nthis is not really a pdf\n")
    code = setup + (
        "import sys; from pathlib import Path; from atlas.core import content; "
        "sys.exit(0 if content.pdf_text(Path(sys.argv[1])) is None else 3)"
    )

    ran = subprocess.run([sys.executable, "-c", code, str(bad)],
                         capture_output=True, text=True, timeout=60)

    assert ran.returncode == 0
    assert ran.stderr == ""
    assert ran.stdout == ""


def test_pdf_text_only_reads_files_named_pdf(fixture_drive):
    """Reading a file on the Drive mount downloads it. The extension is the
    cheap gate that stops a content rule opening every file at every root."""
    with_rules(fixture_drive, {"name": "Issued", "target": "08 OUT/Transmittals",
                               "match": {"pdfText": ["issued for permit"]}})
    project = project_with(fixture_drive, "260914_Ext")
    make_pdf(project / "set.bin", text="ISSUED FOR PERMIT")

    report, _inv, _m = report_for(fixture_drive, "260914_Ext")

    assert report.sweeps == ()


def test_a_pdf_over_the_read_limit_is_never_opened(fixture_drive, monkeypatch):
    with_rules(fixture_drive, ISSUED)
    project = project_with(fixture_drive, "260915_Big")
    make_pdf(project / "A-105.pdf", text="ISSUED FOR PERMIT")
    monkeypatch.setattr(content, "PDF_READ_LIMIT", 16)
    opened = []
    monkeypatch.setattr(content, "PdfReader", lambda *a, **k: opened.append(a))

    report, _inv, _m = report_for(fixture_drive, "260915_Big")

    assert report.sweeps == ()
    assert opened == []


def test_content_is_read_only_after_the_name_qualifies(fixture_drive, monkeypatch):
    with_rules(fixture_drive, {"name": "Sheets", "target": "08 OUT/Transmittals",
                               "match": {"names": ["A-*"], "pdfText": ["issued for permit"]}})
    project = project_with(fixture_drive, "260916_Cheap")
    make_pdf(project / "notes.pdf", text="ISSUED FOR PERMIT")
    read = []
    monkeypatch.setattr(content, "pdf_text", lambda path: read.append(path))

    report, _inv, _m = report_for(fixture_drive, "260916_Cheap")

    assert read == []
    assert report.sweeps == ()


def test_a_pdf_is_read_once_until_it_changes(fixture_drive, monkeypatch):
    """Guards re-derive the report before every write. That must not mean
    downloading the same drawing set twice."""
    project = project_with(fixture_drive, "260917_Cache")
    pdf = make_pdf(project / "A-106.pdf", text="ISSUED FOR PERMIT")
    real = content.PdfReader
    opened = []

    def counting(*args, **kwargs):
        opened.append(args)
        return real(*args, **kwargs)

    monkeypatch.setattr(content, "PdfReader", counting)

    assert "issued for permit" in content.pdf_text(pdf)
    assert "issued for permit" in content.pdf_text(pdf)
    assert len(opened) == 1

    make_pdf(pdf, text="ISSUED FOR CONSTRUCTION - REVISED")
    assert "issued for construction" in content.pdf_text(pdf)
    assert len(opened) == 2


# ------------------------------------------------- the existing write path


def test_conform_files_a_ruled_pdf_and_undo_puts_it_back(fixture_drive):
    with_rules(fixture_drive, ISSUED)
    project = project_with(fixture_drive, "260918_Apply")
    make_pdf(project / "A-107.pdf", text="ISSUED FOR PERMIT")
    report, inv, m = report_for(fixture_drive, "260918_Apply")

    plan = build_plan(report, m, project=inv.path)
    (sweep,) = [a for a in plan.actions if a.kind == SWEEP]
    assert (sweep.src, sweep.dst) == ("A-107.pdf", "08 OUT/Transmittals")

    applied = apply_plan(fixture_drive, inv.path, m, plan, only={SWEEP})
    assert (project / "08 OUT" / "Transmittals" / "A-107.pdf").is_file()
    assert not (project / "A-107.pdf").exists()

    apply_plan(fixture_drive, inv.path, m, invert_plan(applied))
    assert (project / "A-107.pdf").is_file()


def test_the_tree_calls_a_ruled_file_loose_and_offers_its_sweep(fixture_drive):
    with_rules(fixture_drive, FEES)
    project_with(fixture_drive, "260919_Tree", {"fees.xlsx": "x", "mystery.bin": "x"})
    report, inv, m = report_for(fixture_drive, "260919_Tree")

    tree = open_project_tree(inv, m, report)

    assert tree.filing_state("fees.xlsx") == LOOSE
    assert tree.filing_state("mystery.bin") == UNFILED
    (action,) = build_repair_plan(report, m, "fees.xlsx", project=inv.path).actions
    assert (action.kind, action.dst) == (SWEEP, "10 Legal/Invoices")


def test_a_guarded_content_rule_is_fresh_until_the_pdf_stops_matching(fixture_drive):
    """The guard re-derives the Plan from the map. For a content rule that means
    re-reading the PDF - so an edit that takes the phrase out is a stale plan,
    not a file moved on the strength of words it no longer contains."""
    with_rules(fixture_drive, ISSUED)
    project = project_with(fixture_drive, "260920_Guard")
    pdf = make_pdf(project / "A-108.pdf", text="ISSUED FOR PERMIT")
    report, inv, m = report_for(fixture_drive, "260920_Guard")
    one = build_repair_plan(report, m, "A-108.pdf", project=inv.path)
    guard = Guard.for_action(fixture_drive, "260920_Guard", m, one)

    assert guard.check(fixture_drive) is None

    make_pdf(pdf, text="SUPERSEDED - DO NOT USE FOR PERMIT")
    assert guard.check(fixture_drive) is not None


# --------------------------------------------------------------------- lint


def _codes(m):
    return {(f.level, f.code) for f in lint_map(m)}


def test_lint_is_clean_for_rules_that_land_somewhere_blessed(fixture_drive):
    m = with_rules(fixture_drive, ISSUED, FEES,
                   {"name": "Handoffs", "target": ".agent/handoff", "match": {"names": ["*handoff*"]}})

    assert not {code for _l, code in _codes(m) if code.startswith("FILE-RULE")}


def test_lint_refuses_a_rule_target_outside_the_map(fixture_drive):
    m = with_rules(fixture_drive, {"name": "Lost", "target": "99 Nowhere", "match": {"extensions": ["pdf"]}})

    assert ("error", "FILE-RULE-TARGET") in _codes(m)


def test_lint_warns_on_a_rule_target_that_is_not_a_blessed_child(fixture_drive):
    m = with_rules(fixture_drive, {"name": "Sheets", "target": "08 OUT/Loose Sheets",
                                   "match": {"extensions": ["pdf"]}})

    assert ("warn", "FILE-RULE-UNBLESSED-CHILD") in _codes(m)


def test_lint_warns_when_two_rules_share_a_name(fixture_drive):
    """Doctor reports which rule filed a file by its name. Two rules with one
    name make that report ambiguous."""
    m = with_rules(fixture_drive, FEES, {**FEES, "match": {"extensions": ["xls"]}})

    assert ("warn", "FILE-RULE-DUP-NAME") in _codes(m)


# ---------------------------------------------------------------------- CLI


def test_doctor_names_the_rule_that_filed_each_file(fixture_drive, capsys):
    with_rules(fixture_drive, FEES)
    project_with(fixture_drive, "260921_Cli", {"fees.xlsx": "x", "HANDOFF-y.md": "h"})

    assert main(["doctor", "--drive", str(fixture_drive)]) == 1
    text = capsys.readouterr().out
    assert "sweep pending: fees.xlsx -> 10 Legal/Invoices (rule: Fee sheets)" in text
    assert "sweep pending: HANDOFF-y.md -> .agent/handoff/\n" in text

    assert main(["doctor", "--drive", str(fixture_drive), "--json"]) == 1
    (proj,) = json.loads(capsys.readouterr().out)["projects"]
    assert {"file": "fees.xlsx", "target": "10 Legal/Invoices", "rule": "Fee sheets"} in proj["sweeps"]
    assert {"file": "HANDOFF-y.md", "target": ".agent/handoff/", "rule": None} in proj["sweeps"]


def test_report_json_keeps_its_shape_with_rules(fixture_drive):
    with_rules(fixture_drive, FEES)
    project_with(fixture_drive, "260922_Shape", {"fees.xlsx": "x"})

    (proj,) = report_to_dict(report_drive(scan_drive(fixture_drive)))["projects"]

    assert set(proj) == {
        "name", "status", "sections_present", "missing_control_plane",
        "drift", "relocations", "sweeps", "receipts", "unfiled", "ignored",
        "unreadable", "unreadable_deep", "overlong", "depth_capped", "items",
    }


def test_the_console_detail_says_which_rule_files_a_file(fixture_drive):
    """ADR 0008 runs both ways: the fact the CLI prints, the console shows."""
    from atlas.tui.model import project_detail, project_rows

    with_rules(fixture_drive, FEES)
    project_with(fixture_drive, "260923_Detail", {"fees.xlsx": "x"})
    report, _inv, m = report_for(fixture_drive, "260923_Detail")

    detail = project_detail(project_rows((report,), m)[0])

    assert "File fees.xlsx -> 10 Legal/Invoices (rule: Fee sheets)" in detail


def test_a_permission_locked_set_is_still_read(fixture_drive):
    """Issued sets are routinely locked against editing but open without a
    password, usually under AES. That is the common case, not an edge."""
    with_rules(fixture_drive, ISSUED)
    project = project_with(fixture_drive, "260924_Locked")
    pdf = make_pdf(project / "A-109.pdf", text="ISSUED FOR PERMIT")
    writer = PdfWriter(clone_from=str(pdf))
    writer.encrypt(user_password="", owner_password="owner", algorithm="AES-256")
    writer.write(str(pdf))

    report, _inv, _m = report_for(fixture_drive, "260924_Locked")

    assert ("A-109.pdf", "08 OUT/Transmittals") in report.sweeps


def test_a_map_tolerated_file_is_never_ruled(fixture_drive):
    """Ticket 29: a rule for `*.json` must not file `.mcp.json` away - the
    file only works at the root, which is why the map tolerates it."""
    with_rules(fixture_drive, {"name": "JSON", "target": "06 Research", "match": {"extensions": ["json"]}},
               extra={"tolerated": [".mcp.json"]})
    project_with(fixture_drive, "260909_Tolerated", {".mcp.json": "{}", "data.json": "{}"})

    report, _inv, _m = report_for(fixture_drive, "260909_Tolerated")

    assert report.sweeps == (("data.json", "06 Research"),)
    assert report.ignored == (".mcp.json",)
