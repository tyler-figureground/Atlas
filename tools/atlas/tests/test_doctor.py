from __future__ import annotations

from atlas.core.doctor import report_drive, report_to_dict
from atlas.core.scan import scan_drive

from conftest import FIXTURE_MAP, agent_files, make_project, write_map


def project_report(drive, name):
    report = report_drive(scan_drive(drive))
    return next(p for p in report.projects if p.name == name)


def full_control_plane(drive, files=None):
    base = {
        "PROJECT.md": "---\nproject: x\nrevit:\n---\n",
        "decisions/README.md": "# Decisions\n",
        "06 Research/Code/.keep": "",
    }
    base.update(agent_files(drive))
    base.update(files or {})
    return base


def test_conform_project_reports_conform(fixture_drive):
    make_project(
        fixture_drive, "260101_Test-House",
        sections=["01 Model", "06 Research", "08 OUT", "11 Meetings"],
        files=full_control_plane(fixture_drive),
    )
    p = project_report(fixture_drive, "260101_Test-House")
    assert p.status == "conform"
    assert not p.actionable


def test_missing_control_plane_is_drift(fixture_drive):
    make_project(fixture_drive, "260102_Bare-House", sections=["01 Model"])
    p = project_report(fixture_drive, "260102_Bare-House")
    assert p.status == "drift"
    assert "PROJECT.md" in p.missing_control_plane
    assert "decisions" in p.missing_control_plane


def test_stub_project(fixture_drive):
    make_project(fixture_drive, "260103_Stub", files={"note.gdoc": "x"})
    p = project_report(fixture_drive, "260103_Stub")
    assert p.status == "stub"
    assert p.unfiled == ("note.gdoc",)


def test_drift_folder_detected_case_insensitive(fixture_drive):
    make_project(
        fixture_drive, "260104_Drifty",
        sections=["01 Model", "meetings"],
        files=full_control_plane(fixture_drive),
    )
    p = project_report(fixture_drive, "260104_Drifty")
    assert ("meetings", "11 Meetings") in p.drift
    assert p.status == "drift"


def test_relocation_source_counted(fixture_drive):
    make_project(
        fixture_drive, "260105_Reloc",
        sections=["01 Model", "08 OUT/Invoices"],
        files=full_control_plane(fixture_drive, {"08 OUT/Invoices/inv-001.pdf": "x"}),
    )
    p = project_report(fixture_drive, "260105_Reloc")
    hits = {(h.source, h.target, h.file_count) for h in p.relocations}
    assert ("08 OUT/Invoices", "10 Legal/Invoices", 1) in hits


def test_handoff_sweep_matches_glob_and_is_not_unfiled(fixture_drive):
    make_project(
        fixture_drive, "260106_Sweepy",
        sections=["01 Model"],
        files=full_control_plane(fixture_drive, {"HANDOFF-roof-01.md": "x"}),
    )
    p = project_report(fixture_drive, "260106_Sweepy")
    assert ("HANDOFF-roof-01.md", ".agent/handoff/") in p.sweeps
    assert "HANDOFF-roof-01.md" not in p.unfiled


def test_case_only_renamed_source_is_not_a_pending_relocation(fixture_drive, tmp_path):
    # Regression: on case-insensitive mounts, Path.is_dir() matches the RENAMED
    # target ("Change Orders") when probing the old source ("change Orders"),
    # reporting a phantom pending relocation forever. Exact-case probe required.
    import copy
    import json

    from conftest import FIXTURE_MAP, write_map

    data = copy.deepcopy(FIXTURE_MAP)
    data["relocations"]["08 OUT/change Orders"] = "08 OUT/Change Orders"
    write_map(fixture_drive, data)
    make_project(
        fixture_drive, "260109_Cased",
        sections=["01 Model", "08 OUT/Change Orders"],  # already renamed on disk
        files=full_control_plane(fixture_drive),
    )
    p = project_report(fixture_drive, "260109_Cased")
    assert not any(h.source == "08 OUT/change Orders" for h in p.relocations), p.relocations


