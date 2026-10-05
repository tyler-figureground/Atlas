"""Atlas CLI - every TUI capability as a subcommand; --json is the agent interface.

Exit codes: 0 = clean, 1 = findings/pending work, 2 = error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .core.conform import (
    DONE,
    FAILED,
    NotInvertible,
    Plan,
    action_to_dict,
    apply_plan,
    build_plan,
    build_repair_plan,
    invert_plan,
    measure_plan,
    node_key,
    plan_from_dict,
)
from .core.contacts import (
    Contact,
    ContactDraft,
    ContactError,
    add_contact,
    find_contact,
    load_contacts,
    update_contact,
)
from .core.doctor import report_drive, report_project, report_to_dict
from .core.intake import (
    IntakeError,
    ProjectAddress,
    ProjectIntake,
    ProjectUseCase,
    USE_CASES,
)
from .core.lintmap import lint_map
from .core.mapfile import MapError, find_map, load_map
from .core.ops import OpsError, add_sections, find_empty_dirs, new_project, remove_empty_dirs
from .core.pdfexport import PdfError, export_pdf
from .core.refsets import RefSetError, check_draft, list_sets, studio_ignore
from .core.runs import archive_run, list_runs
from .core.templates import TemplateError
from .core.project_data import (
    ProjectDataError,
    ProjectUpdatePlan,
    ProjectUpdateResult,
    apply_project_update,
    load_project_record,
    preview_project_update,
)
from .core.scan import (
    DEFAULT_MOUNT_ROOT,
    READ,
    UNREADABLE,
    ProjectInventory,
    discover_drives,
    exists_exact,
    is_project_dir,
    list_entries,
    scan_drive,
)
from .core.tree import MAPPED, TreeNode, open_project_tree
from .tui.tokens import filing_style  # the Fault Words; pure data, no Textual


class UsageError(Exception):
    """The command cannot run as asked: a bad argument, a missing drive, or a
    drive Atlas cannot read.

    An error, never a finding. `main` prints it to stderr and exits 2, so a
    script can tell "the drive has drift" (1) from "the command failed" (2).
    """


def _resolve_drive(arg: str | None) -> Path:
    if arg:
        # Absolute: path lengths are measured on it, and Windows sees the
        # absolute path whatever was typed (ADR 0006).
        root = Path(os.path.abspath(arg))
        if not find_map(root):
            raise UsageError(f"no _tools/*-map.json under {root}")
        return root
    cwd = Path.cwd()
    for candidate in (cwd, *cwd.parents):
        if find_map(candidate):
            return candidate
    drives = discover_drives()
    if len(drives) == 1:
        return drives[0]
    if not drives:
        raise UsageError(f"no mapped drives found under {DEFAULT_MOUNT_ROOT}; pass --drive")
    names = ", ".join(d.name for d in drives)
    raise UsageError(f"multiple mapped drives ({names}); pass --drive")


def _scan(root: Path):
    """scan_drive, refusing a drive root it could not list.

    An unreadable root yields zero projects, which doctor used to report as
    "0 conform / 0 drift", exit 0 - a disconnected drive dressed as a clean one.
    """
    inventory = scan_drive(root)
    if not inventory.readable:
        raise UsageError(f"cannot read the drive root {root}: {inventory.error}")
    return inventory


def cmd_lint(args: argparse.Namespace) -> int:
    root = _resolve_drive(args.drive)
    try:
        drive_map = load_map(find_map(root))
    except MapError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    findings = lint_map(drive_map)
    if args.json:
        print(json.dumps([f.__dict__ for f in findings], indent=2))
    else:
        print(f"map: {drive_map.path} (v{drive_map.version})")
        if not findings:
            print("lint: clean")
        for f in findings:
            print(f"  {f.level.upper():5} {f.code:22} {f.message}")
    return 1 if any(f.level == "error" for f in findings) else 0


def cmd_doctor(args: argparse.Namespace) -> int:
    root = _resolve_drive(args.drive)
    try:
        report = report_drive(_scan(root))
    except (MapError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report_to_dict(report), indent=2))
    else:
        counts = report.summary()
        print(f"{report.drive} (map v{report.map_version})  "
              f"{counts['conform']} conform / {counts['drift']} drift / "
              f"{counts['unfiled']} unfiled / {counts['stub']} stub")
        for p in report.projects:
            sections = (f"{p.sections_present} sections" if p.root_readable
                        else "sections unknown")
            print(f"\n[{p.status.upper():7}] {p.name}  ({sections})")
            for item in p.missing_control_plane:
                print(f"    control-plane missing: {item}")
            for src, dst in p.drift:
                print(f"    drift: {src} -> {dst}")
            for h in p.relocations:
                count = "files unknown" if h.file_count is None else f"{h.file_count} files"
                print(f"    relocation pending: {h.source} -> {h.target} ({count})")
            rules = dict(p.sweep_rules)
            for name, dst in p.sweeps:
                because = f" (rule: {rules[name]})" if name in rules else ""
                print(f"    sweep pending: {name} -> {dst}{because}")
            for name in p.unfiled:
                print(f"    unfiled: {name}")
            for line in p.unreadable:
                print(f"    cannot read: {line}")
    # An unreadable folder is pending too: a person has to look (ADR 0004).
    pending = any(p.actionable or p.unfiled or p.unreadable for p in report.projects)
    return 1 if pending else 0


def _resolve_project(root: Path, name: str) -> Path:
    """The project folder called ``name``, looked up the way conform does.

    ``root / name`` alone let "..", "." and absolute paths through, and clean's
    seed and analysis-dir protection is relative to the "project" it is given -
    so `clean --project .. --apply` removed seed sections on another drive. A
    project is one entry in the drive root's own listing, by exact name, that
    the scan would call a project. Nothing else.
    """
    if (not name or name in (".", "..") or "/" in name or "\\" in name
            or ":" in name or not is_project_dir(name)):
        raise UsageError(f"'{name}' is not a project folder name; pass one folder "
                         f"directly under {root}")
    listing = list_entries(root)
    if not listing.readable:
        raise UsageError(f"cannot read {root}: {listing.error}")
    if not any(e.is_dir and e.name == name for e in listing):
        raise UsageError(f"no project folder '{name}' under {root}")
    return root / name


def _contact_to_dict(contact: Contact) -> dict[str, object]:
    return {
        "id": contact.id,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "email": contact.email,
        "phone": contact.phone,
        "company": contact.company,
        "address": contact.address,
        "created_at": contact.created_at,
        "updated_at": contact.updated_at,
    }


def _contact_address(contact: Contact) -> str:
    if not contact.address:
        return ""
    parts = [contact.address["street"]]
    if contact.address.get("unit"):
        parts.append(contact.address["unit"])
    parts.append(
        f"{contact.address['city']}, {contact.address['state']} "
        f"{contact.address['postal_code']}"
    )
    return ", ".join(parts)


def _print_contact(contact: Contact, prefix: str = "") -> None:
    print(
        f"{prefix}{contact.first_name} {contact.last_name} "
        f"<{contact.email}> ({contact.id})"
    )
    if contact.company:
        print(f"  company: {contact.company}")
    if contact.phone:
        print(f"  phone: {contact.phone}")
    if address := _contact_address(contact):
        print(f"  address: {address}")


def _prompt_retain(label: str, current: str, *, clearable: bool = False) -> str:
    instruction = "Enter keeps current"
    if clearable:
        instruction += "; '-' clears"
    value = input(f"{label} [{current}] ({instruction}): ")
    if not value:
        return current
    if clearable and value == "-":
        return ""
    return value


def _prompt_choice_retain(
    label: str, current: str, choices: tuple[str, ...]
) -> str:
    allowed = ", ".join(choices)
    while True:
        value = input(
            f"{label} [{current}] (choices: {allowed}; Enter keeps current): "
        )
        if not value:
            return current
        if value in choices:
            return value
        print(f"Invalid choice. Choose one of: {allowed}")


def cmd_contacts_add(args: argparse.Namespace) -> int:
    root = _resolve_drive(args.drive)
    address = None
    if any(
        (
            args.address_street,
            args.address_unit,
            args.address_city,
            args.address_state,
            args.address_zip,
        )
    ):
        address = {
            "street": args.address_street or "",
            "unit": args.address_unit or "",
            "city": args.address_city or "",
            "state": args.address_state or "",
            "postal_code": args.address_zip or "",
            "country": "US",
        }
    try:
        contact = add_contact(
            root,
            ContactDraft(
                first_name=args.first_name,
                last_name=args.last_name,
                email=args.email,
                phone=args.phone,
                company=args.company,
                address=address,
            ),
        )
    except ContactError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(_contact_to_dict(contact), ensure_ascii=False))
    else:
        _print_contact(contact, "added: ")
    return 0


def cmd_contacts_list(args: argparse.Namespace) -> int:
    root = _resolve_drive(args.drive)
    try:
        contacts = load_contacts(root).contacts
    except ContactError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(
            json.dumps(
                [_contact_to_dict(contact) for contact in contacts],
                ensure_ascii=False,
            )
        )
    else:
        for contact in contacts:
            _print_contact(contact)
        if not contacts:
            print("no contacts")
    return 0


def cmd_contacts_edit(args: argparse.Namespace) -> int:
    root = _resolve_drive(args.drive)
    directory = load_contacts(root)
    current = find_contact(directory, args.contact)
    if current is None:
        print(
            f"error: contact not found: {args.contact!r}. Run 'atlas contacts list' "
            "and retry with an existing contact ID or email.",
            file=sys.stderr,
        )
        return 2
    editable_values = (
        args.first_name,
        args.last_name,
        args.email,
        args.phone,
        args.company,
        args.address_street,
        args.address_unit,
        args.address_city,
        args.address_state,
        args.address_zip,
    )
    scripted = (
        args.json
        or args.yes
        or args.clear_address
        or any(value is not None for value in editable_values)
        or not sys.stdin.isatty()
    )
    if scripted and not args.yes:
        print(
            "error: contact edit requires --yes in non-interactive mode; no changes made",
            file=sys.stderr,
        )
        return 2
    if not scripted:
        previous = current.address or {}
        args.first_name = _prompt_retain("First name", current.first_name)
        args.last_name = _prompt_retain("Last name", current.last_name)
        args.email = _prompt_retain("Email", current.email)
        args.phone = _prompt_retain("Phone", current.phone or "", clearable=True)
        args.company = _prompt_retain("Company", current.company or "", clearable=True)
        args.address_street = _prompt_retain(
            "Mailing street or PO box", previous.get("street", ""), clearable=True
        )
        args.address_unit = _prompt_retain(
            "Mailing unit", previous.get("unit", ""), clearable=True
        )
        args.address_city = _prompt_retain(
            "Mailing city", previous.get("city", ""), clearable=True
        )
        args.address_state = _prompt_retain(
            "Mailing state", previous.get("state", ""), clearable=True
        )
        args.address_zip = _prompt_retain(
            "Mailing ZIP", previous.get("postal_code", ""), clearable=True
        )

    address_flags = (
        args.address_street,
        args.address_unit,
        args.address_city,
        args.address_state,
        args.address_zip,
    )
    if args.clear_address and any(value is not None for value in address_flags):
        print(
            "error: --clear-address cannot be combined with mailing address flags; "
            "no changes made",
            file=sys.stderr,
        )
        return 2
    if args.clear_address:
        address = None
    elif any(value is not None for value in address_flags):
        previous = current.address or {}
        address = {
            "street": (
                args.address_street
                if args.address_street is not None
                else previous.get("street", "")
            ),
            "unit": (
                args.address_unit
                if args.address_unit is not None
                else previous.get("unit", "")
            ),
            "city": (
                args.address_city
                if args.address_city is not None
                else previous.get("city", "")
            ),
            "state": (
                args.address_state
                if args.address_state is not None
                else previous.get("state", "")
            ),
            "postal_code": (
                args.address_zip
                if args.address_zip is not None
                else previous.get("postal_code", "")
            ),
            "country": "US",
        }
    else:
        address = current.address

    updated = update_contact(
        root,
        current.id,
        ContactDraft(
            first_name=(
                args.first_name if args.first_name is not None else current.first_name
            ),
            last_name=(
                args.last_name if args.last_name is not None else current.last_name
            ),
            email=args.email if args.email is not None else current.email,
            phone=args.phone if args.phone is not None else current.phone,
            company=args.company if args.company is not None else current.company,
            address=address,
        ),
        expected_updated_at=current.updated_at,
    )
    if args.json:
        print(json.dumps(_contact_to_dict(updated), ensure_ascii=False))
    else:
        _print_contact(updated, "updated: ")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    root = _resolve_drive(args.drive)
    drive_map = load_map(find_map(root))
    try:
        directory = load_contacts(root)
        billing = find_contact(directory, args.billing_contact)
        if billing is None:
            raise OpsError(f"Billing Contact not found: {args.billing_contact}")
        client_reference = args.client_contact or args.billing_contact
        client = find_contact(directory, client_reference)
        if client is None:
            raise OpsError(f"Client Contact not found: {client_reference}")
        intake = ProjectIntake(
            project_name=args.name,
            project_address=ProjectAddress(
                street=args.street,
                unit=args.unit or "",
                city=args.city,
                state=args.state,
                postal_code=args.zip,
            ),
            project_use_case=ProjectUseCase(args.use_case, args.other_use_case or ""),
            billing_contact_id=billing.id,
            client_contact_id=client.id,
            description=args.desc or "",
        )
        result = new_project(root, drive_map, intake)
    except (ContactError, IntakeError, OpsError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(
            json.dumps(
                {
                    "created": result.folder_name,
                    "path": str(result.path),
                    "seeded": list(result.seeded),
                    "templates": list(result.templates),
                    "project_name": result.intake.project_name,
                    "address": result.intake.project_address.formatted,
                    "description": result.intake.description,
                    "use_case": result.intake.project_use_case.display,
                    "use_case_category": result.intake.project_use_case.category,
                    "billing_contact_id": result.intake.billing_contact.id,
                    "client_contact_id": result.intake.client_contact.id,
                }
            )
        )
    else:
        print(f"created: {result.folder_name}")
        print(f"project: {result.intake.project_name}")
        print(f"address: {result.intake.project_address.formatted}")
        print(f"use case: {result.intake.project_use_case.display}")
        print(f"billing: {result.intake.billing_contact.full_name}")
        print(f"client:  {result.intake.client_contact.full_name}")
        print(f"seed:    {', '.join(result.seeded)}")
        if result.templates:
            print(f"files:   {', '.join(result.templates)}")
        agents = f"{drive_map.agents_file}, " if drive_map.agents_file else ""
        print(f"control: {drive_map.project_file}, {drive_map.decisions_dir}\\, "
              f"{agents}{drive_map.claude_file}, {drive_map.analysis_dir}\\")
    return 0


def _project_update_to_dict(result: ProjectUpdateResult) -> dict[str, object]:
    intake = result.record.intake
    return {
        "old_folder": result.old_path.name,
        "folder": result.path.name,
        "path": str(result.path),
        "renamed": result.renamed,
        "project_name": intake.project_name,
        "address": intake.project_address.formatted,
        "description": intake.description,
        "use_case": intake.project_use_case.display,
        "use_case_category": intake.project_use_case.category,
        "billing_contact_id": intake.billing_contact_id,
        "client_contact_id": intake.client_contact_id,
    }


def _project_update_plan_to_dict(plan: ProjectUpdatePlan) -> dict[str, object]:
    intake = plan.intake
    return {
        "applied": False,
        "rename_required": plan.rename_required,
        "old_folder": plan.old_path.name,
        "folder": plan.old_path.name,
        "path": str(plan.old_path),
        "planned_folder": plan.new_path.name,
        "planned_path": str(plan.new_path),
        "project_name": intake.project_name,
        "address": intake.project_address.formatted,
        "description": intake.description,
        "use_case": intake.project_use_case.display,
        "use_case_category": intake.project_use_case.category,
        "billing_contact_id": intake.billing_contact_id,
        "client_contact_id": intake.client_contact_id,
    }


def cmd_project_edit(args: argparse.Namespace) -> int:
    root = _resolve_drive(args.drive)
    drive_map = load_map(find_map(root))
    project = _resolve_project(root, args.folder)
    record = load_project_record(project, project_file=drive_map.project_file)
    editable_values = (
        args.name,
        args.street,
        args.unit,
        args.city,
        args.state,
        args.zip,
        args.use_case,
        args.other_use_case,
        args.billing_contact,
        args.client_contact,
        args.desc,
    )
    scripted = (
        args.json
        or args.yes
        or args.rename
        or args.dry_run
        or any(value is not None for value in editable_values)
        or not sys.stdin.isatty()
    )
    if scripted and not args.yes and not args.dry_run:
        print(
            "error: project edit requires --yes in non-interactive mode; no changes made",
            file=sys.stderr,
        )
        return 2

    current = record.intake
    if not scripted:
        args.name = _prompt_retain("Project name", current.project_name)
        args.street = _prompt_retain("Project street", current.project_address.street)
        args.unit = _prompt_retain(
            "Project unit", current.project_address.unit, clearable=True
        )
        args.city = _prompt_retain("Project city", current.project_address.city)
        args.state = _prompt_retain("Project state", current.project_address.state)
        args.zip = _prompt_retain("Project ZIP", current.project_address.postal_code)
        args.use_case = _prompt_choice_retain(
            "Project use case", current.project_use_case.category, USE_CASES
        )
        if args.use_case == "Other":
            args.other_use_case = _prompt_retain(
                "Other Project Use Case", current.project_use_case.custom_label
            )
        # Default to the stable contact ID, never the snapshot email: the
        # email may have changed in the directory, or now belong to someone
        # else (ADR 0003).
        args.billing_contact = _prompt_retain(
            f"Billing Contact ID or email (now {record.billing_contact.full_name} "
            f"<{record.billing_contact.email}>)",
            current.billing_contact_id,
        )
        args.client_contact = _prompt_retain(
            f"Client Contact ID or email (now {record.client_contact.full_name} "
            f"<{record.client_contact.email}>)",
            current.client_contact_id,
        )
        args.desc = _prompt_retain(
            "Description", current.description, clearable=True
        )
    category = (
        args.use_case
        if args.use_case is not None
        else current.project_use_case.category
    )
    if args.other_use_case is not None:
        custom_label = args.other_use_case
    elif category == "Other" and current.project_use_case.category == "Other":
        custom_label = current.project_use_case.custom_label
    else:
        custom_label = ""
    directory = load_contacts(root)
    billing_reference = args.billing_contact or current.billing_contact_id
    client_reference = args.client_contact or current.client_contact_id
    billing = find_contact(directory, billing_reference)
    if billing is None:
        raise ProjectDataError(
            f"Billing Contact not found: {billing_reference!r}. Run 'atlas contacts list' "
            "and retry with an existing contact ID or email."
        )
    client = find_contact(directory, client_reference)
    if client is None:
        raise ProjectDataError(
            f"Client Contact not found: {client_reference!r}. Run 'atlas contacts list' "
            "and retry with an existing contact ID or email."
        )
    intake = ProjectIntake(
        project_name=args.name if args.name is not None else current.project_name,
        project_address=ProjectAddress(
            street=(
                args.street
                if args.street is not None
                else current.project_address.street
            ),
            unit=(
                args.unit if args.unit is not None else current.project_address.unit
            ),
            city=(
                args.city if args.city is not None else current.project_address.city
            ),
            state=(
                args.state if args.state is not None else current.project_address.state
            ),
            postal_code=(
                args.zip
                if args.zip is not None
                else current.project_address.postal_code
            ),
        ),
        project_use_case=ProjectUseCase(category, custom_label),
        billing_contact_id=billing.id,
        client_contact_id=client.id,
        description=args.desc if args.desc is not None else current.description,
        created=current.created,
    )
    plan = preview_project_update(
        root,
        project,
        intake,
        expected_digest=record.source_digest,
        project_file=drive_map.project_file,
    )
    if args.dry_run:
        if args.json:
            print(json.dumps(_project_update_plan_to_dict(plan), ensure_ascii=False))
        else:
            print("dry run: no changes made")
            print(f"folder:  {plan.old_path.name} -> {plan.new_path.name}")
            print(f"project: {plan.intake.project_name}")
            print(f"address: {plan.intake.project_address.formatted}")
            print(f"use case: {plan.intake.project_use_case.display}")
            print(f"billing: {plan.billing_contact.full_name}")
            print(f"client:  {plan.client_contact.full_name}")
        return 0
    allow_rename = False
    if plan.rename_required:
        if not args.json:
            print(f"folder rename: {plan.old_path.name} -> {plan.new_path.name}")
        if scripted:
            if not args.rename:
                print(
                    f"error: folder rename planned: {plan.old_path.name} -> "
                    f"{plan.new_path.name}; pass --rename with --yes to apply; "
                    "no changes made",
                    file=sys.stderr,
                )
                return 2
            allow_rename = True
        else:
            confirmation = input("Type yes to rename and save (anything else cancels): ")
            if confirmation.strip().casefold() != "yes":
                print("cancelled: project folder rename not confirmed; no changes made")
                return 1
            allow_rename = True
    result = apply_project_update(
        root,
        drive_map,
        plan,
        allow_rename=allow_rename,
    )
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if args.json:
        print(json.dumps(_project_update_to_dict(result), ensure_ascii=False))
    else:
        print(f"updated: {result.path.name}")
        print(f"folder:  {result.old_path.name} -> {result.path.name}")
        print(f"project: {result.record.intake.project_name}")
        print(f"address: {result.record.intake.project_address.formatted}")
        print(f"use case: {result.record.intake.project_use_case.display}")
        print(f"billing: {result.record.billing_contact.full_name}")
        print(f"client:  {result.record.client_contact.full_name}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    root = _resolve_drive(args.drive)
    drive_map = load_map(find_map(root))
    project = _resolve_project(root, args.project)
    try:
        created = add_sections(root, drive_map, project, args.section)
    except OpsError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"created": created}))
    else:
        for rel in created:
            print(f"created: {rel}")
        if not created:
            print("nothing to create (all requested folders already exist)")
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    root = _resolve_drive(args.drive)
    drive_map = load_map(find_map(root))
    project = _resolve_project(root, args.project)
    empties = find_empty_dirs(project, drive_map, include_seeds=args.include_seeds)
    if not args.apply:
        if args.json:
            print(json.dumps({"empty": empties, "applied": False}))
        else:
            print(f"{len(empties)} empty folder(s)" + (":" if empties else ""))
            for rel in empties:
                print(f"  {rel}")
            if empties:
                print("(dry run - pass --apply to remove)")
        return 1 if empties else 0
    removed = remove_empty_dirs(root, project, empties)
    if args.json:
        print(json.dumps({"removed": removed, "applied": True}))
    else:
        for rel in removed:
            print(f"removed: {rel}")
    return 0


def cmd_runs(args: argparse.Namespace) -> int:
    """List agent runs and zip the closed ones (ADR 0011). Dry run by default."""
    root = _resolve_drive(args.drive)
    m = load_map(find_map(root))
    if args.all and args.project:
        raise UsageError("--all cannot be combined with --project")
    if args.all:
        projects = [p.path for p in _scan(root).projects]
    elif args.project:
        projects = [_resolve_project(root, args.project)]
    else:
        raise UsageError("pass --project <name> or --all")
    days = args.days if args.days is not None else m.run_retention_days
    if days < 1:
        raise UsageError("--days must be 1 or more")

    report = []
    pending = 0
    for project in projects:
        runs = list_runs(project, m)
        entries = []
        for run in runs:
            closed = run.closed(days)
            entry = {"run": run.name, "files": run.files, "bytes": run.bytes,
                     "idle_days": run.idle_days, "referenced_by": list(run.referenced_by),
                     "unreadable": list(run.unreadable), "closed": closed}
            if closed and args.apply:
                result = archive_run(root, project, m, run)
                entry.update(status=result.status, note=result.note, archive=result.archive or None)
            elif closed:
                pending += 1
            entries.append(entry)
        if entries:
            report.append({"project": project.name, "runs": entries})

    if args.json:
        print(json.dumps({"retention_days": days, "applied": args.apply, "projects": report}, indent=2))
    else:
        for item in report:
            print(item["project"])
            for e in item["runs"]:
                if "status" in e:
                    state = f"{e['status']}: {e['note']}"
                elif e["closed"]:
                    state = "closed - would archive"
                elif e["referenced_by"]:
                    state = f"open - named in {', '.join(e['referenced_by'])}"
                elif e["unreadable"]:
                    state = "open - part could not be read"
                else:
                    state = f"open - idle {e['idle_days']} of {days} days"
                print(f"  {e['run']}  ({e['files']} files)  {state}")
        if not report:
            print("no agent runs")
        elif pending:
            print(f"\n{pending} closed run(s) (dry run - pass --apply to zip them)")
    return 1 if pending else 0


REFERENCE_SETS_ENV = "ATLAS_REFERENCE_SETS"


def _reference_root(args: argparse.Namespace) -> Path:
    """--root, else $ATLAS_REFERENCE_SETS, else the drive map's top-level
    ``referenceSets``. An absolute path, and deliberately not in controlPlane:
    the sets live on the library drive, and every controlPlane path is
    project-relative."""
    if args.root:
        return Path(os.path.abspath(args.root))
    if os.environ.get(REFERENCE_SETS_ENV):
        return Path(os.environ[REFERENCE_SETS_ENV])
    raw = json.loads(find_map(_resolve_drive(args.drive)).read_text(encoding="utf-8"))
    value = raw.get("referenceSets", "") if isinstance(raw, dict) else ""
    if not isinstance(value, str) or not value:
        raise UsageError("no reference sets folder: pass --root, set "
                         f"{REFERENCE_SETS_ENV}, or add referenceSets to the map")
    return Path(value)


def cmd_refs(args: argparse.Namespace) -> int:
    """List Reference Sets (ADR 0015): status, review dates, problems. Read-only."""
    from datetime import date
    root = _reference_root(args)
    today = date.today()
    rows = []
    for refset in list_sets(root):
        rows.append({
            "type": refset.type, "title": refset.title, "status": refset.status,
            "entity": refset.entity, "reviewed": refset.reviewed,
            "next_review": refset.next_review, "stale": refset.stale(today),
            "exemplars": [e.id for e in refset.exemplars],
            "problems": refset.problems(), "folder": str(refset.folder),
        })
    flagged = sum(1 for r in rows if r["problems"] or r["stale"])
    if args.json:
        print(json.dumps({"root": str(root), "sets": rows}, indent=2))
    else:
        for r in rows:
            state = r["status"] or "no status"
            if r["stale"]:
                state += ", STALE"
            print(f"{r['type'] or '?':20} {state:22} {' '.join(r['exemplars'])}")
            for problem in r["problems"]:
                print(f"  - {problem}")
        if not rows:
            print(f"no reference sets under {root}")
    return 1 if flagged else 0


def cmd_refs_check(args: argparse.Namespace) -> int:
    """Grep a draft for every opened exemplar's leak list. 1 = leaks found."""
    root = _reference_root(args)
    draft = Path(args.draft)
    if not draft.is_file():
        raise UsageError(f"no such draft: {draft}")
    leaks, checked = check_draft(draft, list_sets(root), set_type=args.type,
                                 exemplar_ids=tuple(args.exemplar or ()),
                                 project=args.project, ignore=studio_ignore(root))
    if args.json:
        print(json.dumps({"draft": str(draft), "checked": checked,
                          "leaks": [vars(leak) for leak in leaks]}, indent=2))
    else:
        for leak in leaks:
            print(f"{draft.name}:{leak.line}: {leak.set} {leak.exemplar} owns "
                  f"{leak.string!r} - {leak.text}")
        print(f"{len(leaks)} leak(s); checked {', '.join(checked) or 'no exemplars'}")
    return 1 if leaks else 0


