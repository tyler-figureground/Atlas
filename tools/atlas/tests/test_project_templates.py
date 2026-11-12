"""Map v3: seeded children, template files, the agent workspace, and `atlas runs`.

ADRs 0011 (agent workspace) and 0012 (project templates). Uses the real bundled
templates, so a template edit that breaks a placeholder or the rules block fails
here first.
"""

from __future__ import annotations

import copy
import json
import os
import time
import zipfile
from datetime import date

import pytest

from atlas.cli import main
from atlas.core.conform import apply_plan, build_plan
from atlas.core.doctor import report_project
from atlas.core.lintmap import ERROR, lint_map
from atlas.core.mapfile import MapError, find_map, load_map
from atlas.core.ops import find_empty_dirs, new_project
from atlas.core.projectmd import agents_block_current
from atlas.core.runs import archive_run, list_runs
from atlas.core.scan import ProjectInventory, list_entries
from atlas.core.templates import read_template, render, template_dir

from conftest import FIXTURE_MAP, make_intake, make_project, write_map

V3_MAP = copy.deepcopy(FIXTURE_MAP)
V3_MAP["version"] = "3.0"
V3_MAP["controlPlane"].update({
    "runsDir": ".agent/runs",
    "backupsDir": ".agent/backups",
    "archiveDir": ".agent/archive",
    "runRetentionDays": 14,
    "agentsRules": "agents-rules.md",
})
V3_MAP["sections"] = [
    {"id": "00 Tasks", "seed": True, "children": [
        {"name": "Archive", "seed": True}]},
    *V3_MAP["sections"],
    {"id": "13 AHJ", "seed": True, "children": [
        {"name": "01 Requirements & Pre-Application", "seed": True},
        {"name": "03 Submissions", "seed": True},
        "07 Not Seeded"]},
]
V3_MAP["templates"] = [
    {"path": "00 Tasks/TASKS.md", "template": "TASKS.md", "index": "Live task list"},
    {"path": "13 AHJ/AHJ-REGISTER.md", "template": "AHJ-REGISTER.md", "index": "AHJ register"},
    {"path": ".agent/runs/_RUN-TEMPLATE.md", "template": "RUN-TEMPLATE.md"},
]


@pytest.fixture
def v3_drive(fixture_drive):
    write_map(fixture_drive, V3_MAP)
    return fixture_drive


def _load(drive):
    return load_map(find_map(drive))


def _report(project, m):
    inv = ProjectInventory(path=project, name=project.name, root_entries=list_entries(project))
    return report_project(inv, m)


# ---------------------------------------------------------------- map schema

def test_child_objects_load_as_names_with_seed_flags(v3_drive):
    m = _load(v3_drive)
    ahj = m.section("13 AHJ")
    assert ahj.children == ("01 Requirements & Pre-Application", "03 Submissions", "07 Not Seeded")
    assert ahj.seed_children == ("01 Requirements & Pre-Application", "03 Submissions")
    assert "13 AHJ/03 Submissions" in m.seed_child_paths()
    assert "13 AHJ/07 Not Seeded" not in m.seed_child_paths()
    assert m.agent_dirs == (".agent/handoff", ".agent/runs", ".agent/backups", ".agent/archive")
    assert m.run_retention_days == 14


def test_a_v2_map_still_loads_unchanged(fixture_drive):
    m = _load(fixture_drive)
    assert m.templates == ()
    assert all(s.seed_children == () for s in m.sections)
    assert m.runs_dir == "" and m.agents_rules == ""


@pytest.mark.parametrize("bad_child", [{"seed": True}, {"name": "X", "colour": "red"}, 7])
def test_malformed_child_refuses_the_map(fixture_drive, bad_child):
    data = copy.deepcopy(V3_MAP)
    data["sections"][0]["children"] = [bad_child]
    write_map(fixture_drive, data)
    with pytest.raises(MapError):
        _load(fixture_drive)


@pytest.mark.parametrize("bad_template", [
    {"path": "00 Tasks/TASKS.md"},
    {"path": "../outside.md", "template": "TASKS.md"},
    {"path": "00 Tasks/TASKS.md", "template": "sub/TASKS.md"},
    {"path": "00 Tasks/TASKS.md", "template": "TASKS.md", "extra": 1},
])
def test_malformed_template_refuses_the_map(fixture_drive, bad_template):
    data = copy.deepcopy(V3_MAP)
    data["templates"] = [bad_template]
    write_map(fixture_drive, data)
    with pytest.raises(MapError):
        _load(fixture_drive)


