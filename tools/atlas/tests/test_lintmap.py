from __future__ import annotations

import copy

from atlas.core.lintmap import lint_map
from atlas.core.mapfile import find_map, load_map

from conftest import FIXTURE_MAP, write_map


def codes(findings):
    return {f.code for f in findings}


def test_clean_map_lints_clean(fixture_drive):
    findings = lint_map(load_map(find_map(fixture_drive)))
    assert not [f for f in findings if f.level == "error"], findings


def test_drift_target_must_be_canonical(tmp_path):
    data = copy.deepcopy(FIXTURE_MAP)
    data["driftMap"]["Old"] = "99 Nowhere"
    drive = tmp_path / "D"
    write_map(drive, data)
    assert "DRIFT-TARGET" in codes(lint_map(load_map(find_map(drive))))


def test_drift_entry_that_moves_is_an_error(tmp_path):
    # The v1.1->v2.0 lesson: PS1 Rename-Item cannot move, so a pathy driftMap
    # target must be rejected and routed to relocations instead.
    data = copy.deepcopy(FIXTURE_MAP)
    data["driftMap"]["Agendas"] = "11 Meetings/Agendas"
    drive = tmp_path / "D"
    write_map(drive, data)
    assert "DRIFT-IS-MOVE" in codes(lint_map(load_map(find_map(drive))))


def test_unblessed_analysis_dir_is_error(tmp_path):
    # The exact v1.1 ARCHITECTURE bug: analysisDir pointed at a child the map
    # never blessed, so Add-Section could not create it.
    data = copy.deepcopy(FIXTURE_MAP)
    data["controlPlane"]["analysisDir"] = "06 Research/NotBlessed"
    drive = tmp_path / "D"
    write_map(drive, data)
    assert "ANALYSIS-DIR" in codes(lint_map(load_map(find_map(drive))))


def test_duplicate_child_across_sections_warns(tmp_path):
    # The Invoices-in-two-homes bug class.
    data = copy.deepcopy(FIXTURE_MAP)
    data["sections"][2]["children"].append("Invoices")  # 08 OUT gains Invoices
    drive = tmp_path / "D"
    write_map(drive, data)
    findings = lint_map(load_map(find_map(drive)))
    dup = [f for f in findings if f.code == "DUP-CHILD" and "Invoices" in f.message]
    assert dup and dup[0].level == "warn"


def test_same_leaf_under_two_parents_in_one_section_does_not_warn(tmp_path):
    # ADR 0021: every party in 07 Correspondence has its own In and Out. One
    # section is one home, however many parents repeat the leaf.
    data = copy.deepcopy(FIXTURE_MAP)
    data["sections"][2]["children"] += ["Client/In", "Owner/In"]
    drive = tmp_path / "D"
    write_map(drive, data)
    findings = lint_map(load_map(find_map(drive)))
    assert not [f for f in findings if f.code == "DUP-CHILD" and "'In'" in f.message]


def test_relocation_target_must_be_blessed_root(tmp_path):
    data = copy.deepcopy(FIXTURE_MAP)
    data["relocations"]["Stuff"] = "97 Nowhere/Stuff"
    drive = tmp_path / "D"
    write_map(drive, data)
    assert "RELOC-TARGET" in codes(lint_map(load_map(find_map(drive))))


def test_mixed_prefix_widths_warn(tmp_path):
    data = copy.deepcopy(FIXTURE_MAP)
    data["sections"][0]["children"] = ["0 Site Model", "02 Design"]
    drive = tmp_path / "D"
    write_map(drive, data)
    assert "MIXED-PREFIX" in codes(lint_map(load_map(find_map(drive))))
