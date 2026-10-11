"""Receipt Rules: machine-file sweeps below the project root (ticket 31).

A Receipt Rule is the map saying "a file that looks like this, sitting anywhere
below a project root, is agent scratch and belongs in the agent workspace". It
fires only in an explicitly requested deep pass - `doctor --deep PROJECT`,
`conform --deep` - never in the default root-only report, and it emits a Sweep
or it emits nothing. Containment (ADR 0007) still decides every deep node's
Filing State; a receipt is a finding, not a state.
"""

from __future__ import annotations

import copy
import json
import sys

import pytest

from atlas.cli import main
from atlas.core.conform import CONFLICT, SWEEP, apply_plan, build_plan, invert_plan
from atlas.core.doctor import report_project, report_to_dict
from atlas.core.lintmap import lint_map
from atlas.core.mapfile import MapError, ReceiptRule, find_map, load_map
from atlas.core.deep import ReceiptHit, scan_deep
from atlas.core.scan import scan_drive
from atlas.core.tree import MAPPED, open_project_tree

from conftest import FIXTURE_MAP, agent_files, make_project, write_map

WORKSPACE = {"runsDir": ".agent/runs", "backupsDir": ".agent/backups"}

ZIPS = {"name": "Run zips", "target": ".agent/runs", "match": {"extensions": ["zip"]}}
LOGS = {"name": "Logs", "target": ".agent/backups", "match": {"nameRegex": r"\.log$"}}

SECTIONS = ["01 Model", "06 Research", "08 OUT", "11 Meetings"]
CONTROL_PLANE = {
    "PROJECT.md": "---\nproject: x\n---\n",
    "CLAUDE.md": "# workspace\n",
    "decisions/README.md": "# Decisions\n",
    "06 Research/Code/.keep": "",
}


def with_receipt_rules(drive, *rules, extra=None):
    """The fixture map plus an agent workspace and the given receiptRules."""
    data = copy.deepcopy(FIXTURE_MAP)
    data["controlPlane"].update(WORKSPACE)
    data["receiptRules"] = list(rules)
    data.update(extra or {})
    write_map(drive, data)
    return load_map(find_map(drive))


def project_with(drive, name, files=None, dirs=()):
    """A project that conforms apart from what the test adds: full control
    plane, current agent files, and the agent workspace already present, so a
    conform plan holds only what the test put there."""
    project = make_project(drive, name, sections=SECTIONS,
                           files={**CONTROL_PLANE, **agent_files(drive), **(files or {})})
    for rel in (".agent/runs", ".agent/backups", *dirs):
        (project / rel).mkdir(parents=True, exist_ok=True)
    return project


def report_for(drive, name, *, deep=False):
    inventory = scan_drive(drive)
    inv = next(p for p in inventory.projects if p.name == name)
    m = inventory.map
    if not deep:
        return report_project(inv, m), inv, m
    scan = scan_deep(inv.path, m)
    return report_project(inv, m, receipts=scan.hits,
                          deep_unreadable=scan.unreadable), inv, m


# ------------------------------------------------------------------ the map


def test_receipt_rules_load_in_order_and_normalise_extensions(fixture_drive):
    m = with_receipt_rules(
        fixture_drive,
        {"name": "Zips", "target": ".agent/runs",
         "match": {"extensions": [".ZIP"], "names": "run-*"}},
        LOGS,
    )

    assert m.receipt_rules == (
        ReceiptRule(name="Zips", target=".agent/runs",
                    extensions=("zip",), names=("run-*",)),
        ReceiptRule(name="Logs", target=".agent/backups", name_regex=r"\.log$"),
    )


def test_a_map_without_receipt_rules_loads_unchanged(fixture_drive):
    m = load_map(find_map(fixture_drive))

    assert m.receipt_rules == ()
    assert not hasattr(m, "receiptRules")


