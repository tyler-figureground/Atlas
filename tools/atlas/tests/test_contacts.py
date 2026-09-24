from __future__ import annotations

import json
import os
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from uuid import UUID

import pytest

import atlas.core.contacts as contacts_module
from atlas.core.contacts import (
    ContactDraft,
    ContactError,
    DuplicateContactError,
    MailingAddress,
    add_contact,
    find_contact,
    load_contacts,
    update_contact,
)


def test_mailing_address_accepts_physical_numbered_street_and_is_immutable():
    address = MailingAddress(
        street=" 123 Broadway ",
        unit=" Suite 4 ",
        city=" Oakland ",
        state=" ca ",
        postal_code=" 94607 ",
        country=" us ",
    )

    assert address == MailingAddress(
        street="123 Broadway",
        unit="Suite 4",
        city="Oakland",
        state="CA",
        postal_code="94607",
        country="US",
    )
    with pytest.raises(FrozenInstanceError):
        address.city = "Berkeley"


@pytest.mark.parametrize("street", ["PO Box 123", "P.O. Box 456", "p.o. box 789"])
def test_mailing_address_accepts_po_box_variants(street):
    address = MailingAddress(
        street=street,
        city="Oakland",
        state="CA",
        postal_code="94607",
    )

    assert address.street == street


def test_contact_draft_accepts_mailing_address_and_po_box_round_trips(fixture_drive):
    created = add_contact(
        fixture_drive,
        ContactDraft(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            address=MailingAddress(
                street="P.O. Box 42",
                city="Oakland",
                state="CA",
                postal_code="94607-1234",
            ),
        ),
    )

    assert created.address == {
        "street": "P.O. Box 42",
        "unit": "",
        "city": "Oakland",
        "state": "CA",
        "postal_code": "94607-1234",
        "country": "US",
    }
    assert load_contacts(fixture_drive).contacts == (created,)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"street": "Broadway"}, "street number"),
        ({"city": ""}, "city is required"),
        ({"state": "XX"}, "valid two-letter US"),
        ({"postal_code": "946"}, "ZIP"),
        ({"country": "CA"}, "country must be US"),
    ],
)
def test_mailing_address_rejects_non_mailing_or_incomplete_values(overrides, message):
    values = {
        "street": "PO Box 42",
        "city": "Oakland",
        "state": "CA",
        "postal_code": "94607",
        "country": "US",
    }
    values.update(overrides)

    with pytest.raises(ContactError, match=message):
        MailingAddress(**values)


def test_missing_store_returns_empty_directory_without_writing(fixture_drive):
    directory = load_contacts(fixture_drive)

    assert directory.contacts == ()
    assert not (fixture_drive / "_tools" / "billing-contacts.json").exists()


def test_first_contact_creates_schema_v1_and_round_trips(fixture_drive):
    created = add_contact(
        fixture_drive,
        ContactDraft(first_name=" Ada ", last_name=" Lovelace ", email=" ada@example.com "),
    )

    UUID(created.id)
    assert created.first_name == "Ada"
    assert created.last_name == "Lovelace"
    assert created.email == "ada@example.com"
    assert datetime.fromisoformat(created.created_at.replace("Z", "+00:00")).tzinfo == timezone.utc
    assert created.updated_at == created.created_at
    assert load_contacts(fixture_drive).contacts == (created,)

    stored = json.loads(
        (fixture_drive / "_tools" / "billing-contacts.json").read_text(encoding="utf-8")
    )
    assert stored["schemaVersion"] == 1
    assert stored["contacts"][0]["id"] == created.id


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("first_name", "  "),
        ("last_name", ""),
        ("email", ""),
        ("email", "not-an-email"),
    ],
)
def test_invalid_required_fields_fail_without_writing(fixture_drive, field, value):
    values = {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com"}
    values[field] = value

    with pytest.raises(ContactError, match=field.replace("_", " ")):
        add_contact(fixture_drive, ContactDraft(**values))

    assert not (fixture_drive / "_tools" / "billing-contacts.json").exists()


def test_optional_fields_and_structured_address_round_trip_as_utf8(fixture_drive):
    created = add_contact(
        fixture_drive,
        ContactDraft(
            first_name="Zoë",
            last_name="Saldaña",
            email="zoe@example.com",
            phone=" +1 (510) 555-0100 ",
            company=" Estúdio Norte ",
            address={
                "street": "123 Broadway",
                "unit": "Suite 4",
                "city": "Oakland",
                "state": "ca",
                "postal_code": "94607",
                "country": "us",
            },
        ),
    )

    assert created.phone == "+1 (510) 555-0100"
    assert created.company == "Estúdio Norte"
    assert created.address == {
        "street": "123 Broadway",
        "unit": "Suite 4",
        "city": "Oakland",
        "state": "CA",
        "postal_code": "94607",
        "country": "US",
    }
    assert load_contacts(fixture_drive).contacts == (created,)

    store = fixture_drive / "_tools" / "billing-contacts.json"
    assert "Zoë" in store.read_text(encoding="utf-8")
    assert json.loads(store.read_text(encoding="utf-8"))["contacts"][0]["address"]["postalCode"] == "94607"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"phone": "call-me"}, "phone"),
        ({"phone": "123"}, "phone"),
        ({"address": {"street": "123 Broadway"}}, "address.*city"),
    ],
)
def test_invalid_optional_fields_fail_without_writing(fixture_drive, overrides, message):
    values = {"first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com"}
    values.update(overrides)

    with pytest.raises(ContactError, match=message):
        add_contact(fixture_drive, ContactDraft(**values))

    assert not (fixture_drive / "_tools" / "billing-contacts.json").exists()


