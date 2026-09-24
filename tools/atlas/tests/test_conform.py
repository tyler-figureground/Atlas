from __future__ import annotations

import pytest

from atlas.core.conform import CONFLICT, DONE, apply_plan, build_plan
from atlas.core.doctor import report_project
from atlas.core.mapfile import find_map, load_map
from atlas.core.ops import OpsError
from atlas.core.projectmd import create_crlf_no_bom
from atlas.core.scan import scan_drive

from conftest import make_project


def plan_for(drive, name):
    inventory = scan_drive(drive)
    m = inventory.map
    inv = next(p for p in inventory.projects if p.name == name)
    return build_plan(report_project(inv, m), m), inv, m


def conform(drive, name, only=None):
    plan, inv, m = plan_for(drive, name)
    return apply_plan(drive, inv.path, m, plan, only=only), inv, m


def test_backfill_creates_stub_when_missing(fixture_drive):
    make_project(fixture_drive, "260201_Legacy", sections=["01 Model"])
    result, inv, m = conform(fixture_drive, "260201_Legacy")
    assert (inv.path / "PROJECT.md").is_file()
    assert (inv.path / "decisions" / "README.md").is_file()
    assert (inv.path / "CLAUDE.md").is_file()
    assert (inv.path / "06 Research" / "Code").is_dir()
    raw = (inv.path / "PROJECT.md").read_bytes()
    assert raw.startswith(b"---\r\n") and not raw.startswith(b"\xef\xbb\xbf")
    # display name drops the YYMMDD_ prefix, same as Conform-Project.ps1
    assert b'project: "Legacy"' in raw
    for key in (
        b"address_street:",
        b"address_unit:",
        b"address_city:",
        b"address_state:",
        b"address_postal_code:",
    ):
        assert raw.count(key + b"\r\n") == 1
    # Identity slot, parity with Conform-Project.ps1
    assert b"| Jurisdiction | |\r\n| Virtual tour | |\r\n" in raw
    assert raw.count(b"| Descriptor | |\r\n") == 1
    assert raw.count(b"| Created | |\r\n") == 1


def test_backfill_leaves_existing_prose_as_conflict(fixture_drive):
    make_project(
        fixture_drive, "260202_Prose", sections=["01 Model"],
        files={"PROJECT.md": "# My notes\n\nImportant prose.\n"},
    )
    result, inv, m = conform(fixture_drive, "260202_Prose")
    text = (inv.path / "PROJECT.md").read_text(encoding="utf-8")
    assert text == "# My notes\n\nImportant prose.\n"
    action = next(a for a in result.actions if a.dst == "PROJECT.md")
    assert action.status == CONFLICT and "left unchanged" in action.note


def test_backfill_leaves_existing_contract_alone(fixture_drive):
    original = "---\nproject: x\n---\nbody\n"
    make_project(
        fixture_drive, "260203_HasFM", sections=["01 Model"],
        files={"PROJECT.md": original, "CLAUDE.md": "keep me"},
    )
    result, inv, m = conform(fixture_drive, "260203_HasFM")
    assert (inv.path / "PROJECT.md").read_text(encoding="utf-8") == original
    # CLAUDE.md's words move into AGENTS.md first; then it becomes the pointer.
    assert "keep me" in (inv.path / "AGENTS.md").read_text(encoding="utf-8")
    assert (inv.path / "CLAUDE.md").read_text(encoding="utf-8") == "@AGENTS.md\n"


def test_rename_moves_drift_folder(fixture_drive):
    make_project(
        fixture_drive, "260204_Drifty", sections=["01 Model", "Meetings"],
        files={"Meetings/2026-01-01-kickoff.md": "notes"},
    )
    result, inv, m = conform(fixture_drive, "260204_Drifty")
    assert (inv.path / "11 Meetings" / "2026-01-01-kickoff.md").is_file()
    assert not (inv.path / "Meetings").exists()


def test_rename_merges_no_clobber_into_existing_target(fixture_drive):
    make_project(
        fixture_drive, "260205_Merge",
        sections=["01 Model", "Meetings", "11 Meetings"],
        files={
            "Meetings/a.md": "old-a",
            "Meetings/b.md": "old-b",
            "11 Meetings/a.md": "new-a",   # collision: must survive untouched
        },
    )
    result, inv, m = conform(fixture_drive, "260205_Merge")
    action = next(a for a in result.actions if a.src == "Meetings")
    assert action.status == CONFLICT and "1 name collision" in action.note
    assert (inv.path / "11 Meetings" / "a.md").read_text(encoding="utf-8") == "new-a"
    assert (inv.path / "11 Meetings" / "b.md").read_text(encoding="utf-8") == "old-b"
    assert (inv.path / "Meetings" / "a.md").read_text(encoding="utf-8") == "old-a"


