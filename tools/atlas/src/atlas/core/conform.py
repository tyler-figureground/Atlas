"""P3: conform a project to the map - plan, then apply.

The plan is derived from doctor's ProjectReport (one fact-gathering pass, one
brain). Apply executes in fixed order: control-plane backfill, driftMap
renames, relocations, sweeps. Safety rules are the spec's section 6, verbatim:
deletions are rmdir-shaped (file-empty only), moves never clobber (collisions
survive in place and are reported), case-only renames go through a temp name,
every applied action is logged.

Control-plane backfill is constructive, with two bounded exceptions (ADR 0010).
Missing files are created exclusively. An existing PROJECT.md without the
machine contract is reported as a conflict and left unchanged. AGENTS.md's
marker-wrapped Atlas block is refreshed in place and nothing outside the markers
is touched. CLAUDE.md is rewritten to its one-line pointer only when its words
are stock generator output or already present in AGENTS.md; otherwise it is a
conflict and a person merges it.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from pathlib import Path

from .doctor import ProjectReport, report_project
from .mapfile import DriveMap, find_map, load_map
from .ops import OpsError, append_log, mkdir_below
from .projectmd import (
    FRONT_MATTER_HEAD,
    AgentsBlockError,
    agents_md_lines,
    blank_intake_front_matter,
    blank_intake_identity_rows,
    carried_by,
    claude_md_lines,
    create_crlf_no_bom,
    decisions_readme_lines,
    is_claude_pointer,
    is_legacy_claude,
    meaningful_lines,
    with_agents_block,
    write_crlf_no_bom,
)
from .scan import ProjectInventory, list_entries, long_path, scan_drive

# Action kinds, in apply order.
BACKFILL = "backfill"
RENAME = "rename"
RELOCATE = "relocate"
SWEEP = "sweep"

# Statuses after apply.
DONE = "done"
CONFLICT = "conflict"   # no-clobber leftovers; a human resolves
SKIPPED = "skipped"


# Windows refuses a path longer than this without the extended-length prefix,
# and so do Explorer, Revit, and the studio's PowerShell tools. Atlas warns when a
# move would create one and never applies long_path() on the write side: routing
# around the limit would make the warning dishonest. See ADR 0006 and ticket 19.
WINDOWS_MAX_PATH = 260


class NotInvertible(OpsError):
    """The applied Plan changed the drive in a way its manifests cannot reverse."""


@dataclass(frozen=True)
class Move:
    """One source-and-destination pair an Action actually moved.

    ``is_dir`` is recorded rather than re-read at inversion time: sending a
    merged child back needs to know whether it is a file (a sweep) or a folder
    (a relocate), and asking the filesystem later is both an extra read and a
    race against whatever happened in between.
    """

    src: str
    dst: str
    is_dir: bool


@dataclass(frozen=True)
class Action:
    kind: str
    src: str
    dst: str
    file_count: int = 0
    status: str = ""    # empty until applied
    note: str = ""
    # The Move Manifest: every pair this action actually moved. Empty until
    # applied, and still empty after a backfill, which creates rather than moves.
    moved: tuple[Move, ...] = ()
    # Longest absolute path this action would create, measured at preview time.
    # Zero when the plan was built without a project path to measure against.
    path_length: int = 0

    @property
    def path_warning(self) -> bool:
        return self.path_length > WINDOWS_MAX_PATH


@dataclass(frozen=True)
class Plan:
    project: str
    actions: tuple[Action, ...]

    @property
    def empty(self) -> bool:
        return not self.actions


def _deepest_tail(src: Path) -> int:
    """Longest path below ``src``, measured from ``src`` itself; 0 when empty.

    One walk per previewed action, never per render (ticket 13). What matters
    after a move is not the folder's own path but the deepest thing under it,
    re-hung beneath a destination that may be longer than where it sits now.
    """
    base = long_path(src)
    root_len = len(base)
    deepest = 0
    for root, _dirs, files in os.walk(base, followlinks=False):
        tail = len(root) - root_len
        deepest = max(deepest, tail)
        for name in files:
            deepest = max(deepest, tail + 1 + len(name))
    return deepest


def _path_length(project: Path | None, action: Action) -> int:
    """Longest absolute path the action would leave behind, or 0 if unmeasured."""
    if project is None:
        return 0
    dst = action.dst.replace("\\", "/").rstrip("/")
    if action.kind == BACKFILL:
        return len(str(project / dst))
    if action.kind == SWEEP:
        return len(str(project / dst / Path(action.src).name))
    src = project / action.src
    if not src.is_dir():
        return len(str(project / dst))
    return len(str(project / dst)) + _deepest_tail(src)


def build_plan(report: ProjectReport, m: DriveMap, project: Path | None = None) -> Plan:
    """The Plan for everything the report found wrong with one project.

    ``project`` is the project folder on disk. Given it, every Action carries the
    longest path it would create, which is how the operator finds out before the
    write that a move would push something past MAX_PATH.
    """
    actions: list[Action] = []
    for item in report.missing_control_plane:
        actions.append(Action(kind=BACKFILL, src="", dst=item))
    for found, canonical in report.drift:
        actions.append(Action(kind=RENAME, src=found, dst=canonical))
    for hit in report.relocations:
        actions.append(Action(kind=RELOCATE, src=hit.source, dst=hit.target, file_count=hit.file_count))
    for name, target in report.sweeps:
        actions.append(Action(kind=SWEEP, src=name, dst=target))
    measured = tuple(
        replace(a, path_length=_path_length(project, a)) for a in actions
    )
    return Plan(project=report.name, actions=measured)


def node_key(path: str) -> str:
    """A project-relative path in Node Key form: forward slashes, no leading or
    trailing slash. What an operator types on Windows ("08 OUT\\Invoices",
    "Meetings/") and what the tree hands over must match the same Action."""
    return "/".join(part for part in path.replace("\\", "/").split("/") if part)


def build_repair_plan(report: ProjectReport, m: DriveMap, path: str,
                      project: Path | None = None) -> Plan:
    """The Plan for one node's Repair, holding one Action or none.

    ``path`` is project-relative: the Tree Node's own path for a Drifted,
    Misplaced or Loose node, and the Expectation's path for a Backfill. A Mapped
    or Unfiled node earns no Repair and yields an empty Plan, as does a path the
    report knows nothing about.

    The Action is taken from the full Plan rather than derived a second way. The
    tree introduces no action kinds of its own (ADR 0006), and two derivations of
    "what does this node need" would eventually disagree.
    """
    path = node_key(path)
    full = build_plan(report, m, project=project)
    match = next(
        (a for a in full.actions if a.src == path),
        next((a for a in full.actions if not a.src and a.dst == path), None),
    )
    return Plan(project=report.name, actions=(match,) if match else ())


def action_to_dict(action: Action) -> dict:
    """One Action as JSON. The record is read by six surfaces; this is the one
    that leaves the process, so it names its own fields rather than shipping
    whatever ``__dict__`` happens to hold."""
    return {
        "kind": action.kind,
        "src": action.src,
        "dst": action.dst,
        "file_count": action.file_count,
        "status": action.status,
        "note": action.note,
        "moved": [{"src": mv.src, "dst": mv.dst, "is_dir": mv.is_dir}
                  for mv in action.moved],
        "path_length": action.path_length,
        "path_warning": action.path_warning,
    }


def plan_from_dict(payload: dict) -> Plan:
    """A Plan back from the JSON ``action_to_dict`` produced.

    The return leg. Without it the Move Manifest is write-only: six surfaces can
    read one and nothing can feed one back, which leaves ``invert_plan``
    reachable only from inside a live session. A stateless undo needs this.

    Refuses a manifest missing a field rather than defaulting it. By the time a
    manifest comes back it is operator-supplied input, and a silently defaulted
    ``moved`` becomes an uninvertible Plan two steps later, where the message no
    longer names the real problem. ``path_warning`` is derived and ignored on the
    way in - it is a property, and honouring a supplied one would let a manifest
    contradict its own ``path_length``.
    """
    try:
        actions = tuple(
            Action(
                kind=a["kind"],
                src=a["src"],
                dst=a["dst"],
                file_count=a["file_count"],
                status=a["status"],
                note=a["note"],
                moved=tuple(
                    Move(src=mv["src"], dst=mv["dst"], is_dir=mv["is_dir"])
                    for mv in a["moved"]
                ),
                path_length=a["path_length"],
            )
            for a in payload["actions"]
        )
        return Plan(project=payload["project"], actions=actions)
    except (KeyError, TypeError) as error:
        raise OpsError(f"manifest is missing {error}") from error


# ----------------------------------------------------------------- inverse


def parent_key(rel: str) -> str:
    """Project-relative parent of a project-relative path; "" at the root."""
    normalised = rel.replace("\\", "/").rstrip("/")
    return normalised.rpartition("/")[0]



def invert_plan(plan: Plan) -> Plan:
    """The Plan that reverses an applied one, built from the Move Manifests.

    Undo is not a special execution mode: it is an ordinary Plan that happens to
    move things back, and it goes through ``apply_plan`` like anything else.

    Invertibility is all-or-nothing. An action that changed the drive in a way
    its manifest does not describe - a backfill, which creates, or a removed
    file-empty source, which deletes - makes the whole Plan uninvertible, as does
    a conflict. A partial undo would leave a third state that is neither before
    nor after, and the operator pressed one key expecting one thing.
    """
    for action in plan.actions:
        if action.status == SKIPPED:
            continue    # nothing happened, so there is nothing to reverse
        if action.status != DONE:
            raise NotInvertible(
                f"{action.kind} {action.src or action.dst} is "
                f"{action.status or 'not applied'}; the plan cannot be reversed"
            )
        if not action.moved:
            raise NotInvertible(
                f"{action.kind} {action.src or action.dst} moved nothing Atlas can "
                f"put back; the plan cannot be reversed"
            )
    actions: list[Action] = []
    for action in plan.actions:
        for mv in action.moved:
            if mv.is_dir:
                actions.append(Action(kind=RELOCATE, src=mv.dst, dst=mv.src))
            else:
                # A file goes back by sweep, whose destination is the folder it
                # came from. _apply_move refuses files outright.
                actions.append(Action(kind=SWEEP, src=mv.dst, dst=parent_key(mv.src)))
    return Plan(project=plan.project, actions=tuple(actions))


# ------------------------------------------------------------------ guards

# What one watched directory looked like at preview time.
_Snapshot = tuple[str, str, tuple[tuple[str, bool], ...]]


def _watched_dirs(plan: Plan) -> tuple[str, ...]:
    """The project-relative directories a Plan's actions read and write.

    A move watches the parents its item leaves and arrives in. A sweep's
    destination is already a directory, so it is watched as itself. A backfill
    watches whatever would contain the thing it creates.
    """
    dirs: set[str] = set()
    for action in plan.actions:
        if action.src:
            dirs.add(parent_key(action.src))
        dst = action.dst.replace("\\", "/").rstrip("/")
        dirs.add(dst if action.kind == SWEEP else parent_key(dst))
    return tuple(sorted(dirs))


def _snapshot(project: Path, dirs: tuple[str, ...]) -> tuple[_Snapshot, ...]:
    """Enumerate the watched directories, carrying Load State so that a folder
    that became unreadable reads as a change rather than as an empty one."""
    shots: list[_Snapshot] = []
    for rel in dirs:
        listing = list_entries(project / rel if rel else project)
        shots.append((rel, listing.state,
                      tuple(sorted((e.name, e.is_dir) for e in listing))))
    return tuple(shots)


@dataclass(frozen=True)
class Guard:
    """What a preview saw, and what has to still be true before Atlas writes.

    Guard strength scales with action scope (ADR 0006). A project-wide conform
    keeps the rescan it has always had; a one-action Plan from a Tree Node
    re-reads only the map and the directories that action touches, because a
    keystroke cannot afford a walk of the whole drive.

    Both scopes abort the same way and for the same reasons: the map changed, the
    project went away, the rebuilt actions differ, or a watched directory differs.
    The scoped guard deliberately does not see a change elsewhere in the project -
    that is what makes it cheap, and it is safe because such a change cannot alter
    what the guarded action does.
    """

    project: str
    drive_map: DriveMap
    actions: tuple[Action, ...]
    watched: tuple[_Snapshot, ...]
    whole_project: bool
    node: str = ""
    # Whether the guarded actions can be re-derived from the drive map at all.
    # A repair can: it is a slice of the Plan conform builds, so rebuilding it
    # and comparing is the strongest check available. An undo cannot, because
    # its Plan reverses the map rather than following it - see for_undo.
    derived: bool = True

    @classmethod
    def for_project(cls, drive_root: Path, project: str, m: DriveMap, plan: Plan) -> Guard:
        """Guard a whole-project conform: every action, and the project root."""
        return cls(project=project, drive_map=m, actions=plan.actions,
                   watched=_snapshot(drive_root / project, ("",)),
                   whole_project=True)

    @classmethod
    def for_action(cls, drive_root: Path, project: str, m: DriveMap, plan: Plan) -> Guard:
        """Guard one node's Repair: that action, and the directories it touches."""
        node = plan.actions[0].src or plan.actions[0].dst if plan.actions else ""
        return cls(project=project, drive_map=m, actions=plan.actions,
                   watched=_snapshot(drive_root / project, _watched_dirs(plan)),
                   whole_project=False, node=node)

    @classmethod
    def for_undo(cls, drive_root: Path, project: str, m: DriveMap, inverse: Plan) -> Guard:
        """Guard an undo: the map, and the directories the inverse touches.

        Not ``for_action``. That one re-derives the Plan from the drive map and
        compares, which is the strongest check available for a repair - and
        impossible for an undo, whose Plan reverses the map instead of following
        it. Guarding an inverse that way refuses every time, on a drive nothing
        has changed on. ADR 0006 assumed one guard served both; it does not, and
        ADR 0008's ticket found out by pressing the key.

        What an undo actually has to verify is not "does the map still want this
        work" - it never did - but "are these folders still as they were when the
        repair applied". That is the snapshot, and the snapshot is unchanged.
        """
        node = inverse.actions[0].src or inverse.actions[0].dst if inverse.actions else ""
        return cls(project=project, drive_map=m, actions=inverse.actions,
                   watched=_snapshot(drive_root / project, _watched_dirs(inverse)),
                   whole_project=False, node=node, derived=False)

    def check(self, drive_root: Path) -> str | None:
        """Re-read what was watched. Returns why the Plan is stale, or None."""
        project_path = drive_root / self.project
        if not project_path.is_dir():
            return f"{self.project} is no longer available"

        if self.whole_project:
            # The rescan conform has always paid for: it also refreshes the
            # drive-wide view the operator is looking at.
            fresh_map = scan_drive(drive_root).map
        else:
            map_path = find_map(drive_root)
            if map_path is None:
                return "the drive map is no longer there"
            fresh_map = load_map(map_path)
        if fresh_map != self.drive_map:
            return "the drive map changed"

        if self.derived:
            inv = ProjectInventory(path=project_path, name=self.project,
                                   root_entries=list_entries(project_path))
            report = report_project(inv, fresh_map)
            if self.whole_project:
                fresh = build_plan(report, fresh_map, project=project_path).actions
            else:
                fresh = build_repair_plan(report, fresh_map, self.node,
                                          project=project_path).actions
            if fresh != self.actions:
                return f"{self.project} no longer needs the same work"

        if _snapshot(project_path, tuple(rel for rel, _s, _e in self.watched)) != self.watched:
            return f"{self.project} changed on disk since the preview"
        return None


