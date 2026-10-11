"""The DOSSIER Companion Mode and `atlas dossier` (ticket 36; ticket 09, the
ADR 0005 amendment, ADR 0001).

The mode renders the Dossier Facts Table from `load_project_record` -
identity, the billing/client Contact Snapshots, the decisions summary -
never raw Markdown, and read-only: the last line advertises `e` and `o`, the
surfaces that can actually do something. Missing, malformed and legacy
PROJECT.md render the reason, never blanks (blank means unknown, ADR 0001).

Missing/malformed/legacy rendered headless at the measured widths: 179, 153,
120, 87, 77, 46 columns; 51, 30, 24 rows (the ticket 09 acceptance).
"""

from __future__ import annotations

import json

from textual.widgets import Static

from atlas.cli import main
from atlas.core.mapfile import load_map
from atlas.core.ops import new_project
from atlas.core.project_data import decisions_summary, load_project_record
from atlas.tui.app import AtlasApp
from atlas.tui.layout import DOSSIER

from conftest import agent_files, make_intake, make_project

# The measured terminals (map.md): columns trimodal, rows near-constant at 51.
WIDTHS = (179, 153, 120, 87, 77, 46)
ROWS = (51, 30, 24)

LEGACY_FRONT_MATTER = """\
---
title: 211 Centre Street
client: Confounding Partners
status: active
---

# 211 Centre Street

A Norma-era dossier: front matter, but none of the Atlas intake keys.
"""

MALFORMED = """\
---
project: Half Written
address_street: 9 Broken Lane
---

# Half Written
"""

PROSE = "# Just prose\n"


async def settle(app, pilot) -> None:
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


def _new_project(drive, name="Oak House", description="Kitchen"):
    drive_map = load_map(drive / "_tools" / "testdrive-map.json")
    intake = make_intake(drive, name, description, street="1842 Oak Street",
                         use_case="Renovation + Addition")
    result = new_project(drive, drive_map, intake)
    return result.path


def _body(app) -> str:
    return str(app.query_one("#companion-body", Static).content)


async def _open_dossier(app, pilot) -> str:
    """Cycle the Companion to DOSSIER for the selected project."""
    await settle(app, pilot)
    assert app._companion_mode != DOSSIER
    await pilot.press("d", "d")
    await settle(app, pilot)
    assert app._companion_mode == DOSSIER
    return _body(app)


# ------------------------------------------------------------- the core seam


def test_decisions_summary_counts_and_takes_the_latest_titles(fixture_drive):
    project = _new_project(fixture_drive)
    dossier = project / "PROJECT.md"
    source = dossier.read_text(encoding="utf-8")
    rows = (
        "| 1 | Keep the brick party wall | Accepted | 2026-09-01 |\n"
        "| 2 | R-15 insulation at the rear extension | Accepted | 2026-09-12 |\n"
        "| 3 | Steel instead of glulam at the ridge | Superseded | 2026-09-20 |\n"
        "| 4 | Glulam at the ridge, revised | Accepted | 2026-10-02 |\n"
    )
    marker = "| # | Decision | Status | Date |\n|---|----------|--------|------|\n"
    assert marker in source
    dossier.write_text(source.replace(marker, marker + rows), encoding="utf-8")

    record = load_project_record(project)
    assert record.decisions.count == 4
    # Newest first, capped at three: /decision appends chronologically.
    assert record.decisions.latest == (
        "Glulam at the ridge, revised",
        "Steel instead of glulam at the ridge",
        "R-15 insulation at the rear extension",
    )


def test_decisions_summary_without_a_section_is_zero_not_an_error():
    assert decisions_summary(["# Old dossier", "", "no table here"]).count == 0


# ------------------------------------------------------------- the CLI


