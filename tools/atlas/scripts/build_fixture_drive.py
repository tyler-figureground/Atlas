"""Build a throwaway fixture drive that shows all four repairable Filing States.

Never point this at the studio drive. It writes only under the path given, and
it replaces an existing folder only when that folder carries the marker file it
wrote there itself.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from pypdf import PdfWriter

# Written at the root of every drive this script builds. Its presence is the only
# thing that lets a later run delete that folder.
MARKER = ".atlas-fixture"

FIXTURE_MAP = {
    "drive": "TESTDRIVE",
    "version": "2.0",
    "projectNaming": "YYMMDD_<ShortAddress>-<Description>",
    "controlPlane": {
        "projectFile": "PROJECT.md",
        "decisionsDir": "decisions",
        "handoffsDir": ".agent/handoff",
        "claudeFile": "CLAUDE.md",
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
        "08 OUT/Invoices": "10 Legal/Invoices",
        "HANDOFF-*.md": ".agent/handoff/",
    },
    "fileRules": [
        {
            "name": "Issued sets",
            "target": "08 OUT/Transmittals",
            "match": {"extensions": ["pdf"], "pdfText": ["issued for permit"]},
        },
        {
            "name": "Fee sheets",
            "target": "10 Legal/Invoices",
            "match": {"extensions": ["xlsx"]},
        },
    ],
}


def _pdf(path: Path, title: str) -> None:
    """A one-page PDF carrying `title` in its metadata, for the content rule."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({"/Title": title})
    with path.open("wb") as handle:
        writer.write(handle)


def _clear(root: Path) -> None:
    """Empty ``root`` only if this script built it.

    A mistyped or tab-completed argument must never cost a real drive, project
    or repo: on a Drive File Stream mount the deletion syncs to the shared drive.
    So an existing, non-empty folder is removed only when it carries the marker
    this script writes, and anything else is refused before a byte is touched.
    """
    if not root.exists():
        return
    if not root.is_dir():
        raise SystemExit(f"refusing: {root} is a file, not a fixture drive")
    if not any(root.iterdir()):
        return
    if not (root / MARKER).is_file():
        raise SystemExit(
            f"refusing: {root} exists, is not empty, and has no {MARKER} - "
            "this script only replaces a fixture drive it built itself"
        )
    shutil.rmtree(root)


def build(root: Path) -> None:
    _clear(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / MARKER).write_text(
        "Built by tools/atlas/scripts/build_fixture_drive.py. Safe to delete.\n",
        encoding="utf-8",
    )
    tools = root / "_tools"
    tools.mkdir(parents=True)
    (tools / "testdrive-map.json").write_text(
        json.dumps(FIXTURE_MAP, indent=2), encoding="utf-8"
    )

    project = root / "260813_120 Bowery-Loft"
    for section in ("01 Model/01 Site Model", "01 Model/02 Design",
                    "06 Research/Zoning", "06 Research/Code",
                    "08 OUT/Transmittals", "08 OUT/RFI",
                    "11 Meetings/Agendas", "11 Meetings/Minutes"):
        (project / section).mkdir(parents=True)

    # Drifted: the map renames "Meetings" to "11 Meetings".
    (project / "Meetings").mkdir()
    (project / "Meetings" / "2026-08-13 kickoff.md").write_text("kickoff", encoding="utf-8")

    # Misplaced: the map relocates "08 OUT/Invoices" to "10 Legal/Invoices".
    (project / "08 OUT" / "Invoices").mkdir()
    (project / "08 OUT" / "Invoices" / "INV-001.pdf").write_text("x", encoding="utf-8")

    # Loose: a file the map sweeps into the handoff dir, by glob.
    (project / "HANDOFF-2026-08-13.md").write_text("handoff", encoding="utf-8")

    # Loose by File Rule: one matched on content, one on extension alone. The
    # second PDF is the control - same extension, wrong words, so it stays Unfiled
    # and the tree draws the two states side by side.
    _pdf(project / "A-101 Permit Set.pdf", "ISSUED FOR PERMIT - 2026-08-13")
    _pdf(project / "A-102 Sketch.pdf", "WORK IN PROGRESS - DO NOT USE")
    (project / "fee proposal.xlsx").write_text("fees", encoding="utf-8")

    # Unfiled: nothing in the map accounts for this at all.
    (project / "Random Stuff").mkdir()
    (project / "Random Stuff" / "scratch.txt").write_text("x", encoding="utf-8")

    (project / "PROJECT.md").write_text(
        "# 120 Bowery Loft\n\nFixture project.\n", encoding="utf-8"
    )

    second = root / "260901_44 Pine St"
    (second / "01 Model").mkdir(parents=True)
    (second / "PROJECT.md").write_text("# 44 Pine St\n", encoding="utf-8")

    print(f"built {root}")


if __name__ == "__main__":
    build(Path(sys.argv[1]))