def test_relocation_moves_and_empty_source_removed(fixture_drive):
    make_project(
        fixture_drive, "260206_Reloc",
        sections=["01 Model", "08 OUT/Invoices", "10 Legal"],
        files={"08 OUT/Invoices/inv-1.pdf": "x"},
    )
    result, inv, m = conform(fixture_drive, "260206_Reloc")
    assert (inv.path / "10 Legal" / "Invoices" / "inv-1.pdf").is_file()
    assert not (inv.path / "08 OUT" / "Invoices").exists()

    make_project(fixture_drive, "260207_EmptyDup",
                 sections=["01 Model", "08 OUT/Invoices", "10 Legal/Invoices"])
    result, inv, m = conform(fixture_drive, "260207_EmptyDup")
    action = next(a for a in result.actions if a.src == "08 OUT/Invoices")
    assert action.status == DONE and "file-empty" in action.note
    assert not (inv.path / "08 OUT" / "Invoices").exists()


def test_sweep_moves_handoffs(fixture_drive):
    make_project(
        fixture_drive, "260208_Sweepy", sections=["01 Model"],
        files={"HANDOFF-roof-01.md": "x", "HANDOFF-site-02.md": "y"},
    )
    result, inv, m = conform(fixture_drive, "260208_Sweepy")
    assert (inv.path / ".agent" / "handoff" / "HANDOFF-roof-01.md").is_file()
    assert (inv.path / ".agent" / "handoff" / "HANDOFF-site-02.md").is_file()


def test_conform_never_recreates_missing_project_root(fixture_drive):
    project = make_project(fixture_drive, "260208_Deleted")
    plan, _inventory, drive_map = plan_for(fixture_drive, project.name)
    project.rmdir()

    with pytest.raises(OpsError, match="no longer available"):
        apply_plan(fixture_drive, project, drive_map, plan)

    assert not project.exists()


def test_control_file_creation_never_replaces_concurrent_arrival(tmp_path):
    target = tmp_path / "CLAUDE.md"
    target.write_bytes(b"human content\r\n")

    assert not create_crlf_no_bom(target, ["@PROJECT.md"])
    assert target.read_bytes() == b"human content\r\n"


def test_only_filter_limits_action_classes(fixture_drive):
    make_project(
        fixture_drive, "260209_Filtered", sections=["01 Model", "Meetings"],
        files={"Meetings/x.md": "x"},
    )
    result, inv, m = conform(fixture_drive, "260209_Filtered", only={"rename"})
    assert (inv.path / "11 Meetings").is_dir()
    assert not (inv.path / "PROJECT.md").exists()  # backfill filtered out
    statuses = {a.kind: a.status for a in result.actions}
    assert statuses["backfill"] == "skipped"


def test_v11_replay_full_project_conforms_and_second_plan_is_empty(fixture_drive):
    """The regression gate from the spec: a project shaped like the real
    v1.1 drive state (missing control plane + drift folder + stray invoices +
    root handoffs) conforms in one apply; doctor then reports conform and a
    second plan is empty (idempotency)."""
    make_project(
        fixture_drive, "260210_Replay",
        sections=["01 Model", "06 Research", "08 OUT/Invoices", "10 Legal/Invoices", "Meetings"],
        files={
            "08 OUT/Invoices/inv-feb.pdf": "x",
            "10 Legal/Invoices/inv-jan.pdf": "y",
            "Meetings/kickoff.md": "z",
            "HANDOFF-qaqc-01.md": "h",
        },
    )
    result, inv, m = conform(fixture_drive, "260210_Replay")
    assert all(a.status == DONE for a in result.actions), result.actions

    # End state: single homes, everything preserved.
    assert (inv.path / "10 Legal" / "Invoices" / "inv-jan.pdf").is_file()
    assert (inv.path / "10 Legal" / "Invoices" / "inv-feb.pdf").is_file()
    assert (inv.path / "11 Meetings" / "kickoff.md").is_file()
    assert (inv.path / ".agent" / "handoff" / "HANDOFF-qaqc-01.md").is_file()
    assert not (inv.path / "08 OUT" / "Invoices").exists()

    # Idempotency: nothing left to do, and doctor agrees.
    plan2, inv2, m2 = plan_for(fixture_drive, "260210_Replay")
    assert plan2.empty, plan2.actions
    inventory = scan_drive(fixture_drive)
    report = report_project(next(p for p in inventory.projects if p.name == "260210_Replay"), m2)
    assert report.status == "conform", report
