"""Atlas scaffolds a seat-ready job folder (Pyvoid #1545, PRD-220 REQ-022..024).

Two halves:

- PROJECT.md carries a blank, Pyvoid-owned `revit:` block of exactly six bare
  keys, inside the front matter, under the UTF-8 / no-BOM / CRLF byte contract.
- With the map's `controlPlane.mcpFile` set and this machine's Pyvoid
  `mcp_server` path set (ATLAS_PYVOID_MCP_SERVER), Atlas writes an UNPINNED
  dossier-pointer `.mcp.json`: `env` holds exactly PYVOID_PROJECT_DOSSIER, and
  PYVOID_FLEET_PROJECT is absent - never "". Unset, Atlas skips the file and
  says so (Tyler, 2026-10-07). A per-machine setting, never a map key.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.conform import CONFLICT, DONE, SKIPPED, apply_plan, build_plan
from atlas.core.doctor import report_project
from atlas.core.lintmap import lint_map
from atlas.core.mapfile import find_map, load_map
from atlas.core.mcpjson import MCP_SERVER_ENV, SERVER_NAME
from atlas.core.ops import new_project
from atlas.core.project_data import load_project_record
from atlas.core.scan import scan_drive

from conftest import FIXTURE_MAP, make_intake, make_project, write_map

REVIT_KEYS = ("model", "local", "version", "worksets", "sheet_collection", "library_containers")
REVIT_BLOCK = b"\r\nrevit:\r\n" + b"".join(b"  " + k.encode() + b":\r\n" for k in REVIT_KEYS)


def _seat_map(drive: Path, **control) -> object:
    data = copy.deepcopy(FIXTURE_MAP)
    data["controlPlane"].update({"mcpFile": ".mcp.json", **control})
    write_map(drive, data)
    return load_map(find_map(drive))


@pytest.fixture
def mcp_server(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "machine" / "Pyvoid" / "mcp_server"
    path.mkdir(parents=True)
    monkeypatch.setenv(MCP_SERVER_ENV, str(path))
    return path


def _front_matter(raw: bytes) -> list[str]:
    lines = raw.decode("utf-8").split("\r\n")
    return lines[1:lines.index("---", 1)]


def _revit_block(front: list[str]) -> dict[str, str]:
    start = front.index("revit:")
    block: dict[str, str] = {}
    for line in front[start + 1:]:
        if not line.startswith("  "):
            break
        key, _, value = line.strip().partition(":")
        block[key] = value
    return block


def _server(project: Path) -> dict:
    return json.loads((project / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"][SERVER_NAME]


# ---- PROJECT.md: the blank revit block --------------------------------------

def test_new_project_md_carries_the_blank_six_key_revit_block(fixture_drive):
    m = load_map(find_map(fixture_drive))
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Revit House"))
    raw = (result.path / "PROJECT.md").read_bytes()

    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\n" not in raw.replace(b"\r\n", b"")
    assert raw.endswith(b"\r\n")
    assert REVIT_BLOCK in raw

    front = _front_matter(raw)
    block = _revit_block(front)
    assert tuple(block) == REVIT_KEYS
    assert all(value == "" for value in block.values())   # bare keys: blank means unknown
    assert front.count("revit:") == 1
    assert not any("#" in line for line in front[front.index("revit:"):front.index("revit:") + 7])


def test_atlas_still_reads_and_edits_a_dossier_carrying_the_revit_block(fixture_drive):
    m = load_map(find_map(fixture_drive))
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Readable"))
    record = load_project_record(result.path, project_file=m.project_file)
    assert record.intake.project_name == "Readable"


def test_conform_stub_carries_the_same_revit_block(fixture_drive):
    m = load_map(find_map(fixture_drive))
    project = make_project(fixture_drive, "260402_Stub Job", sections=["01 Model"])
    inventory = scan_drive(fixture_drive)
    inv = next(p for p in inventory.projects if p.name == project.name)
    apply_plan(fixture_drive, inv.path, m, build_plan(report_project(inv, m), m, project=inv.path))
    raw = (project / "PROJECT.md").read_bytes()
    assert REVIT_BLOCK in raw
    assert tuple(_revit_block(_front_matter(raw))) == REVIT_KEYS


REPO = Path(__file__).resolve().parents[3]


def test_dossier_key_table_lists_the_six_pyvoid_owned_keys():
    skill = (REPO / "plugins" / "09-project-dossier" / "skills" / "project-dossier"
             / "SKILL.md").read_text(encoding="utf-8")
    row = next(line for line in skill.splitlines() if line.startswith("| `revit` |"))
    for key in REVIT_KEYS:
        assert f"`{key}`" in row, key
    assert "Pyvoid-owned" in row and "not Atlas-owned" in row
    # The skill's own template carries the same blank block.
    template = skill.split("## Template", 1)[1]
    assert "\nrevit:\n" + "".join(f"  {k}:\n" for k in REVIT_KEYS) in template.replace("\r\n", "\n")


def test_adr_0001_addendum_names_prd_220_and_the_owning_repo():
    adr = (REPO / "docs" / "adr" / "0001-project-md-shared-front-matter-machine-contract.md"
           ).read_text(encoding="utf-8")
    addendum = adr.split("## Addendum - the `revit:` block is Pyvoid-owned", 1)[1]
    assert "PRD-220" in addendum
    assert "owning repo is **Pyvoid** (`tyler-figureground/Pyvoid`)" in addendum
    for key in REVIT_KEYS:
        assert f"`{key}`" in addendum, key


# ---- the map key -------------------------------------------------------------

def test_map_lint_accepts_mcp_file(fixture_drive):
    m = _seat_map(fixture_drive)
    assert m.control_plane["mcpFile"] == ".mcp.json"
    assert m.mcp_file == ".mcp.json"
    assert not [f for f in lint_map(m) if f.level == "error"]


@pytest.mark.parametrize("bad", ["sub/.mcp.json", "../.mcp.json", "C:/x/.mcp.json", "mcp.txt"])
def test_map_lint_refuses_an_mcp_file_that_is_not_a_root_json_file(fixture_drive, bad):
    m = _seat_map(fixture_drive, mcpFile=bad)
    assert "MCP-FILE" in {f.code for f in lint_map(m) if f.level == "error"}


def test_no_mcp_file_in_the_map_means_no_mcp_json(fixture_drive, mcp_server):
    m = load_map(find_map(fixture_drive))
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "No Key"))
    assert not (result.path / ".mcp.json").exists()


# ---- new_project: the unpinned dossier pointer ------------------------------

def test_new_project_writes_the_unpinned_dossier_pointer(fixture_drive, mcp_server):
    m = _seat_map(fixture_drive)
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Seat Ready"))
    server = _server(result.path)
    env = server["env"]

    assert "PYVOID_FLEET_PROJECT" not in env
    assert env["PYVOID_PROJECT_DOSSIER"] == result.path.as_posix()
    assert Path(env["PYVOID_PROJECT_DOSSIER"]) == result.path
    assert len(env) == 1
    assert server["command"] == "uv"
    assert server["args"] == ["run", "--directory", mcp_server.as_posix(), "python", "-m", "pyvoid_mcp"]
    assert server["cwd"] == mcp_server.as_posix()
    assert result.mcp.status == DONE
    raw = (result.path / ".mcp.json").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")


def test_new_project_skips_and_reports_when_the_machine_setting_is_unset(fixture_drive, monkeypatch):
    monkeypatch.delenv(MCP_SERVER_ENV, raising=False)
    m = _seat_map(fixture_drive)
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Unset Machine"))
    assert not (result.path / ".mcp.json").exists()
    assert result.mcp.status == SKIPPED
    assert MCP_SERVER_ENV in result.mcp.note


def test_new_project_skips_a_setting_that_is_not_a_folder(fixture_drive, monkeypatch, tmp_path):
    monkeypatch.setenv(MCP_SERVER_ENV, str(tmp_path / "nowhere"))
    m = _seat_map(fixture_drive)
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Bad Setting"))
    assert not (result.path / ".mcp.json").exists()
    assert result.mcp.status == SKIPPED and "not a folder" in result.mcp.note


def test_fresh_seat_ready_project_is_conform(fixture_drive, mcp_server):
    m = _seat_map(fixture_drive)
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Clean Seat"))
    inventory = scan_drive(fixture_drive)
    inv = next(p for p in inventory.projects if p.name == result.folder_name)
    report = report_project(inv, m)
    assert report.status == "conform", (report.missing_control_plane, report.unfiled)


def test_cli_new_reports_the_skip(fixture_drive, monkeypatch, capsys):
    monkeypatch.delenv(MCP_SERVER_ENV, raising=False)
    _seat_map(fixture_drive)
    contact_id = make_intake(fixture_drive, "Cli Seat").billing_contact_id
    assert main(["new", "--drive", str(fixture_drive), "--name", "Cli Seat",
                 "--street", "9 Elm Street", "--city", "Oakland", "--state", "CA",
                 "--zip", "94612", "--use-case", "Renovation",
                 "--billing-contact", contact_id, "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["mcp"]["status"] == SKIPPED
    assert MCP_SERVER_ENV in out["mcp"]["note"]


# ---- conform: the same pointer, for #1546's backfill -------------------------

def _conform(drive: Path, m, name: str):
    inventory = scan_drive(drive)
    inv = next(p for p in inventory.projects if p.name == name)
    report = report_project(inv, m)
    plan = build_plan(report, m, project=inv.path)
    return report, plan, apply_plan(drive, inv.path, m, plan)


def _action(plan, dst=".mcp.json"):
    return next(a for a in plan.actions if a.dst == dst)


def test_conform_adds_the_pointer_and_keeps_unrelated_servers(fixture_drive, mcp_server):
    m = _seat_map(fixture_drive)
    other = {"command": "node", "args": ["server.js"], "env": {"TOKEN_FILE": "x"}}
    existing = {"mcpServers": {"other-tool": other}, "theme": "dark"}
    project = make_project(fixture_drive, "260403_Has Mcp", sections=["01 Model"],
                           files={".mcp.json": json.dumps(existing)})
    report, _plan, applied = _conform(fixture_drive, m, project.name)
    assert ".mcp.json" in report.missing_control_plane
    assert _action(applied).status == DONE

    document = json.loads((project / ".mcp.json").read_text(encoding="utf-8"))
    assert document["mcpServers"]["other-tool"] == other
    assert document["theme"] == "dark"
    env = document["mcpServers"][SERVER_NAME]["env"]
    assert env == {"PYVOID_PROJECT_DOSSIER": project.as_posix()}


def test_conform_keeps_unicode_line_separators_inside_existing_values(fixture_drive, mcp_server):
    """Only JSON's structural newlines become CRLF: a U+2028 inside a kept
    string value must not split that string and corrupt the file."""
    m = _seat_map(fixture_drive)
    other = {"command": "node", "env": {"NOTE": "a b c\x85d"}}
    project = make_project(fixture_drive, "260408_Unicode Mcp", sections=["01 Model"],
                           files={".mcp.json": json.dumps({"mcpServers": {"other-tool": other}})})
    _report, _plan, applied = _conform(fixture_drive, m, project.name)
    assert _action(applied).status == DONE
    raw = (project / ".mcp.json").read_bytes()
    assert raw.count(b"\n") == raw.count(b"\r\n")
    document = json.loads(raw.decode("utf-8"))
    assert document["mcpServers"]["other-tool"] == other


def test_conform_never_touches_an_existing_pyvoid_entry(fixture_drive, mcp_server):
    """A pinned block `pyvoid-fleet ensure` wrote is not Atlas's to unpin."""
    m = _seat_map(fixture_drive)
    pinned = {"mcpServers": {SERVER_NAME: {"command": "uv", "args": [],
                                           "env": {"PYVOID_FLEET_PROJECT": "k"}}}}
    text = json.dumps(pinned)
    project = make_project(fixture_drive, "260404_Pinned", sections=["01 Model"],
                           files={".mcp.json": text})
    report, _plan, _applied = _conform(fixture_drive, m, project.name)
    assert ".mcp.json" not in report.missing_control_plane
    assert (project / ".mcp.json").read_text(encoding="utf-8") == text