def test_a_target_may_be_the_workspace_or_below_it(fixture_drive):
    m = with_receipt_rules(
        fixture_drive,
        {"name": "Deep", "target": ".agent/runs/receipts", "match": {"extensions": ["zip"]}},
        {"name": "Backups", "target": ".agent/backups", "match": {"names": ["*.bak"]}},
    )

    assert [r.target for r in m.receipt_rules] == [".agent/runs/receipts", ".agent/backups"]


@pytest.mark.parametrize(
    ("rules", "complaint"),
    [
        ({"not": "a list"}, "receiptRules"),
        ([{"target": ".agent/runs", "match": {"extensions": ["zip"]}}], "name"),
        ([{"name": "No home", "match": {"extensions": ["zip"]}}], "target"),
        ([{"name": "Everything", "target": ".agent/runs", "match": {}}], "match"),
        ([{"name": "Typo", "target": ".agent/runs", "match": {"extension": ["zip"]}}], "extension"),
        ([{"name": "Bad regex", "target": ".agent/runs", "match": {"nameRegex": "("}}], "nameRegex"),
        ([{"name": "Escape", "target": "../Elsewhere", "match": {"extensions": ["zip"]}}], "target"),
        ([{"name": "Absolute", "target": "C:/Windows", "match": {"extensions": ["zip"]}}], "target"),
        ([{"name": "Numbers", "target": ".agent/runs", "match": {"extensions": [1]}}], "extensions"),
        ([{"name": "Nothing", "target": ".agent/runs", "match": {"names": []}}], "names"),
    ],
)
def test_a_malformed_receipt_rule_refuses_to_load(fixture_drive, rules, complaint):
    """The ADR 0009 discipline holds below the root too: fail closed."""
    data = copy.deepcopy(FIXTURE_MAP)
    data["controlPlane"].update(WORKSPACE)
    data["receiptRules"] = rules
    write_map(fixture_drive, data)

    with pytest.raises(MapError, match=complaint):
        load_map(find_map(fixture_drive))


def test_a_content_filter_below_the_root_refuses_the_map(fixture_drive):
    """No content filters at depth: a pdfText test there is a download per
    candidate with no enumeration gate in front of it (ticket 26)."""
    data = copy.deepcopy(FIXTURE_MAP)
    data["controlPlane"].update(WORKSPACE)
    data["receiptRules"] = [
        {"name": "Greedy", "target": ".agent/runs",
         "match": {"extensions": ["pdf"], "pdfText": ["run receipt"]}},
    ]
    write_map(fixture_drive, data)

    with pytest.raises(MapError, match="content"):
        load_map(find_map(fixture_drive))


def test_a_target_outside_the_agent_workspace_refuses_the_map(fixture_drive):
    """The fence that makes the class safe to opt into: a Receipt Rule can move
    machine receipts out of the numbered tree, never reorder a person's filing."""
    data = copy.deepcopy(FIXTURE_MAP)
    data["controlPlane"].update(WORKSPACE)
    data["receiptRules"] = [
        {"name": "Overreach", "target": "08 OUT/Transmittals",
         "match": {"extensions": ["pdf"]}},
    ]
    write_map(fixture_drive, data)

    with pytest.raises(MapError, match="workspace"):
        load_map(find_map(fixture_drive))


def test_receipt_rules_need_an_agent_workspace_in_the_map(fixture_drive):
    data = copy.deepcopy(FIXTURE_MAP)   # FIXTURE_MAP names no runsDir/backupsDir
    data["receiptRules"] = [ZIPS]
    write_map(fixture_drive, data)

    with pytest.raises(MapError, match="workspace"):
        load_map(find_map(fixture_drive))


# ------------------------------------------------------------- the deep pass


def test_a_receipt_below_the_root_is_found_by_name(fixture_drive):
    with_receipt_rules(fixture_drive, ZIPS)
    project = project_with(fixture_drive, "260930_Deep",
                           {"06 Research/notes.zip": "z", "06 Research/Code/keep.py": "p"})

    scan = scan_deep(project, load_map(find_map(fixture_drive)))

    assert scan.hits == (ReceiptHit(path="06 Research/notes.zip",
                                    target=".agent/runs", rule="Run zips"),)