def cmd_pdf(args: argparse.Namespace) -> int:
    """Print a Markdown deliverable to a PDF beside it, for reading and sending."""
    result = export_pdf(Path(args.source), Path(args.out) if args.out else None, force=args.force)
    if args.json:
        print(json.dumps({"source": str(result.source), "pdf": str(result.pdf),
                          "replaced": result.replaced}, indent=2))
    else:
        print(f"{'replaced' if result.replaced else 'wrote'} {result.pdf}")
    return 0


def cmd_tree(args: argparse.Namespace) -> int:
    """The tree's facts: Filing State and Load State below the project root.

    A thin wrapper over ``core.tree`` (ticket 24, ADR 0008) - the TUI's seam
    with a second consumer that is not a widget. ``--depth`` is the cost
    control the TUI gets from lazy expansion: one enumeration per folder read,
    never a walk. A folder at the last level is left Unread and carries no
    counts, because an unread count is not zero.
    """
    if args.depth < 1:
        raise UsageError("--depth must be 1 or more")
    root = _resolve_drive(args.drive)
    m = load_map(find_map(root))
    project = _resolve_project(root, args.project)
    inv = ProjectInventory(path=project, name=project.name, root_entries=list_entries(project))
    tree = open_project_tree(inv, m, report_project(inv, m))

    # Read first, describe after: a folder's own Load State and counts change
    # once its children are read, and ``children`` hands out values.
    # Level k's listings give the nodes shown at depth k-1 their counts, so
    # --depth N reads N levels and shows N; the deepest shown stay Unread.
    level = [""]
    for _ in range(args.depth):
        level = [n.key for key in level for n in tree.children(key)
                 if n.is_dir and tree.load_state(n.key) != UNREADABLE]
    outline: list[tuple[int, TreeNode]] = []

    def describe(key: str, depth: int) -> None:
        for node in tree.children(key):
            outline.append((depth, node))
            if node.is_dir and depth + 1 < args.depth and node.load == READ:
                describe(node.key, depth + 1)

    describe("", 0)
    unmet = tree.expectations()
    root_load = tree.load_state("")
    findings = (root_load != READ or unmet
                or any(n.filing != MAPPED or n.load == UNREADABLE for _d, n in outline))

    if args.json:
        nodes = {}
        for _depth, node in outline:
            facts: dict[str, object] = {"name": node.name, "is_dir": node.is_dir,
                                        "filing": node.filing}
            if node.is_dir:
                facts["load"] = node.load
                if node.load == READ:
                    facts["folders"] = node.folders
                    facts["files"] = node.files
            nodes[node.key] = facts
        print(json.dumps({
            "drive": m.drive, "project": project.name, "depth": args.depth,
            "load": root_load, "nodes": nodes,
            "expectations": [{"path": e.path, "kind": e.kind, "repairable": e.repairable}
                             for e in unmet],
        }, indent=2))
        return 1 if findings else 0

    print(f"{project.name}" + ("" if root_load == READ else f"  [{root_load}]"))
    for depth, node in outline:
        name = f"{node.name}/" if node.is_dir else node.name
        facts = []
        if node.filing != MAPPED:
            facts.append(filing_style(node.filing).label)
        if node.is_dir and node.load == READ:
            facts.append(f"{node.folders} folders, {node.files} files")
        elif node.is_dir and node.load == UNREADABLE:
            facts.append("cannot read")
        detail = f"  ({'; '.join(facts)})" if facts else ""
        print(f"{'  ' * (depth + 1)}{name}{detail}")
    if unmet:
        print("\nmissing:")
        for e in unmet:
            repair = "  (conform can backfill)" if e.repairable else ""
            print(f"  {e.path}{repair}")
    return 1 if findings else 0


