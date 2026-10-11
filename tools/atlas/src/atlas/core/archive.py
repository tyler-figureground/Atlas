"""Archive and un-archive a project: the drive-scoped verbs (ADR 0019).

Archiving is an operator ruling, not drift the map detects, so it is not a
conform relocation and it never relaxes the project-scoped containment that
makes ``plan_from_dict`` safe. It gets its own action kinds (ARCHIVE /
UNARCHIVE) on a drive-scoped plan that reuses the conform primitives - the
Action record, the Move Manifest, the inverse-plan and Guard shapes - with
paths validated against the drive root rather than a project.

One plan per project: the folder Move between the drive root and the map's
``controlPlane.archiveRoot``, plus the ``_Project Index.md`` row stamped
``archived YYYY-MM-DD`` (stamped, not removed - the register is history). The
row's prior text is recorded on the applied Action so the inverse restores it
verbatim. The prompt-vault note and contacts are untouched. Open task items
and Revit/CAD files warn in the preview, never refuse: a dormant project with
stale items is the common case, and a true cross-project Revit-link scan is
not knowable from the mount - the model-file count is the honest substitute.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from .conform import (
    CONFLICT,
    DONE,
    FAILED,
    SKIPPED,
    WINDOWS_MAX_PATH,
    Action,
    Move,
    NotInvertible,
    action_to_dict,
    deepest_tail,
)
from .mapfile import DriveMap, find_map, load_map
from .ops import OpsError, append_log
from .project_index import (
    INDEX_NAME,
    ProjectIndexError,
    restore_project_index_row,
    stamp_project_index_status,
)
from .scan import Listing, list_entries, tally_files, walk
from .scan import is_project_dir
from .tyler import TASKS_PATH, TYLER_PATH, open_items

ARCHIVE = "archive"
UNARCHIVE = "unarchive"

# What a preview counts so the operator sees "links into this project from
# live projects will break" before confirming. Revit models and families,
# CAD, and the linked-resource formats (ticket 30). The mount cannot enumerate
# the links themselves - they live inside binary models - so the count is the
# warning, and it is paid once, at plan build, not per render.
MODEL_EXTENSIONS = frozenset({"rvt", "rfa", "rte", "dwg", "ifc", "pcg", "rcp"})


@dataclass(frozen=True)
class ArchivePlan:
    """One drive-scoped plan: move one project folder, stamp its index row.

    Drive-scoped, not project-scoped: ``src``/``dst`` on its actions are
    relative to the drive root, and the conform ``Plan`` machinery never sees
    them. Exactly one action today; the tuple matches the conform shape the
    manifest printer and revert flow already speak.
    """

    project: str        # the folder name being moved, one segment
    archive_root: str   # the map's controlPlane.archiveRoot
    actions: tuple[Action, ...]
    warnings: tuple[str, ...] = ()
    # What the preview must say even when there is nothing to warn about: the
    # vault note and contacts stay behind on purpose (ticket 30).
    notes: tuple[str, ...] = ()
    inverse: bool = False


_VAULT_NOTE = "The prompt-vault note and contacts are untouched - they are historical and shared."


def _folder_name(name: object) -> str:
    """One folder name, never a path - the same shape conform demands of a
    manifest's project."""
    if (not isinstance(name, str) or not name or name in (".", "..")
            or any(c in name for c in "/\\:")):
        raise OpsError(f"'{name}' is not a project folder name")
    return name


def _drive_relative(path: object, field: str) -> str:
    """A drive-root-relative path from an operator-supplied manifest, or refuse.

    The same shape as conform's ``_inside``, scoped one level up: the archive
    plan's containment invariant, refusing a crafted ``..``, absolute or
    drive-lettered path that would move folders anywhere the operator can
    write.
    """
    if not isinstance(path, str):
        raise OpsError(f"manifest {field} is not a path: {path!r}")
    normalised = path.replace("\\", "/")
    if (not normalised.strip("/") or normalised.startswith("/")
            or re.match(r"^[A-Za-z]:", normalised) or ".." in normalised.split("/")):
        raise OpsError(f"manifest {field} '{path}' is not a path inside the drive")
    return normalised.strip("/")


