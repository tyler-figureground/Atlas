from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import date
from pathlib import Path, PureWindowsPath

import pytest

from atlas.cli import main
from atlas.core.contacts import ContactDraft, add_contact
from atlas.core.intake import ProjectAddress, ProjectUseCase
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


def _new_project(fixture_drive, name="Oak House", description="Kitchen"):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    intake = make_intake(
        fixture_drive,
        name,
        description,
        street="1842 Oak Street",
        use_case="Renovation + Addition",
        created=CREATED,
    )
    result = new_project(fixture_drive, drive_map, intake)
    return drive_map, intake, result.path


def test_load_project_record_reads_atlas_02_intake(fixture_drive):
    _, intake, project = _new_project(fixture_drive)

    record = load_project_record(project)

    assert record.path == project
    assert record.intake == intake
    assert record.billing_contact.id == intake.billing_contact_id
    assert record.client_contact.id == intake.client_contact_id
    assert len(record.source_digest) == 64


def test_load_project_record_recovers_address_components_from_full_address(fixture_drive):
    _, _, project = _new_project(fixture_drive)
    dossier = project / "PROJECT.md"
    source = dossier.read_bytes()
    for key in (
        b"address_street:",
        b"address_unit:",
        b"address_city:",
        b"address_state:",
        b"address_postal_code:",
    ):
        source = b"\r\n".join(
            line for line in source.split(b"\r\n") if not line.startswith(key)
        )
    source = source.replace(
        b'address: "1842 Oak Street, Oakland, CA 94612"',
        b'address: "1842 Oak Street, Suite 2, Oakland, CA 94612"',
    )
    dossier.write_bytes(source)

    address = load_project_record(project).intake.project_address

    assert (address.street, address.unit, address.city) == (
        "1842 Oak Street",
        "Suite 2",
        "Oakland",
    )
    assert (address.state, address.postal_code) == ("CA", "94612")


def test_preview_reports_rename_and_keeps_original_creation_date(fixture_drive):
    _, intake, project = _new_project(fixture_drive)
    edited = replace(
        intake,
        project_name="Oak House Revised",
        project_address=replace(intake.project_address, street="99 Pine Avenue"),
        description="Rear Addition",
        created=date(2030, 1, 1),
    )

    plan = preview_project_update(fixture_drive, project, edited)

    assert plan.old_path == project
    assert plan.new_path == fixture_drive / "260813_99 Pine Avenue-Rear Addition"
    assert plan.rename_required is True
    assert plan.intake.created == CREATED
    assert plan.billing_contact.id == intake.billing_contact_id
    assert plan.client_contact.id == intake.client_contact_id
    assert project.is_dir()
    assert not plan.new_path.exists()


def test_preview_preserves_legacy_index_and_captures_original_digest(fixture_drive):
    _, intake, project = _new_project(fixture_drive)
    index = fixture_drive / "_Project Index.md"
    legacy = (
        "# TESTDRIVE - Project Index\r\n\r\n"
        "| Project folder | Created | Descriptor | Status |\r\n"
        "|---|---|---|---|\r\n"
        f"| {project.name} | 2026-08-13 | Kitchen | Active |\r\n"
    ).encode("utf-8")
    index.write_bytes(legacy)

    plan = preview_project_update(
        fixture_drive,
        project,
        replace(intake, project_name="Oak House Revised"),
    )

    assert index.read_bytes() == legacy
    assert plan.index_digest == hashlib.sha256(legacy).hexdigest()
    backups = list(
        (fixture_drive / "_tools" / "logs").glob("Project-Index-pre-migration-*.md")
    )
    assert backups == []


