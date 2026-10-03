"""P2 mutating operations: new project, add section, clean empty.

Safety posture (spec section 6): `new` and `add` are purely constructive and
refuse to touch anything that exists; `clean` is the destructive one and is
dry-run by default with rmdir-only semantics (a directory containing any file
is never deletable). Every applied mutation appends to the drive log.

The full Plan/apply formalism arrives with P3 conform, where plans get long
and reviewable; these three flows have at most a handful of deterministic
steps each.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .contacts import Contact, find_contact, load_contacts
from .intake import ContactSnapshot, IntakeError, ProjectIntake, ResolvedProjectIntake
from .mapfile import DriveMap
from .naming import (
    NamingError,
    build_folder_name,
    clean_name_part,
    validate_project_child_path,
    validate_project_folder_path,
)
from .project_index import (
    ProjectIndexError,
    append_project_index_row,
    preflight_project_index,
)
from .scan import walk
from .projectmd import (
    agents_md_lines,
    claude_md_lines,
    create_crlf_no_bom,
    decisions_readme_lines,
    project_md_lines,
)
from .templates import TemplateError, render_template, template_values


class OpsError(Exception):
    """A requested operation is invalid (exists already, unblessed name, ...)."""


class PartialProjectError(OpsError):
    """Creation stopped after the project directory became visible."""

    def __init__(self, path: Path, detail: str) -> None:
        self.path = path
        super().__init__(f"project partially created at {path}: {detail}; inspect before retrying")


def mkdir_below(root: Path, relative: str) -> bool:
    """Create a relative directory without ever recreating a missing root."""

    if not root.is_dir():
        raise OpsError(f"project folder is no longer available: {root}")
    parts = tuple(part for part in relative.replace("\\", "/").split("/") if part)
    current = root
    final_created = False
    for index, part in enumerate(parts):
        current = current / part
        try:
            current.mkdir()
            if index == len(parts) - 1:
                final_created = True
        except FileExistsError:
            if not current.is_dir():
                raise OpsError(f"cannot create folder; a file exists at {current}") from None
        except FileNotFoundError:
            raise OpsError(f"project folder disappeared while creating {relative}") from None
    return final_created


def append_log(drive_root: Path, message: str) -> None:
    log_dir = drive_root / "_tools" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"atlas-{datetime.now():%Y%m%d}.log"
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{stamp} {message}\n")


# ---------------------------------------------------------------- new project

@dataclass(frozen=True)
class NewProjectResult:
    path: Path
    folder_name: str
    seeded: tuple[str, ...]
    intake: ResolvedProjectIntake
    templates: tuple[str, ...] = ()


def _contact_snapshot(contact: Contact) -> ContactSnapshot:
    address = ""
    if contact.address:
        parts = [contact.address["street"]]
        if contact.address.get("unit"):
            parts.append(contact.address["unit"])
        parts.append(
            f"{contact.address['city']}, {contact.address['state']} "
            f"{contact.address['postal_code']}"
        )
        address = ", ".join(parts)
    return ContactSnapshot(
        id=contact.id,
        first_name=contact.first_name,
        last_name=contact.last_name,
        email=contact.email,
        phone=contact.phone or "",
        company=contact.company or "",
        address=address,
    )


def _resolve_intake(drive_root: Path, request: ProjectIntake) -> ResolvedProjectIntake:
    directory = load_contacts(drive_root)
    billing = find_contact(directory, request.billing_contact_id)
    client = find_contact(directory, request.client_contact_id)
    if billing is None:
        raise OpsError("selected Billing Contact is no longer available; review contacts and retry")
    if client is None:
        raise OpsError("selected Client Contact is no longer available; review contacts and retry")
    try:
        return ResolvedProjectIntake(
            request=request,
            billing_contact=_contact_snapshot(billing),
            client_contact=_contact_snapshot(client),
        )
    except IntakeError as error:
        raise OpsError(str(error)) from error


def new_project(drive_root: Path, m: DriveMap, request: ProjectIntake) -> NewProjectResult:
    resolved = _resolve_intake(drive_root, request)
    name = clean_name_part(resolved.project_name)
    desc = clean_name_part(resolved.description)
    folder_part = clean_name_part(resolved.project_address.short)
    folder_name = build_folder_name(request.created, folder_part, desc)
    created = request.created
    try:
        project = validate_project_folder_path(drive_root, folder_name)
    except NamingError as error:
        raise OpsError(str(error)) from error
    if project.exists():
        raise OpsError(f"a folder named '{folder_name}' already exists")
    planned_paths = [m.project_file, m.decisions_dir, f"{m.decisions_dir}/README.md", m.claude_file]
    if m.agents_file:
        planned_paths.append(m.agents_file)
    if m.analysis_dir:
        planned_paths.append(m.analysis_dir)
    planned_paths.extend(section.id for section in m.sections if section.seed)
    planned_paths.extend(m.seed_child_paths())
    planned_paths.extend(m.agent_dirs)
    planned_paths.extend(t.path for t in m.templates)
    values = template_values(folder_name, name, created.isoformat())
    try:
        # Read every template before anything is created: a missing one stops
        # the intake here, not half-way through a project folder.
        rendered = [(t.path, render_template(t.template, values)) for t in m.templates]
    except TemplateError as error:
        raise OpsError(str(error)) from error
    try:
        for relative in planned_paths:
            validate_project_child_path(project, relative)
    except NamingError as error:
        raise OpsError(str(error)) from error
    try:
        preflight_project_index(drive_root, m)
    except ProjectIndexError as error:
        raise OpsError(str(error)) from error

    try:
        project.mkdir()
    except FileExistsError:
        raise OpsError(f"a folder named '{folder_name}' appeared while creating it") from None
    except OSError as error:
        raise OpsError(f"cannot create project folder {project}: {error}") from error
    seeded = []
    try:
        for section in m.sections:
            if not section.seed:
                continue
            mkdir_below(project, section.id)
            seeded.append(section.id)
        for child in m.seed_child_paths():
            mkdir_below(project, child)
        for agent_dir in m.agent_dirs:
            mkdir_below(project, agent_dir)
        for relative, lines in rendered:
            parent = relative.rpartition("/")[0]
            if parent:
                mkdir_below(project, parent)
            if not create_crlf_no_bom(project / relative, lines):
                raise OpsError(f"{relative} appeared while creating the project; left unchanged")

        if not create_crlf_no_bom(
            project / m.project_file,
            project_md_lines(m, folder_name, resolved),
        ):
            raise OpsError(f"{m.project_file} appeared while creating the project; left unchanged")
        mkdir_below(project, m.decisions_dir)
        if not create_crlf_no_bom(project / m.decisions_dir / "README.md", decisions_readme_lines()):
            raise OpsError("decisions/README.md appeared while creating the project; left unchanged")
        if m.analysis_dir:
            mkdir_below(project, m.analysis_dir)
        # AGENTS.md first: CLAUDE.md is only the pointer at it (ADR 0010).
        if m.agents_file and not create_crlf_no_bom(project / m.agents_file, agents_md_lines(m)):
            raise OpsError(f"{m.agents_file} appeared while creating the project; left unchanged")
        if not create_crlf_no_bom(project / m.claude_file, claude_md_lines(m)):
            raise OpsError(f"{m.claude_file} appeared while creating the project; left unchanged")
        append_project_index_row(drive_root, m, folder_name, request)
        append_log(drive_root, f"[{folder_name}] new: seeded {', '.join(seeded)}; control plane written")
    except PartialProjectError:
        raise
    except (OpsError, ProjectIndexError, OSError) as error:
        raise PartialProjectError(project, str(error)) from error
    return NewProjectResult(
        path=project,
        folder_name=folder_name,
        seeded=tuple(seeded),
        intake=resolved,
        templates=tuple(path for path, _lines in rendered),
    )


# ---------------------------------------------------------------- add section

def add_sections(drive_root: Path, m: DriveMap, project: Path, requests: list[str]) -> list[str]:
    """Create blessed folders. Requests are 'NN Section' or 'NN Section/Child'
    where Child must be a blessed child entry (children may themselves contain
    slashes, e.g. '00 Library/Families'). No free-text names, ever."""
    if not project.is_dir():
        raise OpsError(f"project folder is no longer available: {project}")
    created: list[str] = []
    for req in requests:
        rel = _resolve_blessed(m, req)
        if mkdir_below(project, rel):
            created.append(rel)
    if created:
        append_log(drive_root, f"[{project.name}] add: {', '.join(created)}")
    return created


def _resolve_blessed(m: DriveMap, request: str) -> str:
    req = request.replace("\\", "/").strip().strip("/")
    for section in m.sections:
        if req == section.id:
            return section.id
        prefix = section.id + "/"
        if req.startswith(prefix):
            child = req[len(prefix):]
            if child in section.children:
                return f"{section.id}/{child}"
            raise OpsError(f"'{child}' is not a blessed child of '{section.id}'")
    raise OpsError(f"'{request}' is not a canonical section (check the map)")


# ---------------------------------------------------------------- clean empty

def find_empty_dirs(project: Path, m: DriveMap, include_seeds: bool = False) -> list[str]:
    """Directories removable by pure rmdir cascade: no file anywhere beneath.
    Control-plane dirs are always kept; seed section tops kept unless asked."""
    protected_tops = {m.decisions_dir}
    for agent_dir in m.agent_dirs:
        protected_tops.add(agent_dir.replace("\\", "/").split("/")[0])
    # The analysisDir is control plane: doctor reports it missing, so clean
    # must never be the thing that removes it.
    analysis_rel = m.analysis_dir.replace("\\", "/") if m.analysis_dir else None
    seed_ids = {s.id for s in m.sections if s.seed} | set(m.seed_child_paths())

    empties: list[str] = []
    # Bottom-up, never through a link: a junction's target lives outside the
    # project, and a link counts as content so its folder is never "empty".
    for root, dirs, files, links in walk(project, topdown=False):
        root_path = Path(root)
        if root_path == project:
            continue
        rel = root_path.relative_to(project).as_posix()
        top = rel.split("/")[0]
        if top in protected_tops:
            continue
        if analysis_rel and rel == analysis_rel:
            continue
        if not include_seeds and rel in seed_ids:
            continue
        # Empty means: no files or links here, and every subdir already marked
        # empty.
        if files or links:
            continue
        if all(f"{rel}/{d}" in empties for d in dirs):
            empties.append(rel)
    return sorted(empties)


def remove_empty_dirs(drive_root: Path, project: Path, rels: list[str]) -> list[str]:
    """rmdir deepest-first; refuses (skips) anything non-empty by construction."""
    removed: list[str] = []
    for rel in sorted(rels, key=lambda r: r.count("/"), reverse=True):
        target = project / rel
        try:
            target.rmdir()
            removed.append(rel)
        except OSError:
            pass  # gained content since the scan; rmdir-only means we skip
    if removed:
        append_log(drive_root, f"[{project.name}] clean: removed {len(removed)} empty dirs")
    return removed
