"""`contacts add --id`: a contact minted in the CRM keeps its UUID (CRM ADR 0004)."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid1, uuid4

import pytest

from atlas.cli import main
from atlas.core.contacts import (
    ContactDraft,
    ContactError,
    DuplicateContactIdError,
    add_contact,
    load_contacts,
)


def _store(drive: Path) -> Path:
    return drive / "_tools" / "billing-contacts.json"


def _add(drive: Path, email: str, *extra: str) -> int:
    return main(["contacts", "add", "--drive", str(drive), "--first-name", "Ada",
                 "--last-name", "Lovelace", "--email", email, "--json", *extra])


def test_cli_keeps_the_supplied_id(fixture_drive, capsys):
    wanted = str(uuid4())

    assert _add(fixture_drive, "ada@example.com", f"--id={wanted}", "--yes") == 0

    added = json.loads(capsys.readouterr().out)
    assert added["id"] == wanted
    assert [c.id for c in load_contacts(fixture_drive).contacts] == [wanted]


def test_supplied_id_is_stored_canonical(fixture_drive):
    wanted = uuid4()

    contact = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
        contact_id=wanted.hex.upper(),
    )

    assert contact.id == str(wanted)
    stored = json.loads(_store(fixture_drive).read_text(encoding="utf-8"))
    assert stored["contacts"][0]["id"] == str(wanted)


@pytest.mark.parametrize("bad", ["not-a-uuid", "", str(uuid1()),
                                 "00000000-0000-0000-0000-000000000000"])
def test_non_uuid4_exits_2_and_writes_nothing(fixture_drive, capsys, bad):
    assert _add(fixture_drive, "ada@example.com", f"--id={bad}") == 2

    assert "UUID4" in capsys.readouterr().err
    assert not _store(fixture_drive).exists()


def test_duplicate_id_exits_2_and_keeps_the_store(fixture_drive, capsys):
    wanted = str(uuid4())
    assert _add(fixture_drive, "ada@example.com", f"--id={wanted}") == 0
    capsys.readouterr()
    before = _store(fixture_drive).read_bytes()

    assert _add(fixture_drive, "other@example.com", f"--id={wanted.upper()}") == 2

    err = capsys.readouterr().err
    assert "contact ID already exists" in err and wanted in err
    assert _store(fixture_drive).read_bytes() == before


def test_duplicate_email_with_new_id_exits_2(fixture_drive, capsys):
    assert _add(fixture_drive, "ada@example.com") == 0
    capsys.readouterr()
    before = _store(fixture_drive).read_bytes()

    assert _add(fixture_drive, "ADA@example.com", f"--id={uuid4()}") == 2

    assert "email already exists" in capsys.readouterr().err
    assert _store(fixture_drive).read_bytes() == before


def test_core_raises_typed_errors(fixture_drive):
    wanted = str(uuid4())
    draft = ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com")
    add_contact(fixture_drive, draft, contact_id=wanted)

    with pytest.raises(DuplicateContactIdError):
        add_contact(fixture_drive,
                    ContactDraft(first_name="B", last_name="C", email="b@example.com"),
                    contact_id=wanted)
    with pytest.raises(ContactError):
        add_contact(fixture_drive, draft, contact_id="nope")


def test_without_id_atlas_still_mints_one(fixture_drive, capsys):
    assert _add(fixture_drive, "ada@example.com") == 0

    minted = json.loads(capsys.readouterr().out)["id"]
    from uuid import UUID
    assert UUID(minted).version == 4