def test_cli_project_edit_dry_run_preserves_legacy_index(fixture_drive, capsys):
    _, _, project = _new_project(fixture_drive)
    index = fixture_drive / "_Project Index.md"
    legacy = (
        "# TESTDRIVE - Project Index\r\n\r\n"
        "| Project folder | Created | Descriptor | Status |\r\n"
        "|---|---|---|---|\r\n"
        f"| {project.name} | 2026-08-13 | Kitchen | Active |\r\n"
    ).encode("utf-8")
    index.write_bytes(legacy)

    status = main(
        [
            "project",
            "edit",
            project.name,
            "--drive",
            str(fixture_drive),
            "--name",
            "Oak House Revised",
            "--dry-run",
        ]
    )

    assert status == 0
    assert "dry run: no changes made" in capsys.readouterr().out
    assert index.read_bytes() == legacy
    assert list(
        (fixture_drive / "_tools" / "logs").glob("Project-Index-pre-migration-*.md")
    ) == []


def test_apply_migrates_legacy_index_before_updating_project(fixture_drive):
    drive_map, intake, project = _new_project(fixture_drive)
    index = fixture_drive / "_Project Index.md"
    legacy = (
        "# TESTDRIVE - Project Index\r\n\r\n"
        "| Project folder | Created | Descriptor | Status |\r\n"
        "|---|---|---|---|\r\n"
        f"| {project.name} | 2026-08-13 | Kitchen | Active |\r\n"
    ).encode("utf-8")
    index.write_bytes(legacy)
    edited = replace(intake, project_name="Oak House Revised")
    plan = preview_project_update(fixture_drive, project, edited)

    result = apply_project_update(fixture_drive, drive_map, plan)

    assert result.record.intake.project_name == "Oak House Revised"
    migrated = index.read_bytes()
    assert b"| Project folder | Project name | Full project address |" in migrated
    assert b"| Oak House Revised |" in migrated
    backups = list(
        (fixture_drive / "_tools" / "logs").glob("Project-Index-pre-migration-*.md")
    )
    assert len(backups) == 1
    assert backups[0].read_bytes() == legacy


def test_preview_and_apply_support_missing_project_index(fixture_drive):
    drive_map, intake, project = _new_project(fixture_drive)
    index = fixture_drive / "_Project Index.md"
    index.unlink()
    plan = preview_project_update(
        fixture_drive,
        project,
        replace(intake, project_name="Oak House Revised"),
    )

    assert plan.index_digest is None
    assert not index.exists()

    result = apply_project_update(fixture_drive, drive_map, plan)

    assert result.record.intake.project_name == "Oak House Revised"
    assert index.read_bytes().count(f"| {project.name} |".encode()) == 1


def test_apply_migration_failure_leaves_project_untouched(fixture_drive):
    drive_map, intake, project = _new_project(fixture_drive)
    index = fixture_drive / "_Project Index.md"
    malformed_legacy = (
        "# TESTDRIVE - Project Index\r\n\r\n"
        "| Project folder | Created | Descriptor | Status |\r\n"
        "|---|---|---|\r\n"
        f"| {project.name} | 2026-08-13 | Kitchen | Active |\r\n"
    ).encode("utf-8")
    index.write_bytes(malformed_legacy)
    dossier_before = (project / "PROJECT.md").read_bytes()
    plan = preview_project_update(
        fixture_drive,
        project,
        replace(
            intake,
            project_address=replace(intake.project_address, street="99 Pine Avenue"),
        ),
    )

    with pytest.raises(ProjectDataError, match="cannot prepare project index"):
        apply_project_update(fixture_drive, drive_map, plan, allow_rename=True)

    assert project.is_dir()
    assert not plan.new_path.exists()
    assert (project / "PROJECT.md").read_bytes() == dossier_before
    assert index.read_bytes() == malformed_legacy


def test_update_plan_treats_windows_case_only_spelling_as_rename(fixture_drive):
    _, intake, project = _new_project(fixture_drive)
    plan = preview_project_update(fixture_drive, project, intake)
    old_path = PureWindowsPath(r"Q:\Projects\260813_1842 Oak Street-Kitchen")
    new_path = PureWindowsPath(r"Q:\Projects\260813_1842 OAK STREET-KITCHEN")
    windows_plan = replace(plan, old_path=old_path, new_path=new_path)

    assert old_path == new_path  # PureWindowsPath reproduces Windows Path equality everywhere.
    assert windows_plan.rename_required is True