def _readable(listing: Listing, what: str) -> None:
    if not listing.readable:
        raise OpsError(f"cannot read {what}: {listing.error}")


def _project_facts(project: Path) -> tuple[int, int, tuple[str, ...]]:
    """(total files, model files, unreadable folders) in one walk, paid once."""
    errors: list[tuple[str, str]] = []
    total = 0
    models = 0
    for _root, _dirs, files, _links in walk(project, errors=errors):
        total += len(files)
        models += sum(1 for f in files
                      if f.rpartition(".")[2].lower() in MODEL_EXTENSIONS)
    base = os.fspath(project)
    unreadable = tuple(
        os.path.relpath(where, base).replace("\\", "/") for where, _why in errors
    )
    return total, models, unreadable


def _open_task_items(project: Path) -> tuple[str, ...]:
    """Open checkbox items in the project's two task lists, one line each.

    Counted and listed in the preview, never a refusal: a dormant project with
    stale open items is the common case (ticket 30).
    """
    items: list[str] = []
    for rel in (TASKS_PATH, TYLER_PATH):
        path = project / rel
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue    # absent or unreadable: the digest reports that; archive does not
        for item in open_items(text):
            items.append(f"{rel}: {item.text}")
    return tuple(items)


def _archive_warnings(project: Path, model_count: int,
                      unreadable: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(warnings, open-item lines) for the archive preview."""
    warnings: list[str] = []
    if model_count:
        warnings.append(
            f"{model_count} Revit/CAD/linked-resource file(s) in this project - "
            f"links into it from live projects will break"
        )
    for rel in unreadable:
        warnings.append(f"cannot read {rel} - the move will refuse it")
    open_lines = _open_task_items(project)
    if open_lines:
        warnings.append(f"{len(open_lines)} open task item(s) stay open:")
    return tuple(warnings), open_lines


def build_archive_plan(drive_root: Path, m: DriveMap, name: str,
                       *, today: date | None = None) -> ArchivePlan:
    """The plan that archives one project. Precondition refusals raise OpsError.

    Refuses: a name that is not one project folder, a project not at the drive
    root (already archived, or never there), an unreadable project root, and a
    destination name already taken at the archive root. Warns, never refuses:
    model files, unreadable folders below the root, open task items.
    """
    name = _folder_name(name)
    if not is_project_dir(name):
        raise OpsError(f"'{name}' is not a project folder; only projects can be archived")
    root_entries = list_entries(drive_root)
    _readable(root_entries, f"the drive root {drive_root}")
    project = drive_root / name
    if not any(e.is_dir and e.name == name for e in root_entries):
        raise OpsError(f"no project folder '{name}' under {drive_root} "
                       f"(already archived projects unarchive by name)")
    _readable(list_entries(project), f"the project root {project}")

    archive_root = m.archive_root
    archive_path = drive_root / archive_root
    if archive_path.exists():
        if not archive_path.is_dir():
            raise OpsError(f"the archive root {archive_root} exists and is not a folder")
        archive_listing = list_entries(archive_path)
        _readable(archive_listing, f"the archive root {archive_path}")
        if any(e.name == name for e in archive_listing):
            raise OpsError(f"'{name}' is already taken under {archive_root}")

    file_count, models, unreadable = _project_facts(project)
    warnings, open_lines = _archive_warnings(project, models, unreadable)
    stamp = f"archived {(today or date.today()).isoformat()}"
    action = Action(
        kind=ARCHIVE,
        src=name,
        dst=f"{archive_root}/{name}",
        file_count=file_count,
        note=f"stamp the project index row '{stamp}'",
        path_length=len(str(drive_root / archive_root / name)) + deepest_tail(project),
    )
    return ArchivePlan(
        project=name,
        archive_root=archive_root,
        actions=(action,),
        warnings=warnings + open_lines,
        notes=(_VAULT_NOTE,),
    )


def build_unarchive_plan(drive_root: Path, m: DriveMap, name: str,
                         *, today: date | None = None) -> ArchivePlan:
    """The plan that brings one archived project back, found by name.

    The archive root is enumerated only here, on demand. Refuses: no archive
    root, an unreadable one, a name not under it, a name already taken at the
    drive root.
    """
    name = _folder_name(name)
    archive_root = m.archive_root
    archive_path = drive_root / archive_root
    if not archive_path.is_dir():
        raise OpsError(f"nothing is archived: no {archive_root} under {drive_root}")
    archive_listing = list_entries(archive_path)
    _readable(archive_listing, f"the archive root {archive_path}")
    if not any(e.is_dir and e.name == name for e in archive_listing):
        raise OpsError(f"no archived project '{name}' under {archive_root}")
    project = archive_path / name
    _readable(list_entries(project), f"the project root {project}")

    root_entries = list_entries(drive_root)
    _readable(root_entries, f"the drive root {drive_root}")
    if any(e.name == name for e in root_entries):
        raise OpsError(f"'{name}' is already taken at the drive root")

    file_count, _models, unreadable = _project_facts(project)
    warnings = tuple(f"cannot read {rel} - the move will refuse it" for rel in unreadable)
    open_lines = _open_task_items(project)
    if open_lines:
        warnings += (f"{len(open_lines)} open task item(s) come back with it:", *open_lines)
    action = Action(
        kind=UNARCHIVE,
        src=f"{archive_root}/{name}",
        dst=name,
        file_count=file_count,
        note="restore the project index row",
        path_length=len(str(drive_root / name)) + deepest_tail(project),
        # Emptied by the move, the archive root goes with it (rmdir-only, so a
        # root still holding other projects stays).
        prune=(archive_root,),
    )
    return ArchivePlan(
        project=name,
        archive_root=archive_root,
        actions=(action,),
        warnings=warnings,
        notes=(_VAULT_NOTE,),
    )


# ------------------------------------------------------------------- guard

# What one watched directory looked like at preview time. An absent folder
# (the archive root before its first use) is a state of its own: re-checking
# an absent folder against a read one must read as a change.
_DirSnapshot = tuple[str, bool, str, tuple[tuple[str, bool], ...]]


def _dir_snapshot(path: Path, rel: str) -> _DirSnapshot:
    if not path.exists():
        return (rel, False, "", ())
    listing = list_entries(path)
    return (rel, True, listing.state,
            tuple(sorted((e.name, e.is_dir) for e in listing)))


@dataclass(frozen=True)
class ArchiveGuard:
    """What an archive preview saw, checked before the write (ADR 0006 shape,
    drive scope). Watches the map and the two drive-level parents - the drive
    root and the archive root - rather than project folders. There is no
    re-derivation: an archive is an operator ruling, never map-derived, so the
    guard is the ``for_undo`` shape by construction.
    """

    drive_map: DriveMap
    project: str
    watched: tuple[_DirSnapshot, ...]

    @classmethod
    def for_plan(cls, drive_root: Path, m: DriveMap, plan: ArchivePlan) -> ArchiveGuard:
        return cls(
            drive_map=m,
            project=plan.project,
            watched=(
                _dir_snapshot(drive_root, ""),
                _dir_snapshot(drive_root / plan.archive_root, plan.archive_root),
            ),
        )

    def check(self, drive_root: Path) -> str | None:
        """Re-read what was watched. Returns why the plan is stale, or None."""
        if not drive_root.is_dir():
            return "the drive root is no longer available"
        map_path = find_map(drive_root)
        if map_path is None:
            return "the drive map is no longer there"
        if load_map(map_path) != self.drive_map:
            return "the drive map changed"
        fresh = tuple(
            _dir_snapshot(drive_root / rel if rel else drive_root, rel)
            for rel, _exists, _state, _entries in self.watched
        )
        if fresh != self.watched:
            return "the drive changed since the preview"
        return None


# ------------------------------------------------------------------ inverse

def invert_archive_plan(plan: ArchivePlan) -> ArchivePlan:
    """The plan that reverses an applied archive or un-archive.

    Same contract as conform's ``invert_plan``: undo is an ordinary plan that
    moves things back, all-or-nothing. The inverse restores the recorded
    project-index row verbatim rather than re-stamping, so the register says
    exactly what it said before. Folders the original apply created (the
    archive root, on first use) are pruned after the move back if empty.
    Re-invoking archive after undo is redo.
    """
    actions: list[Action] = []
    for action in plan.actions:
        if action.status == FAILED and not action.moved:
            raise NotInvertible(
                f"{action.kind} {action.src} failed before anything moved; "
                f"nothing to reverse"
            )
        if action.status not in (DONE, FAILED):
            raise NotInvertible(
                f"{action.kind} {action.src} is {action.status or 'not applied'}; "
                f"the plan cannot be reversed"
            )
        if not action.moved:
            raise NotInvertible(
                f"{action.kind} {action.src} moved nothing Atlas can put back; "
                f"the plan cannot be reversed"
            )
        if len(action.moved) != 1:
            raise NotInvertible(
                f"{action.kind} {action.src} has a partial manifest; "
                f"the plan cannot be reversed"
            )
        mv = action.moved[0]
        prune = tuple(sorted(action.created, key=lambda k: k.count("/"), reverse=True))
        actions.append(Action(
            kind=UNARCHIVE if action.kind == ARCHIVE else ARCHIVE,
            src=mv.dst,
            dst=mv.src,
            note="restore the project index row" if action.index_row else "",
            index_row=action.index_row,
            prune=prune,
        ))
    return ArchivePlan(project=plan.project, archive_root=plan.archive_root,
                       actions=tuple(actions), inverse=True)


# ------------------------------------------------------------------- apply

def apply_archive_plan(drive_root: Path, m: DriveMap, plan: ArchivePlan,
                       *, today: date | None = None) -> ArchivePlan:
    """Execute the plan; returns it with the action's status and manifest filled.

    The folder moves first, by one rename - never a clobber, and an unreadable
    folder below the root refuses rather than moving what Atlas cannot account
    for. The index stamp follows; a stamp failure after the move is a FAILED
    action whose manifest still carries the move, so the revert can put the
    folder back.
    """
    applied: list[Action] = []
    try:
        for action in plan.actions:
            applied.append(_apply_one(drive_root, m, plan, action, today=today))
    finally:
        _log_applied(drive_root, plan, applied)
    return replace(plan, actions=tuple(applied))


def _apply_one(drive_root: Path, m: DriveMap, plan: ArchivePlan,
               action: Action, *, today: date | None) -> Action:
    src = drive_root / action.src
    dst = drive_root / action.dst
    if not src.is_dir():
        return replace(action, status=SKIPPED, note="source gone")
    if dst.exists():
        return replace(action, status=CONFLICT, note="name exists at destination")

    # A folder Atlas cannot read is not accounted for. Leave the project where
    # it is rather than move what cannot be seen (the conform rule, one level up).
    tally = tally_files(src)
    if not tally.known:
        rel, _why = tally.unreadable[0]
        where = action.src if rel == "." else f"{action.src}/{rel}"
        return replace(action, status=CONFLICT, note=f"cannot read {where}; left in place")

    absent = tuple(
        "/".join(action.dst.split("/")[:depth])
        for depth in range(1, len(action.dst.split("/")))
        if not (drive_root / "/".join(action.dst.split("/")[:depth])).exists()
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    created = tuple(rel for rel in absent if (drive_root / rel).exists())
    moved = (Move(src=action.src, dst=action.dst, is_dir=True),)

    try:
        if action.index_row:
            # An inverse restores the recorded row verbatim; only a fresh plan
            # stamps.
            prior = restore_project_index_row(drive_root, m, plan.project,
                                              action.index_row)
        elif not (drive_root / INDEX_NAME).is_file():
            # No register at all is the no-row case, not a failure: the index
            # may predate Atlas or never have existed on this drive.
            prior = None
        elif action.kind == ARCHIVE:
            stamp = f"archived {(today or date.today()).isoformat()}"
            prior = stamp_project_index_status(drive_root, m, plan.project, stamp)
        else:
            prior = stamp_project_index_status(drive_root, m, plan.project, "Active")
    except ProjectIndexError as error:
        return replace(action, status=FAILED, moved=moved, created=created,
                       note=f"folder moved; the project index stamp failed: {error}")

    note = action.note if prior is not None else f"{action.note}; no project-index row"
    result = replace(action, status=DONE, moved=moved, created=created,
                     index_row=prior or "", note=note)
    if result.prune:
        _prune_empty(drive_root, result.prune)
    return result


def _prune_empty(drive_root: Path, keys: tuple[str, ...]) -> None:
    """Remove each folder that is now entirely empty, deepest first - the
    archive root an undone archive created. rmdir is the whole check."""
    for key in keys:
        try:
            (drive_root / key).rmdir()
        except OSError:
            pass


def _log_applied(drive_root: Path, plan: ArchivePlan, applied: list[Action]) -> None:
    """One drive-log line per applied archive, as conform does."""
    parts = []
    for a in applied:
        if a.status == DONE:
            parts.append(f"{a.kind} {a.src} -> {a.dst}")
        elif a.status == FAILED and a.moved:
            parts.append(f"{a.kind} {a.src} -> {a.dst} FAILED ({a.note})")
    if parts:
        try:
            append_log(drive_root, f"[{plan.project}] " + "; ".join(parts))
        except OSError:
            pass    # the log is a record, never a reason to lose the result


# ------------------------------------------------------------- manifests

def archive_plan_to_dict(plan: ArchivePlan, drive: str) -> dict:
    """One ArchivePlan as JSON - the record ``unarchive --revert`` reads back."""
    return {
        "drive": drive,
        "scope": "drive",
        "project": plan.project,
        "archive_root": plan.archive_root,
        "actions": [action_to_dict(a) for a in plan.actions],
        "warnings": list(plan.warnings),
    }


def archive_plan_from_dict(payload: dict) -> ArchivePlan:
    """An ArchivePlan back from the JSON ``archive_plan_to_dict`` produced.

    The return leg, shaped on ``plan_from_dict`` and just as strict: every path
    is validated drive-root-relative, so a crafted manifest cannot move folders
    outside the drive. The conform parser's project-scoped containment is not
    relaxed to make room for this - archive manifests have their own door
    (ADR 0019).
    """
    try:
        if payload.get("scope") != "drive":
            raise OpsError("manifest is not a drive-scoped archive manifest")
        actions = tuple(
            Action(
                kind=_archive_kind(a["kind"]),
                src=_drive_relative(a["src"], "src"),
                dst=_drive_relative(a["dst"], "dst"),
                file_count=a.get("file_count", 0),
                status=a["status"],
                note=a["note"],
                moved=tuple(
                    Move(src=_drive_relative(mv["src"], "moved src"),
                         dst=_drive_relative(mv["dst"], "moved dst"),
                         is_dir=mv["is_dir"])
                    for mv in a["moved"]
                ),
                path_length=a.get("path_length", 0),
                created=tuple(_drive_relative(k, "created") for k in a.get("created", ())),
                prune=tuple(_drive_relative(k, "prune") for k in a.get("prune", ())),
                index_row=_row_text(a.get("index_row", "")),
            )
            for a in payload["actions"]
        )
        return ArchivePlan(
            project=_folder_name(payload["project"]),
            archive_root=_drive_relative(payload["archive_root"], "archive_root"),
            actions=actions,
        )
    except (KeyError, TypeError) as error:
        raise OpsError(f"manifest is missing {error}") from error


def _archive_kind(kind: object) -> str:
    if kind not in (ARCHIVE, UNARCHIVE):
        raise OpsError(
            f"manifest names an unknown action kind {kind!r} for an archive plan"
        )
    return kind


def _row_text(value: object) -> str:
    if not isinstance(value, str):
        raise OpsError(f"manifest index_row is not text: {value!r}")
    return value


__all__ = [
    "ARCHIVE",
    "UNARCHIVE",
    "MODEL_EXTENSIONS",
    "ArchiveGuard",
    "ArchivePlan",
    "apply_archive_plan",
    "archive_plan_from_dict",
    "archive_plan_to_dict",
    "build_archive_plan",
    "build_unarchive_plan",
    "invert_archive_plan",
]