def test_conform_leaves_unparseable_mcp_json_as_a_conflict(fixture_drive, mcp_server):
    m = _seat_map(fixture_drive)
    project = make_project(fixture_drive, "260405_Broken Mcp", sections=["01 Model"],
                           files={".mcp.json": "{not json"})
    _report, _plan, applied = _conform(fixture_drive, m, project.name)
    assert _action(applied).status == CONFLICT
    assert (project / ".mcp.json").read_text(encoding="utf-8") == "{not json"


def test_conform_plan_and_apply_report_the_skip_when_unset(fixture_drive, monkeypatch):
    monkeypatch.delenv(MCP_SERVER_ENV, raising=False)
    m = _seat_map(fixture_drive)
    project = make_project(fixture_drive, "260406_Unset", sections=["01 Model"])
    _report, plan, applied = _conform(fixture_drive, m, project.name)
    assert MCP_SERVER_ENV in _action(plan).note          # the dry run says so
    action = _action(applied)
    assert action.status == SKIPPED and MCP_SERVER_ENV in action.note
    assert not (project / ".mcp.json").exists()


def test_mcp_json_is_never_unfiled(fixture_drive, mcp_server):
    m = _seat_map(fixture_drive)
    project = make_project(fixture_drive, "260407_Filed", sections=["01 Model"],
                           files={".mcp.json": json.dumps({"mcpServers": {}})})
    inventory = scan_drive(fixture_drive)
    inv = next(p for p in inventory.projects if p.name == project.name)
    assert ".mcp.json" not in report_project(inv, m).unfiled