def test_apply_case_only_rename_updates_real_folder_dossier_and_index(fixture_drive):
    drive_map, intake, project = _new_project(fixture_drive)
    edited = replace(
        intake,
        project_address=replace(intake.project_address, street="1842 OAK STREET"),
        description="KITCHEN",
    )
    plan = preview_project_update(fixture_drive, project, edited)

    result = apply_project_update(fixture_drive, drive_map, plan, allow_rename=True)

    matching_names = [
        child.name
        for child in fixture_drive.iterdir()
        if child.is_dir() and child.name.casefold() == plan.new_path.name.casefold()
    ]
    assert matching_names == [plan.new_path.name]
    assert result.path.name == matching_names[0]
    dossier = (result.path / "PROJECT.md").read_bytes().decode("utf-8")
    assert f"# {matching_names[0]}\r\n" in dossier
    index = (fixture_drive / "_Project Index.md").read_text(encoding="utf-8")
    assert f"| {matching_names[0]} |" in index
    assert f"| {project.name} |" not in index
    assert not any(".atlas-rename-" in child.name for child in fixture_drive.iterdir())


def test_case_only_rename_rolls_back_exact_spelling_and_dossier_on_index_failure(
    fixture_drive,
):
    drive_map, intake, project = _new_project(fixture_drive)
    index = fixture_drive / "_Project Index.md"
    original_index = index.read_bytes()
    row = next(
        line
        for line in original_index.splitlines(keepends=True)
        if line.startswith(f"| {project.name} |".encode())
    )
    duplicate_index = original_index + row
    index.write_bytes(duplicate_index)
    dossier_before = (project / "PROJECT.md").read_bytes()
    edited = replace(
        intake,
        project_address=replace(intake.project_address, street="1842 OAK STREET"),
        description="KITCHEN",
    )
    plan = preview_project_update(fixture_drive, project, edited)

    with pytest.raises(ProjectDataError, match="duplicate matching rows.*project restored"):
        apply_project_update(fixture_drive, drive_map, plan, allow_rename=True)

    matching_names = [
        child.name
        for child in fixture_drive.iterdir()
        if child.is_dir() and child.name.casefold() == project.name.casefold()
    ]
    assert matching_names == [project.name]
    assert (project / "PROJECT.md").read_bytes() == dossier_before
    assert index.read_bytes() == duplicate_index
    assert not any(".atlas-rename-" in child.name for child in fixture_drive.iterdir())


def _windows_lock_error(target):
    """A WinError 5 as Windows raises it, on every OS. The 5-arg OSError form
    sets ``winerror`` only on Windows, so CI on Linux would never retry."""
    error = PermissionError(13, "Access is denied", str(target))
    error.winerror = 5
    return error


def test_case_only_rename_survives_transient_windows_locks(fixture_drive, monkeypatch):
    drive_map, intake, project = _new_project(fixture_drive)
    edited = replace(
        intake,
        project_address=replace(intake.project_address, street="1842 OAK STREET"),
        description="KITCHEN",
    )
    plan = preview_project_update(fixture_drive, project, edited)

    # Windows antivirus/search-indexer/sync clients briefly hold freshly
    # written folders, failing renames with WinError 5. The rename must retry
    # through the transient lock instead of failing the whole update.
    monkeypatch.setattr(
        "atlas.core.project_data._RENAME_RETRY_DELAYS", (0.001, 0.001, 0.001)
    )
    real_rename = Path.rename
    failures = {"count": 0}

    def flaky_rename(self, target):
        if failures["count"] < 2:
            failures["count"] += 1
            raise _windows_lock_error(target)
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", flaky_rename)

    result = apply_project_update(fixture_drive, drive_map, plan, allow_rename=True)

    assert failures["count"] == 2
    assert result.path.name == plan.new_path.name
    assert result.path.is_dir()
    assert not any(".atlas-rename-" in child.name for child in fixture_drive.iterdir())


