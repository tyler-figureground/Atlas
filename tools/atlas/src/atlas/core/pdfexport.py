"""Print a Markdown deliverable to PDF: `atlas pdf`.

Tyler reads and sends deliverables printed or as PDF, where raw Markdown tables do
not read (calibration, 2026-10-05). This renders the Markdown to HTML with a print
stylesheet and has a Chromium browser print it - Edge ships with every Windows PC,
so staff install nothing.

One write: the PDF beside the source. An existing PDF is replaced only when it is
older than its source (a stale export) or when forced - a PDF newer than its
Markdown may hold edits made after export.
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from markdown_it import MarkdownIt

BROWSER_ENV = "ATLAS_BROWSER"
_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)

CSS = """
@page { size: Letter; margin: 0.75in 0.7in; }
body { font: 10.5pt/1.45 "Segoe UI", Helvetica, Arial, sans-serif; color: #111; }
h1 { font-size: 17pt; margin: 0 0 6pt; }
h2 { font-size: 13pt; margin: 16pt 0 4pt; border-bottom: 0.5pt solid #999; padding-bottom: 2pt; }
h3 { font-size: 11pt; margin: 12pt 0 3pt; }
h2, h3 { break-after: avoid; }
p, li { orphans: 2; widows: 2; }
ul, ol { padding-left: 18pt; margin: 3pt 0 6pt; }
li { margin: 1.5pt 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 9pt; font-size: 9.5pt; }
th, td { border: 0.5pt solid #888; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: #eee; }
tr { break-inside: avoid; }
code { font: 9pt Consolas, Menlo, monospace; }
pre { white-space: pre-wrap; font-size: 9pt; }
blockquote { margin: 6pt 0; padding-left: 9pt; border-left: 2pt solid #bbb; color: #333; }
"""


class PdfError(ValueError):
    pass


def strip_front_matter(text: str) -> tuple[str, dict[str, str]]:
    """Body without its YAML block, plus that block's flat ``key: value`` pairs."""
    text = text.lstrip("\ufeff")
    match = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not match:
        return text, {}
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and not line[:1].isspace():
            fields[key.strip()] = value.strip().strip("\"'")
    return text[match.end():], fields


def render_html(markdown: str, fallback_title: str) -> str:
    body, fields = strip_front_matter(markdown)
    heading = re.search(r"^#\s+(.+)$", body, re.M)
    title = fields.get("title") or (heading.group(1).strip() if heading else fallback_title)
    md = MarkdownIt("commonmark", {"html": True, "linkify": False}).enable("table")
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
            f"<body>{md.render(body)}</body></html>")


def find_browser() -> str:
    override = os.environ.get(BROWSER_ENV)
    if override:
        if not Path(override).is_file():
            raise PdfError(f"{BROWSER_ENV} names no file: {override}")
        return override
    for name in ("msedge", "chrome", "chromium", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in _CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    raise PdfError(f"no Edge or Chrome found; set {BROWSER_ENV} to a Chromium browser")


@dataclass(frozen=True)
class Export:
    source: Path
    pdf: Path
    replaced: bool


def export_pdf(source: Path, out: Path | None = None, *, force: bool = False,
               browser: str | None = None, timeout: int = 90) -> Export:
    if source.suffix.lower() != ".md" or not source.is_file():
        raise PdfError(f"not a Markdown file: {source}")
    pdf = out or source.with_suffix(".pdf")
    replaced = pdf.exists()
    if replaced and not force and pdf.stat().st_mtime >= source.stat().st_mtime:
        raise PdfError(f"{pdf.name} is newer than {source.name} and may hold later edits; "
                       "pass --force to replace it")
    page = render_html(source.read_text(encoding="utf-8", errors="replace"), source.stem)
    browser = browser or find_browser()
    with tempfile.TemporaryDirectory(prefix="atlas-pdf-") as tmp:
        html_path = Path(tmp) / "page.html"
        html_path.write_text(page, encoding="utf-8")
        target = Path(tmp) / "out.pdf"
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run",
               f"--user-data-dir={Path(tmp) / 'profile'}",
               "--no-pdf-header-footer", f"--print-to-pdf={target}", html_path.as_uri()]
        try:
            subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as error:
            raise PdfError(f"browser did not finish within {timeout}s") from error
        if not target.is_file() or target.read_bytes()[:5] != b"%PDF-":
            raise PdfError("the browser produced no PDF")
        shutil.copyfile(target, pdf)
    return Export(source, pdf, replaced)
