"""PROJECT.md shapes the dossier skill writes, and what Atlas does with them.

Two writers share PROJECT.md: `/project-dossier` (Claude) and Atlas (ADR 0001).
Atlas parses only the keys it owns; everything else is carried through.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from atlas.core.contacts import ContactDraft, ContactError, add_contact
from atlas.core.intake import IntakeError, ProjectAddress
from atlas.core.mapfile import load_map
from atlas.core.ops import new_project
from atlas.core.project_data import (
    ProjectDataError,
    apply_project_update,
    load_project_record,
    preview_project_update,
)

from conftest import make_intake


CREATED = date(2026, 8, 13)


def _project(fixture_drive, description=""):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    intake = make_intake(
        fixture_drive,
        "Oak House",
        description,
        street="100 Oak Street",
        created=CREATED,
    )
    result = new_project(fixture_drive, drive_map, intake)
    return drive_map, intake, result.path


def _replace_line(project, prefix: bytes, *new_lines: bytes) -> None:
    dossier = project / "PROJECT.md"
    lines = dossier.read_bytes().split(b"\r\n")
    matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    assert len(matches) == 1, prefix
    lines[matches[0] : matches[0] + 1] = list(new_lines)
    dossier.write_bytes(b"\r\n".join(lines))


def _edit(fixture_drive, drive_map, project, **changes):
    record = load_project_record(project)
    plan = preview_project_update(fixture_drive, project, replace(record.intake, **changes))
    result = apply_project_update(fixture_drive, drive_map, plan, allow_rename=True)
    return plan, result


# ---------------------------------------------------------------- #15 Norma keys


@pytest.mark.parametrize(
    "prefix, shape",
    [
        (b"occupancy_group:", [b'occupancy_group: [B, "S-1"]']),
        (b"occupancy_group:", [b"occupancy_group:", b"  - B", b'  - "S-1"']),
        (b"edition:", [b"edition: '2022 NYC BC'"]),
        (b"construction_type:", [b"construction_type: &type V-B"]),
        (b"sprinklered:", [b"sprinklered: {system: NFPA 13}"]),
    ],
)
def test_edit_carries_norma_keys_of_any_yaml_shape_through_untouched(
    fixture_drive, prefix, shape
):
    drive_map, _, project = _project(fixture_drive)
    _replace_line(project, prefix, *shape)

    _, result = _edit(fixture_drive, drive_map, project, project_name="Oak House Revised")

    raw = (result.path / "PROJECT.md").read_bytes()
    assert b"\r\n".join(shape) + b"\r\n" in raw
    assert b'project: "Oak House Revised"\r\n' in raw
    assert load_project_record(result.path).intake.project_name == "Oak House Revised"


def test_atlas_key_in_block_form_is_still_refused(fixture_drive):
    _, _, project = _project(fixture_drive)
    _replace_line(project, b"project:", b"project:", b"  - Oak House")

    with pytest.raises(ProjectDataError, match="unsupported YAML for 'project'"):
        load_project_record(project)


# ---------------------------------------------------------------- #32 comments


def test_template_inline_comments_on_blank_keys_read_as_empty(fixture_drive):
    drive_map, _, project = _project(fixture_drive)
    _replace_line(project, b"address_unit:", b"address_unit:                # optional")
    _replace_line(
        project, b"description:", b"description:                 # optional folder qualifier"
    )

    record = load_project_record(project)
    assert record.intake.project_address.unit == ""
    assert record.intake.description == ""

    plan, result = _edit(fixture_drive, drive_map, project, project_name="Oak House Revised")

    assert plan.rename_required is False
    raw = (result.path / "PROJECT.md").read_bytes()
    assert b"# optional," not in raw
    assert b"address_unit:                # optional\r\n" in raw
    assert b'address: "100 Oak Street, Oakland, CA 94612"\r\n' in raw


def test_rewritten_key_keeps_its_comment_in_its_column(fixture_drive):
    drive_map, intake, project = _project(fixture_drive)
    _replace_line(project, b"address_unit:", b"address_unit:                # optional")

    _, result = _edit(
        fixture_drive,
        drive_map,
        project,
        project_address=replace(intake.project_address, unit="Apt 4B"),
    )

    raw = (result.path / "PROJECT.md").read_bytes()
    assert b'address_unit: "Apt 4B"       # optional\r\n' in raw
    assert load_project_record(result.path).intake.project_address.unit == "Apt 4B"


@pytest.mark.parametrize(
    "line, expected",
    [
        (b'project: "Oak House"  # display name', "Oak House"),
        (b"project: 'Oak House'", "Oak House"),
        (b"project: 'Oak ''House'''  # quoted", "Oak 'House'"),
        (b'project: "Oak #1"', "Oak #1"),
        (b"project: Oak#1", "Oak#1"),
        (b"project: Oak House   # display name", "Oak House"),
    ],
)
def test_atlas_scalars_accept_yaml_quoting_and_comments(fixture_drive, line, expected):
    _, _, project = _project(fixture_drive)
    _replace_line(project, b"project:", line)

    assert load_project_record(project).intake.project_name == expected


def test_unchanged_atlas_key_keeps_its_own_quoting(fixture_drive):
    drive_map, _, project = _project(fixture_drive)
    _replace_line(project, b"project:", b"project: 'Oak House'  # display name")

    _, result = _edit(fixture_drive, drive_map, project, description="Kitchen")

    raw = (result.path / "PROJECT.md").read_bytes()
    assert b"project: 'Oak House'  # display name\r\n" in raw


def test_name_alias_is_read_and_rewritten_in_place(fixture_drive):
    drive_map, _, project = _project(fixture_drive)
    _replace_line(project, b"project:", b"name: Oak House")

    assert load_project_record(project).intake.project_name == "Oak House"

    _, result = _edit(fixture_drive, drive_map, project, project_name="Pine House")

    raw = (result.path / "PROJECT.md").read_bytes()
    assert b'name: "Pine House"\r\n' in raw
    assert b"project:" not in raw.split(b"\r\n---\r\n")[0]


# ---------------------------------------------------------------- #34 control characters

LINE_BREAKERS = ["\t", "\x7f", "\x85", "\u2028", "\u2029"]


@pytest.mark.parametrize("character", LINE_BREAKERS)
def test_intake_refuses_every_control_or_line_break_character(fixture_drive, character):
    intake = make_intake(fixture_drive, "Oak House", created=CREATED)

    with pytest.raises(IntakeError, match="control characters"):
        replace(intake, project_name=f"Oak{character}House")
    with pytest.raises(IntakeError, match="control characters"):
        replace(intake, description=f"Kitchen{character}Bath")


@pytest.mark.parametrize("character", LINE_BREAKERS)
@pytest.mark.parametrize("field", ["first_name", "last_name", "company", "phone"])
def test_contact_drafts_refuse_control_characters(fixture_drive, character, field):
    values = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "phone": "510 555 0100",
        "company": "Engines",
    }
    values[field] = values[field][:2] + character + values[field][2:]

    with pytest.raises(ContactError, match="control characters"):
        add_contact(fixture_drive, ContactDraft(**values))


@pytest.mark.parametrize("character", LINE_BREAKERS)
def test_snapshot_from_a_stored_contact_with_a_line_breaker_stays_editable(
    fixture_drive, character
):
    # A contact written into the shared store by another tool can carry such a
    # character. Assigning it to a project must not brick the dossier.
    drive_map, _, project = _project(fixture_drive)
    contact = add_contact(
        fixture_drive,
        ContactDraft(first_name="Bob", last_name="Builder", email="bob@example.com"),
    )
    store = fixture_drive / "_tools" / "billing-contacts.json"
    payload = json.loads(store.read_text(encoding="utf-8"))
    for item in payload["contacts"]:
        if item["id"] == contact.id:
            item["company"] = f"Builder{character}Co"
    store.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    _, result = _edit(
        fixture_drive,
        drive_map,
        project,
        billing_contact_id=contact.id,
        client_contact_id=contact.id,
    )

    raw = (result.path / "PROJECT.md").read_bytes()
    assert character.encode("utf-8") not in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")
    reloaded = load_project_record(result.path)
    assert reloaded.billing_contact.company == f"Builder{character}Co"

    _edit(fixture_drive, drive_map, result.path, project_name="Still Editable")


@pytest.mark.parametrize("character", LINE_BREAKERS)
def test_yaml_writer_escapes_line_breakers(character):
    from atlas.core.projectmd import yaml_quote

    quoted = yaml_quote(f"a{character}b")

    assert character not in quoted
    assert json.loads(quoted) == f"a{character}b"


# ---------------------------------------------------------------- #35 Identity rows

APN_ROW = (
    "| Address / BBL | 100 Oak Street, Oakland, CA 94612 · APN 000-0000-000 "
    "(county GIS, 2026-09-01) |"
).encode("utf-8")


def _identity_lines(path):
    text = (path / "PROJECT.md").read_bytes().decode("utf-8")
    section = text.split("## Identity", 1)[1].split("\r\n## ", 1)[0]
    return [line for line in section.split("\r\n") if line.startswith("|")]


def test_name_only_edit_leaves_other_identity_rows_and_provenance_alone(fixture_drive):
    drive_map, _, project = _project(fixture_drive)
    _replace_line(project, b"| Address / BBL |", APN_ROW)
    _replace_line(project, b"| Client |", b"| Client | Test Oak House (client, 2026-08-13) |")
    _replace_line(project, b"| Created |", b"| Created | 2026-08-13 (Atlas intake, 2026-08-13) |")
    before = _identity_lines(project)

    _, result = _edit(fixture_drive, drive_map, project, project_name="Oak House Revised")

    after = _identity_lines(result.path)
    changed = [(old, new) for old, new in zip(before, after) if old != new]
    assert changed == [("| Project | Oak House |", "| Project | Oak House Revised |")]


def test_changed_value_keeps_the_provenance_that_follows_it(fixture_drive):
    drive_map, intake, project = _project(fixture_drive)
    _replace_line(project, b"| Address / BBL |", APN_ROW)
    _replace_line(project, b"| Project |", b"| Project | Oak House (client, 2026-08-13) |")

    _, result = _edit(
        fixture_drive,
        drive_map,
        project,
        project_name="Pine House",
        project_address=replace(intake.project_address, unit="Apt 4B"),
    )

    lines = _identity_lines(result.path)
    assert "| Project | Pine House (client, 2026-08-13) |" in lines
    assert (
        "| Address / BBL | 100 Oak Street, Apt 4B, Oakland, CA 94612 · APN 000-0000-000 "
        "(county GIS, 2026-09-01) |"
    ) in lines


def test_created_row_with_provenance_loads(fixture_drive):
    _, _, project = _project(fixture_drive)
    _replace_line(project, b"| Created |", b"| Created | 2026-08-13 (Atlas intake, 2026-08-13) |")

    assert load_project_record(project).intake.created == CREATED


def test_address_corrected_outside_the_components_is_refused_not_reverted(fixture_drive):
    _, _, project = _project(fixture_drive)
    _replace_line(project, b"address:", b'address: "100 Oak Street, Oakland, CA 94607"')
    _replace_line(
        project, b"| Address / BBL |", b"| Address / BBL | 100 Oak Street, Oakland, CA 94607 |"
    )
    before = (project / "PROJECT.md").read_bytes()

    with pytest.raises(ProjectDataError, match="address disagrees.*94607.*Identity table wins"):
        load_project_record(project)

    assert (project / "PROJECT.md").read_bytes() == before


def test_client_row_a_person_wrote_survives_a_client_contact_change(fixture_drive):
    drive_map, _, project = _project(fixture_drive)
    _replace_line(project, b"| Client |", b"| Client | Acme Holdings LLC (client, 2026-08-13) |")
    bob = add_contact(
        fixture_drive,
        ContactDraft(first_name="Bob", last_name="Builder", email="bob@example.com"),
    )

    _, result = _edit(fixture_drive, drive_map, project, client_contact_id=bob.id)

    lines = _identity_lines(result.path)
    assert "| Client | Acme Holdings LLC (client, 2026-08-13) |" in lines
    assert "| Client Contact | Bob Builder |" in lines


def test_seeded_client_row_follows_a_client_contact_change(fixture_drive):
    drive_map, _, project = _project(fixture_drive)
    bob = add_contact(
        fixture_drive,
        ContactDraft(first_name="Bob", last_name="Builder", email="bob@example.com"),
    )

    _, result = _edit(fixture_drive, drive_map, project, client_contact_id=bob.id)

    assert "| Client | Bob Builder |" in _identity_lines(result.path)


def test_heading_the_dossier_skill_wrote_is_not_replaced_by_the_folder(fixture_drive):
    drive_map, intake, project = _project(fixture_drive)
    _replace_line(project, b"# 260813_", "# Project Dossier — Oak House".encode("utf-8"))

    plan, result = _edit(
        fixture_drive,
        drive_map,
        project,
        project_address=replace(intake.project_address, street="99 Pine Avenue"),
    )

    assert plan.rename_required
    raw = (result.path / "PROJECT.md").read_bytes()
    assert "\r\n# Project Dossier — Oak House\r\n".encode("utf-8") in raw


# ---------------------------------------------------------------- #36 shapes


@pytest.mark.parametrize(
    "reshape",
    [
        pytest.param(lambda raw: raw.replace(b"\r\n", b"\n"), id="LF"),
        pytest.param(lambda raw: raw[:-2], id="no-trailing-newline"),
        pytest.param(lambda raw: raw.replace(b"\r\n", b"\n")[:-1], id="LF-no-trailing-newline"),
        pytest.param(lambda raw: b"\xef\xbb\xbf" + raw, id="BOM"),
    ],
)
def test_line_endings_and_bom_read_the_same_and_write_back_crlf(fixture_drive, reshape):
    drive_map, _, project = _project(fixture_drive)
    dossier = project / "PROJECT.md"
    dossier.write_bytes(reshape(dossier.read_bytes()))

    assert load_project_record(project).intake.project_name == "Oak House"
    _, result = _edit(fixture_drive, drive_map, project, project_name="Pine House")

    raw = (result.path / "PROJECT.md").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert raw.endswith(b"\r\n")
    assert b"\n" not in raw.replace(b"\r\n", b"")
    assert load_project_record(result.path).intake.project_name == "Pine House"


def test_aligned_identity_table_reads_and_keeps_its_padding(fixture_drive):
    drive_map, _, project = _project(fixture_drive)
    _replace_line(project, b"| Created |", b"| Created          | 2026-08-13                  |")
    _replace_line(project, b"| Descriptor |", b"| Descriptor       |                             |")
    _replace_line(project, b"| Project |", b"| Project          | Oak House                   |")

    assert load_project_record(project).intake.created == CREATED
    _, result = _edit(fixture_drive, drive_map, project, description="Kitchen")

    lines = _identity_lines(result.path)
    assert "| Created          | 2026-08-13                  |" in lines
    assert "| Project          | Oak House                   |" in lines
    assert "| Descriptor | Kitchen |" in lines


def test_one_word_contact_name_is_editable(fixture_drive):
    drive_map, _, project = _project(fixture_drive)
    _replace_line(project, b"billing_contact_name:", b'billing_contact_name: "Cher"')

    record = load_project_record(project)
    assert record.billing_contact.full_name == "Cher"

    _edit(fixture_drive, drive_map, project, project_name="Pine House")


def test_missing_identity_rows_are_tolerated(fixture_drive):
    drive_map, _, project = _project(fixture_drive)
    for field in (b"| Created |", b"| Billing Phone |", b"| Descriptor |"):
        _replace_line(project, field)

    assert load_project_record(project).intake.created == CREATED
    _, result = _edit(fixture_drive, drive_map, project, description="Kitchen")

    lines = _identity_lines(result.path)
    assert "| Descriptor | Kitchen |" in lines
    assert not any(line.startswith("| Billing Phone |") for line in lines)


# ------------------------------------------------- parity with the dossier skill

SKILL = (
    Path(__file__).resolve().parents[3]
    / "plugins"
    / "09-project-dossier"
    / "skills"
    / "project-dossier"
    / "SKILL.md"
)


def _skill_template() -> list[str]:
    text = SKILL.read_text(encoding="utf-8")
    template = text.split("## Template", 1)[1].split("```markdown\n", 1)[1]
    return template.split("\n```", 1)[0].split("\n")


def _fill_key(lines: list[str], key: str, value: str) -> None:
    # Claude filling the template: the value goes after the key and the
    # template's own comment stays where it was.
    index = next(i for i, line in enumerate(lines) if line.startswith(f"{key}:"))
    line = lines[index]
    comment = line.find("#")
    head = f"{key}: {value}"
    if comment < 0:
        lines[index] = head
    else:
        lines[index] = head + " " * max(1, comment - len(head)) + line[comment:]


def _fill_row(lines: list[str], field: str, value: str) -> None:
    index = next(i for i, line in enumerate(lines) if line.startswith(f"| {field} |"))
    lines[index] = f"| {field} | {value} |"


def test_dossier_written_from_the_skill_template_round_trips_an_edit(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    ada = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    lines = _skill_template()
    for key, value in (
        ("project", "Oak House"),
        ("address", "100 Oak Street, Oakland, CA 02134"),
        ("address_street", "100 Oak Street"),
        ("address_city", "Oakland"),
        ("address_state", "CA"),
        ("address_postal_code", '"02134"'),
        ("project_use_case", "Renovation"),
        ("project_use_case_category", "Renovation"),
        ("jurisdiction", "california"),
        ("occupancy_group", '[B, "S-1"]'),
        ("edition", "'2025 CBC'"),
    ):
        _fill_key(lines, key, value)
    for role in ("billing", "client"):
        _fill_key(lines, f"{role}_contact_id", ada.id)
        _fill_key(lines, f"{role}_contact_name", "Ada Lovelace")
        _fill_key(lines, f"{role}_contact_email", "ada@example.com")
    for field, value in (
        ("Project", "Oak House (client, 2026-08-13)"),
        ("Address / BBL", "100 Oak Street, Oakland, CA 02134 · APN 000-0000-000 (county GIS, 2026-08-13)"),
        ("Project Use Case", "Renovation (client, 2026-08-13)"),
        ("Client", "Ada Lovelace (client, 2026-08-13)"),
        ("Created", "2026-08-13 (Atlas intake, 2026-08-13)"),
        ("Jurisdiction", "california (client, 2026-08-13)"),
    ):
        _fill_row(lines, field, value)
    project = fixture_drive / "260813_100 Oak Street"
    project.mkdir()
    source = "\n".join(lines).replace("{project name}", "Oak House") + "\n"
    (project / "PROJECT.md").write_bytes(source.encode("utf-8"))

    record = load_project_record(project)
    assert record.intake.project_address.postal_code == "02134"
    assert record.intake.project_address.unit == ""
    assert record.intake.description == ""

    plan, result = _edit(
        fixture_drive,
        drive_map,
        project,
        project_name="Oak House Annex",
        project_address=replace(record.intake.project_address, unit="Unit 2"),
    )

    assert plan.rename_required is False
    raw = (result.path / "PROJECT.md").read_bytes()
    text = raw.decode("utf-8")
    assert b"\n" not in raw.replace(b"\r\n", b"")
    assert 'occupancy_group: [B, "S-1"]' in text
    assert "edition: '2025 CBC'" in text
    assert "| Project | Oak House Annex (client, 2026-08-13) |" in text
    assert (
        "| Address / BBL | 100 Oak Street, Unit 2, Oakland, CA 02134 · APN 000-0000-000 "
        "(county GIS, 2026-08-13) |"
    ) in text
    assert "| Created | 2026-08-13 (Atlas intake, 2026-08-13) |" in text
    assert "# Project Dossier — Oak House\r\n" in text
    unchanged = [line for line in source.split("\n") if "occupancy_group" in line]
    assert unchanged[0] in text
    again = load_project_record(result.path)
    assert again.intake.project_name == "Oak House Annex"
    assert again.intake.project_address.unit == "Unit 2"