def test_case_only_rename_reports_persistent_windows_lock_after_retries(
    fixture_drive, monkeypatch
):
    drive_map, intake, project = _new_project(fixture_drive)
    dossier_before = (project / "PROJECT.md").read_bytes()
    edited = replace(
        intake,
        project_address=replace(intake.project_address, street="1842 OAK STREET"),
        description="KITCHEN",
    )
    plan = preview_project_update(fixture_drive, project, edited)

    monkeypatch.setattr(
        "atlas.core.project_data._RENAME_RETRY_DELAYS", (0.001, 0.001)
    )

    def locked_rename(self, target):
        raise _windows_lock_error(target)

    monkeypatch.setattr(Path, "rename", locked_rename)

    with pytest.raises(ProjectDataError, match="Access is denied"):
        apply_project_update(fixture_drive, drive_map, plan, allow_rename=True)


def test_apply_renames_and_refreshes_dossier_index_and_log(fixture_drive):
    drive_map, intake, project = _new_project(fixture_drive)
    dossier = project / "PROJECT.md"
    source = dossier.read_bytes().replace(
        b"jurisdiction:\r\n",
        b'custom_extension: "keep  exactly"\r\njurisdiction:\r\n',
    )
    source += b"\r\n## Custom Notes\r\n\r\n  Preserve  spacing | and \\slashes.\r\n"
    dossier.write_bytes(source)
    contact = add_contact(
        fixture_drive,
        ContactDraft(
            first_name="Private",
            last_name="Person",
            email="private.person@example.com",
            phone="510-555-0199",
            company="Confidential LLC",
        ),
    )
    edited = replace(
        intake,
        project_name="Pine House",
        project_address=ProjectAddress(
            street="99 Pine Avenue",
            unit="Suite 4",
            city="Berkeley",
            state="CA",
            postal_code="94704",
        ),
        project_use_case=ProjectUseCase("Other", "Historic Study"),
        billing_contact_id=contact.id,
        client_contact_id=contact.id,
        description="Rear Addition",
    )
    plan = preview_project_update(fixture_drive, project, edited)

    result = apply_project_update(
        fixture_drive,
        drive_map,
        plan,
        allow_rename=True,
    )

    assert result.old_path == project
    assert result.path == plan.new_path
    assert result.renamed is True
    assert not project.exists()
    raw = (result.path / "PROJECT.md").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\n" not in raw.replace(b"\r\n", b"")
    assert b'custom_extension: "keep  exactly"\r\n' in raw
    assert b"## Custom Notes\r\n\r\n  Preserve  spacing | and \\slashes.\r\n" in raw
    text = raw.decode("utf-8")
    assert f'project: "Pine House"' in text
    assert f'billing_contact_id: "{contact.id}"' in text
    assert '| Billing Contact | Private Person |' in text
    assert '| Client Email | private.person@example.com |' in text
    assert f"# {plan.new_path.name}\r\n" in text
    assert load_project_record(result.path).intake == replace(edited, created=CREATED)
    index = (fixture_drive / "_Project Index.md").read_bytes()
    assert index.count(f"| {plan.new_path.name} |".encode()) == 1
    assert project.name.encode() not in index
    assert b"private.person@example.com" not in index
    logs = b"".join(
        path.read_bytes()
        for path in (fixture_drive / "_tools" / "logs").glob("atlas-*.log")
    )
    assert b"project update" in logs
    assert b"private.person@example.com" not in logs
    assert b"Private Person" not in logs


def test_apply_requires_explicit_rename_approval(fixture_drive):
    drive_map, intake, project = _new_project(fixture_drive)
    edited = replace(
        intake,
        project_address=replace(intake.project_address, street="99 Pine Avenue"),
    )
    plan = preview_project_update(fixture_drive, project, edited)
    dossier_before = (project / "PROJECT.md").read_bytes()
    index_before = (fixture_drive / "_Project Index.md").read_bytes()

    with pytest.raises(ProjectDataError, match="allow_rename=True"):
        apply_project_update(fixture_drive, drive_map, plan)

    assert (project / "PROJECT.md").read_bytes() == dossier_before
    assert (fixture_drive / "_Project Index.md").read_bytes() == index_before
    assert not plan.new_path.exists()


