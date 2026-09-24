from __future__ import annotations

import hashlib
import os
from dataclasses import replace
from datetime import date

import pytest

import atlas.core.project_index as project_index_module
from atlas.core.intake import ProjectAddress, ProjectIntake, ProjectUseCase
from atlas.core.mapfile import load_map
from atlas.core.project_index import (
    ProjectIndexError,
    append_project_index_row,
    preflight_project_index,
    update_project_index_row,
)


def _intake() -> ProjectIntake:
    return ProjectIntake(
        project_name="Café | Annex Study",
        project_address=ProjectAddress(
            street="100 Main | Broadway",
            unit="Suite 2",
            city="Oakland",
            state="CA",
            postal_code="94612",
        ),
        project_use_case=ProjectUseCase("Other", "Arts | Culture Center"),
        billing_contact_id="billing-private-id",
        client_contact_id="client-private-id",
        description="Early | phase only",
        created=date(2026, 8, 13),
    )


def test_preflight_creates_missing_expanded_index_as_utf8_crlf(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")

    path = preflight_project_index(fixture_drive, drive_map)

    assert path == fixture_drive / "_Project Index.md"
    assert path.read_bytes() == (
        "# TESTDRIVE - Project Index\r\n"
        "\r\n"
        "Auto-maintained by Atlas. One row per project (searchable table of contents).\r\n"
        "\r\n"
        "| Project folder | Project name | Full project address | Project use case | Created | Description | Status |\r\n"
        "|---|---|---|---|---|---|---|\r\n"
    ).encode("utf-8")


def test_append_writes_escaped_non_sensitive_intake_row(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")

    append_project_index_row(
        fixture_drive,
        drive_map,
        "260813_100 Main-Study|Set\nA",
        _intake(),
    )

    raw = (fixture_drive / "_Project Index.md").read_bytes()
    assert raw.endswith(
        (
            "| 260813_100 Main-Study\\|Set A | Café \\| Annex Study | "
            "100 Main \\| Broadway, Suite 2, Oakland, CA 94612 | "
            "Arts \\| Culture Center | 2026-08-13 | Early \\| phase only | Active |\r\n"
        ).encode("utf-8")
    )
    assert b"\n" not in raw.replace(b"\r\n", b"")
    assert b"billing-private-id" not in raw
    assert b"client-private-id" not in raw


def test_append_inserts_crlf_when_index_has_no_trailing_newline(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    index = preflight_project_index(fixture_drive, drive_map)
    without_trailing_newline = index.read_bytes().removesuffix(b"\r\n")
    index.write_bytes(without_trailing_newline)

    append_project_index_row(fixture_drive, drive_map, "260813_100 Main", _intake())

    raw = index.read_bytes()
    assert raw.startswith(without_trailing_newline + b"\r\n")
    assert raw.endswith(b"| 2026-08-13 | Early \\| phase only | Active |\r\n")
    assert b"\n" not in raw.replace(b"\r\n", b"")


def test_append_preserves_concurrent_change_detected_before_atomic_replace(
    fixture_drive, monkeypatch
):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    index = preflight_project_index(fixture_drive, drive_map)
    external = index.read_bytes() + b"<!-- concurrent edit -->\r\n"
    real_atomic_write = project_index_module._atomic_write

    def inject_change(path, contents, expected):
        index.write_bytes(external)
        real_atomic_write(path, contents, expected)

    monkeypatch.setattr(project_index_module, "_atomic_write", inject_change)

    with pytest.raises(ProjectIndexError, match="external change preserved"):
        append_project_index_row(fixture_drive, drive_map, "260813_100 Main", _intake())

    assert index.read_bytes() == external


def test_preflight_migrates_exact_legacy_table_and_backs_up_original(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    index = fixture_drive / "_Project Index.md"
    legacy = (
        "# TESTDRIVE - Project Index\r\n"
        "\r\n"
        "Auto-maintained by New-Project. One row per project (searchable table of contents).\r\n"
        "\r\n"
        "| Project folder | Created | Descriptor | Status |\r\n"
        "|---|---|---|---|\r\n"
        "| 240101_100 Main-Kitchen | 2024-01-01 | Kitchen | Active |\r\n"
        "| 240102_200 Oak |  |  |  |\r\n"
    ).encode("utf-8")
    index.write_bytes(legacy)

    preflight_project_index(fixture_drive, drive_map)

    assert index.read_bytes() == (
        "# TESTDRIVE - Project Index\r\n"
        "\r\n"
        "Auto-maintained by New-Project. One row per project (searchable table of contents).\r\n"
        "\r\n"
        "| Project folder | Project name | Full project address | Project use case | Created | Description | Status |\r\n"
        "|---|---|---|---|---|---|---|\r\n"
        "| 240101_100 Main-Kitchen |  |  |  | 2024-01-01 | Kitchen | Active |\r\n"
        "| 240102_200 Oak |  |  |  |  |  |  |\r\n"
    ).encode("utf-8")
    backups = list((fixture_drive / "_tools" / "logs").glob("Project-Index-pre-migration-*.md"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == legacy


@pytest.mark.parametrize(
    "table",
    [
        "| Folder | Created | Descriptor | Status |\r\n|---|---|---|---|",
        "| Project folder | Created | Descriptor | Status |\r\n|---|---|---|",
        (
            "| Project folder | Created | Descriptor | Status |\r\n"
            "|---|---|---|---|\r\n"
            "| folder | date | desc | Active | surprise |"
        ),
        (
            "| Project folder | Project name | Full project address | Project use case | "
            "Created | Description | Status |\r\n"
            "|---|---|---|---|"
        ),
    ],
)
def test_preflight_refuses_unknown_table_shape_without_modification(fixture_drive, table):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    index = fixture_drive / "_Project Index.md"
    original = (f"# Hand edited\r\n\r\n{table}\r\n").encode("utf-8")
    index.write_bytes(original)

    with pytest.raises(ProjectIndexError, match="unknown project-index table shape"):
        preflight_project_index(fixture_drive, drive_map)

    assert index.read_bytes() == original
    assert not (fixture_drive / "_tools" / "logs").exists()


def test_legacy_migration_preserves_external_edit_arriving_before_move(fixture_drive, monkeypatch):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    index = fixture_drive / "_Project Index.md"
    legacy = (
        "# TESTDRIVE - Project Index\r\n\r\n"
        "| Project folder | Created | Descriptor | Status |\r\n"
        "|---|---|---|---|\r\n"
        "| old | 2024-01-01 | Test | Active |\r\n"
    ).encode("utf-8")
    external = legacy + b"| external | 2025-01-01 | Added | Active |\r\n"
    index.write_bytes(legacy)
    real_replace = project_index_module.os.replace
    injected = False

    def inject_then_move(source, destination):
        nonlocal injected
        if source == index and not injected:
            index.write_bytes(external)
            injected = True
        return real_replace(source, destination)

    monkeypatch.setattr(project_index_module.os, "replace", inject_then_move)

    preflight_project_index(fixture_drive, drive_map)

    backups = list((fixture_drive / "_tools" / "logs").glob("Project-Index-pre-migration-*.md"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == external
    assert "| external |  |  |  | 2025-01-01 | Added | Active |" in index.read_text(encoding="utf-8")


def test_existing_writer_lock_refuses_without_creating_index(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    index = fixture_drive / "_Project Index.md"
    lock = fixture_drive / "_Project Index.md.lock"
    lock.write_text("busy", encoding="utf-8")

    with pytest.raises(ProjectIndexError, match="being updated"):
        preflight_project_index(fixture_drive, drive_map)

    assert not index.exists()
    assert lock.read_text(encoding="utf-8") == "busy"


def test_stale_writer_lock_is_recovered(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    lock = fixture_drive / "_Project Index.md.lock"
    lock.write_text("abandoned", encoding="utf-8")
    os.utime(lock, (1, 1))

    index = preflight_project_index(fixture_drive, drive_map)

    assert index.exists()
    assert not lock.exists()


def test_append_preserves_external_content_added_before_row(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    index = preflight_project_index(fixture_drive, drive_map)
    external_row = b"| manual | edit | address | use | 2026-01-01 | note | Active |\r\n"
    with index.open("ab") as stream:
        stream.write(external_row)

    append_project_index_row(fixture_drive, drive_map, "260813_100 Main", _intake())

    contents = index.read_bytes()
    assert external_row in contents
    assert contents.endswith(b"| 260813_100 Main | Caf\xc3\xa9 \\| Annex Study | 100 Main \\| Broadway, Suite 2, Oakland, CA 94612 | Arts \\| Culture Center | 2026-08-13 | Early \\| phase only | Active |\r\n")


def test_append_inserts_row_inside_table_before_trailing_prose(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    index = preflight_project_index(fixture_drive, drive_map)
    notes = b"\r\n## Notes\r\n\r\nKeep this prose after the table.\r\n"
    index.write_bytes(index.read_bytes() + notes)

    append_project_index_row(fixture_drive, drive_map, "260813_100 Main", _intake())

    contents = index.read_bytes()
    row = b"| 260813_100 Main | Caf\xc3\xa9 \\| Annex Study |"
    assert contents.index(row) < contents.index(b"## Notes")
    assert contents.endswith(notes)


def test_preflight_replace_failure_cleans_temporary_files(fixture_drive, monkeypatch):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")

    def fail_replace(source, destination):
        assert source.parent == destination.parent == fixture_drive
        assert source.exists()
        raise OSError("simulated replace failure")

    monkeypatch.setattr(project_index_module.os, "replace", fail_replace)

    with pytest.raises(ProjectIndexError, match="cannot atomically write"):
        preflight_project_index(fixture_drive, drive_map)

    assert sorted(path.name for path in fixture_drive.iterdir()) == ["_tools"]


def test_update_replaces_one_existing_row_without_pii_or_duplicate(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    old_folder = "260813_100 Main-Old"
    append_project_index_row(fixture_drive, drive_map, old_folder, _intake())
    index = fixture_drive / "_Project Index.md"
    original = index.read_bytes().replace(b"| Active |\r\n", b"| On Hold |\r\n")
    index.write_bytes(original)
    digest = hashlib.sha256(original).hexdigest()
    revised = ProjectIntake(
        project_name="Revised Study",
        project_address=ProjectAddress(
            street="200 Oak Avenue",
            city="Oakland",
            state="CA",
            postal_code="94612",
        ),
        project_use_case=ProjectUseCase("Feasibility"),
        billing_contact_id="new-billing-private-id",
        client_contact_id="new-client-private-id",
        description="Phase 2",
        created=date(2026, 8, 13),
    )

    update_project_index_row(
        fixture_drive,
        drive_map,
        old_folder,
        "260813_200 Oak Avenue-Phase 2",
        revised,
        expected_digest=digest,
    )

    raw = index.read_bytes()
    assert raw.count(b"| 260813_200 Oak Avenue-Phase 2 |") == 1
    assert old_folder.encode() not in raw
    assert b"| Revised Study | 200 Oak Avenue, Oakland, CA 94612 | Feasibility |" in raw
    assert raw.endswith(b"| 2026-08-13 | Phase 2 | On Hold |\r\n")
    assert b"private-id" not in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")


def test_update_repairs_missing_row_using_append_semantics(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    index = preflight_project_index(fixture_drive, drive_map)
    original = index.read_bytes()

    update_project_index_row(
        fixture_drive,
        drive_map,
        "260813_missing-old-row",
        "260813_100 Main-Repaired",
        _intake(),
        expected_digest=hashlib.sha256(original).hexdigest(),
    )

    raw = index.read_bytes()
    assert raw.endswith(
        (
            "| 260813_100 Main-Repaired | Café \\| Annex Study | "
            "100 Main \\| Broadway, Suite 2, Oakland, CA 94612 | "
            "Arts \\| Culture Center | 2026-08-13 | Early \\| phase only | Active |\r\n"
        ).encode("utf-8")
    )
    assert b"billing-private-id" not in raw
    assert b"client-private-id" not in raw


def test_update_missing_row_inserts_inside_table_and_later_update_finds_one(
    fixture_drive,
):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    index = preflight_project_index(fixture_drive, drive_map)
    notes = b"\r\n## Notes\r\n\r\nKeep this prose after the table.\r\n"
    original = index.read_bytes() + notes
    index.write_bytes(original)
    repaired_folder = "260813_100 Main-Repaired"

    update_project_index_row(
        fixture_drive,
        drive_map,
        "260813_missing-old-row",
        repaired_folder,
        _intake(),
        expected_digest=hashlib.sha256(original).hexdigest(),
    )

    repaired = index.read_bytes()
    assert repaired.index(f"| {repaired_folder} |".encode()) < repaired.index(b"## Notes")
    assert repaired.endswith(notes)

    update_project_index_row(
        fixture_drive,
        drive_map,
        repaired_folder,
        repaired_folder,
        replace(_intake(), project_name="Later Revision"),
        expected_digest=hashlib.sha256(repaired).hexdigest(),
    )

    updated = index.read_bytes()
    assert updated.count(f"| {repaired_folder} |".encode()) == 1
    assert b"| Later Revision |" in updated
    assert updated.endswith(notes)


def test_update_still_blocks_duplicate_matching_rows(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    folder = "260813_100 Main-Old"
    append_project_index_row(fixture_drive, drive_map, folder, _intake())
    index = fixture_drive / "_Project Index.md"
    original = index.read_bytes()
    row = next(
        line
        for line in original.splitlines(keepends=True)
        if line.startswith(f"| {folder} |".encode())
    )
    duplicate = original + row
    index.write_bytes(duplicate)

    with pytest.raises(ProjectIndexError, match="duplicate matching rows"):
        update_project_index_row(
            fixture_drive,
            drive_map,
            folder,
            "260813_100 Main-Revised",
            _intake(),
            expected_digest=hashlib.sha256(duplicate).hexdigest(),
        )

    assert index.read_bytes() == duplicate


def test_update_leaves_untouched_status_cell_byte_identical(fixture_drive):
    # An edit that does not touch Status must not re-escape it: a pipe in the
    # cell used to double its backslashes on every edit.
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    folder = "260813_100 Main-Old"
    append_project_index_row(fixture_drive, drive_map, folder, _intake())
    index = fixture_drive / "_Project Index.md"
    status = rb"On hold \| see C:\\notes"
    index.write_bytes(
        index.read_bytes().replace(b"| Active |\r\n", b"| " + status + b" |\r\n")
    )

    for _ in range(3):
        update_project_index_row(
            fixture_drive,
            drive_map,
            folder,
            folder,
            _intake(),
            expected_digest=hashlib.sha256(index.read_bytes()).hexdigest(),
        )

    assert index.read_bytes().endswith(b"| " + status + b" |\r\n")


def test_update_finds_row_whose_folder_cell_is_escaped(fixture_drive):
    drive_map = load_map(fixture_drive / "_tools" / "testdrive-map.json")
    folder = r"260813_100 Main-A\B"
    append_project_index_row(fixture_drive, drive_map, folder, _intake())
    index = fixture_drive / "_Project Index.md"

    update_project_index_row(
        fixture_drive,
        drive_map,
        folder,
        folder,
        replace(_intake(), project_name="Renamed"),
        expected_digest=hashlib.sha256(index.read_bytes()).hexdigest(),
    )

    raw = index.read_bytes()
    assert raw.count(rb"| 260813_100 Main-A\\B |") == 1
    assert b"| Renamed |" in raw
