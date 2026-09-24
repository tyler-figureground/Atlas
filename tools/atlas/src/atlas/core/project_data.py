"""Read and safely update Atlas project-intake data in existing dossiers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from uuid import uuid4

from .contacts import Contact, ContactError, find_contact, load_contacts
from .intake import ContactSnapshot, IntakeError, ProjectAddress, ProjectIntake, ProjectUseCase
from .mapfile import DriveMap
from .naming import NamingError, build_folder_name, clean_name_part, validate_project_folder_path
from .projectmd import table_cell, yaml_quote
from .project_index import (
    INDEX_NAME,
    ProjectIndexError,
    preflight_project_index,
    update_project_index_row,
)


__all__ = [
    "ProjectDataError",
    "ProjectRecord",
    "ProjectUpdatePlan",
    "ProjectUpdateResult",
    "apply_project_update",
    "load_project_record",
    "preview_project_update",
]


class ProjectDataError(Exception):
    """An existing project dossier cannot be interpreted or changed safely."""


@dataclass(frozen=True)
class ProjectRecord:
    path: Path
    intake: ProjectIntake
    billing_contact: ContactSnapshot
    client_contact: ContactSnapshot
    source_digest: str
    _source: bytes = field(repr=False, compare=False)


@dataclass(frozen=True)
class ProjectUpdatePlan:
    old_path: Path
    new_path: Path
    intake: ProjectIntake
    billing_contact: ContactSnapshot
    client_contact: ContactSnapshot
    source_digest: str
    contacts_digest: str | None
    index_digest: str | None
    _source: bytes = field(repr=False, compare=False)

    @property
    def rename_required(self) -> bool:
        return str(self.old_path) != str(self.new_path)


@dataclass(frozen=True)
class ProjectUpdateResult:
    old_path: Path
    path: Path
    renamed: bool
    record: ProjectRecord


def _read_source(project_path: Path) -> tuple[Path, Path, bytes]:
    project = Path(project_path)
    dossier = project / "PROJECT.md"
    try:
        source = dossier.read_bytes()
    except OSError as error:
        raise ProjectDataError(f"cannot read project dossier {dossier}: {error}") from error
    if source.startswith(b"\xef\xbb\xbf"):
        raise ProjectDataError(f"{dossier} has a UTF-8 BOM; repair it before editing")
    try:
        source.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ProjectDataError(f"{dossier} is not UTF-8: {error}") from error
    if not source.endswith(b"\r\n") or b"\n" in source.replace(b"\r\n", b""):
        raise ProjectDataError(f"{dossier} must use CRLF line endings with a trailing newline")
    return project, dossier, source


# The front-matter keys Atlas reads and writes. Only these are parsed, and
# only as flat scalars; every other line - the Norma keys a dossier may write
# as a list or a block, comments, anything a newer skill adds - is carried
# through byte-for-byte and never validated here (ADR 0001).
_ATLAS_KEYS = frozenset(
    (
        "project",
        "name",
        "address",
        "address_street",
        "address_unit",
        "address_city",
        "address_state",
        "address_postal_code",
        "description",
        "project_use_case",
        "project_use_case_category",
        *(
            f"{role}_contact_{suffix}"
            for role in ("billing", "client")
            for suffix in ("id", "name", "email", "phone", "company", "address")
        ),
    )
)
_KEY_LINE = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*):(?=[ \t]|$)")


@dataclass(frozen=True)
class _FrontMatter:
    """Where the Atlas keys sit in the front matter, and what they hold."""

    end: int
    values: dict[str, str]
    line_of: dict[str, int]
    comment_at: dict[str, int]


def _closing_double_quote(body: str) -> int:
    index = 1
    while index < len(body):
        character = body[index]
        if character == "\\":
            index += 2
            continue
        if character == '"':
            return index
        index += 1
    return -1


def _yaml_scalar(rest: str, *, key: str, dossier: Path) -> tuple[str, int | None]:
    """Parse the text after ``key:`` as one flat YAML scalar.

    Returns the value and, when the line carries a trailing ``# comment``, the
    comment's offset within ``rest`` so a rewrite can keep it. YAML's rule: a
    ``#`` starts a comment only when whitespace precedes it, and a value that
    is only a comment is empty (the dossier template writes
    ``address_unit:  # optional``).
    """

    body = rest.lstrip(" \t")
    offset = len(rest) - len(body)
    if not body:
        return "", None
    if body.startswith("#"):
        return "", offset
    if body[0] == '"':
        end = _closing_double_quote(body)
        if end < 0:
            raise ProjectDataError(f"{dossier} has invalid YAML value for '{key}'")
        try:
            value = json.loads(body[: end + 1])
        except json.JSONDecodeError as error:
            raise ProjectDataError(f"{dossier} has invalid YAML value for '{key}'") from error
        tail_start = end + 1
    elif body[0] == "'":
        pieces: list[str] = []
        index = 1
        while True:
            quote = body.find("'", index)
            if quote < 0:
                raise ProjectDataError(f"{dossier} has invalid YAML value for '{key}'")
            if body[quote + 1 : quote + 2] == "'":
                pieces.append(body[index : quote + 1])
                index = quote + 2
                continue
            pieces.append(body[index:quote])
            break
        value = "".join(pieces)
        tail_start = quote + 1
    else:
        if body[0] in "[{&*!>|%@`":
            raise ProjectDataError(f"{dossier} uses unsupported YAML for '{key}'")
        comment = re.search(r"[ \t]#", body)
        if comment is None:
            return body.rstrip(" \t"), None
        return body[: comment.start()].rstrip(" \t"), offset + comment.start() + 1
    tail = body[tail_start:]
    after = tail.lstrip(" \t")
    if not after:
        return value, None
    if after.startswith("#") and len(after) < len(tail):
        return value, offset + tail_start + len(tail) - len(after)
    raise ProjectDataError(f"{dossier} has invalid YAML value for '{key}'")


def _front_matter_bounds(lines: list[str], dossier: Path) -> int:
    if not lines or lines[0].rstrip() != "---":
        raise ProjectDataError(f"{dossier} is missing Atlas YAML front matter")
    for index in range(1, len(lines)):
        if lines[index].rstrip() == "---":
            return index
    raise ProjectDataError(f"{dossier} has unterminated YAML front matter")


def _parse_front_matter(lines: list[str], dossier: Path) -> _FrontMatter:
    end = _front_matter_bounds(lines, dossier)
    values: dict[str, str] = {}
    line_of: dict[str, int] = {}
    comment_at: dict[str, int] = {}
    current: str | None = None
    for index in range(1, end):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[:1] in (" ", "\t"):
            # A continuation line belongs to the key above it. Atlas keys are
            # flat scalars, so one here is a shape Atlas cannot rewrite safely.
            if current is not None:
                raise ProjectDataError(f"{dossier} uses unsupported YAML for '{current}'")
            continue
        match = _KEY_LINE.match(line)
        key = match.group(1) if match else None
        if key not in _ATLAS_KEYS:
            current = None
            continue
        if key in values:
            raise ProjectDataError(f"{dossier} has duplicate YAML key '{key}'")
        rest = line[match.end() :]
        value, comment = _yaml_scalar(rest, key=key, dossier=dossier)
        values[key] = value
        line_of[key] = index
        if comment is not None:
            comment_at[key] = match.end() + comment
        current = key
    return _FrontMatter(end=end, values=values, line_of=line_of, comment_at=comment_at)


def _front_matter(source: bytes, dossier: Path) -> dict[str, str]:
    values = dict(_parse_front_matter(source.decode("utf-8").split("\r\n"), dossier).values)
    if not values.get("project") and values.get("name"):
        # SKILL.md: `name` is an accepted alias of `project`.
        values["project"] = values["name"]
    return values


def _identity_value(source: bytes, field_name: str, dossier: Path) -> str:
    prefix = f"| {field_name} |"
    matches = []
    for line in source.decode("utf-8").split("\r\n"):
        if line.startswith(prefix) and line.endswith("|"):
            matches.append(line[len(prefix) : -1].strip())
    if len(matches) != 1:
        raise ProjectDataError(
            f"{dossier} must contain exactly one '{field_name}' Identity row"
        )
    return matches[0].replace(r"\|", "|").replace(r"\\", "\\")


def _required(values: dict[str, str], key: str, dossier: Path) -> str:
    value = values.get(key, "").strip()
    if not value:
        raise ProjectDataError(f"{dossier} is missing required Atlas intake key '{key}'")
    return value


def _snapshot(values: dict[str, str], role: str, dossier: Path) -> ContactSnapshot:
    name = _required(values, f"{role}_contact_name", dossier)
    pieces = name.rsplit(maxsplit=1)
    if len(pieces) != 2:
        raise ProjectDataError(f"{dossier} {role} contact name must include first and last name")
    try:
        return ContactSnapshot(
            id=_required(values, f"{role}_contact_id", dossier),
            first_name=pieces[0],
            last_name=pieces[1],
            email=_required(values, f"{role}_contact_email", dossier),
            phone=values.get(f"{role}_contact_phone", ""),
            company=values.get(f"{role}_contact_company", ""),
            address=values.get(f"{role}_contact_address", ""),
        )
    except IntakeError as error:
        raise ProjectDataError(f"{dossier} has invalid {role} contact snapshot: {error}") from error


def _project_address(values: dict[str, str], dossier: Path) -> ProjectAddress:
    component_keys = (
        "address_street",
        "address_unit",
        "address_city",
        "address_state",
        "address_postal_code",
    )
    present = tuple(key in values for key in component_keys)
    if any(present) and not all(present):
        raise ProjectDataError(f"{dossier} has incomplete structured address keys")
    if all(present):
        return ProjectAddress(
            street=_required(values, "address_street", dossier),
            unit=values["address_unit"],
            city=_required(values, "address_city", dossier),
            state=_required(values, "address_state", dossier),
            postal_code=_required(values, "address_postal_code", dossier),
        )

    full_address = _required(values, "address", dossier)
    parts = [part.strip() for part in full_address.rsplit(",", 3)]
    if len(parts) == 3:
        street, city, region = parts
        unit = ""
    elif len(parts) == 4:
        street, unit, city, region = parts
    else:
        raise ProjectDataError(f"{dossier} full address cannot be separated into US address fields")
    match = re.fullmatch(r"([A-Za-z]{2})\s+(\d{5}(?:-\d{4})?)", region)
    if match is None:
        raise ProjectDataError(f"{dossier} full address must end with state and ZIP")
    return ProjectAddress(
        street=street,
        unit=unit,
        city=city,
        state=match.group(1),
        postal_code=match.group(2),
    )


def load_project_record(project_path: Path) -> ProjectRecord:
    """Load one Atlas 0.2 project dossier through its intake contract."""

    project, dossier, source = _read_source(project_path)
    values = _front_matter(source, dossier)
    try:
        address = _project_address(values, dossier)
        category = _required(values, "project_use_case_category", dossier)
        display = _required(values, "project_use_case", dossier)
        use_case = ProjectUseCase(category, display if category == "Other" else "")
        if use_case.display != display:
            raise ProjectDataError(
                f"{dossier} project use case and category do not match"
            )
        billing = _snapshot(values, "billing", dossier)
        client = _snapshot(values, "client", dossier)
        created = date.fromisoformat(_identity_value(source, "Created", dossier))
        intake = ProjectIntake(
            project_name=_required(values, "project", dossier),
            project_address=address,
            project_use_case=use_case,
            billing_contact_id=billing.id,
            client_contact_id=client.id,
            description=values.get("description", ""),
            created=created,
        )
    except (IntakeError, ValueError) as error:
        raise ProjectDataError(f"{dossier} has invalid Atlas intake data: {error}") from error
    return ProjectRecord(
        path=project,
        intake=intake,
        billing_contact=billing,
        client_contact=client,
        source_digest=hashlib.sha256(source).hexdigest(),
        _source=source,
    )


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


def preview_project_update(
    drive_root: Path, project_path: Path, intake: ProjectIntake
) -> ProjectUpdatePlan:
    """Validate an edit and return its deterministic, non-mutating plan."""

    root = Path(drive_root).resolve(strict=True)
    record = load_project_record(project_path)
    old_path = record.path.resolve(strict=True)
    if old_path.parent != root:
        raise ProjectDataError(f"project folder must be a direct child of drive root: {old_path}")
    planned_intake = replace(intake, created=record.intake.created)
    folder_name = build_folder_name(
        planned_intake.created,
        clean_name_part(planned_intake.project_address.short),
        clean_name_part(planned_intake.description),
    )
    try:
        new_path = validate_project_folder_path(root, folder_name)
    except NamingError as error:
        raise ProjectDataError(str(error)) from error
    try:
        directory = load_contacts(root)
    except ContactError as error:
        raise ProjectDataError(str(error)) from error
    billing = find_contact(directory, planned_intake.billing_contact_id)
    client = find_contact(directory, planned_intake.client_contact_id)
    if billing is None:
        raise ProjectDataError(
            "selected Billing Contact is no longer available; review contacts and retry"
        )
    if client is None:
        raise ProjectDataError(
            "selected Client Contact is no longer available; review contacts and retry"
        )
    index_path = root / INDEX_NAME
    try:
        index_source = index_path.read_bytes()
    except FileNotFoundError:
        index_digest = None
    except OSError as error:
        raise ProjectDataError(f"cannot read project index {index_path}: {error}") from error
    else:
        index_digest = hashlib.sha256(index_source).hexdigest()
    return ProjectUpdatePlan(
        old_path=old_path,
        new_path=new_path,
        intake=planned_intake,
        billing_contact=_contact_snapshot(billing),
        client_contact=_contact_snapshot(client),
        source_digest=record.source_digest,
        contacts_digest=directory._digest,
        index_digest=index_digest,
        _source=record._source,
    )


_yaml = yaml_quote


_table = table_cell


def _contact_values(role: str, contact: ContactSnapshot) -> dict[str, str]:
    return {
        f"{role}_contact_id": contact.id,
        f"{role}_contact_name": contact.full_name,
        f"{role}_contact_email": contact.email,
        f"{role}_contact_phone": contact.phone,
        f"{role}_contact_company": contact.company,
        f"{role}_contact_address": contact.address,
    }


def _render_updated_dossier(plan: ProjectUpdatePlan) -> bytes:
    intake = plan.intake
    front_values = {
        "project": intake.project_name,
        "address": intake.project_address.formatted,
        "address_street": intake.project_address.street,
        "address_unit": intake.project_address.unit,
        "address_city": intake.project_address.city,
        "address_state": intake.project_address.state,
        "address_postal_code": intake.project_address.postal_code,
        "description": intake.description,
        "project_use_case": intake.project_use_case.display,
        "project_use_case_category": intake.project_use_case.category,
        **_contact_values("billing", plan.billing_contact),
        **_contact_values("client", plan.client_contact),
    }
    identity_values = {
        "Project": intake.project_name,
        "Address / BBL": intake.project_address.formatted,
        "Project Use Case": intake.project_use_case.display,
        "Client": plan.client_contact.full_name,
        "Billing Contact": plan.billing_contact.full_name,
        "Billing Email": plan.billing_contact.email,
        "Billing Phone": plan.billing_contact.phone,
        "Billing Company": plan.billing_contact.company,
        "Billing Address": plan.billing_contact.address,
        "Client Contact": plan.client_contact.full_name,
        "Client Email": plan.client_contact.email,
        "Client Phone": plan.client_contact.phone,
        "Client Company": plan.client_contact.company,
        "Client Address": plan.client_contact.address,
        "Descriptor": intake.description,
        "Created": intake.created.isoformat(),
    }

    lines = plan._source[:-2].split(b"\r\n")
    try:
        text_lines = [line.decode("utf-8") for line in lines]
    except UnicodeDecodeError as error:
        raise ProjectDataError(f"project dossier is no longer UTF-8: {error}") from error
    front = _parse_front_matter(text_lines, plan.old_path / "PROJECT.md")
    front_end = front.end
    if "project" not in front.line_of and "name" in front.line_of:
        # Keep the alias the dossier chose rather than adding a second key.
        front_values["name"] = front_values.pop("project")
    output: list[bytes] = list(lines[: front_end])
    appended: list[bytes] = []
    for key, value in front_values.items():
        index = front.line_of.get(key)
        if index is None:
            appended.append(f"{key}: {_yaml(value)}".encode("utf-8"))
            continue
        if front.values[key] == value:
            continue  # unchanged: the line keeps its quoting and comment
        rewritten = f"{key}: {_yaml(value)}"
        comment_at = front.comment_at.get(key)
        if comment_at is not None:
            comment = text_lines[index][comment_at:]
            rewritten += " " * max(1, comment_at - len(rewritten)) + comment
        output[index] = rewritten.encode("utf-8")
    output.extend(appended)
    output.append(lines[front_end])

    body = list(lines[front_end + 1 :])
    heading_indexes = [index for index, line in enumerate(body) if line.startswith(b"# ")]
    if not heading_indexes:
        raise ProjectDataError("project dossier is missing its top heading")
    body[heading_indexes[0]] = f"# {plan.new_path.name}".encode("utf-8")
    seen_identity: set[str] = set()
    in_identity = False
    for index, raw_line in enumerate(body):
        if raw_line == b"## Identity":
            if in_identity:
                raise ProjectDataError("project dossier has duplicate Identity sections")
            in_identity = True
            continue
        if in_identity and raw_line.startswith(b"## "):
            in_identity = False
        if not in_identity:
            continue
        try:
            line = raw_line.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ProjectDataError(f"project dossier is no longer UTF-8: {error}") from error
        for field_name, value in identity_values.items():
            if line.startswith(f"| {field_name} |") and line.endswith("|"):
                if field_name in seen_identity:
                    raise ProjectDataError(
                        f"project dossier has duplicate '{field_name}' Identity rows"
                    )
                body[index] = f"| {field_name} | {_table(value)} |".encode("utf-8")
                seen_identity.add(field_name)
                break
    missing_identity = set(identity_values) - seen_identity
    if missing_identity:
        names = ", ".join(sorted(missing_identity))
        raise ProjectDataError(f"project dossier is missing Identity row(s): {names}")
    return b"\r\n".join((*output, *body)) + b"\r\n"


def _atomic_replace(path: Path, contents: bytes, expected: bytes) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        if path.read_bytes() != expected:
            raise ProjectDataError(
                f"project dossier changed since preview: {path}; review changes and retry"
            )
        os.replace(temporary, path)
        temporary = None
    except ProjectDataError:
        raise
    except OSError as error:
        raise ProjectDataError(
            f"cannot atomically update project dossier {path}: {error}"
        ) from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _same_underlying_path(first: Path, second: Path) -> bool:
    try:
        return os.path.samefile(first, second)
    except OSError:
        return False


def _rename_folder(source: Path, destination: Path) -> None:
    case_only = (
        source.name != destination.name
        and source.name.casefold() == destination.name.casefold()
    )
    if not case_only:
        source.rename(destination)
        return

    temporary = source.with_name(f".{source.name}.atlas-rename-{uuid4().hex}.tmp")
    source.rename(temporary)
    try:
        temporary.rename(destination)
    except OSError as error:
        try:
            temporary.rename(source)
        except OSError as rollback_error:
            raise ProjectDataError(
                f"case-only rename failed: {error}; folder rollback failed: {rollback_error}"
            ) from error
        raise


def _restore_after_index_failure(
    old_path: Path, current_path: Path, original: bytes, updated: bytes
) -> str | None:
    try:
        if str(current_path) != str(old_path):
            if old_path.exists() and not _same_underlying_path(current_path, old_path):
                return f"cannot roll back rename because {old_path} now exists"
            _rename_folder(current_path, old_path)
        _atomic_replace(old_path / "PROJECT.md", original, updated)
    except (OSError, ProjectDataError) as error:
        return str(error)
    return None


def apply_project_update(
    drive_root: Path,
    drive_map: DriveMap,
    plan: ProjectUpdatePlan,
    *,
    allow_rename: bool = False,
) -> ProjectUpdateResult:
    """Apply a previewed edit after rechecking every mutable source."""

    root = Path(drive_root).resolve(strict=True)
    old_path = plan.old_path
    if old_path.parent != root:
        raise ProjectDataError(f"planned project is outside drive root: {old_path}")
    if plan.rename_required and not allow_rename:
        raise ProjectDataError("project folder rename requires allow_rename=True")
    if (
        plan.rename_required
        and plan.new_path.exists()
        and not _same_underlying_path(old_path, plan.new_path)
    ):
        raise ProjectDataError(f"rename destination already exists: {plan.new_path}")
    dossier = old_path / "PROJECT.md"
    try:
        current_source = dossier.read_bytes()
    except OSError as error:
        raise ProjectDataError(f"cannot verify project dossier {dossier}: {error}") from error
    if hashlib.sha256(current_source).hexdigest() != plan.source_digest:
        raise ProjectDataError(
            f"project dossier changed since preview: {dossier}; review changes and retry"
        )
    try:
        directory = load_contacts(root)
    except ContactError as error:
        raise ProjectDataError(str(error)) from error
    if directory._digest != plan.contacts_digest:
        raise ProjectDataError("contact directory changed since preview; review contacts and retry")
    index_path = root / INDEX_NAME
    try:
        current_index = index_path.read_bytes()
    except FileNotFoundError:
        if plan.index_digest is not None:
            raise ProjectDataError(
                "project index changed since preview; review changes and retry"
            ) from None
        current_index = None
    except OSError as error:
        raise ProjectDataError(f"cannot verify project index {index_path}: {error}") from error
    if current_index is not None and (
        plan.index_digest is None
        or hashlib.sha256(current_index).hexdigest() != plan.index_digest
    ):
        raise ProjectDataError("project index changed since preview; review changes and retry")

    updated = _render_updated_dossier(plan)
    try:
        prepared_index_path = preflight_project_index(root, drive_map)
        prepared_index = prepared_index_path.read_bytes()
    except (ProjectIndexError, OSError) as error:
        raise ProjectDataError(f"cannot prepare project index: {error}") from error
    prepared_index_digest = hashlib.sha256(prepared_index).hexdigest()

    _atomic_replace(dossier, updated, current_source)
    current_path = old_path
    if plan.rename_required:
        try:
            _rename_folder(old_path, plan.new_path)
        except (OSError, ProjectDataError) as error:
            try:
                _atomic_replace(dossier, current_source, updated)
            except ProjectDataError as rollback_error:
                raise ProjectDataError(
                    f"cannot rename project folder: {error}; dossier rollback failed: {rollback_error}"
                ) from error
            raise ProjectDataError(
                f"cannot rename project folder: {error}; dossier restored"
            ) from error
        current_path = plan.new_path
    try:
        update_project_index_row(
            root,
            drive_map,
            old_path.name,
            current_path.name,
            plan.intake,
            expected_digest=prepared_index_digest,
        )
    except ProjectIndexError as error:
        rollback_error = _restore_after_index_failure(
            old_path, current_path, current_source, updated
        )
        if rollback_error:
            raise ProjectDataError(
                f"cannot update project index: {error}; project rollback failed: {rollback_error}"
            ) from error
        raise ProjectDataError(f"cannot update project index: {error}; project restored") from error

    from .ops import append_log

    append_log(
        root,
        f"[{current_path.name}] project update: folder {old_path.name} -> {current_path.name}",
    )
    record = load_project_record(current_path)
    return ProjectUpdateResult(
        old_path=old_path,
        path=current_path,
        renamed=plan.rename_required,
        record=record,
    )
