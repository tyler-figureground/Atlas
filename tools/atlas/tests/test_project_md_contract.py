"""PROJECT.md shapes the dossier skill writes, and what Atlas does with them.

Two writers share PROJECT.md: `/project-dossier` (Claude) and Atlas (ADR 0001).
Atlas parses only the keys it owns; everything else is carried through.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from atlas.core.intake import ProjectAddress
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