def test_duplicate_email_ignores_case_and_whitespace_without_rewriting(fixture_drive):
    add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="Ada@Example.com"),
    )
    store = fixture_drive / "_tools" / "billing-contacts.json"
    before = store.read_bytes()

    with pytest.raises(DuplicateContactError, match="email already exists") as caught:
        add_contact(
            fixture_drive,
            ContactDraft(first_name="Augusta", last_name="King", email=" ada@example.COM "),
        )

    assert caught.value.existing.email == "ada@example.com"
    assert store.read_bytes() == before
    assert len(load_contacts(fixture_drive).contacts) == 1


def test_update_contact_changes_fields_but_preserves_identity_and_created_at(fixture_drive):
    original = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )

    updated = update_contact(
        fixture_drive,
        original.id,
        ContactDraft(
            first_name=" Augusta ",
            last_name=" King ",
            email=" countess@example.com ",
            phone=" +44 20 7946 0958 ",
            company=" Analytical Engines ",
            address={
                "street": "PO Box 42",
                "city": "Oakland",
                "state": "ca",
                "postal_code": "94607",
            },
        ),
    )

    assert updated.id == original.id
    assert updated.created_at == original.created_at
    assert datetime.fromisoformat(updated.updated_at.replace("Z", "+00:00")) > datetime.fromisoformat(
        original.updated_at.replace("Z", "+00:00")
    )
    assert updated.first_name == "Augusta"
    assert updated.last_name == "King"
    assert updated.email == "countess@example.com"
    assert updated.phone == "+44 20 7946 0958"
    assert updated.company == "Analytical Engines"
    assert updated.address["street"] == "PO Box 42"
    assert load_contacts(fixture_drive).contacts == (updated,)


def test_update_contact_email_uniqueness_excludes_the_contact_itself(fixture_drive):
    ada = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    grace = add_contact(
        fixture_drive,
        ContactDraft(first_name="Grace", last_name="Hopper", email="grace@example.com"),
    )

    updated = update_contact(
        fixture_drive,
        ada.id,
        ContactDraft(first_name="Ada", last_name="Lovelace", email=" ADA@EXAMPLE.COM "),
    )
    assert updated.email == "ada@example.com"

    store = fixture_drive / "_tools" / "billing-contacts.json"
    before = store.read_bytes()
    with pytest.raises(DuplicateContactError) as caught:
        update_contact(
            fixture_drive,
            ada.id,
            ContactDraft(first_name="Ada", last_name="Lovelace", email=" GRACE@example.com "),
        )

    assert caught.value.existing == grace
    assert "Grace Hopper" in str(caught.value)
    assert "select that contact or use a different email" in str(caught.value)
    assert store.read_bytes() == before


def test_update_contact_missing_id_is_actionable_and_does_not_rewrite(fixture_drive):
    add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    store = fixture_drive / "_tools" / "billing-contacts.json"
    before = store.read_bytes()

    with pytest.raises(
        ContactError,
        match="contact ID not found.*existing contact ID.*file not changed",
    ):
        update_contact(
            fixture_drive,
            "024b17fb-71a8-4075-825a-a77f315f8a52",
            ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
        )

    assert store.read_bytes() == before