def test_tolerated_root_files_not_unfiled(fixture_drive):
    make_project(
        fixture_drive, "260107_Ledger",
        sections=["01 Model"],
        files=full_control_plane(fixture_drive, {"jdp-time-ledger.ndjson": "{}", "desktop.ini": ""}),
    )
    p = project_report(fixture_drive, "260107_Ledger")
    assert p.unfiled == ()


def test_report_json_shape(fixture_drive):
    make_project(fixture_drive, "260108_Any", sections=["01 Model"])
    d = report_to_dict(report_drive(scan_drive(fixture_drive)))
    assert d["drive"] == "TESTDRIVE"
    assert {"conform", "drift", "unfiled", "stub"} <= set(d["summary"])
    (proj,) = [p for p in d["projects"] if p["name"] == "260108_Any"]
    assert set(proj) == {
        "name", "status", "sections_present", "missing_control_plane",
        "drift", "relocations", "sweeps", "receipts", "unfiled", "ignored",
        "unreadable", "unreadable_deep", "overlong", "depth_capped", "items",
    }
    # An agent reading this must be able to tell "nothing wrong here" from
    # "Atlas could not look". ADR 0004.
    assert proj["unreadable"] == []
    # The budget block is always there; uncounted is None, never a zero.
    assert d["budget"]["cap"] == 400_000
    assert d["budget"]["counted"] is False and d["budget"]["total_items"] is None


def test_underscore_and_00_dirs_excluded(fixture_drive):
    make_project(fixture_drive, "_Archived Projects", sections=["01 Model"])
    make_project(fixture_drive, "00 Templates")
    report = report_drive(scan_drive(fixture_drive))
    names = {p.name for p in report.projects}
    assert "_Archived Projects" not in names
    assert "00 Templates" not in names


def test_map_tolerated_entries_are_ignored_never_unfiled(fixture_drive):
    """Ticket 29: agent tool config must sit at the project root to work, so
    flagging it unfiled is a finding nobody can act on."""
    write_map(fixture_drive, FIXTURE_MAP | {"tolerated": [".mcp.json", ".pi"]})
    make_project(
        fixture_drive, "260110_Dots",
        sections=["01 Model", "06 Research", "08 OUT", "11 Meetings"],
        files=full_control_plane(fixture_drive, {".mcp.json": "{}", ".pi/run/log.txt": "x"}),
    )
    p = project_report(fixture_drive, "260110_Dots")
    assert p.unfiled == ()
    assert p.ignored == (".mcp.json", ".pi")
    assert p.status == "conform"


def test_hard_coded_os_noise_stays_silent(fixture_drive):
    """Only map-tolerated entries surface as ignored - desktop.ini is universal
    background and would add an ignored line to every project on the drive."""
    write_map(fixture_drive, FIXTURE_MAP | {"tolerated": [".pi"]})
    make_project(
        fixture_drive, "260111_Noise",
        sections=["01 Model", "06 Research", "08 OUT", "11 Meetings"],
        files=full_control_plane(fixture_drive, {"desktop.ini": "", "jdp-time-ledger.ndjson": "{}"}),
    )
    p = project_report(fixture_drive, "260111_Noise")
    assert p.unfiled == ()
    assert p.ignored == ()


def test_report_json_names_ignored(fixture_drive):
    write_map(fixture_drive, FIXTURE_MAP | {"tolerated": [".pi"]})
    make_project(
        fixture_drive, "260112_Json",
        sections=["01 Model", "06 Research", "08 OUT", "11 Meetings"],
        files=full_control_plane(fixture_drive, {".pi/run/log.txt": "x"}),
    )
    report = report_to_dict(report_drive(scan_drive(fixture_drive)))
    row = next(p for p in report["projects"] if p["name"] == "260112_Json")
    assert row["ignored"] == [".pi"]
    assert row["unfiled"] == []
