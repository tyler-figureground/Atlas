from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from atlas.cli import main


def _add_contact(fixture_drive: Path, capsys, **overrides):
    values = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        **overrides,
    }
    arguments = [
        "contacts",
        "add",
        "--drive",
        str(fixture_drive),
        "--first-name",
        values["first_name"],
        "--last-name",
        values["last_name"],
        "--email",
        values["email"],
        "--json",
    ]
    for key, flag in (("phone", "--phone"), ("company", "--company")):
        if key in values:
            arguments.extend((flag, values[key]))
    assert main(arguments) == 0
    return json.loads(capsys.readouterr().out)


def _new_project(fixture_drive: Path, capsys, billing_contact: str):
    assert main(
        [
            "new",
            "--drive",
            str(fixture_drive),
            "--name",
            "Oak House",
            "--street",
            "1842 Oak Street",
            "--unit",
            "Unit 4",
            "--city",
            "Oakland",
            "--state",
            "CA",
            "--zip",
            "94612",
            "--use-case",
            "Renovation",
            "--billing-contact",
            billing_contact,
            "--desc",
            "Kitchen",
            "--json",
        ]
    ) == 0
    return json.loads(capsys.readouterr().out)


def test_contacts_edit_flags_preserve_identity_and_accept_po_box(fixture_drive, capsys):
    original = _add_contact(
        fixture_drive,
        capsys,
        phone="510-555-0100",
        company="Analytical Engines",
    )

    status = main(
        [
            "contacts",
            "edit",
            original["id"],
            "--drive",
            str(fixture_drive),
            "--first-name",
            "Augusta Ada",
            "--address-street",
            "P.O. Box 42",
            "--address-city",
            "Oakland",
            "--address-state",
            "ca",
            "--address-zip",
            "94607",
            "--yes",
            "--json",
        ]
    )

    assert status == 0
    output = json.loads(capsys.readouterr().out)
    assert output["id"] == original["id"]
    assert output["first_name"] == "Augusta Ada"
    assert output["last_name"] == "Lovelace"
    assert output["phone"] == "510-555-0100"
    assert output["company"] == "Analytical Engines"
    assert output["address"] == {
        "street": "P.O. Box 42",
        "unit": "",
        "city": "Oakland",
        "state": "CA",
        "postal_code": "94607",
        "country": "US",
    }


def test_contacts_edit_flags_cover_every_editable_contact_field(fixture_drive, capsys):
    original = _add_contact(fixture_drive, capsys)

    assert main(
        [
            "contacts",
            "edit",
            original["email"],
            "--drive",
            str(fixture_drive),
            "--first-name",
            "Augusta Ada",
            "--last-name",
            "King",
            "--email",
            "countess@example.com",
            "--phone",
            "+1 510 555 0199",
            "--company",
            "Difference Engine Works",
            "--address-street",
            "123 Broadway",
            "--address-unit",
            "Suite 4",
            "--address-city",
            "Oakland",
            "--address-state",
            "CA",
            "--address-zip",
            "94607",
            "--yes",
            "--json",
        ]
    ) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["id"] == original["id"]
    assert output["first_name"] == "Augusta Ada"
    assert output["last_name"] == "King"
    assert output["email"] == "countess@example.com"
    assert output["phone"] == "+1 510 555 0199"
    assert output["company"] == "Difference Engine Works"
    assert output["address"]["unit"] == "Suite 4"