# ------------------------------------------------------------------- apply

def apply_plan(drive_root: Path, project: Path, m: DriveMap, plan: Plan,
               only: set[str] | None = None) -> Plan:
    """Execute the plan; returns it with per-action statuses filled in."""
    if not project.is_dir():
        raise OpsError(f"project folder is no longer available: {project}")
    applied: list[Action] = []
    order = {BACKFILL: 0, RENAME: 1, RELOCATE: 2, SWEEP: 3}
    for action in sorted(plan.actions, key=lambda a: order[a.kind]):
        if only and action.kind not in only:
            applied.append(replace(action, status=SKIPPED, note="filtered by --only"))
            continue
        if action.kind == BACKFILL:
            applied.append(_apply_backfill(project, m, action))
        elif action.kind == RENAME:
            applied.append(_apply_move(project, action, merge_into_existing=True))
        elif action.kind == RELOCATE:
            applied.append(_apply_move(project, action, merge_into_existing=True))
        elif action.kind == SWEEP:
            applied.append(_apply_sweep(project, action))
    result = Plan(project=plan.project, actions=tuple(applied))
    done = [a for a in result.actions if a.status == DONE]
    if done:
        append_log(drive_root, f"[{project.name}] conform: " +
                   "; ".join(f"{a.kind} {a.src or a.dst} -> {a.dst}" for a in done))
    return result


