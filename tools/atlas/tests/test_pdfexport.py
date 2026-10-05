"""atlas pdf: Markdown to a printable PDF beside it."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core import pdfexport
from atlas.core.pdfexport import PdfError, export_pdf, render_html, strip_front_matter


def test_render_strips_front_matter_and_titles_from_it():
    page = render_html("---\ntitle: \"Code Memo\"\ndate: 2026-10-05\n---\n# Heading\n\n| a | b |\n|---|---|\n| 1 | 2 |\n",
                       "fallback")
    assert "<title>Code Memo</title>" in page
    assert "date: 2026-10-05" not in page
    assert "<table>" in page and "<td>1</td>" in page


def test_render_title_falls_back_to_heading_then_name():
    assert "<title>Minutes</title>" in render_html("# Minutes\n\ntext\n", "x")
    assert "<title>x</title>" in render_html("no heading\n", "x")


def test_front_matter_crlf():
    body, fields = strip_front_matter("---\r\ntitle: T\r\n---\r\nBody\r\n")
    assert fields == {"title": "T"} and body.startswith("Body")


def _fake_run(writes: bool = True):
    def run(cmd, **kwargs):
        target = next(a.split("=", 1)[1] for a in cmd if a.startswith("--print-to-pdf="))
        if writes:
            Path(target).write_bytes(b"%PDF-1.7 fake")
        class R:  # noqa: N801
            returncode = 0
        return R()
    return run


def test_export_writes_beside_source(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pdfexport.subprocess, "run", _fake_run())
    src = tmp_path / "memo.md"
    src.write_text("# Memo\n", encoding="utf-8")
    result = export_pdf(src, browser="fake")
    assert result.pdf == tmp_path / "memo.pdf" and not result.replaced
    assert result.pdf.read_bytes().startswith(b"%PDF-")


def test_newer_pdf_is_not_replaced_without_force(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pdfexport.subprocess, "run", _fake_run())
    src = tmp_path / "memo.md"
    src.write_text("# Memo\n", encoding="utf-8")
    pdf = tmp_path / "memo.pdf"
    pdf.write_bytes(b"%PDF- hand edited")
    later = time.time() + 60
    os.utime(pdf, (later, later))
    with pytest.raises(PdfError, match="newer"):
        export_pdf(src, browser="fake")
    assert pdf.read_bytes() == b"%PDF- hand edited"
    assert export_pdf(src, browser="fake", force=True).replaced


def test_stale_pdf_is_replaced(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pdfexport.subprocess, "run", _fake_run())
    pdf = tmp_path / "memo.pdf"
    pdf.write_bytes(b"%PDF- old")
    old = time.time() - 600
    os.utime(pdf, (old, old))
    src = tmp_path / "memo.md"
    src.write_text("# Memo\n", encoding="utf-8")
    assert export_pdf(src, browser="fake").replaced
    assert pdf.read_bytes() == b"%PDF-1.7 fake"


def test_no_pdf_produced_is_an_error(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pdfexport.subprocess, "run", _fake_run(writes=False))
    src = tmp_path / "memo.md"
    src.write_text("# Memo\n", encoding="utf-8")
    with pytest.raises(PdfError, match="no PDF"):
        export_pdf(src, browser="fake")
    assert not (tmp_path / "memo.pdf").exists()


def test_cli_rejects_non_markdown(tmp_path: Path):
    other = tmp_path / "x.txt"
    other.write_text("x", encoding="utf-8")
    assert main(["pdf", str(other)]) == 2


def test_cli_json(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(pdfexport.subprocess, "run", _fake_run())
    monkeypatch.setattr(pdfexport, "find_browser", lambda: "fake")
    src = tmp_path / "memo.md"
    src.write_text("# Memo\n", encoding="utf-8")
    assert main(["pdf", str(src), "--json"]) == 0
    assert '"replaced": false' in capsys.readouterr().out