def cmd_revert(args: argparse.Namespace, root: Path, m) -> int:
    """Undo an applied conform from the manifest it printed.

    The CLI has no session, so it cannot hold the TUI's undo stack (ADR 0006:
    in memory, one per Project). What it can do is take back what it printed -
    `--json` out, `--revert` in - which makes `invert_plan` reachable from
    outside without Atlas persisting any state of its own to the drive.
    """
    manifest = Path(args.revert)
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: cannot read {manifest}: {error}", file=sys.stderr)
        return 2

    plans = payload if isinstance(payload, list) else [payload]
    try:
        for p in plans:
            # A manifest from drive A must never apply to a same-named project
            # on drive B. One without a drive cannot prove where it came from.
            if not isinstance(p, dict) or p.get("drive") != m.drive:
                found = p.get("drive") if isinstance(p, dict) else None
                print(f"error: {manifest} is from drive {found or '(unnamed)'}, "
                      f"not {m.drive}; nothing moved", file=sys.stderr)
                return 2
        inverses = [invert_plan(plan_from_dict(p)) for p in plans]
    except NotInvertible as error:
        print(f"error: cannot reverse this manifest: {error}", file=sys.stderr)
        return 2
    except (OpsError, KeyError, TypeError) as error:
        print(f"error: cannot read {manifest}: {error}", file=sys.stderr)
        return 2

    # Every project and every precondition before anything moves: a
    # multi-project manifest must not stop halfway. The guard an undo needs is
    # "is each thing still where the repair left it" - checked by exact name.
    for inverse in inverses:
        project_path = _resolve_project(root, inverse.project)
        for action in inverse.actions:
            if not exists_exact(project_path, node_key(action.src)):
                print(f"error: {inverse.project}/{action.src} is no longer where the "
                      f"repair left it; nothing moved", file=sys.stderr)
                return 2
    # Undo moves things too: its preview carries the MAX_PATH warning.
    inverses = [measure_plan(inverse, root / inverse.project) for inverse in inverses]

    if not args.apply:
        _print_plans(inverses, args, m.drive, applied=False)
        return 1 if any(not p.empty for p in inverses) else 0

    results = [apply_plan(root, root / inverse.project, m, inverse) for inverse in inverses]
    _print_plans(results, args, m.drive, applied=True)
    if any(a.status == FAILED for p in results for a in p.actions):
        return 2
    return 1 if any(a.status != DONE for p in results for a in p.actions) else 0