# ---- control plane ---------------------------------------------------------

_HAS_FRONT_MATTER = re.compile(r"^\s*---")  # same test Conform-Project.ps1 uses


def _conform_project_md_lines(m: DriveMap, leaf: str) -> list[str]:
    """The Conform-Project.ps1 stub (leaner than New-Project's - no Site/
    Zoning/Program sections, no folder map; Conform never invents metadata)."""
    display = re.sub(r"^\d{6}_", "", leaf)
    lines = list(FRONT_MATTER_HEAD)
    lines += blank_intake_front_matter(display)
    lines += [
        "",
        f"# {leaf}",
        "",
        "> Maintained by Architecture Studio skills and the project team. Facts only -",
        "> rationale lives in `decisions/`. The YAML front-matter above is the machine",
        "> mirror of the Identity + Code tables; keep them in agreement.",
        "> **Next:** run `/project-dossier` to fill in the project facts.",
        "",
        "## Identity", "",
        "| Field | Value |", "|-------|-------|",
    ]
    lines += blank_intake_identity_rows(display)
    lines += [
        "",
        "## Code", "",
        "<!-- Mirrors the machine contract in the front-matter. Change a value here -> change it there too. -->", "",
        "| Item | Value | Source | Date |", "|------|-------|--------|------|",
        "| Building code edition | | | |", "| Occupancy group | | | |", "| Construction type | | | |",
        "| Sprinklered | | | |", "| Stories | | | |", "| Building area (SF) | | | |", "| Frontage (ft) | | | |",
        "| Existing C-of-O occupant load | | | |", "| Existing exits | | | |",
        "| Place-of-assembly strategy | | | |", "| Tenancy | | | |",
        "",
        "## Decisions", "",
        "<!-- maintained by /decision - do not edit by hand -->", "",
        "| # | Decision | Status | Date |", "|---|----------|--------|------|",
    ]
    return lines


