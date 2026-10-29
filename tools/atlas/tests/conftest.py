"""Fixture drive builder: a miniature mapped drive in tmp_path."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
import re

import pytest

from atlas.core.contacts import ContactDraft, add_contact, find_contact, load_contacts
from atlas.core.intake import ProjectAddress, ProjectIntake, ProjectUseCase
from atlas.core.mapfile import find_map, load_map
from atlas.core.projectmd import agents_md_lines, claude_md_lines
from atlas.core.templates import ENV_VAR as TEMPLATES_ENV_VAR


@pytest.fixture(autouse=True)
def _bundled_templates(monkeypatch):
    """Tests always read the repo's bundled templates.

    ATLAS_TEMPLATES exists to try a template against a real drive; a machine
    that has it set (this one does, pointing at a drive copy) must not change
    what the suite asserts.
    """
    monkeypatch.delenv(TEMPLATES_ENV_VAR, raising=False)


@pytest.fixture(autouse=True)
def _no_machine_pyvoid(monkeypatch):
    """Tests never see this machine's Pyvoid mcp_server setting.

    ATLAS_PYVOID_MCP_SERVER is per-machine (Pyvoid #1545). A machine that has
    it set must not make every scaffold in the suite grow a .mcp.json; a test
    that wants one sets it to a tmp folder itself.
    """
    monkeypatch.delenv("ATLAS_PYVOID_MCP_SERVER", raising=False)


@pytest.fixture(autouse=True)
def _local_cache(monkeypatch, tmp_path):
    """Tests never touch the machine's real Content Index cache.

    ATLAS_CACHE_DIR exists so tests and unusual machines can point the cache
    elsewhere; a machine that has it set must not change what the suite
    asserts, and the suite must never write there. Pointing it at a tmp path
    (not just deleting it) matters since ticket 35: the console loads and
    first-builds the index at drive-open, so every TUI test would otherwise
    write to this machine's real cache.
    """
    monkeypatch.setenv("ATLAS_CACHE_DIR", str(tmp_path / "atlas-cache"))

FIXTURE_MAP = {
    "drive": "TESTDRIVE",
    "version": "2.0",
    "projectNaming": "YYMMDD_<ShortAddress>-<Description>",
    "controlPlane": {
        "projectFile": "PROJECT.md",
        "decisionsDir": "decisions",
        "handoffsDir": ".agent/handoff",
        "claudeFile": "CLAUDE.md",
        "agentsFile": "AGENTS.md",
        "analysisDir": "06 Research/Code",
    },
    "sections": [
        {"id": "01 Model", "seed": True, "children": ["01 Site Model", "02 Design"]},
        {"id": "06 Research", "seed": True, "children": ["Zoning", "Code"]},
        {"id": "08 OUT", "seed": True, "children": ["Transmittals", "RFI"]},
        {"id": "10 Legal", "seed": False, "children": ["Invoices", "Proposals-Contracts"]},
        {"id": "11 Meetings", "seed": True, "children": ["Agendas", "Minutes"]},
    ],
    "driftMap": {"Meetings": "11 Meetings", "10 Legal Business": "10 Legal"},
    "relocations": {
        "_note": "commentary keys are ignored",
        "08 OUT/Invoices": "10 Legal/Invoices",
        "HANDOFF-*.md": ".agent/handoff/",
    },
}


def write_map(drive: Path, data: dict | None = None) -> Path:
    tools = drive / "_tools"
    tools.mkdir(parents=True, exist_ok=True)
    map_path = tools / "testdrive-map.json"
    map_path.write_text(json.dumps(data or FIXTURE_MAP), encoding="utf-8")
    return map_path


def make_intake(
    drive: Path,
    name: str,
    description: str = "",
    *,
    street: str | None = None,
    use_case: str = "Renovation",
    created: date = date(2026, 8, 13),
) -> ProjectIntake:
    token = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-") or "project"
    email = f"{token}@example.com"
    contact = find_contact(load_contacts(drive), email)
    if contact is None:
        contact = add_contact(
            drive,
            ContactDraft(first_name="Test", last_name=name, email=email),
        )
    return ProjectIntake(
        project_name=name,
        project_address=ProjectAddress(
            street=street or f"100 {name} Street",
            city="Oakland",
            state="CA",
            postal_code="94612",
        ),
        project_use_case=ProjectUseCase(use_case),
        billing_contact_id=contact.id,
        client_contact_id=contact.id,
        description=description,
        created=created,
    )


def make_project(drive: Path, name: str, *, sections: list[str] = (), files: dict[str, str] | None = None) -> Path:
    project = drive / name
    project.mkdir(parents=True, exist_ok=True)
    for section in sections:
        (project / section).mkdir(parents=True, exist_ok=True)
    for rel, content in (files or {}).items():
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return project


def _pdf_string(s: str) -> bytes:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1")


def make_pdf(path: Path, text: str = "", title: str | None = None) -> Path:
    """A real one-page PDF: ``text`` on page one, ``title`` in its metadata.

    Hand-assembled rather than written through pypdf so a test of Atlas reading a
    PDF does not also depend on pypdf being able to write one, and so the bytes are
    exactly what a title block exporter would leave: a content stream with the
    words in it and nothing clever.
    """
    content = b"BT /F1 12 Tf 72 720 Td (" + _pdf_string(text) + b") Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    if title is not None:
        objects.append(b"<< /Title (" + _pdf_string(title) + b") >>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    trailer = b"<< /Size %d /Root 1 0 R" % (len(objects) + 1)
    if title is not None:
        trailer += b" /Info %d 0 R" % len(objects)
    out += b"trailer\n" + trailer + b" >>\nstartxref\n%d\n%%%%EOF\n" % xref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))
    return path


def agent_files(drive: Path) -> dict[str, str]:
    """AGENTS.md and CLAUDE.md exactly as Atlas writes them for this drive's map."""
    m = load_map(find_map(drive))
    return {
        m.agents_file: "\n".join(agents_md_lines(m)) + "\n",
        m.claude_file: "\n".join(claude_md_lines(m)) + "\n",
    }


@pytest.fixture()
def fixture_drive(tmp_path: Path) -> Path:
    drive = tmp_path / "TESTDRIVE"
    drive.mkdir()
    write_map(drive)
    return drive