def _action_line(a) -> str:
    status = f" [{a.status}]" if a.status else ""
    note = f"  ({a.note})" if a.note else ""
    files = f" ({a.file_count} files)" if a.file_count else ""
    src = f"{a.src} -> " if a.src else ""
    warning = f"  [path {a.path_length} > 260]" if a.path_warning else ""
    return f"    {a.kind:9} {src}{a.dst}{files}{status}{note}{warning}"


def _print_plans(plans, args: argparse.Namespace, drive: str, *, applied: bool) -> None:
    """Plans in conform's shapes: JSON a later --revert can read, or text."""
    if args.json:
        print(json.dumps([
            {"drive": drive, "project": plan.project,
             "actions": [action_to_dict(a) for a in plan.actions]}
            for plan in plans
        ], indent=2))
        return
    for plan in plans:
        print(f"[{'APPLIED' if applied else 'PLAN':7}] {plan.project}")
        for a in plan.actions:
            print(_action_line(a))
    if not applied and any(not p.empty for p in plans):
        print("\n(dry run - pass --apply to perform)")


def cmd_conform(args: argparse.Namespace) -> int:
    root = _resolve_drive(args.drive)
    inventory = _scan(root)
    m = inventory.map
    if args.revert:
        return cmd_revert(args, root, m)
    if args.all and (args.project or args.node):
        # --all used to win silently, dropping --project and planning --node
        # in every project on the drive.
        print("error: --all cannot be combined with --project or --node", file=sys.stderr)
        return 2
    if args.node and not args.project:
        # A Node Key is project-relative, so the same key names a different
        # folder in every project. Drive-wide is meaningless here.
        print("error: --node needs --project <name>", file=sys.stderr)
        return 2
    if args.all:
        targets = list(inventory.projects)
    else:
        if not args.project:
            print("error: pass --project <name> or --all", file=sys.stderr)
            return 2
        targets = [p for p in inventory.projects if p.name == args.project]
        if not targets:
            print(f"error: no project folder '{args.project}' under {root}", file=sys.stderr)
            return 2

    only = set(args.only) if args.only else None
    results = []
    pending = False
    # What conform cannot repair but doctor still reports: only a person can
    # decide where an Unfiled item belongs. Not "OK", and not exit 0.
    leftovers: dict[str, int] = {}
    # Projects, or parts of them, Atlas could not read. Never repaired - what
    # cannot be read cannot be planned - and never reported as fine.
    unread: dict[str, tuple[str, ...]] = {}
    for inv in targets:
        report = report_project(inv, m)
        if report.unreadable:
            unread[inv.name] = report.unreadable
        if not report.root_readable:
            results.append(Plan(project=inv.name, actions=()))
            continue
        if not args.node and report.unfiled:
            leftovers[inv.name] = len(report.unfiled)
        if args.node:
            plan = build_repair_plan(report, m, args.node, project=inv.path)
            key = node_key(args.node)
            if plan.empty and not exists_exact(inv.path, key):
                # "Needs no repair" is a claim about a node Atlas looked at. A
                # path that matched nothing and is not on disk is a typo.
                print(f"error: no such node '{key}' in {inv.name}", file=sys.stderr)
                return 2
        else:
            plan = build_plan(report, m, project=inv.path)
        if plan.empty:
            results.append(plan)
            continue
        if args.apply:
            results.append(apply_plan(root, inv.path, m, plan, only=only))
        else:
            results.append(plan)
            pending = True

    if args.json:
        # "drive" lets --revert refuse a manifest from another drive.
        print(json.dumps([
            {"drive": m.drive, "project": plan.project,
             "actions": [action_to_dict(a) for a in plan.actions]}
            for plan in results
        ], indent=2))
    else:
        for plan in results:
            left = leftovers.get(plan.project, 0)
            cannot = unread.get(plan.project, ())
            if plan.empty:
                if cannot:
                    print(f"[REVIEW ] {plan.project}: cannot read {cannot[0]}; "
                          f"nothing changed")
                elif args.node:
                    print(f"[OK     ] {plan.project}: {args.node} needs no repair")
                elif left:
                    print(f"[REVIEW ] {plan.project}: nothing Atlas can repair; "
                          f"{left} item(s) need a person")
                else:
                    print(f"[OK     ] {plan.project}: conforms already")
                continue
            print(f"[{'APPLIED' if args.apply else 'PLAN':7}] {plan.project}")
            for a in plan.actions:
                print(_action_line(a))
            if left:
                print(f"    {left} unfiled item(s) need a person")
            for line in cannot:
                print(f"    cannot read: {line}")
        if not args.apply and pending:
            print("\n(dry run - pass --apply to perform)")
    if args.apply:
        if any(a.status == FAILED for plan in results for a in plan.actions):
            # An OS error stopped an action part-way. The JSON above carries
            # what moved before it, so --revert can still put it back.
            return 2
        conflicts = any(a.status == "conflict" for plan in results for a in plan.actions)
        return 1 if conflicts or leftovers or unread else 0
    return 1 if pending or leftovers or unread else 0


