"""Atlas CLI - every TUI capability as a subcommand; --json is the agent interface.

Exit codes: 0 = clean, 1 = findings/pending work, 2 = error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core.conform import (
    NotInvertible,
    action_to_dict,
    apply_plan,
    build_plan,
    build_repair_plan,
    invert_plan,
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
from .core.project_data import (
    ProjectDataError,
    ProjectUpdatePlan,
    ProjectUpdateResult,
    apply_project_update,
    load_project_record,
    preview_project_update,
)
from .core.scan import DEFAULT_MOUNT_ROOT, discover_drives, scan_drive


class UsageError(Exception):
    """The command cannot run as asked: a bad argument or a missing drive.

    An error, never a finding. `main` prints it to stderr and exits 2, so a
    script can tell "the drive has drift" (1) from "the command failed" (2).
    """


def _resolve_drive(arg: str | None) -> Path:
    if arg:
        root = Path(arg)
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
        report = report_drive(scan_drive(root))
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
            print(f"\n[{p.status.upper():7}] {p.name}  ({p.sections_present} sections)")
            for item in p.missing_control_plane:
                print(f"    control-plane missing: {item}")
            for src, dst in p.drift:
                print(f"    drift: {src} -> {dst}")
            for h in p.relocations:
                print(f"    relocation pending: {h.source} -> {h.target} ({h.file_count} files)")
            rules = dict(p.sweep_rules)
            for name, dst in p.sweeps:
                because = f" (rule: {rules[name]})" if name in rules else ""
                print(f"    sweep pending: {name} -> {dst}{because}")
            for name in p.unfiled:
                print(f"    unfiled: {name}")
    pending = any(p.actionable or p.unfiled for p in report.projects)
    return 1 if pending else 0


def _resolve_project(root: Path, name: str) -> Path:
    project = root / name
    if not project.is_dir():
        raise UsageError(f"no project folder '{name}' under {root}")
    return project


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
    record = load_project_record(project)
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
        args.billing_contact = _prompt_retain(
            "Billing Contact ID or email", record.billing_contact.email
        )
        args.client_contact = _prompt_retain(
            "Client Contact ID or email", record.client_contact.email
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
    plan = preview_project_update(root, project, intake)
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
        inverses = [(p["project"], invert_plan(plan_from_dict(p))) for p in plans]
    except NotInvertible as error:
        print(f"error: cannot reverse this manifest: {error}", file=sys.stderr)
        return 2
    except (OpsError, KeyError, TypeError) as error:
        print(f"error: cannot read {manifest}: {error}", file=sys.stderr)
        return 2

    for name, inverse in inverses:
        project_path = root / name
        if not project_path.is_dir():
            print(f"error: no project folder '{name}' under {root}", file=sys.stderr)
            return 2
        done = apply_plan(root, project_path, m, inverse)
        for a in done.actions:
            print(f"    {a.kind:9} {a.src} -> {a.dst} [{a.status}]")
    return 0


def cmd_conform(args: argparse.Namespace) -> int:
    root = _resolve_drive(args.drive)
    inventory = scan_drive(root)
    m = inventory.map
    if args.revert:
        return cmd_revert(args, root, m)
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
    for inv in targets:
        report = report_project(inv, m)
        if not args.node and report.unfiled:
            leftovers[inv.name] = len(report.unfiled)
        if args.node:
            plan = build_repair_plan(report, m, args.node, project=inv.path)
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
        print(json.dumps([
            {"project": plan.project,
             "actions": [action_to_dict(a) for a in plan.actions]}
            for plan in results
        ], indent=2))
    else:
        for plan in results:
            left = leftovers.get(plan.project, 0)
            if plan.empty:
                if args.node:
                    print(f"[OK     ] {plan.project}: {args.node} needs no repair")
                elif left:
                    print(f"[REVIEW ] {plan.project}: nothing Atlas can repair; "
                          f"{left} item(s) need a person")
                else:
                    print(f"[OK     ] {plan.project}: conforms already")
                continue
            print(f"[{'APPLIED' if args.apply else 'PLAN':7}] {plan.project}")
            for a in plan.actions:
                status = f" [{a.status}]" if a.status else ""
                note = f"  ({a.note})" if a.note else ""
                files = f" ({a.file_count} files)" if a.file_count else ""
                src = f"{a.src} -> " if a.src else ""
                warning = f"  [path {a.path_length} > 260]" if a.path_warning else ""
                print(f"    {a.kind:9} {src}{a.dst}{files}{status}{note}{warning}")
            if left:
                print(f"    {left} unfiled item(s) need a person")
        if not args.apply and pending:
            print("\n(dry run - pass --apply to perform)")
    if args.apply:
        conflicts = any(a.status == "conflict" for plan in results for a in plan.actions)
        return 1 if conflicts or leftovers else 0
    return 1 if pending or leftovers else 0


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
    sub = parser.add_subparsers(dest="command")

    for name, fn, help_text in (
        ("lint", cmd_lint, "validate the drive's map file"),
        ("doctor", cmd_doctor, "read-only drive-wide conformance report"),
        ("new", cmd_new, "create a project (seed sections + control plane + index row)"),
        ("add", cmd_add, "add blessed folders to a project"),
        ("clean", cmd_clean, "list/remove file-empty folders (rmdir-only; dry run by default)"),
        ("conform", cmd_conform, "plan/apply conformance: backfill, renames, relocations, sweeps"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--drive", help="drive root (default: walk up from cwd, else auto-discover)")
        p.add_argument("--json", action="store_true", help="machine-readable output")
        p.set_defaults(fn=fn)

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
        return run_tui()
    try:
        return args.fn(args)
    except (ContactError, IntakeError, OpsError, ProjectDataError, MapError,
            UsageError, OSError) as error:
        # Every error exits 2, never 1: 1 means the drive has findings. An
        # OSError here is the backstop - a locked file, a vanished mount - and is
        # reported, not raised as a traceback over empty --json stdout.
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