def _apply_backfill(project: Path, m: DriveMap, action: Action) -> Action:
    target = action.dst
    if target == m.project_file:
        path = project / m.project_file
        if not path.exists():
            if create_crlf_no_bom(path, _conform_project_md_lines(m, project.name)):
                return replace(action, status=DONE, note="created stub")
            return replace(action, status=SKIPPED, note="appeared during apply; rerun")
        raw = path.read_text(encoding="utf-8-sig")
        if _HAS_FRONT_MATTER.match(raw):
            return replace(action, status=SKIPPED, note="machine contract already present")
        return replace(
            action,
            status=CONFLICT,
            note="existing PROJECT.md lacks machine contract; left unchanged",
        )
    if target == m.decisions_dir:
        mkdir_below(project, m.decisions_dir)
        dec = project / m.decisions_dir
        readme = dec / "README.md"
        if not readme.exists() and not create_crlf_no_bom(readme, decisions_readme_lines()):
            return replace(action, status=SKIPPED, note="README appeared during apply; rerun")
        return replace(action, status=DONE)
    if m.agents_file and target == m.agents_file:
        return _backfill_agents(project, m, action)
    if target == m.claude_file:
        return _backfill_claude(project, m, action)
    if target == m.analysis_dir:
        mkdir_below(project, m.analysis_dir)
        return replace(action, status=DONE)
    return replace(action, status=SKIPPED, note=f"unknown control-plane item '{target}'")