def test_the_default_doctor_pass_reports_none_of_it(fixture_drive, capsys):
    """The default pass is root-only and its cost bound is unchanged: a receipt
    in a numbered section is invisible until --deep is asked for."""
    with_receipt_rules(fixture_drive, ZIPS)
    project_with(fixture_drive, "260931_Default", {"06 Research/notes.zip": "z"})

    report, _inv, _m = report_for(fixture_drive, "260931_Default")
    assert report.receipts == ()
    assert report.status == "conform"

    assert main(["doctor", "--drive", str(fixture_drive)]) == 0
    assert "notes.zip" not in capsys.readouterr().out


def test_root_files_are_not_receipts(fixture_drive):
    """The root is File Rules' ground. A receipt rule never fires there."""
    with_receipt_rules(fixture_drive, ZIPS)
    project_with(fixture_drive, "260932_Root", {"at-root.zip": "z"})

    report, _inv, _m = report_for(fixture_drive, "260932_Root", deep=True)

    assert report.receipts == ()
    assert "at-root.zip" in report.unfiled


def test_the_agent_workspace_is_never_swept(fixture_drive):
    """Files already in runsDir/backupsDir are where receipts belong; the walk
    does not descend into the workspace, and never reports from it."""
    with_receipt_rules(fixture_drive, ZIPS)
    project_with(fixture_drive, "260933_Workspace", {
        ".agent/runs/done.zip": "z",
        ".agent/backups/kept.zip": "z",
        ".agent/runs/nested/deep.zip": "z",
        "06 Research/stray.zip": "z",
    })

    report, _inv, _m = report_for(fixture_drive, "260933_Workspace", deep=True)

    assert [h.path for h in report.receipts] == ["06 Research/stray.zip"]


def test_the_first_matching_receipt_rule_wins(fixture_drive):
    with_receipt_rules(
        fixture_drive,
        {"name": "Named", "target": ".agent/backups", "match": {"names": ["run-*"]}},
        ZIPS,
    )
    project_with(fixture_drive, "260934_Order", {"01 Model/run-9.zip": "z"})

    report, _inv, _m = report_for(fixture_drive, "260934_Order", deep=True)

    assert report.receipts == (ReceiptHit(path="01 Model/run-9.zip",
                                          target=".agent/backups", rule="Named"),)


def test_receipts_are_findings_not_filing_states(fixture_drive):
    """Containment (ADR 0007) is untouched: the matched file is still Mapped in
    the tree and earns no repair key - the finding lives on doctor/conform."""
    with_receipt_rules(fixture_drive, ZIPS)
    project_with(fixture_drive, "260935_Contained", {"06 Research/notes.zip": "z"})
    report, inv, m = report_for(fixture_drive, "260935_Contained", deep=True)

    tree = open_project_tree(inv, m, report_project(inv, m))

    assert tree.filing_state("06 Research/notes.zip") == MAPPED
    assert report.receipts  # the finding exists beside the state, never as it


def test_a_deep_unreadable_folder_is_reported_never_empty(fixture_drive, monkeypatch):
    """ADR 0004 at depth: a folder the walk cannot open is a finding, not a
    silent absence."""
    import os
    with_receipt_rules(fixture_drive, ZIPS)
    project_with(fixture_drive, "260936_Denied", {"06 Research/Code/.keep": ""})
    real_scandir = os.scandir

    def scandir(path):
        if str(path).endswith("Code"):
            raise PermissionError(13, "Access is denied", str(path))
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", scandir)

    report, _inv, _m = report_for(fixture_drive, "260936_Denied", deep=True)

    # Their own finding since plan 1.5, never bundled with the root list.
    assert any("06 Research/Code" in line for line in report.deep_unreadable)
    assert report.unreadable == ()
    assert report.status == "unfiled"


