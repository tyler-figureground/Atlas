"""The CRM link: `crm_id` in PROJECT.md, `project link`, and `new --date/--crm-id`.

The CRM's Bridge calls these only as `atlas ... --json --yes` (CRM ADR 0004):
exit 0 done, 2 error, and a retried command must be a no-op, not a failure.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.project_data import load_project_record, read_crm_id


def _contact(drive: Path, capsys) -> str:
    assert main([
        "contacts", "add", "--drive", str(drive), "--first-name", "Ada",
        "--last-name", "Lovelace", "--email", "ada@example.com", "--json",
    ]) == 0
    return json.loads(capsys.readouterr().out)["id"]


def _new(drive: Path, capsys, *extra: str) -> tuple[int, dict | None, str]:
    contact = _contact(drive, capsys) if not (drive / "_tools" / "billing-contacts.json").exists() \
        else "ada@example.com"
    status = main([
        "new", "--drive", str(drive), "--name", "Oak House", "--street", "1842 Oak Street",
        "--city", "Oakland", "--state", "CA", "--zip", "94612", "--use-case", "Renovation",
        "--billing-contact", contact, "--client-contact", contact,
        "--desc", "Kitchen", "--json", *extra,
    ])
    captured = capsys.readouterr()
    return status, (json.loads(captured.out) if status == 0 else None), captured.err


def _link(drive: Path, folder: str, crm_id: str, *extra: str) -> int:
    return main(["project", "link", folder, f"--crm-id={crm_id}", "--drive", str(drive),
                 "--json", *extra])


# -- atlas new --date / --crm-id ---------------------------------------------


def test_new_date_sets_folder_prefix_and_created(fixture_drive, capsys):
    status, created, _ = _new(fixture_drive, capsys, "--date", "260415", "--yes")

    assert status == 0
    assert created["created"].startswith("260415_")
    assert created["created_date"] == "2026-04-15"
    assert created["crm_id"] is None
    text = (fixture_drive / created["created"] / "PROJECT.md").read_text(encoding="utf-8")
    assert "| Created | 2026-04-15 |" in text
    assert "crm_id" not in text
    index = (fixture_drive / "_Project Index.md").read_text(encoding="utf-8")
    assert "2026-04-15" in index


def test_new_without_date_keeps_today(fixture_drive, capsys):
    from datetime import date

    status, created, _ = _new(fixture_drive, capsys)

    assert status == 0
    assert created["created"].startswith(date.today().strftime("%y%m%d") + "_")


@pytest.mark.parametrize("bad", ["2604151", "26041", "260230", "261301", "abcdef", "2026-04-15",
                                 "990101"])
def test_new_rejects_invalid_date_and_creates_nothing(fixture_drive, capsys, bad):
    _contact(fixture_drive, capsys)
    before = sorted(p.name for p in fixture_drive.iterdir())

    status, _, err = _new(fixture_drive, capsys, "--date", bad)

    assert status == 2
    assert "--date" in err
    assert sorted(p.name for p in fixture_drive.iterdir()) == before


def test_new_crm_id_is_written_and_read_back(fixture_drive, capsys):
    status, created, _ = _new(fixture_drive, capsys, "--date", "260415",
                              "--crm-id", "j57abc_DEF-123", "--yes")

    assert status == 0
    assert created["crm_id"] == "j57abc_DEF-123"
    project = fixture_drive / created["created"]
    raw = (project / "PROJECT.md").read_bytes()
    assert b'\r\ncrm_id: "j57abc_DEF-123"\r\n' in raw
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert load_project_record(project).crm_id == "j57abc_DEF-123"


def test_new_rejects_invalid_crm_id_before_creating(fixture_drive, capsys):
    _contact(fixture_drive, capsys)
    before = sorted(p.name for p in fixture_drive.iterdir())

    status, _, err = _new(fixture_drive, capsys, "--crm-id=")
    assert status == 2 and "CRM id" in err
    status, _, err = _new(fixture_drive, capsys, "--crm-id", "bad id\nx")

    assert status == 2
    assert "CRM id" in err
    assert sorted(p.name for p in fixture_drive.iterdir()) == before


# -- atlas project link ------------------------------------------------------


def test_link_adds_key_keeps_every_other_byte_and_is_idempotent(fixture_drive, capsys):
    _, created, _ = _new(fixture_drive, capsys)
    folder = created["created"]
    dossier = fixture_drive / folder / "PROJECT.md"
    before = dossier.read_bytes()

    assert _link(fixture_drive, folder, "j57abc", "--yes") == 0
    result = json.loads(capsys.readouterr().out)
    assert result == {
        "folder": folder, "path": str(fixture_drive / folder), "crm_id": "j57abc",
        "previous_crm_id": None, "changed": True, "applied": True,
    }
    after = dossier.read_bytes()
    added = [line for line in after.split(b"\r\n") if line not in before.split(b"\r\n")]
    assert added == [b'crm_id: "j57abc"']
    # Only one line was added: every other line is byte-for-byte as before.
    assert after.replace(b'crm_id: "j57abc"\r\n', b"") == before

    assert _link(fixture_drive, folder, "j57abc", "--yes") == 0
    again = json.loads(capsys.readouterr().out)
    assert again["changed"] is False and again["applied"] is False
    assert dossier.read_bytes() == after


def test_link_refuses_a_different_existing_id(fixture_drive, capsys):
    _, created, _ = _new(fixture_drive, capsys, "--crm-id", "first")
    folder = created["created"]
    dossier = fixture_drive / folder / "PROJECT.md"
    before = dossier.read_bytes()

    assert _link(fixture_drive, folder, "second", "--yes") == 2
    err = capsys.readouterr().err
    assert "already linked" in err and "first" in err
    assert dossier.read_bytes() == before


def test_link_requires_yes_when_scripted(fixture_drive, capsys):
    _, created, _ = _new(fixture_drive, capsys)
    folder = created["created"]
    dossier = fixture_drive / folder / "PROJECT.md"
    before = dossier.read_bytes()

    assert _link(fixture_drive, folder, "j57abc") == 2
    assert "--yes" in capsys.readouterr().err
    assert dossier.read_bytes() == before


def test_link_dry_run_writes_nothing(fixture_drive, capsys):
    _, created, _ = _new(fixture_drive, capsys)
    folder = created["created"]
    dossier = fixture_drive / folder / "PROJECT.md"
    before = dossier.read_bytes()

    assert _link(fixture_drive, folder, "j57abc", "--dry-run") == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["changed"] is True and plan["applied"] is False
    assert dossier.read_bytes() == before


def test_link_fills_a_blank_key_and_keeps_its_comment(fixture_drive):
    project = fixture_drive / "260101_1 Test Street"
    project.mkdir()
    (project / "PROJECT.md").write_bytes(
        b"---\nproject: Test\ncrm_id:   # set by the CRM\noccupancy_group: [B, \"S-1\"]\n---\n# body\n"
    )

    assert _link(fixture_drive, project.name, "abc", "--yes") == 0
    text = (project / "PROJECT.md").read_bytes()
    assert text == (
        b"---\r\nproject: Test\r\ncrm_id: \"abc\" # set by the CRM\r\n"
        b"occupancy_group: [B, \"S-1\"]\r\n---\r\n# body\r\n"
    )
    assert read_crm_id(project) == "abc"


@pytest.mark.parametrize("bad", ["", "-lead", "has space", "x" * 129, "quote\"d"])
def test_link_rejects_invalid_id(fixture_drive, capsys, bad):
    _, created, _ = _new(fixture_drive, capsys)

    assert _link(fixture_drive, created["created"], bad, "--yes") == 2
    assert "invalid CRM id" in capsys.readouterr().err


def test_link_refuses_unsupported_crm_id_shape(fixture_drive, capsys):
    project = fixture_drive / "260101_1 Test Street"
    project.mkdir()
    (project / "PROJECT.md").write_bytes(b"---\ncrm_id: [a, b]\n---\n")

    assert _link(fixture_drive, project.name, "abc", "--yes") == 2
    assert "unsupported YAML for 'crm_id'" in capsys.readouterr().err


# -- read surfaces -----------------------------------------------------------


def test_dossier_and_search_json_expose_crm_id(fixture_drive, capsys):
    _, linked, _ = _new(fixture_drive, capsys, "--crm-id", "j57abc")

    assert main(["dossier", linked["created"], "--drive", str(fixture_drive), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["crm_id"] == "j57abc"

    assert main(["search", "Oak", "--drive", str(fixture_drive), "--json"]) == 0
    hits = json.loads(capsys.readouterr().out)["results"]
    assert hits and all(hit["crm_id"] == "j57abc" for hit in hits)


def test_dossier_json_crm_id_is_null_when_unlinked(fixture_drive, capsys):
    _, created, _ = _new(fixture_drive, capsys)

    assert main(["dossier", created["created"], "--drive", str(fixture_drive), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["crm_id"] is None


def test_new_explicit_no_client_round_trips_null(fixture_drive, capsys):
    contact = _contact(fixture_drive, capsys)
    status = main([
        "new", "--drive", str(fixture_drive), "--name", "No Client", "--street",
        "1842 Oak Street", "--city", "Oakland", "--state", "CA", "--zip", "94612",
        "--use-case", "Renovation", "--billing-contact", contact,
        "--no-client-contact", "--date", "260415", "--json", "--yes",
    ])
    created = json.loads(capsys.readouterr().out)

    assert status == 0
    assert created["client_contact_id"] is None
    assert created["billing_contact"]["kind"] == "person"
    assert created["client_contact"] is None
    assert main(["dossier", created["created"], "--drive", str(fixture_drive), "--json"]) == 0
    dossier = json.loads(capsys.readouterr().out)
    assert dossier["billing_contact"]["kind"] == "person"
    assert dossier["client_contact"] is None


def test_organization_billing_round_trips_without_synthetic_names(fixture_drive, capsys):
    assert main([
        "contacts", "add", "--drive", str(fixture_drive), "--kind", "organization",
        "--display-name", "Figure Ground", "--legal-name",
        "Figure Ground Architecture, Inc.", "--email", "accounts@example.com", "--json",
    ]) == 0
    organization = json.loads(capsys.readouterr().out)
    status = main([
        "new", "--drive", str(fixture_drive), "--name", "Organization Billing",
        "--street", "1842 Oak Street", "--city", "Oakland", "--state", "CA",
        "--zip", "94612", "--use-case", "Renovation", "--billing-contact",
        organization["id"], "--no-client-contact", "--date", "260415", "--json", "--yes",
    ])
    created = json.loads(capsys.readouterr().out)

    assert status == 0
    assert created["billing_contact"]["kind"] == "organization"
    assert created["client_contact"] is None
    assert main(["dossier", created["created"], "--drive", str(fixture_drive), "--json"]) == 0
    billing = json.loads(capsys.readouterr().out)["billing_contact"]
    assert billing["kind"] == "organization"
    assert billing["display_name"] == "Figure Ground"
    assert "first_name" not in billing and "last_name" not in billing


def test_new_never_defaults_client_to_billing(fixture_drive, capsys):
    contact = _contact(fixture_drive, capsys)
    status = main([
        "new", "--drive", str(fixture_drive), "--name", "Ambiguous", "--street",
        "1842 Oak Street", "--city", "Oakland", "--state", "CA", "--zip", "94612",
        "--use-case", "Renovation", "--billing-contact", contact, "--json", "--yes",
    ])

    assert status == 2
    assert "--client-contact or --no-client-contact" in capsys.readouterr().err


def test_project_edit_omits_to_keep_and_explicitly_clears_client(fixture_drive, capsys):
    _, created, _ = _new(fixture_drive, capsys, "--date", "260415", "--yes")
    folder = created["created"]

    assert main([
        "project", "edit", folder, "--drive", str(fixture_drive), "--use-case", "Addition",
        "--yes", "--json",
    ]) == 0
    kept = json.loads(capsys.readouterr().out)
    assert kept["client_contact_id"] == kept["billing_contact_id"]
    assert kept["client_contact"]["kind"] == "person"

    assert main([
        "project", "edit", folder, "--drive", str(fixture_drive),
        "--clear-client-contact", "--yes", "--json",
    ]) == 0
    cleared = json.loads(capsys.readouterr().out)
    assert cleared["client_contact_id"] is None
    assert cleared["client_contact"] is None
    assert load_project_record(fixture_drive / folder).client_contact is None


def test_reading_legacy_project_snapshot_never_rewrites_it(fixture_drive, capsys):
    _, created, _ = _new(fixture_drive, capsys, "--date", "260415", "--yes")
    dossier = fixture_drive / created["created"] / "PROJECT.md"
    source = dossier.read_bytes()
    legacy = b"\r\n".join(
        line
        for line in source.split(b"\r\n")
        if not any(
            marker in line
            for marker in (
                b"_contact_kind:", b"_contact_display_name:", b"_contact_legal_name:"
            )
        )
    )
    dossier.write_bytes(legacy)
    before = dossier.read_bytes()

    assert main(["dossier", created["created"], "--drive", str(fixture_drive), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["billing_contact"]["kind"] == "person"
    assert dossier.read_bytes() == before