# ---- agent files (ADR 0010) ---------------------------------------------------

def _root_spelling(project: Path, name: str) -> str | None:
    """How the root file ``name`` is actually spelled, or None if it is absent.

    Path.exists() is case-insensitive on this mount, so it cannot tell AGENTS.md
    from the Agents.md a person saved by hand. Only a listing can.
    """
    variant = None
    for e in list_entries(project):
        if e.is_dir or e.name.lower() != name.lower():
            continue
        if e.name == name:
            return name
        variant = e.name
    return variant


def _canonical_spelling(project: Path, name: str) -> tuple[bool, str]:
    """Give the root file ``name`` exactly that spelling.

    Returns whether it exists, plus a note when a case variant was renamed. Two
    steps through a temp name, as for folders: a one-step case-only rename is a
    no-op on a case-insensitive mount.
    """
    found = _root_spelling(project, name)
    if found is None:
        return False, ""
    if found == name:
        return True, ""
    tmp = project / f"{found}.atlas-tmp"
    (project / found).rename(tmp)
    tmp.rename(project / name)
    return True, f"renamed {found} -> {name}"


def _read_utf8(path: Path) -> tuple[bytes, str] | None:
    raw = path.read_bytes()
    try:
        return raw, raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def _notes(*parts: str) -> str:
    return "; ".join(p for p in parts if p)