def test_contacts_edit_interactive_prompts_retain_current_values(
    fixture_drive, capsys, monkeypatch
):
    original = _add_contact(
        fixture_drive,
        capsys,
        phone="510-555-0100",
        company="Analytical Engines",
    )
    answers = iter(("", "", "ADA.NEW@example.com", "", "", "", "", "", "", ""))
    prompts = []

    def answer(prompt):
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr("builtins.input", answer)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    status = main(
        [
            "contacts",
            "edit",
            "ADA@example.com",
            "--drive",
            str(fixture_drive),
        ]
    )

    assert status == 0
    assert len(prompts) == 10
    assert all("Enter keeps current" in prompt for prompt in prompts)
    assert "updated: Ada Lovelace <ada.new@example.com>" in capsys.readouterr().out
    assert main(["contacts", "list", "--drive", str(fixture_drive), "--json"]) == 0
    updated = json.loads(capsys.readouterr().out)[0]
    assert updated["id"] == original["id"]
    assert updated["phone"] == "510-555-0100"
    assert updated["company"] == "Analytical Engines"


def test_project_edit_flags_update_all_fields_and_rename_folder(fixture_drive, capsys):
    billing = _add_contact(fixture_drive, capsys)
    client = _add_contact(
        fixture_drive,
        capsys,
        first_name="Grace",
        last_name="Hopper",
        email="grace@example.com",
    )
    created = _new_project(fixture_drive, capsys, billing["id"])

    status = main(
        [
            "project",
            "edit",
            created["created"],
            "--drive",
            str(fixture_drive),
            "--name",
            "Oak Studio",
            "--street",
            "200 Pine Street",
            "--unit",
            "",
            "--city",
            "Berkeley",
            "--state",
            "ca",
            "--zip",
            "94704",
            "--use-case",
            "Other",
            "--other-use-case",
            "Adaptive Reuse",
            "--billing-contact",
            client["email"],
            "--client-contact",
            billing["id"],
            "--desc",
            "Studio",
            "--rename",
            "--yes",
            "--json",
        ]
    )

    assert status == 0
    output = json.loads(capsys.readouterr().out)
    assert output["old_folder"] == created["created"]
    assert output["folder"].endswith("_200 Pine Street-Studio")
    assert output["renamed"] is True
    assert output["project_name"] == "Oak Studio"
    assert output["address"] == "200 Pine Street, Berkeley, CA 94704"
    assert output["description"] == "Studio"
    assert output["use_case"] == "Adaptive Reuse"
    assert output["use_case_category"] == "Other"
    assert output["billing_contact_id"] == client["id"]
    assert output["client_contact_id"] == billing["id"]
    assert not (fixture_drive / created["created"]).exists()
    assert Path(output["path"]).is_dir()