def test_apply_refuses_rename_collision_without_writing(fixture_drive):
    drive_map, intake, project = _new_project(fixture_drive)
    edited = replace(
        intake,
        project_address=replace(intake.project_address, street="99 Pine Avenue"),
    )
    plan = preview_project_update(fixture_drive, project, edited)
    plan.new_path.mkdir()
    dossier_before = (project / "PROJECT.md").read_bytes()
    index_before = (fixture_drive / "_Project Index.md").read_bytes()

    with pytest.raises(ProjectDataError, match="destination already exists"):
        apply_project_update(fixture_drive, drive_map, plan, allow_rename=True)

    assert (project / "PROJECT.md").read_bytes() == dossier_before
    assert (fixture_drive / "_Project Index.md").read_bytes() == index_before


def test_apply_refuses_stale_dossier_without_writing_index_or_renaming(fixture_drive):
    drive_map, intake, project = _new_project(fixture_drive)
    edited = replace(
        intake,
        project_address=replace(intake.project_address, street="99 Pine Avenue"),
    )
    plan = preview_project_update(fixture_drive, project, edited)
    dossier = project / "PROJECT.md"
    dossier.write_bytes(dossier.read_bytes() + b"<!-- concurrent edit -->\r\n")
    stale = dossier.read_bytes()
    index_before = (fixture_drive / "_Project Index.md").read_bytes()

    with pytest.raises(ProjectDataError, match="dossier changed since preview"):
        apply_project_update(fixture_drive, drive_map, plan, allow_rename=True)

    assert dossier.read_bytes() == stale
    assert (fixture_drive / "_Project Index.md").read_bytes() == index_before
    assert not plan.new_path.exists()


def test_apply_refuses_contact_directory_change_without_writing(fixture_drive):
    drive_map, intake, project = _new_project(fixture_drive)
    plan = preview_project_update(fixture_drive, project, intake)
    dossier_before = (project / "PROJECT.md").read_bytes()
    index_before = (fixture_drive / "_Project Index.md").read_bytes()
    add_contact(
        fixture_drive,
        ContactDraft(
            first_name="Concurrent",
            last_name="Contact",
            email="concurrent@example.com",
        ),
    )

    with pytest.raises(ProjectDataError, match="contact directory changed since preview"):
        apply_project_update(fixture_drive, drive_map, plan)

    assert (project / "PROJECT.md").read_bytes() == dossier_before
    assert (fixture_drive / "_Project Index.md").read_bytes() == index_before


def test_apply_refuses_stale_project_index_without_writing_dossier(fixture_drive):
    drive_map, intake, project = _new_project(fixture_drive)
    plan = preview_project_update(fixture_drive, project, replace(intake, project_name="Revised"))
    dossier_before = (project / "PROJECT.md").read_bytes()
    index = fixture_drive / "_Project Index.md"
    index.write_bytes(index.read_bytes() + b"<!-- concurrent index edit -->\r\n")
    stale_index = index.read_bytes()

    with pytest.raises(ProjectDataError, match="index changed since preview"):
        apply_project_update(fixture_drive, drive_map, plan)

    assert (project / "PROJECT.md").read_bytes() == dossier_before
    assert index.read_bytes() == stale_index


def test_apply_repairs_existing_project_missing_from_index(fixture_drive):
    drive_map, intake, project = _new_project(fixture_drive)
    index = fixture_drive / "_Project Index.md"
    contents = index.read_bytes()
    index.write_bytes(
        b"".join(
            line
            for line in contents.splitlines(keepends=True)
            if not line.startswith(f"| {project.name} |".encode())
        )
    )
    edited = replace(intake, project_name="Oak House Repaired")
    plan = preview_project_update(fixture_drive, project, edited)

    result = apply_project_update(fixture_drive, drive_map, plan)

    assert result.record.intake.project_name == "Oak House Repaired"
    repaired = index.read_bytes()
    assert repaired.count(f"| {project.name} |".encode()) == 1
    assert b"| Oak House Repaired |" in repaired
    assert repaired.endswith(b"| Active |\r\n")