def _utf8_streams() -> None:
    """Write UTF-8 whatever the pipe's default encoding.

    A redirected stdout on Windows is cp1252, and a project or contact name with
    a character outside it would crash the print - after the command had
    already written to the drive, so the retry fails as a duplicate. Only the
    encoding changes; a stream that cannot be reconfigured is left alone.
    """
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if encoding == "utf8":
            continue
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _utf8_streams()
    parser = argparse.ArgumentParser(prog="atlas", description="Map-driven studio drive tooling.")
    parser.add_argument("--version", action="version", version=f"atlas {__version__}")
    # The console's own drive. A separate dest: a subcommand's --drive default
    # would otherwise overwrite it in the shared namespace.
    parser.add_argument("--drive", dest="console_drive", metavar="DRIVE",
                        help="open the console on this drive root instead of the drive picker")
    sub = parser.add_subparsers(dest="command")

    for name, fn, help_text in (
        ("lint", cmd_lint, "validate the drive's map file"),
        ("doctor", cmd_doctor, "read-only drive-wide conformance report"),
        ("new", cmd_new, "create a project (seed sections + control plane + index row)"),
        ("add", cmd_add, "add blessed folders to a project"),
        ("clean", cmd_clean, "list/remove file-empty folders (rmdir-only; dry run by default)"),
        ("conform", cmd_conform, "plan/apply conformance: backfill, renames, relocations, sweeps"),
        ("tree", cmd_tree, "one project's folders and files: Filing State, Load State, "
                           "unmet Expectations (read-only)"),
        ("runs", cmd_runs, "list agent runs; zip closed ones into the archive (dry run by default)"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--drive", help="drive root (default: walk up from cwd, else auto-discover)")
        p.add_argument("--json", action="store_true", help="machine-readable output")
        p.set_defaults(fn=fn)

    sub.choices["tree"].add_argument("project", help="project folder name")
    sub.choices["tree"].add_argument(
        "--depth", type=int, default=1,
        help="levels to read below the project root (default 1). Each level is one "
             "enumeration per folder; the deepest level shown stays Unread")

    contacts = sub.add_parser("contacts", help="list, add, and edit shared contacts")
    contact_commands = contacts.add_subparsers(dest="contacts_command", required=True)
    contacts_list = contact_commands.add_parser("list", help="list shared contacts")
    contacts_list.add_argument(
        "--drive", help="drive root (default: walk up from cwd, else auto-discover)"
    )
    contacts_list.add_argument("--json", action="store_true", help="machine-readable output")
    contacts_list.set_defaults(fn=cmd_contacts_list)
    contacts_add = contact_commands.add_parser("add", help="add a shared contact")
    contacts_add.add_argument(
        "--drive", help="drive root (default: walk up from cwd, else auto-discover)"
    )
    contacts_add.add_argument("--json", action="store_true", help="machine-readable output")
    contacts_add.add_argument("--first-name", required=True)
    contacts_add.add_argument("--last-name", required=True)
    contacts_add.add_argument("--email", required=True)
    contacts_add.add_argument("--phone")
    contacts_add.add_argument("--company")
    contacts_add.add_argument("--address-street")
    contacts_add.add_argument("--address-unit")
    contacts_add.add_argument("--address-city")
    contacts_add.add_argument("--address-state")
    contacts_add.add_argument("--address-zip")
    contacts_add.set_defaults(fn=cmd_contacts_add)
    contacts_edit = contact_commands.add_parser("edit", help="edit a shared contact")
    contacts_edit.add_argument("contact", help="contact ID or email")
    contacts_edit.add_argument(
        "--drive", help="drive root (default: walk up from cwd, else auto-discover)"
    )
    contacts_edit.add_argument(
        "--json", action="store_true", help="machine-readable output; never prompts"
    )
    contacts_edit.add_argument(
        "--yes", action="store_true", help="confirm a non-interactive edit"
    )
    contacts_edit.add_argument("--first-name")
    contacts_edit.add_argument("--last-name")
    contacts_edit.add_argument("--email")
    contacts_edit.add_argument("--phone", help="use an empty value to clear")
    contacts_edit.add_argument("--company", help="use an empty value to clear")
    contacts_edit.add_argument("--address-street", help="physical street or PO box")
    contacts_edit.add_argument("--address-unit")
    contacts_edit.add_argument("--address-city")
    contacts_edit.add_argument("--address-state")
    contacts_edit.add_argument("--address-zip")
    contacts_edit.add_argument("--clear-address", action="store_true")
    contacts_edit.set_defaults(fn=cmd_contacts_edit)

    project = sub.add_parser("project", help="manage an existing project")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    project_edit = project_commands.add_parser("edit", help="edit existing project intake")
    project_edit.add_argument("folder", help="project folder name")
    project_edit.add_argument(
        "--drive", help="drive root (default: walk up from cwd, else auto-discover)"
    )
    project_edit.add_argument(
        "--json", action="store_true", help="machine-readable output; never prompts"
    )
    project_edit.add_argument(
        "--yes",
        action="store_true",
        help="confirm a non-interactive edit",
    )
    project_edit.add_argument(
        "--rename",
        action="store_true",
        help="allow a confirmed non-interactive edit to rename the project folder",
    )
    project_edit.add_argument(
        "--dry-run",
        action="store_true",
        help="preview a non-interactive edit without changing files",
    )
    project_edit.add_argument("--name", help="project name")
    project_edit.add_argument("--street", help="project street address")
    project_edit.add_argument(
        "--unit", help="project address unit; use an empty value to clear"
    )
    project_edit.add_argument("--city", help="project address city")
    project_edit.add_argument("--state", help="two-letter US state")
    project_edit.add_argument("--zip", help="ZIP or ZIP+4")
    project_edit.add_argument("--use-case", choices=USE_CASES)
    project_edit.add_argument("--other-use-case")
    project_edit.add_argument("--billing-contact", help="contact ID or email")
    project_edit.add_argument("--client-contact", help="contact ID or email")
    project_edit.add_argument(
        "--desc",
        "--description",
        dest="desc",
        help="short descriptor; use an empty value to clear",
    )
    project_edit.set_defaults(fn=cmd_project_edit)

    refs = sub.add_parser("refs", help="reference sets: list them, check a draft for leaks (read-only)")
    refs.add_argument("--root", help="reference sets folder (default: $ATLAS_REFERENCE_SETS, "
                                     "else the map's referenceSets)")
    refs.add_argument("--drive", help="drive root whose map names the reference sets folder")
    refs.add_argument("--json", action="store_true", help="machine-readable output")
    refs.set_defaults(fn=cmd_refs)
    refs_commands = refs.add_subparsers(dest="refs_command")
    refs_check = refs_commands.add_parser(
        "check", help="grep a draft for the leak lists of the exemplars it used")
    refs_check.add_argument("draft", help="the file to check")
    refs_check.add_argument("--type", help="only this set (default: the draft's reference "
                                           "marker, else every set)")
    refs_check.add_argument("--exemplar", action="append", help="only this exemplar ID (repeatable)")
    refs_check.add_argument("--project", help="the project the draft is for, when it is kept "
                                              "outside that project's folder: its own exemplars are skipped")
    refs_check.add_argument("--root", default=argparse.SUPPRESS)
    refs_check.add_argument("--drive", default=argparse.SUPPRESS)
    refs_check.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    refs_check.set_defaults(fn=cmd_refs_check)

    pdf = sub.add_parser("pdf", help="print a Markdown deliverable to a PDF beside it (Edge/Chrome)")
    pdf.add_argument("source", help="the .md file")
    pdf.add_argument("--out", help="PDF path (default: beside the source, same name)")
    pdf.add_argument("--force", action="store_true",
                     help="replace a PDF that is newer than its source")
    pdf.add_argument("--json", action="store_true", help="machine-readable output")
    pdf.set_defaults(fn=cmd_pdf)

    sub.choices["new"].add_argument("--name", required=True, help="project name")
    sub.choices["new"].add_argument("--street", required=True, help="project street address")
    sub.choices["new"].add_argument("--unit", default="", help="project address unit")
    sub.choices["new"].add_argument("--city", required=True, help="project address city")
    sub.choices["new"].add_argument("--state", required=True, help="two-letter US state")
    sub.choices["new"].add_argument("--zip", required=True, help="ZIP or ZIP+4")
    sub.choices["new"].add_argument("--use-case", required=True, choices=USE_CASES)
    sub.choices["new"].add_argument("--other-use-case", default="")
    sub.choices["new"].add_argument(
        "--billing-contact", required=True, help="contact ID or email"
    )
    sub.choices["new"].add_argument(
        "--client-contact", help="contact ID or email (default: billing contact)"
    )
    sub.choices["new"].add_argument("--desc", default="", help="short descriptor (e.g. ADU, Renovation)")
    sub.choices["add"].add_argument("--project", required=True, help="project folder name")
    sub.choices["add"].add_argument("--section", action="append", required=True,
                                    help="'NN Section' or 'NN Section/Child' (repeatable)")
    sub.choices["clean"].add_argument("--project", required=True, help="project folder name")
    sub.choices["clean"].add_argument("--apply", action="store_true", help="actually remove")
    sub.choices["clean"].add_argument("--include-seeds", action="store_true",
                                      help="allow removing empty seed sections too")
    sub.choices["runs"].add_argument("--project", help="project folder name")
    sub.choices["runs"].add_argument("--all", action="store_true", help="every project on the drive")
    sub.choices["runs"].add_argument("--apply", action="store_true", help="zip closed runs and remove their folders")
    sub.choices["runs"].add_argument("--days", type=int,
                                     help="idle days before a run is closed (default: the map's runRetentionDays, else 14)")
    sub.choices["conform"].add_argument("--project", help="project folder name")
    sub.choices["conform"].add_argument(
        "--revert", metavar="FILE",
        help="undo an applied conform from the --json manifest it printed")
    sub.choices["conform"].add_argument(
        "--node",
        help="repair one node by its project-relative path; needs --project. "
             "Unlike --only, which filters by action class, this names a folder")
    sub.choices["conform"].add_argument("--all", action="store_true", help="every project on the drive")
    sub.choices["conform"].add_argument("--apply", action="store_true", help="perform the plan")
    sub.choices["conform"].add_argument("--only", action="append",
                                        choices=["backfill", "rename", "relocate", "sweep"],
                                        help="limit apply to an action class (repeatable)")

    args = parser.parse_args(argv)
    if args.command is None:
        from .tui.app import run_tui  # lazy: textual import only when needed
        drive = _resolve_drive(args.console_drive) if args.console_drive else None
        return run_tui(drive)
    try:
        return args.fn(args)
    except (ContactError, IntakeError, OpsError, ProjectDataError, MapError,
            TemplateError, UsageError, RefSetError, PdfError, OSError) as error:
        # Every error exits 2, never 1: 1 means the drive has findings. An
        # OSError here is the backstop - a locked file, a vanished mount - and is
        # reported, not raised as a traceback over empty --json stdout.
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