def _backfill_agents(project: Path, m: DriveMap, action: Action) -> Action:
    exists, renamed = _canonical_spelling(project, m.agents_file)
    path = project / m.agents_file
    if not exists:
        claude = project / m.claude_file
        seed = _read_utf8(claude) if m.claude_file and claude.is_file() else None
        text = seed[1] if seed else ""
        if meaningful_lines(text) and not is_claude_pointer(text, m) and not is_legacy_claude(text, m):
            # A person's CLAUDE.md becomes AGENTS.md with its words intact; the
            # CLAUDE.md backfill points at it once it can see them here.
            lines, note = with_agents_block(text.splitlines(), m), f"created from {m.claude_file}"
        else:
            lines, note = agents_md_lines(m), ""
        if not create_crlf_no_bom(path, lines):
            return replace(action, status=SKIPPED, note="appeared during apply; rerun")
        return replace(action, status=DONE, note=note)

    read = _read_utf8(path)
    if read is None:
        return replace(action, status=CONFLICT, note=_notes(renamed, "not UTF-8; left unchanged"))
    raw, text = read
    try:
        lines = with_agents_block(text.splitlines(), m)
    except AgentsBlockError as error:
        return replace(action, status=CONFLICT, note=_notes(renamed, str(error)))
    if lines == text.splitlines():
        return replace(action, status=DONE if renamed else SKIPPED,
                       note=renamed or "Atlas block already current")
    if path.read_bytes() != raw:
        return replace(action, status=SKIPPED, note=_notes(renamed, "changed during apply; rerun"))
    write_crlf_no_bom(path, lines)
    return replace(action, status=DONE, note=_notes(renamed, "Atlas block written"))