@pytest.mark.skipif(sys.platform != "win32", reason="NTFS junctions")
def test_the_deep_pass_never_descends_into_a_junction(fixture_drive, tmp_path):
    import _winapi
    with_receipt_rules(fixture_drive, ZIPS)
    project = project_with(fixture_drive, "260937_Link")
    elsewhere = tmp_path / "ELSEWHERE"
    elsewhere.mkdir()
    (elsewhere / "off-drive.zip").write_text("z", encoding="utf-8")
    _winapi.CreateJunction(str(elsewhere), str(project / "06 Research" / "Linked"))

    scan = scan_deep(project, load_map(find_map(fixture_drive)))

    assert scan.hits == ()
    assert (elsewhere / "off-drive.zip").is_file()


# ------------------------------------------------------------------ doctor


def test_doctor_deep_reports_the_receipt_and_names_the_rule(fixture_drive, capsys):
    with_receipt_rules(fixture_drive, ZIPS)
    project_with(fixture_drive, "260938_Doctor", {"06 Research/notes.zip": "z"})

    assert main(["doctor", "--drive", str(fixture_drive), "--deep", "260938_Doctor"]) == 1
    text = capsys.readouterr().out
    assert "sweep pending (deep): 06 Research/notes.zip -> .agent/runs (rule: Run zips)" in text


def test_doctor_deep_json_marks_the_sweep_deep(fixture_drive, capsys):
    with_receipt_rules(fixture_drive, ZIPS)
    project_with(fixture_drive, "260939_Json", {"06 Research/notes.zip": "z"})

    assert main(["doctor", "--drive", str(fixture_drive), "--deep", "260939_Json",
                 "--json"]) == 1
    (proj,) = json.loads(capsys.readouterr().out)["projects"]
    assert proj["receipts"] == [
        {"file": "06 Research/notes.zip", "target": ".agent/runs",
         "rule": "Run zips", "deep": True},
    ]
    assert proj["sweeps"] == []


def test_doctor_deep_all_pays_the_whole_drive_by_flag(fixture_drive, capsys):
    with_receipt_rules(fixture_drive, ZIPS)
    project_with(fixture_drive, "260940_First", {"06 Research/a.zip": "z"})
    project_with(fixture_drive, "260941_Second", {"01 Model/b.zip": "z"})

    assert main(["doctor", "--drive", str(fixture_drive), "--deep", "--all"]) == 1
    text = capsys.readouterr().out
    assert "sweep pending (deep): 06 Research/a.zip -> .agent/runs (rule: Run zips)" in text
    assert "sweep pending (deep): 01 Model/b.zip -> .agent/runs (rule: Run zips)" in text


def test_doctor_deep_needs_a_project_or_all(fixture_drive, capsys):
    assert main(["doctor", "--drive", str(fixture_drive), "--deep"]) == 2
    assert "deep" in capsys.readouterr().err


def test_doctor_deep_refuses_an_unknown_project(fixture_drive, capsys):
    assert main(["doctor", "--drive", str(fixture_drive), "--deep", "260999_Ghost"]) == 2


# ------------------------------------------------------------------ conform


def test_conform_deep_plans_a_sweep_and_dry_run_moves_nothing(fixture_drive, capsys):
    with_receipt_rules(fixture_drive, ZIPS)
    project = project_with(fixture_drive, "260942_Plan", {"06 Research/notes.zip": "z"})

    assert main(["conform", "--drive", str(fixture_drive), "--project", "260942_Plan",
                 "--deep"]) == 1
    text = capsys.readouterr().out
    assert "sweep     06 Research/notes.zip -> .agent/runs" in text
    assert "dry run" in text
    assert (project / "06 Research" / "notes.zip").is_file()