def test_the_same_template_path_twice_refuses_the_map(fixture_drive):
    data = copy.deepcopy(V3_MAP)
    data["templates"] = [data["templates"][0], dict(data["templates"][0])]
    write_map(fixture_drive, data)
    with pytest.raises(MapError, match="twice"):
        _load(fixture_drive)


# ---------------------------------------------------------------- templates

def test_tasks_template_sweeps_the_set_before_every_issue():
    text = read_template("TASKS.md")
    assert "**Issuing a drawing set**" in text   # Atlas #19, Pyvoid #4840
    assert "`/jdp set sweep`" in text


def test_every_bundled_template_renders_without_leftover_placeholders():
    values = {"project_folder": "261002_1 Main St-Test", "project_name": "Test", "created": "2026-10-02"}
    names = sorted(p.name for p in template_dir().iterdir() if p.suffix == ".md")
    assert "Task List Template.md" not in names   # ADR 0023: one task file
    assert {"TASKS.md", "AHJ-REGISTER.md", "RESEARCH-INDEX.md",
            "RUN-TEMPLATE.md", "agents-rules.md", "INTAKE.md", "BRIEF.md",
            "CORRESPONDENCE-README.md"} <= set(names)
    for name in names:
        text = "\n".join(render(read_template(name), values))
        assert "{{" not in text, name


def test_render_leaves_unknown_placeholders_visible():
    assert render("{{project_name}} {{typo}}", {"project_name": "A"}) == ["A {{typo}}"]


# ---------------------------------------------------------------- new project

def test_new_project_seeds_children_templates_and_agent_workspace(v3_drive):
    m = _load(v3_drive)
    result = new_project(v3_drive, m, make_intake(v3_drive, "Fire House", "Demo",
                                                  street="295 West Lane",
                                                  created=date(2026, 10, 2)))
    project = result.path
    for rel in ("00 Tasks/Archive", "13 AHJ/01 Requirements & Pre-Application",
                "13 AHJ/03 Submissions", ".agent/runs", ".agent/backups", ".agent/archive",
                ".agent/handoff"):
        assert (project / rel).is_dir(), rel
    assert not (project / "13 AHJ/07 Not Seeded").exists()
    tasks = (project / "00 Tasks/TASKS.md").read_bytes()
    assert not tasks.startswith(b"\xef\xbb\xbf") and b"\r\n" in tasks
    text = tasks.decode("utf-8")
    assert "# Tasks - Fire House" in text
    assert result.folder_name in text and "updated: 2026-10-02" in text
    assert (project / "13 AHJ/AHJ-REGISTER.md").read_text(encoding="utf-8").startswith("# AHJ register - Fire House")
    agents = (project / "AGENTS.md").read_text(encoding="utf-8")
    assert "## Where agent work goes" in agents
    assert "| Live task list | `00 Tasks/TASKS.md` |" in agents
    assert "`.agent/runs/`" in agents
    assert "_Task List Template.md" not in agents and "00 Tasks/Lists" not in agents
    assert "No other task lists or prompt files anywhere" in agents
    assert agents_block_current(agents, m)
    report = _report(project, m)
    assert report.missing_control_plane == () and report.unfiled == ()


def test_clean_keeps_seeded_children_and_the_agent_workspace(v3_drive):
    m = _load(v3_drive)
    project = new_project(v3_drive, m, make_intake(v3_drive, "Clean House")).path
    (project / "13 AHJ/07 Not Seeded").mkdir()
    empties = find_empty_dirs(project, m)
    assert empties == ["13 AHJ/07 Not Seeded"]