def test_project_edit_noninteractive_rename_requires_separate_gate(
    fixture_drive, capsys
):
    contact = _add_contact(fixture_drive, capsys)
    created = _new_project(fixture_drive, capsys, contact["id"])
    original = fixture_drive / created["created"]
    dossier_before = (original / "PROJECT.md").read_bytes()

    status = main(
        [
            "project",
            "edit",
            created["created"],
            "--drive",
            str(fixture_drive),
            "--street",
            "200 Pine Street",
            "--yes",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    expected = created["created"].replace("1842 Oak Street", "200 Pine Street")
    assert status == 2
    assert captured.out == ""
    assert f"{created['created']} -> {expected}" in captured.err
    assert "--rename" in captured.err
    assert "--yes" in captured.err
    assert "no changes made" in captured.err
    assert original.is_dir()
    assert (original / "PROJECT.md").read_bytes() == dossier_before
    assert not (fixture_drive / expected).exists()


def test_project_edit_rename_without_yes_never_mutates(fixture_drive, capsys):
    contact = _add_contact(fixture_drive, capsys)
    created = _new_project(fixture_drive, capsys, contact["id"])
    original = fixture_drive / created["created"]
    dossier_before = (original / "PROJECT.md").read_bytes()

    status = main(
        [
            "project",
            "edit",
            created["created"],
            "--drive",
            str(fixture_drive),
            "--street",
            "200 Pine Street",
            "--rename",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    expected = created["created"].replace("1842 Oak Street", "200 Pine Street")
    assert status == 2
    assert captured.out == ""
    assert "requires --yes" in captured.err
    assert "no changes made" in captured.err
    assert original.is_dir()
    assert (original / "PROJECT.md").read_bytes() == dossier_before
    assert not (fixture_drive / expected).exists()


def test_project_edit_dry_run_json_previews_without_confirmation_or_mutation(
    fixture_drive, capsys
):
    contact = _add_contact(fixture_drive, capsys)
    created = _new_project(fixture_drive, capsys, contact["id"])
    original = fixture_drive / created["created"]
    dossier_before = (original / "PROJECT.md").read_bytes()

    status = main(
        [
            "project",
            "edit",
            created["created"],
            "--drive",
            str(fixture_drive),
            "--street",
            "200 Pine Street",
            "--dry-run",
            "--json",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    expected = created["created"].replace("1842 Oak Street", "200 Pine Street")
    assert status == 0
    assert output["applied"] is False
    assert output["rename_required"] is True
    assert output["folder"] == created["created"]
    assert output["planned_folder"] == expected
    assert output["address"] == "200 Pine Street, Unit 4, Oakland, CA 94612"
    assert original.is_dir()
    assert (original / "PROJECT.md").read_bytes() == dossier_before
    assert not (fixture_drive / expected).exists()


def test_project_edit_interactive_retains_values_and_confirms_rename(
    fixture_drive, capsys, monkeypatch
):
    contact = _add_contact(fixture_drive, capsys)
    created = _new_project(fixture_drive, capsys, contact["id"])
    answers = iter(
        (
            "",
            "200 Pine Street",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "yes",
        )
    )
    prompts = []

    def answer(prompt):
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr("builtins.input", answer)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    status = main(
        [
            "project",
            "edit",
            created["created"],
            "--drive",
            str(fixture_drive),
        ]
    )

    assert status == 0
    assert len(prompts) == 11
    assert all("Enter keeps current" in prompt for prompt in prompts[:10])
    assert "Type yes to rename and save" in prompts[-1]
    output = capsys.readouterr().out
    expected = created["created"].replace("1842 Oak Street", "200 Pine Street")
    assert f"folder rename: {created['created']} -> {expected}" in output
    assert f"updated: {expected}" in output
    assert not (fixture_drive / created["created"]).exists()
    assert (fixture_drive / expected).is_dir()


def test_project_edit_interactive_use_case_lists_choices_and_retries_in_place(
    fixture_drive, capsys, monkeypatch
):
    contact = _add_contact(fixture_drive, capsys)
    created = _new_project(fixture_drive, capsys, contact["id"])
    answers = iter(
        (
            "Oak Studio",
            "",
            "",
            "",
            "",
            "",
            "Not a use case",
            "Addition",
            "",
            "",
            "",
        )
    )
    prompts = []

    def answer(prompt):
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr("builtins.input", answer)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    status = main(
        [
            "project",
            "edit",
            created["created"],
            "--drive",
            str(fixture_drive),
        ]
    )

    captured = capsys.readouterr()
    use_case_prompts = [prompt for prompt in prompts if "Project use case" in prompt]
    assert status == 0
    assert len(use_case_prompts) == 2
    assert all("Renovation" in prompt and "Other" in prompt for prompt in use_case_prompts)
    assert "Invalid choice" in captured.out
    dossier = (fixture_drive / created["created"] / "PROJECT.md").read_text(
        encoding="utf-8"
    )
    assert 'project: "Oak Studio"' in dossier
    assert 'project_use_case: "Addition"' in dossier


@pytest.mark.parametrize("old_email_reused", [False, True], ids=["email-changed", "email-reused"])
def test_project_edit_interactive_keeps_contacts_by_id_not_snapshot_email(
    fixture_drive, capsys, monkeypatch, old_email_reused
):
    # ADR 0003: stable IDs exist so a changed email does not break the link.
    from atlas.core.contacts import ContactDraft, update_contact
    from atlas.core.project_data import load_project_record

    ada = _add_contact(fixture_drive, capsys)
    created = _new_project(fixture_drive, capsys, ada["id"])
    update_contact(
        fixture_drive,
        ada["id"],
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@new.example.com"),
    )
    if old_email_reused:
        _add_contact(fixture_drive, capsys, first_name="Bob", last_name="Builder")
    prompts = []

    def answer(prompt):
        prompts.append(prompt)
        return ""

    monkeypatch.setattr("builtins.input", answer)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    status = main(["project", "edit", created["created"], "--drive", str(fixture_drive)])

    assert status == 0
    contact_prompts = [prompt for prompt in prompts if "Contact" in prompt]
    assert len(contact_prompts) == 2
    assert all(ada["id"] in prompt and "Ada Lovelace" in prompt for prompt in contact_prompts)
    record = load_project_record(fixture_drive / created["created"])
    assert record.intake.billing_contact_id == ada["id"]
    assert record.intake.client_contact_id == ada["id"]
    assert record.billing_contact.full_name == "Ada Lovelace"
    assert record.client_contact.full_name == "Ada Lovelace"


def test_project_edit_interactive_refuses_a_dossier_changed_while_prompting(
    fixture_drive, capsys, monkeypatch
):
    ada = _add_contact(fixture_drive, capsys)
    created = _new_project(fixture_drive, capsys, ada["id"])
    dossier = fixture_drive / created["created"] / "PROJECT.md"
    concurrent = []

    def answer(prompt):
        if prompt.startswith("Description") and not concurrent:
            # Claude fixes the name while the operator is at the prompts.
            dossier.write_bytes(
                dossier.read_bytes().replace(
                    b'project: "Oak House"', b'project: "Oak Street Residence"'
                )
            )
            concurrent.append(dossier.read_bytes())
        return ""

    monkeypatch.setattr("builtins.input", answer)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    status = main(["project", "edit", created["created"], "--drive", str(fixture_drive)])

    assert status == 2
    assert "changed since you opened it" in capsys.readouterr().err
    assert dossier.read_bytes() == concurrent[0]


def test_contacts_edit_flags_without_yes_never_prompt_or_write(
    fixture_drive, capsys, monkeypatch
):
    original = _add_contact(fixture_drive, capsys)
    store = fixture_drive / "_tools" / "billing-contacts.json"
    before = store.read_bytes()

    def unexpected_prompt(_prompt):
        raise AssertionError("script mode prompted")

    monkeypatch.setattr("builtins.input", unexpected_prompt)

    status = main(
        [
            "contacts",
            "edit",
            original["id"],
            "--drive",
            str(fixture_drive),
            "--email",
            "new@example.com",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert status == 2
    assert captured.out == ""
    assert "requires --yes" in captured.err
    assert "no changes made" in captured.err
    assert store.read_bytes() == before


def test_project_edit_interactive_rejects_shorthand_rename_confirmation(
    fixture_drive, capsys, monkeypatch
):
    contact = _add_contact(fixture_drive, capsys)
    created = _new_project(fixture_drive, capsys, contact["id"])
    answers = iter(("", "200 Pine Street", "", "", "", "", "", "", "", "", "y"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    status = main(
        [
            "project",
            "edit",
            created["created"],
            "--drive",
            str(fixture_drive),
        ]
    )

    captured = capsys.readouterr()
    expected = created["created"].replace("1842 Oak Street", "200 Pine Street")
    assert status == 1
    assert "not confirmed" in captured.out
    assert captured.err == ""
    assert (fixture_drive / created["created"]).is_dir()
    assert not (fixture_drive / expected).exists()


def test_contacts_edit_from_non_tty_without_flags_never_prompts(
    fixture_drive, capsys, monkeypatch
):
    original = _add_contact(fixture_drive, capsys)
    store = fixture_drive / "_tools" / "billing-contacts.json"
    before = store.read_bytes()
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    def unexpected_prompt(_prompt):
        raise AssertionError("non-TTY mode prompted")

    monkeypatch.setattr("builtins.input", unexpected_prompt)

    status = main(
        [
            "contacts",
            "edit",
            original["id"],
            "--drive",
            str(fixture_drive),
        ]
    )

    captured = capsys.readouterr()
    assert status == 2
    assert captured.out == ""
    assert "non-interactive" in captured.err
    assert "--yes" in captured.err
    assert store.read_bytes() == before


def test_project_edit_json_reports_rename_collision_without_partial_output(
    fixture_drive, capsys, monkeypatch
):
    contact = _add_contact(fixture_drive, capsys)
    created = _new_project(fixture_drive, capsys, contact["id"])
    destination_name = created["created"].replace("1842 Oak Street", "200 Pine Street")
    (fixture_drive / destination_name).mkdir()

    def unexpected_prompt(_prompt):
        raise AssertionError("JSON mode prompted")

    monkeypatch.setattr("builtins.input", unexpected_prompt)

    status = main(
        [
            "project",
            "edit",
            created["created"],
            "--drive",
            str(fixture_drive),
            "--street",
            "200 Pine Street",
            "--rename",
            "--yes",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert status == 2
    assert captured.out == ""
    assert "rename destination already exists" in captured.err
    assert (fixture_drive / created["created"]).is_dir()


def test_contacts_add_json_returns_structured_contact(fixture_drive, capsys):
    status = main(
        [
            "contacts",
            "add",
            "--drive",
            str(fixture_drive),
            "--first-name",
            "Ada",
            "--last-name",
            "Lovelace",
            "--email",
            "ADA@example.com",
            "--phone",
            "+1 (510) 555-0100",
            "--company",
            "Analytical Engines",
            "--address-street",
            "123 Broadway",
            "--address-unit",
            "Suite 4",
            "--address-city",
            "Oakland",
            "--address-state",
            "ca",
            "--address-zip",
            "94607",
            "--json",
        ]
    )

    assert status == 0
    output = json.loads(capsys.readouterr().out)
    assert output["first_name"] == "Ada"
    assert output["email"] == "ada@example.com"
    assert output["address"] == {
        "street": "123 Broadway",
        "unit": "Suite 4",
        "city": "Oakland",
        "state": "CA",
        "postal_code": "94607",
        "country": "US",
    }


def test_contacts_list_json_returns_sorted_contacts(fixture_drive, capsys):
    for first_name, last_name, email in (
        ("Ada", "Lovelace", "ada@example.com"),
        ("Grace", "Hopper", "grace@example.com"),
    ):
        assert main(
            [
                "contacts",
                "add",
                "--drive",
                str(fixture_drive),
                "--first-name",
                first_name,
                "--last-name",
                last_name,
                "--email",
                email,
                "--json",
            ]
        ) == 0
        capsys.readouterr()

    assert main(["contacts", "list", "--drive", str(fixture_drive), "--json"]) == 0

    output = json.loads(capsys.readouterr().out)
    assert [contact["email"] for contact in output] == [
        "grace@example.com",
        "ada@example.com",
    ]


def test_new_json_creates_complete_intake_and_defaults_client_to_billing(
    fixture_drive, capsys
):
    assert main(
        [
            "contacts",
            "add",
            "--drive",
            str(fixture_drive),
            "--first-name",
            "Ada",
            "--last-name",
            "Lovelace",
            "--email",
            "ada@example.com",
            "--json",
        ]
    ) == 0
    contact = json.loads(capsys.readouterr().out)

    status = main(
        [
            "new",
            "--drive",
            str(fixture_drive),
            "--name",
            "Oak House",
            "--street",
            "1842 Oak Street",
            "--unit",
            "Unit 4",
            "--city",
            "Oakland",
            "--state",
            "ca",
            "--zip",
            "94612",
            "--use-case",
            "Renovation",
            "--billing-contact",
            "ADA@example.com",
            "--desc",
            "Kitchen",
            "--json",
        ]
    )

    assert status == 0
    output = json.loads(capsys.readouterr().out)
    assert set(("created", "path", "seeded")) <= output.keys()
    assert output["created"].endswith("_1842 Oak Street-Kitchen")
    assert Path(output["path"]).is_dir()
    assert output["project_name"] == "Oak House"
    assert output["address"] == "1842 Oak Street, Unit 4, Oakland, CA 94612"
    assert output["billing_contact_id"] == contact["id"]
    assert output["client_contact_id"] == contact["id"]


def test_contacts_add_and_list_human_output(fixture_drive, capsys):
    status = main(
        [
            "contacts",
            "add",
            "--drive",
            str(fixture_drive),
            "--first-name",
            "Grace",
            "--last-name",
            "Hopper",
            "--email",
            "grace@example.com",
        ]
    )

    assert status == 0
    added = capsys.readouterr()
    assert "added: Grace Hopper <grace@example.com>" in added.out
    assert added.err == ""

    assert main(["contacts", "list", "--drive", str(fixture_drive)]) == 0
    listed = capsys.readouterr()
    assert "Grace Hopper <grace@example.com>" in listed.out
    assert listed.err == ""


def test_contacts_list_human_output_includes_optional_details(fixture_drive, capsys):
    assert main(
        [
            "contacts",
            "add",
            "--drive",
            str(fixture_drive),
            "--first-name",
            "Ada",
            "--last-name",
            "Lovelace",
            "--email",
            "ada@example.com",
            "--phone",
            "510-555-0100",
            "--company",
            "Analytical Engines",
            "--address-street",
            "123 Broadway",
            "--address-city",
            "Oakland",
            "--address-state",
            "CA",
            "--address-zip",
            "94607",
        ]
    ) == 0
    capsys.readouterr()

    assert main(["contacts", "list", "--drive", str(fixture_drive)]) == 0

    output = capsys.readouterr().out
    assert "company: Analytical Engines" in output
    assert "phone: 510-555-0100" in output
    assert "address: 123 Broadway, Oakland, CA 94607" in output


@pytest.mark.parametrize(
    "required_flag",
    (
        "--name",
        "--street",
        "--city",
        "--state",
        "--zip",
        "--use-case",
        "--billing-contact",
    ),
)
def test_new_requires_every_complete_intake_flag(fixture_drive, capsys, required_flag):
    arguments = [
        "new",
        "--drive",
        str(fixture_drive),
        "--name",
        "Oak House",
        "--street",
        "1842 Oak Street",
        "--city",
        "Oakland",
        "--state",
        "CA",
        "--zip",
        "94612",
        "--use-case",
        "Renovation",
        "--billing-contact",
        "ada@example.com",
    ]
    position = arguments.index(required_flag)
    del arguments[position : position + 2]

    with pytest.raises(SystemExit) as caught:
        main(arguments)

    assert caught.value.code == 2
    assert required_flag in capsys.readouterr().err


def test_new_resolves_distinct_client_by_id_and_custom_other_use_case(
    fixture_drive, capsys
):
    contacts = []
    for first_name, last_name, email in (
        ("Ada", "Lovelace", "ada@example.com"),
        ("Grace", "Hopper", "grace@example.com"),
    ):
        assert main(
            [
                "contacts",
                "add",
                "--drive",
                str(fixture_drive),
                "--first-name",
                first_name,
                "--last-name",
                last_name,
                "--email",
                email,
                "--json",
            ]
        ) == 0
        contacts.append(json.loads(capsys.readouterr().out))

    assert main(
        [
            "new",
            "--drive",
            str(fixture_drive),
            "--name",
            "Reuse Study",
            "--street",
            "10 Market Street",
            "--city",
            "Oakland",
            "--state",
            "CA",
            "--zip",
            "94607",
            "--use-case",
            "Other",
            "--other-use-case",
            "Adaptive Reuse",
            "--billing-contact",
            "ada@example.com",
            "--client-contact",
            contacts[1]["id"],
            "--json",
        ]
    ) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["use_case"] == "Adaptive Reuse"
    assert output["use_case_category"] == "Other"
    assert output["billing_contact_id"] == contacts[0]["id"]
    assert output["client_contact_id"] == contacts[1]["id"]


def test_new_human_output_reports_complete_intake(fixture_drive, capsys):
    assert main(
        [
            "contacts",
            "add",
            "--drive",
            str(fixture_drive),
            "--first-name",
            "Ada",
            "--last-name",
            "Lovelace",
            "--email",
            "ada@example.com",
        ]
    ) == 0
    capsys.readouterr()

    assert main(
        [
            "new",
            "--drive",
            str(fixture_drive),
            "--name",
            "Oak House",
            "--street",
            "1842 Oak Street",
            "--city",
            "Oakland",
            "--state",
            "CA",
            "--zip",
            "94612",
            "--use-case",
            "Renovation",
            "--billing-contact",
            "ada@example.com",
        ]
    ) == 0

    output = capsys.readouterr().out
    assert "project: Oak House" in output
    assert "address: 1842 Oak Street, Oakland, CA 94612" in output
    assert "use case: Renovation" in output
    assert "billing: Ada Lovelace" in output
    assert "client:  Ada Lovelace" in output
    assert "run /project-dossier" not in output


def test_contact_error_returns_2(fixture_drive, capsys):
    status = main(
        [
            "contacts",
            "add",
            "--drive",
            str(fixture_drive),
            "--first-name",
            "Ada",
            "--last-name",
            "Lovelace",
            "--email",
            "invalid",
        ]
    )

    captured = capsys.readouterr()
    assert status == 2
    assert "error:" in captured.err
    assert captured.out == ""


def test_intake_error_returns_2(fixture_drive, capsys):
    assert main(
        [
            "contacts",
            "add",
            "--drive",
            str(fixture_drive),
            "--first-name",
            "Ada",
            "--last-name",
            "Lovelace",
            "--email",
            "ada@example.com",
        ]
    ) == 0
    capsys.readouterr()

    status = main(
        [
            "new",
            "--drive",
            str(fixture_drive),
            "--name",
            "Oak House",
            "--street",
            "Oak Street",
            "--city",
            "Oakland",
            "--state",
            "CA",
            "--zip",
            "94612",
            "--use-case",
            "Renovation",
            "--billing-contact",
            "ada@example.com",
        ]
    )

    captured = capsys.readouterr()
    assert status == 2
    assert "street number" in captured.err
    assert captured.out == ""


def test_ops_error_returns_2(fixture_drive, capsys):
    status = main(
        [
            "new",
            "--drive",
            str(fixture_drive),
            "--name",
            "Oak House",
            "--street",
            "1842 Oak Street",
            "--city",
            "Oakland",
            "--state",
            "CA",
            "--zip",
            "94612",
            "--use-case",
            "Renovation",
            "--billing-contact",
            "missing@example.com",
        ]
    )

    captured = capsys.readouterr()
    assert status == 2
    assert "Billing Contact not found" in captured.err
    assert captured.out == ""


def test_other_without_custom_label_returns_2(fixture_drive, capsys):
    assert main(
        [
            "contacts",
            "add",
            "--drive",
            str(fixture_drive),
            "--first-name",
            "Ada",
            "--last-name",
            "Lovelace",
            "--email",
            "ada@example.com",
        ]
    ) == 0
    capsys.readouterr()

    status = main(
        [
            "new",
            "--drive",
            str(fixture_drive),
            "--name",
            "Reuse Study",
            "--street",
            "10 Market Street",
            "--city",
            "Oakland",
            "--state",
            "CA",
            "--zip",
            "94607",
            "--use-case",
            "Other",
            "--billing-contact",
            "ada@example.com",
        ]
    )

    captured = capsys.readouterr()
    assert status == 2
    assert "custom Project Use Case" in captured.err
    assert captured.out == ""