def test_conform_without_deep_leaves_receipts_alone(fixture_drive, capsys):
    with_receipt_rules(fixture_drive, ZIPS)
    project = project_with(fixture_drive, "260943_Shallow", {"06 Research/notes.zip": "z"})

    assert main(["conform", "--drive", str(fixture_drive), "--project",
                 "260943_Shallow"]) == 0
    assert (project / "06 Research" / "notes.zip").is_file()


def test_conform_deep_sweeps_and_revert_restores_the_nested_path(fixture_drive, capsys, tmp_path):
    """The whole existing path, unchanged: plan, apply, Move Manifest, undo."""
    with_receipt_rules(fixture_drive, ZIPS)
    project = project_with(fixture_drive, "260944_Apply", {"06 Research/notes.zip": "z"})

    assert main(["conform", "--drive", str(fixture_drive), "--project", "260944_Apply",
                 "--deep", "--apply", "--json"]) == 0
    assert not (project / "06 Research" / "notes.zip").exists()
    assert (project / ".agent" / "runs" / "notes.zip").is_file()

    manifest = tmp_path / "applied.json"
    manifest.write_text(capsys.readouterr().out, encoding="utf-8")
    assert main(["conform", "--drive", str(fixture_drive), "--revert", str(manifest),
                 "--apply"]) == 0
    assert (project / "06 Research" / "notes.zip").is_file()
    assert not (project / ".agent" / "runs" / "notes.zip").exists()


def test_a_name_collision_at_the_target_is_a_conflict_not_a_clobber(fixture_drive):
    with_receipt_rules(fixture_drive, ZIPS)
    project = project_with(fixture_drive, "260945_Clash", {"06 Research/notes.zip": "new"})
    (project / ".agent" / "runs" / "notes.zip").write_text("old", encoding="utf-8")
    report, inv, m = report_for(fixture_drive, "260945_Clash", deep=True)

    applied = apply_plan(fixture_drive, inv.path, m, build_plan(report, m, project=inv.path))

    (sweep,) = [a for a in applied.actions if a.kind == SWEEP]
    assert sweep.status == CONFLICT
    assert (project / "06 Research" / "notes.zip").read_text(encoding="utf-8") == "new"
    assert (project / ".agent" / "runs" / "notes.zip").read_text(encoding="utf-8") == "old"


def test_conform_deep_all_sweeps_every_project(fixture_drive, capsys):
    with_receipt_rules(fixture_drive, ZIPS)
    one = project_with(fixture_drive, "260946_AllA", {"06 Research/a.zip": "z"})
    two = project_with(fixture_drive, "260947_AllB", {"01 Model/b.zip": "z"})

    assert main(["conform", "--drive", str(fixture_drive), "--all", "--deep",
                 "--apply"]) == 0
    assert (one / ".agent" / "runs" / "a.zip").is_file()
    assert (two / ".agent" / "runs" / "b.zip").is_file()


def test_conform_deep_rejects_node_and_revert(fixture_drive, capsys, tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text("[]", encoding="utf-8")

    assert main(["conform", "--drive", str(fixture_drive), "--project", "x",
                 "--node", "06 Research", "--deep"]) == 2
    assert main(["conform", "--drive", str(fixture_drive), "--revert", str(manifest),
                 "--deep"]) == 2


# --------------------------------------------------------------------- lint


def _codes(m):
    return {(f.level, f.code) for f in lint_map(m)}


def test_lint_is_clean_for_receipt_rules_in_the_workspace(fixture_drive):
    m = with_receipt_rules(fixture_drive, ZIPS, LOGS)

    assert not {code for _l, code in _codes(m) if code.startswith("RECEIPT-RULE")}


def test_lint_warns_when_two_receipt_rules_share_a_name(fixture_drive):
    """Doctor names the rule behind each deep finding; two rules with one name
    make that report ambiguous."""
    m = with_receipt_rules(fixture_drive, ZIPS,
                           {**ZIPS, "match": {"extensions": ["7z"]}})

    assert ("warn", "RECEIPT-RULE-DUP-NAME") in _codes(m)