def test_missing_template_stops_intake_before_any_folder_exists(v3_drive, monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_TEMPLATES", str(tmp_path / "nowhere"))
    m = _load(v3_drive)
    with pytest.raises(Exception, match="template 'TASKS.md'"):
        new_project(v3_drive, m, make_intake(v3_drive, "No Templates"))
    assert not any(p.name.endswith("No Templates Street") for p in v3_drive.iterdir())


# ---------------------------------------------------------------- conform

def test_conform_backfills_templates_into_an_old_project_and_never_overwrites(v3_drive):
    m = _load(v3_drive)
    project = make_project(v3_drive, "250101_Old House", sections=["01 Model"],
                           files={"13 AHJ/AHJ-REGISTER.md": "# ours\n"})
    report = _report(project, m)
    assert "00 Tasks/TASKS.md" in report.missing_control_plane
    assert "13 AHJ/AHJ-REGISTER.md" not in report.missing_control_plane
    applied = apply_plan(v3_drive, project, m, build_plan(report, m, project))
    by_dst = {a.dst: a for a in applied.actions}
    assert by_dst["00 Tasks/TASKS.md"].status == "done"
    assert "# Tasks - Old House" in (project / "00 Tasks/TASKS.md").read_text(encoding="utf-8")
    assert (project / ".agent/runs/_RUN-TEMPLATE.md").is_file()
    assert (project / "13 AHJ/AHJ-REGISTER.md").read_text(encoding="utf-8") == "# ours\n"
    # One pass: the template made 00 Tasks, and its seeded folders came with it.
    for rel in ("00 Tasks/Archive", "13 AHJ/03 Submissions"):
        assert (project / rel).is_dir(), rel
    assert not (project / "13 AHJ/07 Not Seeded").exists()
    # An absent seeded section with no template stays absent: 11 Meetings.
    assert not (project / "11 Meetings").exists()
    assert _report(project, m).missing_control_plane == ()


INTAKE_ENTRY = {"path": "00 Tasks/INTAKE.md", "template": "INTAKE.md",
                "index": "Day-1 intake questions - send to Tyler before research"}


def test_research_and_asking_reaches_every_new_project(v3_drive):
    # Pyvoid #2899/#2912: intake list, research rule, basis rows and the parked list.
    data = copy.deepcopy(V3_MAP)
    data["templates"].append(INTAKE_ENTRY)
    write_map(v3_drive, data)
    m = _load(v3_drive)
    project = new_project(v3_drive, m, make_intake(v3_drive, "Ask House")).path
    intake = (project / "00 Tasks/INTAKE.md").read_text(encoding="utf-8")
    assert intake.startswith("# Day-1 intake - Ask House")
    assert "12. Sheet list" in intake
    agents = (project / "AGENTS.md").read_text(encoding="utf-8")
    assert "## Research and asking" in agents
    assert "`00 Tasks/INTAKE.md`" in agents
    assert "| Day-1 intake questions - send to Tyler before research | `00 Tasks/INTAKE.md` |" in agents
    assert agents_block_current(agents, m)
    tasks = (project / "00 Tasks/TASKS.md").read_text(encoding="utf-8")
    assert tasks.index("## Holds") < tasks.index("## Parked - outside sheet scope") < tasks.index("## Done")
    assert "## Lists" not in tasks and "00 Tasks/Lists" not in tasks
    assert "indented under its line" in tasks
    project_md = (project / "PROJECT.md").read_text(encoding="utf-8").splitlines()
    assert "basis: []" in project_md
    assert project_md.index("basis: []") < project_md.index("---", 1)


def test_conform_backfills_the_intake_without_overwriting(v3_drive):
    data = copy.deepcopy(V3_MAP)
    data["templates"].append(INTAKE_ENTRY)
    write_map(v3_drive, data)
    m = _load(v3_drive)
    project = make_project(v3_drive, "250101_Intake House", sections=["01 Model"],
                           files={"00 Tasks/TASKS.md": "# ours\n"})
    report = _report(project, m)
    assert "00 Tasks/INTAKE.md" in report.missing_control_plane
    apply_plan(v3_drive, project, m, build_plan(report, m, project))
    assert (project / "00 Tasks/INTAKE.md").read_text(encoding="utf-8").startswith("# Day-1 intake - Intake House")
    assert (project / "00 Tasks/TASKS.md").read_text(encoding="utf-8") == "# ours\n"


def test_seeded_children_of_a_present_section_are_backfilled(v3_drive):
    data = copy.deepcopy(V3_MAP)
    next(s for s in data["sections"] if s["id"] == "06 Research")["children"] = [
        {"name": "Zoning", "seed": True}, "Code"]
    write_map(v3_drive, data)
    m = _load(v3_drive)
    project = make_project(v3_drive, "250101_Research House", sections=["06 Research"])
    assert "06 Research/Zoning" in _report(project, m).missing_control_plane
    apply_plan(v3_drive, project, m, build_plan(_report(project, m), m, project))
    assert (project / "06 Research/Zoning").is_dir()


# ---------------------------------------------------------------- lint

def test_lint_flags_a_missing_template_and_a_target_outside_the_map(v3_drive):
    data = copy.deepcopy(V3_MAP)
    data["templates"] += [{"path": "99 Nowhere/X.md", "template": "TASKS.md"},
                          {"path": "00 Tasks/Y.md", "template": "Nope.md"}]
    write_map(v3_drive, data)
    codes = {(f.level, f.code) for f in lint_map(_load(v3_drive))}
    assert (ERROR, "TEMPLATE-TARGET") in codes
    assert (ERROR, "TEMPLATE-MISSING") in codes


def test_lint_is_clean_for_the_v3_fixture(v3_drive):
    assert [f for f in lint_map(_load(v3_drive)) if f.level == ERROR] == []


# ---------------------------------------------------------------- runs

def _run(project, name, files, age_days):
    folder = project / ".agent/runs" / name
    for rel, body in files.items():
        path = folder / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        stamp = time.time() - age_days * 86400
        os.utime(path, (stamp, stamp))
    return folder


@pytest.fixture
def run_project(v3_drive):
    m = _load(v3_drive)
    project = new_project(v3_drive, m, make_intake(v3_drive, "Run House")).path
    _run(project, "260901-old-audit", {"a.py": "print(1)", "deep/b.json": "{}"}, 20)
    _run(project, "260930-fresh", {"c.json": "{}"}, 2)
    _run(project, "260902-still-cited", {"d.json": "{}"}, 30)
    tasks = project / "00 Tasks/TASKS.md"
    tasks.write_text(tasks.read_text(encoding="utf-8") + "\n- see 260902-still-cited\n", encoding="utf-8")
    return v3_drive, m, project


def test_runs_close_by_idle_days_and_stay_open_while_named(run_project):
    _drive, m, project = run_project
    runs = {r.name: r for r in list_runs(project, m)}
    assert set(runs) == {"260901-old-audit", "260930-fresh", "260902-still-cited"}  # template file is not a run
    assert runs["260901-old-audit"].closed(14)
    assert not runs["260930-fresh"].closed(14)
    assert runs["260902-still-cited"].referenced_by == ("00 Tasks/TASKS.md",)
    assert not runs["260902-still-cited"].closed(14)


def test_archive_zips_verifies_and_removes_the_run(run_project):
    drive, m, project = run_project
    run = next(r for r in list_runs(project, m) if r.name == "260901-old-audit")
    result = archive_run(drive, project, m, run)
    assert result.status == "archived"
    assert not (project / ".agent/runs/260901-old-audit").exists()
    with zipfile.ZipFile(project / ".agent/archive/260901-old-audit.zip") as zf:
        assert sorted(zf.namelist()) == ["260901-old-audit/a.py", "260901-old-audit/deep/b.json"]
        assert zf.read("260901-old-audit/a.py") == b"print(1)"


def test_archive_never_overwrites_an_existing_zip(run_project):
    drive, m, project = run_project
    (project / ".agent/archive/260901-old-audit.zip").write_bytes(b"older")
    run = next(r for r in list_runs(project, m) if r.name == "260901-old-audit")
    assert archive_run(drive, project, m, run).status == "skipped"
    assert (project / ".agent/runs/260901-old-audit/a.py").is_file()
    assert (project / ".agent/archive/260901-old-audit.zip").read_bytes() == b"older"


def test_runs_cli_previews_then_applies(run_project, capsys):
    drive, _m, project = run_project
    assert main(["runs", "--drive", str(drive), "--project", project.name, "--json"]) == 1
    preview = json.loads(capsys.readouterr().out)
    closed = [r["run"] for p in preview["projects"] for r in p["runs"] if r["closed"]]
    assert closed == ["260901-old-audit"] and preview["applied"] is False
    assert (project / ".agent/runs/260901-old-audit").is_dir()
    assert main(["runs", "--drive", str(drive), "--project", project.name, "--apply"]) == 0
    assert "archived" in capsys.readouterr().out
    assert (project / ".agent/archive/260901-old-audit.zip").is_file()
    assert main(["runs", "--drive", str(drive), "--project", project.name]) == 0



def _old_audit(project, m):
    return next(r for r in list_runs(project, m) if r.name == "260901-old-audit")


def test_a_file_dated_before_1980_still_archives(run_project):
    """#58: zipfile refuses pre-1980 timestamps by default; the run crashed
    and left a .zip.partial behind."""
    drive, m, project = run_project
    os.utime(project / ".agent/runs/260901-old-audit/a.py", (0, 0))
    result = archive_run(drive, project, m, _old_audit(project, m))
    assert result.status == "archived", result.note
    assert not list((project / ".agent/archive").glob("*.partial"))
    with zipfile.ZipFile(project / ".agent/archive/260901-old-audit.zip") as zf:
        assert zf.read("260901-old-audit/a.py") == b"print(1)"


@pytest.mark.skipif(os.name != "nt", reason="native Windows long paths")
@pytest.mark.parametrize("long_root", [False, True])
def test_archive_sweeps_long_stale_partials_on_legacy_windows(run_project, monkeypatch, long_root):
    from dataclasses import replace
    from pathlib import Path
    from atlas.core.scan import long_path

    drive, m, project = run_project
    run = _old_audit(project, m)
    if long_root:
        m = replace(m, control_plane={**m.control_plane,
                    "archiveDir": ".agent/archive/" + "a" * 80 + "/" + "b" * 80})
    archive = project / m.archive_dir
    os.makedirs(long_path(archive), exist_ok=True)
    stale = archive / (run.name + ".zip." + "z" * 100 + ".partial")
    fresh = archive / (run.name + ".zip.fresh.partial")
    unrelated = archive / "other.zip.partial"
    for path in (stale, fresh, unrelated):
        Path(long_path(path)).write_bytes(b"keep unless stale and same run")
    old = time.time() - 2 * 86400
    os.utime(long_path(stale), (old, old))
    os.utime(long_path(unrelated), (old, old))
    assert len(str(stale)) >= 260
    real_stat, real_scandir = os.stat, os.scandir

    def legacy(call, path, *args, **kwargs):
        raw = os.fspath(path)
        if not raw.startswith("\\\\?\\") and len(raw) >= 260:
            raise FileNotFoundError(3, "legacy MAX_PATH", raw)
        return call(path, *args, **kwargs)

    monkeypatch.setattr(os, "scandir", lambda path: legacy(real_scandir, path))
    # Restrict the stat injection to cleanup candidates, not archive policy.
    def stat(path, *args, **kwargs):
        if os.fspath(path).endswith(".partial"):
            return legacy(real_stat, path, *args, **kwargs)
        return real_stat(path, *args, **kwargs)
    monkeypatch.setattr(os, "stat", stat)

    if long_root:
        # Cleanup is also safe for an already-existing long archive root;
        # this is not authority to create new archive directories past policy.
        from atlas.core.runs import _sweep_stale_partials
        _sweep_stale_partials(archive, run.name)
    else:
        result = archive_run(drive, project, m, run)
        assert result.status == "archived", result.note
    assert not os.path.exists(long_path(stale))
    assert Path(long_path(fresh)).read_bytes() == b"keep unless stale and same run"
    assert Path(long_path(unrelated)).read_bytes() == b"keep unless stale and same run"
    if not long_root:
        with zipfile.ZipFile(long_path(archive / (run.name + ".zip"))) as zf:
            assert zf.read(run.name + "/a.py") == b"print(1)"


def test_a_stale_partial_from_a_crashed_run_does_not_block_the_next(run_project):
    """#58: mode "x" on one fixed partial name refused every run after a
    crash. Each attempt now writes its own; a day-old leftover is swept, a
    fresh one (maybe another process's) is left alone."""
    drive, m, project = run_project
    archive = project / ".agent/archive"
    archive.mkdir(parents=True, exist_ok=True)
    stale = archive / "260901-old-audit.zip.partial"
    stale.write_bytes(b"half a zip")
    two_days_ago = time.time() - 2 * 86400
    os.utime(stale, (two_days_ago, two_days_ago))
    fresh = archive / "260901-old-audit.zip.999-abcdef12.partial"
    fresh.write_bytes(b"in flight elsewhere")

    result = archive_run(drive, project, m, _old_audit(project, m))
    assert result.status == "archived", result.note
    assert not stale.exists()
    assert fresh.read_bytes() == b"in flight elsewhere"
    assert not (project / ".agent/runs/260901-old-audit").exists()
    assert sorted(p.name for p in archive.iterdir()) == [
        "260901-old-audit.zip", "260901-old-audit.zip.999-abcdef12.partial"]


def test_a_zip_that_appears_while_zipping_is_never_overwritten(run_project, monkeypatch):
    """#58 review: another process publishing first must win untouched, and
    this run's folder must stay."""
    import atlas.core.runs as runs

    drive, m, project = run_project
    target = project / ".agent/archive/260901-old-audit.zip"
    real = runs._walk_files

    def walk_then_race(source):
        found = real(source)
        if source.name == "260901-old-audit":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"the other machine's zip")
        return found

    run = _old_audit(project, m)
    monkeypatch.setattr(runs, "_walk_files", walk_then_race)
    result = archive_run(drive, project, m, run)
    assert result.status == "skipped" and "appeared" in result.note
    assert target.read_bytes() == b"the other machine's zip"
    assert (project / ".agent/runs/260901-old-audit/a.py").is_file()
    assert not list(target.parent.glob("*.partial"))