def test_update_contact_refuses_malformed_store_without_rewriting(fixture_drive):
    store = fixture_drive / "_tools" / "billing-contacts.json"
    store.write_bytes(b"{not json")
    before = store.read_bytes()

    with pytest.raises(ContactError, match="not valid JSON.*file not changed"):
        update_contact(
            fixture_drive,
            "024b17fb-71a8-4075-825a-a77f315f8a52",
            ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
        )

    assert store.read_bytes() == before


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        (b"{not json", "not valid JSON"),
        (b'{"schemaVersion": 2, "contacts": []}\n', "unsupported schemaVersion 2"),
        (b'{"schemaVersion": 1}\n', "missing.*contacts"),
    ],
)
def test_invalid_store_is_actionable_and_never_rewritten(fixture_drive, contents, message):
    store = fixture_drive / "_tools" / "billing-contacts.json"
    store.write_bytes(contents)

    with pytest.raises(ContactError, match=message):
        add_contact(
            fixture_drive,
            ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
        )

    assert store.read_bytes() == contents


def test_directory_is_sorted_and_contacts_are_found_by_id_or_email(fixture_drive):
    lovelace = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    add_contact(
        fixture_drive,
        ContactDraft(
            first_name="Grace", last_name="Hopper", email="grace-z@example.com", company="Zeta"
        ),
    )
    hopper_alpha = add_contact(
        fixture_drive,
        ContactDraft(
            first_name="Grace", last_name="Hopper", email="grace-a@example.com", company="Alpha"
        ),
    )
    directory = load_contacts(fixture_drive)

    assert [contact.email for contact in directory.contacts] == [
        "grace-a@example.com",
        "grace-z@example.com",
        "ada@example.com",
    ]
    assert find_contact(directory, lovelace.id) == lovelace
    assert find_contact(directory, " GRACE-A@EXAMPLE.COM ") == hopper_alpha
    assert find_contact(directory, "missing@example.com") is None


def test_existing_writer_lock_refuses_without_changing_store(fixture_drive):
    created = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    store = fixture_drive / "_tools" / "billing-contacts.json"
    lock = store.with_suffix(".json.lock")
    before = store.read_bytes()
    lock.write_text("busy", encoding="utf-8")

    with pytest.raises(ContactError, match="being updated"):
        add_contact(
            fixture_drive,
            ContactDraft(first_name="Grace", last_name="Hopper", email="grace@example.com"),
        )

    assert store.read_bytes() == before
    assert load_contacts(fixture_drive).contacts == (created,)


def test_stale_writer_lock_is_recovered(fixture_drive):
    store = fixture_drive / "_tools" / "billing-contacts.json"
    lock = store.with_suffix(".json.lock")
    lock.write_text("abandoned", encoding="utf-8")
    os.utime(lock, (1, 1))

    created = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )

    assert created.email == "ada@example.com"
    assert not lock.exists()


def test_update_contact_respects_existing_writer_lock(fixture_drive):
    created = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    store = fixture_drive / "_tools" / "billing-contacts.json"
    lock = store.with_suffix(".json.lock")
    before = store.read_bytes()
    lock.write_text("busy", encoding="utf-8")

    with pytest.raises(ContactError, match="being updated"):
        update_contact(
            fixture_drive,
            created.id,
            ContactDraft(first_name="Augusta", last_name="King", email="ada@example.com"),
        )

    assert store.read_bytes() == before


def test_atomic_replace_failure_preserves_store_and_cleans_temp(fixture_drive, monkeypatch):
    add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    tools_dir = fixture_drive / "_tools"
    store = tools_dir / "billing-contacts.json"
    before = store.read_bytes()

    def fail_replace(source, destination):
        assert source.parent == destination.parent == tools_dir
        assert source.exists()
        raise OSError("simulated replace failure")

    monkeypatch.setattr(contacts_module.os, "replace", fail_replace)

    with pytest.raises(ContactError, match="cannot atomically replace"):
        add_contact(
            fixture_drive,
            ContactDraft(first_name="Grace", last_name="Hopper", email="grace@example.com"),
        )

    assert store.read_bytes() == before
    assert sorted(path.name for path in tools_dir.iterdir()) == [
        "billing-contacts.json",
        "testdrive-map.json",
    ]


def test_update_contact_atomic_replace_failure_preserves_store(fixture_drive, monkeypatch):
    created = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    tools_dir = fixture_drive / "_tools"
    store = tools_dir / "billing-contacts.json"
    before = store.read_bytes()

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(contacts_module.os, "replace", fail_replace)

    with pytest.raises(ContactError, match="cannot atomically replace"):
        update_contact(
            fixture_drive,
            created.id,
            ContactDraft(first_name="Augusta", last_name="King", email="ada@example.com"),
        )

    assert store.read_bytes() == before
    assert sorted(path.name for path in tools_dir.iterdir()) == [
        "billing-contacts.json",
        "testdrive-map.json",
    ]