def test_dossier_json_names_its_fields(fixture_drive, capsys):
    project = _new_project(fixture_drive)
    status = main(["dossier", project.name, "--drive", str(fixture_drive), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert status == 0
    assert payload["drive"] == "TESTDRIVE"
    assert payload["project"] == project.name
    assert payload["name"] == "Oak House"
    assert payload["address"] == "1842 Oak Street, Oakland, CA 94612"
    assert payload["use_case"] == "Renovation + Addition"
    assert payload["description"] == "Kitchen"
    assert payload["created"] == "2026-08-13"
    assert payload["billing_contact"]["email"] == "oak-house@example.com"
    assert payload["client_contact"]["id"] == payload["billing_contact"]["id"]
    assert payload["decisions"] == {"count": 0, "latest": []}
    assert len(payload["source_digest"]) == 64


def test_dossier_text_renders_the_facts_table(fixture_drive, capsys):
    project = _new_project(fixture_drive)
    status = main(["dossier", project.name, "--drive", str(fixture_drive)])
    out = capsys.readouterr().out

    assert status == 0
    assert "Project     Oak House" in out
    assert "1842 Oak Street, Oakland, CA 94612" in out
    assert "Renovation + Addition" in out
    assert "Billing:" in out and "Client:" in out
    assert "Decisions (none recorded)" in out
    assert "e edit" in out and "o open" in out


def test_dossier_malformed_exits_2_with_the_reason(fixture_drive, capsys):
    make_project(fixture_drive, "260813_Broken",
                 files={"PROJECT.md": MALFORMED, **agent_files(fixture_drive)})
    status = main(["dossier", "260813_Broken", "--drive", str(fixture_drive)])
    err = capsys.readouterr().err
    assert status == 2
    assert "incomplete structured address keys" in err


def test_dossier_missing_exits_2(fixture_drive, capsys):
    make_project(fixture_drive, "260813_Bare", files=agent_files(fixture_drive))
    status = main(["dossier", "260813_Bare", "--drive", str(fixture_drive)])
    err = capsys.readouterr().err
    assert status == 2
    assert "cannot read project dossier" in err


def test_dossier_unknown_project_exits_2(fixture_drive, capsys):
    _new_project(fixture_drive)
    status = main(["dossier", "260813_Ghost", "--drive", str(fixture_drive)])
    assert status == 2
    assert "no project folder" in capsys.readouterr().err


# ------------------------------------------------------------- the mode


async def test_the_mode_renders_the_facts_table(fixture_drive):
    """The stub string is gone: a real project draws its validated facts."""
    _new_project(fixture_drive)
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        body = await _open_dossier(app, pilot)
        assert "lands here" not in body
        assert "Project     Oak House" in body
        assert "1842 Oak Street, Oakland, CA 94612" in body
        assert "Renovation + Addition" in body
        assert "Billing:" in body and "oak-house@example.com" in body
        assert "Client:" in body
        assert "Decisions (none recorded)" in body
        # Read-only, and the footer line says where the writes live.
        assert "e edit" in body and "o open" in body


async def test_a_missing_dossier_points_at_the_unmet_expectation(fixture_drive):
    make_project(fixture_drive, "260813_Bare", sections=["01 Model"],
                 files=agent_files(fixture_drive))
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        body = await _open_dossier(app, pilot)
        assert "No PROJECT.md" in body
        assert "unmet Expectation" in body
        assert "e edit" not in body    # nothing to edit; backfill lives one mode away


async def test_a_malformed_dossier_renders_the_reason(fixture_drive):
    make_project(fixture_drive, "260813_Broken",
                 files={"PROJECT.md": MALFORMED, **agent_files(fixture_drive)})
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        body = await _open_dossier(app, pilot)
        assert "PROJECT.md has incomplete structured address keys" in body
        assert "Blank would mean unknown" in body


async def test_a_legacy_dossier_renders_as_malformed_for_atlas(fixture_drive):
    """Norma-era front matter without the Atlas intake keys: the same honesty,
    not a guess - blank would mis-scope the facts Norma trusts (ticket 09)."""
    make_project(fixture_drive, "260813_Legacy",
                 files={"PROJECT.md": LEGACY_FRONT_MATTER, **agent_files(fixture_drive)})
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        body = await _open_dossier(app, pilot)
        assert "PROJECT.md is missing required Atlas intake key" in body
        # None of the legacy prose leaks through as if it were a fact.
        assert "Confounding" not in body


async def test_a_prose_dossier_says_the_front_matter_is_missing(fixture_drive):
    make_project(fixture_drive, "260813_Prose",
                 files={"PROJECT.md": PROSE, **agent_files(fixture_drive)})
    app = AtlasApp(fixture_drive, follow_debounce=0)

    async with app.run_test(size=(120, 51)) as pilot:
        body = await _open_dossier(app, pilot)
        assert "PROJECT.md is missing Atlas YAML front matter" in body


# ------------------------------------------------------------- headless renders


async def test_the_error_states_hold_at_the_measured_widths(fixture_drive):
    """The ticket 09 acceptance: missing, malformed and legacy, each rendering
    its reason at every measured width and row count."""
    make_project(fixture_drive, "260813_Bare", sections=["01 Model"],
                 files=agent_files(fixture_drive))
    make_project(fixture_drive, "260813_Broken",
                 files={"PROJECT.md": MALFORMED, **agent_files(fixture_drive)})
    make_project(fixture_drive, "260813_Legacy",
                 files={"PROJECT.md": LEGACY_FRONT_MATTER, **agent_files(fixture_drive)})

    expectations = {
        "260813_Bare": "No PROJECT.md",
        "260813_Broken": "incomplete structured address keys",
        "260813_Legacy": "missing required Atlas intake key",
    }
    for width in WIDTHS:
        for rows in ROWS:
            app = AtlasApp(fixture_drive, follow_debounce=0)
            async with app.run_test(size=(width, rows)) as pilot:
                await settle(app, pilot)
                for name, expected in expectations.items():
                    app._fill(preserve=name)
                    await settle(app, pilot)
                    row = app._selected_row()
                    assert row is not None and row.key == name, (width, rows, name)
                    app._companion_mode = DOSSIER
                    app._update_workspace(row)
                    await pilot.pause()
                    body = _body(app)
                    assert expected in body, (width, rows, name, body)
                    assert "lands here" not in body


async def test_the_facts_table_holds_at_the_measured_widths(fixture_drive):
    _new_project(fixture_drive)

    for width in WIDTHS:
        for rows in ROWS:
            app = AtlasApp(fixture_drive, follow_debounce=0)
            async with app.run_test(size=(width, rows)) as pilot:
                body = await _open_dossier(app, pilot)
                assert "Oak House" in body, (width, rows)
                assert "Billing:" in body, (width, rows)
                assert "e edit" in body, (width, rows)