def _backfill_claude(project: Path, m: DriveMap, action: Action) -> Action:
    exists, renamed = _canonical_spelling(project, m.claude_file)
    path = project / m.claude_file
    if not exists:
        if not create_crlf_no_bom(path, claude_md_lines(m)):
            return replace(action, status=SKIPPED, note="appeared during apply; rerun")
        return replace(action, status=DONE)
    if not m.agents_file:
        return replace(action, status=DONE if renamed else SKIPPED, note=renamed or "exists")

    read = _read_utf8(path)
    if read is None:
        return replace(action, status=CONFLICT, note=_notes(renamed, "not UTF-8; left unchanged"))
    raw, text = read
    if is_claude_pointer(text, m):
        return replace(action, status=DONE if renamed else SKIPPED,
                       note=renamed or "already a pointer")
    agents = project / m.agents_file
    host = _read_utf8(agents) if agents.is_file() else None
    if host is None:
        return replace(action, status=CONFLICT, note=_notes(
            renamed, f"no readable {m.agents_file} to point at; left unchanged"))
    if not (is_legacy_claude(text, m) or carried_by(text, host[1])):
        return replace(action, status=CONFLICT, note=_notes(
            renamed, f"has words {m.agents_file} lacks; merge them there, then rerun"))
    if path.read_bytes() != raw:
        return replace(action, status=SKIPPED, note=_notes(renamed, "changed during apply; rerun"))
    write_crlf_no_bom(path, claude_md_lines(m))
    return replace(action, status=DONE, note=_notes(renamed, f"now points at {m.agents_file}"))


# ---- moves (renames + relocations share one engine) -------------------------

def _file_count(path: Path) -> int:
    total = 0
    for _r, _d, files in os.walk(path, followlinks=False):
        total += len(files)
    return total


def _remove_if_file_empty(path: Path) -> bool:
    if _file_count(path) != 0:
        return False
    for root, dirs, _files in os.walk(path, topdown=False, followlinks=False):
        for d in dirs:
            (Path(root) / d).rmdir()
    path.rmdir()
    return True


def _apply_move(project: Path, action: Action, merge_into_existing: bool) -> Action:
    src = project / action.src
    dst = project / action.dst
    if not src.is_dir():
        return replace(action, status=SKIPPED, note="source gone")

    # Empty duplicate: the canonical home already owns the artifact class.
    if _remove_if_file_empty(src):
        return replace(action, status=DONE, note="removed file-empty source")

    if src.resolve() == dst.resolve() and action.src != action.dst:
        # Case-only rename on a case-insensitive mount: two-step via temp.
        tmp = src.with_name(src.name + ".atlas-tmp")
        src.rename(tmp)
        tmp.rename(dst)
        return replace(action, status=DONE, note="case-only rename",
                       moved=(Move(src=action.src, dst=action.dst, is_dir=True),))

    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
        return replace(action, status=DONE,
                       moved=(Move(src=action.src, dst=action.dst, is_dir=True),))

    if not merge_into_existing:
        return replace(action, status=CONFLICT, note="target exists")

    # Merge, never clobber: move each child whose name is free at the target.
    manifest: list[Move] = []
    left = 0
    for child in list(src.iterdir()):
        target = dst / child.name
        if target.exists():
            left += 1
            continue
        is_dir = child.is_dir()
        child.rename(target)
        manifest.append(Move(src=f"{action.src}/{child.name}",
                             dst=f"{action.dst}/{child.name}", is_dir=is_dir))
    moved = len(manifest)
    if left == 0 and _remove_if_file_empty(src):
        return replace(action, status=DONE, note=f"merged {moved} item(s)",
                       moved=tuple(manifest))
    return replace(action, status=CONFLICT,
                   note=f"merged {moved}, {left} name collision(s) left in {action.src}",
                   moved=tuple(manifest))


def _apply_sweep(project: Path, action: Action) -> Action:
    src = project / action.src
    if not src.is_file():
        return replace(action, status=SKIPPED, note="source gone")
    dst_rel = action.dst.replace("\\", "/").rstrip("/")
    dst_dir = project / dst_rel
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = dst_dir / src.name
    if target.exists():
        return replace(action, status=CONFLICT, note="name exists at target")
    src.rename(target)
    return replace(action, status=DONE,
                   moved=(Move(src=action.src, dst=f"{dst_rel}/{src.name}", is_dir=False),))