def test_concurrent_change_is_reloaded_and_retried_once(fixture_drive, monkeypatch):
    add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    store = fixture_drive / "_tools" / "billing-contacts.json"
    concurrent_payload = json.loads(store.read_text(encoding="utf-8"))
    concurrent_payload["contacts"].append(
        {
            "id": "024b17fb-71a8-4075-825a-a77f315f8a52",
            "firstName": "Katherine",
            "lastName": "Johnson",
            "email": "katherine@example.com",
            "phone": None,
            "company": None,
            "address": None,
            "createdAt": "2026-08-31T12:00:00Z",
            "updatedAt": "2026-08-31T12:00:00Z",
        }
    )
    real_fsync = contacts_module.os.fsync
    flushes = 0

    def inject_concurrent_write(file_descriptor):
        nonlocal flushes
        real_fsync(file_descriptor)
        flushes += 1
        if flushes == 1:
            store.write_text(
                json.dumps(concurrent_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    monkeypatch.setattr(contacts_module.os, "fsync", inject_concurrent_write)

    add_contact(
        fixture_drive,
        ContactDraft(first_name="Grace", last_name="Hopper", email="grace@example.com"),
    )

    assert flushes == 2
    assert {contact.email for contact in load_contacts(fixture_drive).contacts} == {
        "ada@example.com",
        "grace@example.com",
        "katherine@example.com",
    }


def test_update_contact_reloads_once_after_concurrent_change(fixture_drive, monkeypatch):
    ada = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    store = fixture_drive / "_tools" / "billing-contacts.json"
    concurrent_payload = json.loads(store.read_text(encoding="utf-8"))
    concurrent_payload["contacts"].append(
        {
            "id": "024b17fb-71a8-4075-825a-a77f315f8a52",
            "firstName": "Katherine",
            "lastName": "Johnson",
            "email": "katherine@example.com",
            "phone": None,
            "company": None,
            "address": None,
            "createdAt": "2026-08-31T12:00:00Z",
            "updatedAt": "2026-08-31T12:00:00Z",
        }
    )
    real_fsync = contacts_module.os.fsync
    flushes = 0

    def inject_concurrent_write(file_descriptor):
        nonlocal flushes
        real_fsync(file_descriptor)
        flushes += 1
        if flushes == 1:
            store.write_text(
                json.dumps(concurrent_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    monkeypatch.setattr(contacts_module.os, "fsync", inject_concurrent_write)

    updated = update_contact(
        fixture_drive,
        ada.id,
        ContactDraft(first_name="Augusta", last_name="King", email="ada@example.com"),
    )

    assert flushes == 2
    directory = load_contacts(fixture_drive)
    assert find_contact(directory, ada.id) == updated
    assert find_contact(directory, "katherine@example.com") is not None


def test_second_concurrent_change_is_preserved_and_add_is_refused(fixture_drive, monkeypatch):
    add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    store = fixture_drive / "_tools" / "billing-contacts.json"
    real_fsync = contacts_module.os.fsync
    flushes = 0

    def keep_changing_store(file_descriptor):
        nonlocal flushes
        real_fsync(file_descriptor)
        flushes += 1
        payload = json.loads(store.read_text(encoding="utf-8"))
        payload["concurrentRevision"] = flushes
        store.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    monkeypatch.setattr(contacts_module.os, "fsync", keep_changing_store)

    with pytest.raises(ContactError, match="changed twice.*not overwritten"):
        add_contact(
            fixture_drive,
            ContactDraft(first_name="Grace", last_name="Hopper", email="grace@example.com"),
        )

    assert flushes == 2
    assert json.loads(store.read_text(encoding="utf-8"))["concurrentRevision"] == 2
    assert find_contact(load_contacts(fixture_drive), "grace@example.com") is None


@pytest.mark.parametrize(
    ("contacts", "message"),
    [
        ([{"firstName": "Ada"}], "contact 1.*id"),
        (
            [
                {
                    "id": "not-a-uuid",
                    "firstName": "Ada",
                    "lastName": "Lovelace",
                    "email": "ada@example.com",
                    "createdAt": "2026-08-31T12:00:00Z",
                    "updatedAt": "2026-08-31T12:00:00Z",
                }
            ],
            "contact 1.*UUID",
        ),
        (
            [
                {
                    "id": "024b17fb-71a8-4075-825a-a77f315f8a52",
                    "firstName": "Ada",
                    "lastName": "Lovelace",
                    "email": "ada@example.com",
                    "createdAt": "2026-08-31T12:00:00",
                    "updatedAt": "2026-08-31T12:00:00Z",
                }
            ],
            "contact 1.*createdAt.*UTC",
        ),
        (
            [
                {
                    "id": "024b17fb-71a8-4075-825a-a77f315f8a52",
                    "firstName": "Ada",
                    "lastName": "Lovelace",
                    "email": "Ada@example.com",
                    "createdAt": "2026-08-31T12:00:00Z",
                    "updatedAt": "2026-08-31T12:00:00Z",
                },
                {
                    "id": "d947c460-ff3f-49aa-a26d-00f00d5dabe0",
                    "firstName": "Augusta",
                    "lastName": "King",
                    "email": "ada@EXAMPLE.COM",
                    "createdAt": "2026-08-31T12:00:00Z",
                    "updatedAt": "2026-08-31T12:00:00Z",
                },
            ],
            "duplicate email",
        ),
    ],
)
def test_malformed_contact_records_fail_without_writing(fixture_drive, contacts, message):
    store = fixture_drive / "_tools" / "billing-contacts.json"
    store.write_text(
        json.dumps({"schemaVersion": 1, "contacts": contacts}) + "\n",
        encoding="utf-8",
    )
    before = store.read_bytes()

    with pytest.raises(ContactError, match=message):
        load_contacts(fixture_drive)

    assert store.read_bytes() == before


def test_loaded_address_uses_mailing_address_validation(fixture_drive):
    add_contact(
        fixture_drive,
        ContactDraft(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            address={
                "street": "123 Broadway",
                "city": "Oakland",
                "state": "CA",
                "postal_code": "94607",
            },
        ),
    )
    store = fixture_drive / "_tools" / "billing-contacts.json"
    payload = json.loads(store.read_text(encoding="utf-8"))
    payload["contacts"][0]["address"]["street"] = "Broadway"
    store.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    before = store.read_bytes()

    with pytest.raises(ContactError, match="address.*street number.*file not changed"):
        load_contacts(fixture_drive)

    assert store.read_bytes() == before


def _store_with_unknown_fields(fixture_drive):
    ada = add_contact(
        fixture_drive,
        ContactDraft(
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            address={
                "street": "123 Broadway",
                "city": "Oakland",
                "state": "CA",
                "postal_code": "94607",
            },
        ),
    )
    store = fixture_drive / "_tools" / "billing-contacts.json"
    payload = json.loads(store.read_text(encoding="utf-8"))
    payload["_note"] = "maintained by the office manager"
    payload["contacts"][0]["title"] = "Principal"
    payload["contacts"][0]["notes"] = {"since": 2019}
    payload["contacts"][0]["address"]["attention"] = "Accounts"
    store.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return ada, store


def test_unrelated_add_keeps_unknown_directory_and_contact_fields(fixture_drive):
    # The directory is shared: a newer Atlas on another workstation may add a
    # field this build does not know. Writing must not strip it.
    _, store = _store_with_unknown_fields(fixture_drive)

    add_contact(
        fixture_drive,
        ContactDraft(first_name="Bob", last_name="Builder", email="bob@example.com"),
    )

    payload = json.loads(store.read_text(encoding="utf-8"))
    assert payload["_note"] == "maintained by the office manager"
    ada = next(item for item in payload["contacts"] if item["email"] == "ada@example.com")
    assert ada["title"] == "Principal"
    assert ada["notes"] == {"since": 2019}
    assert ada["address"]["attention"] == "Accounts"


def test_update_keeps_unknown_fields_of_the_edited_contact(fixture_drive):
    ada, store = _store_with_unknown_fields(fixture_drive)

    update_contact(
        fixture_drive,
        ada.id,
        ContactDraft(
            first_name="Ada",
            last_name="King",
            email="ada@example.com",
            address={
                "street": "123 Broadway",
                "city": "Oakland",
                "state": "CA",
                "postal_code": "94607",
            },
        ),
    )

    payload = json.loads(store.read_text(encoding="utf-8"))
    assert payload["_note"] == "maintained by the office manager"
    edited = payload["contacts"][0]
    assert (edited["lastName"], edited["title"]) == ("King", "Principal")
    assert edited["address"]["attention"] == "Accounts"