def test_an_interrupt_mid_zip_removes_the_partial_and_keeps_the_run(run_project, monkeypatch):
    drive, m, project = run_project

    def interrupted(self, *args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(zipfile.ZipFile, "write", interrupted)
    with pytest.raises(KeyboardInterrupt):
        archive_run(drive, project, m, _old_audit(project, m))
    assert not list((project / ".agent/archive").glob("*"))
    assert (project / ".agent/runs/260901-old-audit/a.py").is_file()


def test_runs_apply_exits_2_on_a_failed_run_and_1_on_a_skipped_one(run_project, capsys, monkeypatch):
    """#58: --apply returned 0 whatever archive_run reported."""
    import atlas.cli as cli
    from atlas.core.runs import RunResult

    drive, _m, project = run_project
    monkeypatch.setattr(cli, "archive_run",
                        lambda *a, **k: RunResult("260901-old-audit", "failed", "disk full"))
    assert main(["runs", "--drive", str(drive), "--project", project.name, "--apply"]) == 2
    assert "failed: disk full" in capsys.readouterr().out
    monkeypatch.setattr(cli, "archive_run",
                        lambda *a, **k: RunResult("260901-old-audit", "skipped", "zip exists"))
    assert main(["runs", "--drive", str(drive), "--project", project.name, "--apply"]) == 1


def test_posix_publish_falls_back_where_hard_links_are_refused(tmp_path, monkeypatch):
    """#58 review: Drive on a Mac, SMB and exFAT refuse os.link; the run
    must still archive, and still never over an existing zip."""
    import errno

    import atlas.core.runs as runs

    def no_links(src, dst):
        raise OSError(errno.ENOTSUP, "Operation not supported")

    monkeypatch.setattr(runs.os, "link", no_links)
    partial, archive = tmp_path / "r.zip.1-a.partial", tmp_path / "r.zip"
    partial.write_bytes(b"zip")
    runs._publish_posix(partial, archive)
    assert archive.read_bytes() == b"zip" and not partial.exists()

    partial.write_bytes(b"second")
    with pytest.raises(FileExistsError):
        runs._publish_posix(partial, archive)
    assert archive.read_bytes() == b"zip"


def test_a_run_name_with_glob_characters_sweeps_only_its_own(run_project):
    from atlas.core.runs import _sweep_stale_partials

    _drive, _m, project = run_project
    archive = project / ".agent/archive"
    archive.mkdir(parents=True, exist_ok=True)
    mine = archive / "260901-[draft].zip.partial"
    other = archive / "260901-d.zip.partial"
    for leftover in (mine, other):
        leftover.write_bytes(b"x")
        os.utime(leftover, (0, 0))
    _sweep_stale_partials(archive, "260901-[draft]")
    assert not mine.exists() and other.exists()

def test_runs_cli_needs_a_target(run_project, capsys):
    drive, _m, _project = run_project
    assert main(["runs", "--drive", str(drive)]) == 2


BRIEF_ENTRY = {"path": "BRIEF.md", "template": "BRIEF.md",
               "index": "Read first - settled (do not ask), open questions, holds"}


def test_brief_and_ask_last_rules_reach_every_project(v3_drive):
    # Agents re-asked settled scope (Montez 2026-10-03): the brief, the ask gate,
    # the after-meeting steps and the size limits ride in every AGENTS.md block.
    data = copy.deepcopy(V3_MAP)
    data["templates"].append(BRIEF_ENTRY)
    write_map(v3_drive, data)
    m = _load(v3_drive)
    project = new_project(v3_drive, m, make_intake(v3_drive, "Brief House")).path
    brief = (project / "BRIEF.md").read_text(encoding="utf-8")
    assert "# Brief - Brief House" in brief
    assert brief.index("## Settled - do not ask") < brief.index("## Open - ask only these")
    agents = (project / "AGENTS.md").read_text(encoding="utf-8")
    for heading in ("## Read first, ask last", "## Look before you make",
                    "## After every meeting", "## Control files stay small"):
        assert heading in agents, heading
    assert "atlas refs check <draft>" in agents  # ADR 0015
    assert agents.index("## Finish the job") < agents.index("## Read first, ask last") < agents.index("## Look before you make")
    # ADR 0017: rule kinds lead; Revit, native-over-drawn and code basis ride in every block.
    assert agents.index("## How these rules bind") < agents.index("## Finish the job")
    for heading in ("## Do the task asked", "## Working in the Revit model",
                    "## Drawings - native over drawn", "## Code work"):
        assert heading in agents, heading
    assert "**Hard line**" in agents and "**Project input**" in agents
    # Family library: where families live, where downloads go, the reference library.
    assert agents.count("## Revit families and the reference library") == 1
    assert agents.index("## Working in the Revit model") < agents.index("## Revit families and the reference library") < agents.index("## Drawings - native over drawn")
    for required in ("G:\\Shared drives\\Config\\3 3D\\0_Revit\\Families`",
                     "G:\\Shared drives\\Config\\3 3D\\0_Revit\\Families\\_INBOX`",
                     "bimobject.com", "bimsmith.com", "G:\\Shared drives\\LIBRARY - Reference`"):
        assert required in agents, required
    # California permit routing: one conditional section after the code basis,
    # Napa scoped, never a statewide claim, filed under ADR 0021 paths.
    assert agents.count("## California permit requirements") == 1
    assert agents.index("## Code work") < agents.index("## California permit requirements") < agents.index("## After every meeting")
    for required in ("_agent\\START_HERE.md", "not statewide coverage", "For non-California projects",
                     "norma <verb>", "07 Correspondence/AHJ/01 Requirements & Pre-Application/"):
        assert required in agents, required
    assert "13 AHJ" not in agents.split("## California permit requirements")[1].split("## After every meeting")[0]
    run_template = (project / ".agent" / "runs" / "_RUN-TEMPLATE.md").read_text(encoding="utf-8")
    assert "- Reference:" in run_template
    assert "4. To-do lists:" in agents  # ADR 0016: production vs Tyler's errands
    assert "00 Tasks/TYLER.md" in agents and "DECISION" in agents
    assert "| Read first - settled (do not ask), open questions, holds | `BRIEF.md` |" in agents
    assert agents_block_current(agents, m)


def test_conform_backfills_the_brief_without_overwriting(v3_drive):
    data = copy.deepcopy(V3_MAP)
    data["templates"].append(BRIEF_ENTRY)
    write_map(v3_drive, data)
    m = _load(v3_drive)
    fresh = make_project(v3_drive, "250101_Brief House", sections=["01 Model"])
    kept = make_project(v3_drive, "250101_Kept House", sections=["01 Model"],
                        files={"BRIEF.md": "# ours\n"})
    for project in (fresh, kept):
        apply_plan(v3_drive, project, m, build_plan(_report(project, m), m, project))
    assert (fresh / "BRIEF.md").read_text(encoding="utf-8").startswith("---")
    assert (kept / "BRIEF.md").read_text(encoding="utf-8") == "# ours\n"


def test_conform_backfills_the_agent_workspace_into_an_old_project(v3_drive):
    # AGENTS.md says "copy it to .agent/backups/" - a project made before the
    # workspace existed must get the folder, or the backup rule has nowhere to go.
    m = _load(v3_drive)
    project = make_project(v3_drive, "250101_Workspace House", sections=["01 Model"])
    report = _report(project, m)
    assert ".agent/backups" in report.missing_control_plane
    assert ".agent/archive" not in report.missing_control_plane
    apply_plan(v3_drive, project, m, build_plan(report, m, project))
    assert (project / ".agent/backups").is_dir() and (project / ".agent/runs").is_dir()
    assert _report(project, m).missing_control_plane == ()
