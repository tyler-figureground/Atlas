"""Atlas CLI - every TUI capability as a subcommand; --json is the agent interface.

Exit codes: 0 = clean, 1 = findings/pending work, 2 = error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

from . import __version__
from .core.archive import (
    ArchiveGuard,
    apply_archive_plan,
    archive_plan_from_dict,
    archive_plan_to_dict,
    build_archive_plan,
    build_unarchive_plan,
    invert_archive_plan,
)
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
from .core.contentindex import build_index, index_path, load_index, query_index
from .core.contacts import (
    Contact,
    ContactDraft,
    ContactError,
    add_contact,
    find_contact,
    load_contacts,
    update_contact,
)
from .core.doctor import budget as doctor_budget
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
from .core.meetings import meeting_dict, scan_dict, scan_meetings
from .core.permits import describe, scan_permits
from .core.taskqueue import PARKED, TASKS_PATH, next_task, task_dict
from .core.taskqueue import STATES as QUEUE_STATES
from .core.taskqueue import collect as collect_queue
from .core.permits import scan_dict as permit_scan_dict
from .core.ops import (
    OpsError, add_sections, append_log, find_empty_dirs, new_project, remove_empty_dirs,
)
from .core.pdfexport import PdfError, export_pdf
from .core.deep import BUDGET_WARN_FRACTION, scan_deep
from .core.refsets import (
    RefSetError,
    check_draft,
    contents_lines,
    doctor_sets,
    list_sets,
    splice_contents,
    studio_ignore,
)
from .core.runs import archive_run, list_runs
from .core.templates import TemplateError
from .core.project_data import (
    ProjectDataError,
    ProjectUpdatePlan,
    ProjectUpdateResult,
    apply_crm_link,
    apply_project_update,
    check_crm_id,
    load_project_record,
    plan_crm_link,
    preview_project_update,
    read_crm_id,
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
from .core.search import RESULT_CAP, build_name_index, search_names
from .core.tree import MAPPED, TreeNode, open_project_tree
from .core.tyler import (
    collect as collect_tyler, digest_path, item_dict, queue_dict, render as render_tyler,
)
from .tui.tokens import filing_style  # the Fault Words; pure data, no Textual
from .tui.dossier import dossier_lines  # the Dossier Facts Table; pure strings


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
    inventory = _scan(root)
    deep = None
    if args.deep:
        if args.all and args.project:
            raise UsageError("--all cannot be combined with a project name")
        if args.all:
            deep = frozenset(p.name for p in inventory.projects)
        elif args.project:
            _resolve_project(root, args.project)
            deep = frozenset({args.project})
        else:
            raise UsageError("--deep walks one project: name it, or pass --all to "
                             "pay the whole drive")
    elif args.project:
        raise UsageError("doctor's default pass is root-only; --deep PROJECT is "
                         "the scoped walk below a project root")
    try:
        report = report_drive(inventory, deep=deep)
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
        # The item budget speaks in text only once it is worth saying; --json
        # always carries it (plan 1.6).
        budget_info = doctor_budget(report)
        if (budget_info["counted"] and budget_info["total_items"] is not None
                and budget_info["total_items"] > budget_info["cap"] * BUDGET_WARN_FRACTION):
            print(f"drive items: {budget_info['total_items']:,} of the "
                  f"{budget_info['cap']:,} shared-drive item cap "
                  f"({budget_info['percent_of_cap']:g}%)")
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
            for hit in p.receipts:
                print(f"    sweep pending (deep): {hit.path} -> {hit.target} "
                      f"(rule: {hit.rule})")
            for entry in p.overlong:
                print(f"    over-long path ({entry.length} chars): {entry.path}")
            for line in p.deep_unreadable:
                print(f"    cannot read (deep): {line}")
            for line in p.depth_capped:
                print(f"    depth guard: not scanned below {line}")
            for name in p.unfiled:
                print(f"    unfiled: {name}")
            # Map-tolerated entries are not findings, but they are never a
            # silent absence either (ticket 29).
            if p.ignored:
                print(f"    ignored (map-tolerated): {', '.join(p.ignored)}")
            for line in p.unreadable:
                print(f"    cannot read: {line}")
            # Report-only warnings (roadmap F4, F6): never the status, never
            # the exit code.
            if p.meetings is not None:
                for m in p.meetings.pending:
                    when = m.date.isoformat() if m.date else "date unknown"
                    state = "" if m.transcribed else " (not transcribed)"
                    print(f"    warning: meeting not closed out ({when}){state}: "
                          f"{p.meetings.folder}/{m.label}")
                for line in p.meetings.unreadable:
                    print(f"    warning: cannot read meetings folder: {line}")
                for line in p.meetings.skipped:
                    print(f"    warning: meetings folder past maxDepth, not scanned: "
                          f"{p.meetings.folder}/{line}")
            if p.budgets is not None:
                for b in p.budgets.breaches:
                    print(f"    warning: {b.message}")
                for line in p.budgets.unreadable:
                    print(f"    warning: cannot read for budget: {line}")
            if p.permits is not None:
                for line in p.permits.misnamed:
                    print(f"    warning: round folder not R<n>_YYMMDD: {line}")
                for line in p.permits.findings:
                    print(f"    warning: permits: {line}")
                for line in p.permits.unreadable:
                    print(f"    warning: cannot read for permits: {line}")
    # An unreadable folder is pending too: a person has to look (ADR 0004).
    # So is an over-long path or a depth-guard truncation: findings Atlas
    # cannot repair, which is exactly what the exit code is for.
    pending = any(p.actionable or p.unfiled or p.unreadable or p.deep_unreadable
                  or p.overlong or p.depth_capped for p in report.projects)
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


def _created_date(value: str | None) -> date:
    """``--date YYMMDD`` as a date; today when absent. A bad date is an error."""
    if value is None:
        return date.today()
    if re.fullmatch(r"\d{6}", value) is None:
        raise UsageError(f"--date must be YYMMDD (six digits), got {value!r}")
    try:
        parsed = datetime.strptime(value, "%y%m%d").date()
    except ValueError:
        raise UsageError(f"--date {value!r} is not a real calendar date (YYMMDD)") from None
    if parsed.year < 2000:
        # strptime reads 69-99 as 19xx; no studio project predates 2000.
        raise UsageError(f"--date {value!r} reads as {parsed.year}; use a date from 2000 on")
    return parsed


def cmd_new(args: argparse.Namespace) -> int:
    root = _resolve_drive(args.drive)
    drive_map = load_map(find_map(root))
    created = _created_date(args.date)
    if args.crm_id is not None:
        check_crm_id(args.crm_id)   # an empty --crm-id is an error, not "unlinked"
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
            created=created,
        )
        result = new_project(root, drive_map, intake, crm_id=args.crm_id or "")
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
                    "created_date": created.isoformat(),
                    "crm_id": args.crm_id or None,
                    "mcp": ({"status": result.mcp.status, "note": result.mcp.note}
                            if result.mcp else None),
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
        if args.crm_id:
            print(f"crm id:  {args.crm_id}")
        print(f"seed:    {', '.join(result.seeded)}")
        if result.templates:
            print(f"files:   {', '.join(result.templates)}")
        agents = f"{drive_map.agents_file}, " if drive_map.agents_file else ""
        print(f"control: {drive_map.project_file}, {drive_map.decisions_dir}\\, "
              f"{agents}{drive_map.claude_file}, {drive_map.analysis_dir}\\")
        if result.mcp:
            print(f"mcp:     {result.mcp.status}: {result.mcp.note}")
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


def cmd_project_link(args: argparse.Namespace) -> int:
    """Link a project to its CRM Project by writing ``crm_id`` (ADR 0001).

    Idempotent: the same id again changes nothing and exits 0. A different
    existing id exits 2 - relinking is a person's call, never a retry's.
    """
    root = _resolve_drive(args.drive)
    drive_map = load_map(find_map(root))
    project = _resolve_project(root, args.folder)
    plan = plan_crm_link(project, args.crm_id, project_file=drive_map.project_file)

    def payload(applied: bool) -> dict[str, object]:
        return {
            "folder": project.name,
            "path": str(project),
            "crm_id": plan.crm_id,
            "previous_crm_id": plan.previous or None,
            "changed": plan.changed,
            "applied": applied,
        }

    if not plan.changed or args.dry_run:
        if args.json:
            print(json.dumps(payload(False), ensure_ascii=False))
        elif not plan.changed:
            print(f"already linked: {project.name} -> {plan.crm_id}")
        else:
            print("dry run: no changes made")
            print(f"link:    {project.name} -> {plan.crm_id}")
        return 0
    if not args.yes:
        if args.json or not sys.stdin.isatty():
            print("error: project link requires --yes in non-interactive mode; "
                  "no changes made", file=sys.stderr)
            return 2
        print(f"link: {project.name} -> {plan.crm_id}")
        if input("Type yes to write crm_id (anything else cancels): ").strip().casefold() != "yes":
            print("cancelled: no changes made")
            return 1
    apply_crm_link(plan)
    try:
        append_log(root, f"[{project.name}] project link: crm_id {plan.crm_id}")
    except OSError as error:
        print(f"warning: linked, but the Atlas log could not be written: {error}",
              file=sys.stderr)
    if args.json:
        print(json.dumps(payload(True), ensure_ascii=False))
    else:
        print(f"linked: {project.name} -> {plan.crm_id}")
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


# ---------------------------------------------------------------- archive


def _print_archive_plan(plan, *, applied: bool) -> None:
    for a in plan.actions:
        print(_action_line(a))
    for warning in plan.warnings:
        print(f"    warning: {warning}")
    for note in plan.notes:
        print(f"    note: {note}")
    if not applied:
        print("(dry run - pass --apply to perform)")


def _run_archive_plan(args: argparse.Namespace, root: Path, m, plan) -> int:
    if not args.apply:
        if args.json:
            print(json.dumps([archive_plan_to_dict(plan, m.drive)], indent=2))
        else:
            _print_archive_plan(plan, applied=False)
        return 1
    stale = ArchiveGuard.for_plan(root, m, plan).check(root)
    if stale:
        print(f"error: {stale}; preview again before applying", file=sys.stderr)
        return 2
    applied = apply_archive_plan(root, m, plan)
    if args.json:
        print(json.dumps([archive_plan_to_dict(applied, m.drive)], indent=2))
    else:
        _print_archive_plan(applied, applied=True)
    if any(a.status == FAILED for a in applied.actions):
        return 2
    return 0 if all(a.status == DONE for a in applied.actions) else 1


def cmd_archive(args: argparse.Namespace) -> int:
    """Archive one project to the map's archiveRoot (ADR 0019). Dry run by default."""
    root = _resolve_drive(args.drive)
    m = load_map(find_map(root))
    try:
        plan = build_archive_plan(root, m, args.name)
    except OpsError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return _run_archive_plan(args, root, m, plan)


def cmd_unarchive(args: argparse.Namespace) -> int:
    """Bring an archived project back by name, or undo an applied archive from
    the manifest it printed (`--json` out, `--revert` in - the same shape as
    conform's revert; the CLI holds no undo stack)."""
    root = _resolve_drive(args.drive)
    m = load_map(find_map(root))
    if args.name and args.revert:
        print("error: pass a project name or --revert FILE, not both", file=sys.stderr)
        return 2
    if args.revert:
        return _archive_revert(args, root, m)
    if not args.name:
        print("error: pass a project name or --revert FILE", file=sys.stderr)
        return 2
    try:
        plan = build_unarchive_plan(root, m, args.name)
    except OpsError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return _run_archive_plan(args, root, m, plan)


def _archive_revert(args: argparse.Namespace, root: Path, m) -> int:
    manifest = Path(args.revert)
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: cannot read {manifest}: {error}", file=sys.stderr)
        return 2
    plans = payload if isinstance(payload, list) else [payload]
    inverses = []
    for p in plans:
        # A manifest from drive A must never move folders on drive B.
        if not isinstance(p, dict) or p.get("drive") != m.drive:
            found = p.get("drive") if isinstance(p, dict) else None
            print(f"error: {manifest} is from drive {found or '(unnamed)'}, "
                  f"not {m.drive}; nothing moved", file=sys.stderr)
            return 2
        try:
            plan = archive_plan_from_dict(p)
        except OpsError as error:
            print(f"error: cannot read {manifest}: {error}", file=sys.stderr)
            return 2
        # A preview's manifest reverses nothing - only an applied one can.
        if any(a.status != DONE for a in plan.actions):
            print(f"error: {manifest} records a preview, not an applied archive; "
                  f"nothing to revert", file=sys.stderr)
            return 2
        try:
            inverses.append(invert_archive_plan(plan))
        except NotInvertible as error:
            print(f"error: cannot reverse this manifest: {error}", file=sys.stderr)
            return 2
    # Every source still where the archive left it, before anything moves.
    for inverse in inverses:
        for action in inverse.actions:
            if not (root / action.src).is_dir():
                print(f"error: {action.src} is no longer where the archive left it; "
                      f"nothing moved", file=sys.stderr)
                return 2
    if not args.apply:
        if args.json:
            print(json.dumps([archive_plan_to_dict(p, m.drive) for p in inverses], indent=2))
        else:
            for inverse in inverses:
                _print_archive_plan(inverse, applied=False)
        return 1
    results = [apply_archive_plan(root, m, inverse) for inverse in inverses]
    if args.json:
        print(json.dumps([archive_plan_to_dict(p, m.drive) for p in results], indent=2))
    else:
        for result in results:
            _print_archive_plan(result, applied=True)
    if any(a.status == FAILED for p in results for a in p.actions):
        return 2
    return 0 if all(a.status == DONE for p in results for a in p.actions) else 1


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
            "retired": list(refset.retired),
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
            retired = f"  (retired: {' '.join(r['retired'])})" if r["retired"] else ""
            print(f"{r['type'] or '?':20} {state:22} {' '.join(r['exemplars'])}{retired}")
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


def cmd_refs_doctor(args: argparse.Namespace) -> int:
    """Validate every set (robustness plan 1.1). 0 = clean, 2 = problems or error:
    a doctor run is a gate, so problems share the error code and stale stays a
    warning."""
    from datetime import date
    root = _reference_root(args)
    reports = doctor_sets(root, date.today())
    total = sum(len(r.problems) for r in reports)
    if args.json:
        print(json.dumps({
            "root": str(root),
            "problems": total,
            "sets": [{
                "type": r.type, "title": r.title, "status": r.status,
                "stale": r.stale, "folder": str(r.folder),
                "problems": [{"file": p.file, "message": p.message} for p in r.problems],
            } for r in reports],
        }, indent=2))
    else:
        for r in reports:
            state = r.status or "no status"
            if r.stale:
                state += ", STALE"
            print(f"{r.type or r.folder.name:20} {state:22} {len(r.problems)} problem(s)")
            for p in r.problems:
                print(f"  - {p.file}: {p.message}")
        if not reports:
            print(f"no reference sets under {root}")
        else:
            print(f"{total} problem(s) across {len(reports)} set(s)")
    return 2 if total else 0


def cmd_refs_index(args: argparse.Namespace) -> int:
    """Rebuild the README atlas:contents block from card front matter (plan 1.2).

    Dry run prints the diff, like `runs`/`clean`; --apply writes. Line endings
    and the trailing newline are kept as found, so an unchanged regenerate is
    byte-identical.
    """
    import difflib
    from datetime import date
    root = _reference_root(args)
    readme = root / "README.md"
    if not readme.is_file():
        raise UsageError(f"no README.md under {root}")
    raw = readme.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    block = contents_lines(list_sets(root), date.today())
    new_lines = splice_contents(lines, block)
    changed = new_lines != lines
    applied = False
    if changed and args.apply:
        out = newline.join(new_lines)
        if text.endswith(("\n", "\r")):
            out += newline
        readme.write_bytes(out.encode("utf-8"))
        applied = True
    if args.json:
        print(json.dumps({
            "readme": str(readme),
            "changed": changed,
            "applied": applied,
            "sets": [s.type for s in list_sets(root)],
        }, indent=2))
    elif not changed:
        print("index up to date")
    else:
        diff = difflib.unified_diff(lines, new_lines, lineterm="",
                                    fromfile=str(readme), tofile=f"{readme} (generated)")
        print("\n".join(diff))
        if applied:
            print(f"wrote {readme}")
        else:
            print("\n(dry run - pass --apply to write)")
    return 1 if changed and not applied else 0


def cmd_refs_gallery(args: argparse.Namespace) -> int:
    """Write the human-facing gallery (``Reference Sets.html``) beside the sets
    README. A pure generated artifact - written directly, like ``tyler --write``;
    byte-identical on regenerate over unchanged cards. 0 = written, 2 = error."""
    from .core.refsgallery import thumbnail, write_gallery
    root = _reference_root(args)
    sets = list_sets(root)
    path = write_gallery(root, sets)
    shots = sum(1 for s in sets if thumbnail(s.folder.name, s))
    if args.json:
        print(json.dumps({"gallery": str(path), "sets": [s.type for s in sets],
                          "tiles": len(sets), "thumbnails": shots}, indent=2))
    else:
        print(f"wrote {path} ({len(sets)} sets, {shots} thumbnails)")
    return 0


def cmd_tyler(args: argparse.Namespace) -> int:
    """Roll up Tyler's open errands and DECISION blockers across projects (ADR 0016).

    Read-only by default; ``--write`` regenerates ``_tools/TYLER-TODAY.md``.
    """
    root = _resolve_drive(args.drive)
    digest = collect_tyler(_scan(root))
    if args.json:
        print(json.dumps({
            "drive": digest.drive,
            "errands": digest.errand_count,
            "decisions": digest.decision_count,
            "queue": queue_dict(digest, date.today()),
            "projects": [
                {"name": p.name,
                 "tyler_missing": p.tyler_missing,
                 "tasks_missing": p.tasks_missing,
                 "errands": [item_dict(i) for i in p.errands],
                 "decisions": [{**item_dict(i), "blocks": p.blocks(i)} for i in p.decisions],
                 "meetings": scan_dict(p.meetings) if p.meetings is not None else None,
                 "permits": (permit_scan_dict(p.permits, date.today())
                             if p.permits is not None else None)}
                for p in digest.projects
            ],
        }, indent=2))
        return 0
    text = render_tyler(digest)
    if args.write:
        out = digest_path(root)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out} ({digest.errand_count} errands / "
              f"{digest.decision_count} decisions)")
    else:
        print(text, end="")
    return 0


def cmd_meetings(args: argparse.Namespace) -> int:
    """The Meeting Inbox (roadmap F4): every project's meetings, or with
    ``--pending`` only those with no minutes yet. Read-only; the feed a
    scheduled `/meeting-closeout` run works from. Exit 0 whatever it finds:
    a pending meeting is work to do, not a drive fault."""
    root = _resolve_drive(args.drive)
    inventory = _scan(root)
    rule = inventory.map.meetings
    if rule is None:
        raise UsageError("the map has no 'meetings' rule; add one to "
                         f"{inventory.map.path} to turn the Meeting Inbox on")
    projects = sorted(inventory.projects, key=lambda p: p.name)
    if args.project:
        _resolve_project(root, args.project)
        projects = [p for p in projects if p.name == args.project]
    rows = []
    for inv in projects:
        scan = scan_meetings(inv.path, rule)
        meetings = scan.pending if args.pending else scan.meetings
        rows.append((inv, scan, meetings))
    if args.json:
        print(json.dumps([
            {"project": inv.name,
             "path": str(inv.path / scan.folder),
             **scan_dict(scan),
             "meetings": [meeting_dict(m) for m in meetings]}
            for inv, scan, meetings in rows
        ], indent=2))
        return 0
    total = 0
    for inv, scan, meetings in rows:
        if not meetings and not scan.unreadable and not scan.skipped:
            continue
        print(f"\n{inv.name}")
        for m in meetings:
            when = m.date.isoformat() if m.date else "date unknown"
            if m.closed:
                state = f"closed: {m.minutes}"
            else:
                state = "PENDING" if m.transcribed else "PENDING, not transcribed"
            print(f"    {when}  {m.label}  [{state}]")
        for line in scan.unreadable:
            print(f"    cannot read: {line}")
        for line in scan.skipped:
            print(f"    past maxDepth, not scanned: {line}")
        total += len(meetings)
    what = "pending meetings" if args.pending else "meetings"
    print(f"\n{total} {what}" if total else f"no {what}")
    return 0


def cmd_permits(args: argparse.Namespace) -> int:
    """The permit tracker (roadmap F3, ADR 0024): every application in each
    project's AHJ register, whose court the ball is in and for how long, plus
    where the round folders disagree with the register. Read-only; exit 0
    whatever it finds."""
    root = _resolve_drive(args.drive)
    inventory = _scan(root)
    rule = inventory.map.permits
    if rule is None:
        raise UsageError("the map has no 'permits' rule; add one to "
                         f"{inventory.map.path} to turn the permit tracker on")
    projects = sorted(inventory.projects, key=lambda p: p.name)
    if args.project:
        _resolve_project(root, args.project)
        projects = [p for p in projects if p.name == args.project]
    today = date.today()
    rows = [(inv, scan_permits(inv.path, rule, today)) for inv in projects]
    if args.json:
        print(json.dumps([{"project": inv.name, **permit_scan_dict(scan, today)}
                          for inv, scan in rows], indent=2))
        return 0
    total = 0
    for inv, scan in rows:
        quiet = not (scan.applications or scan.findings or scan.misnamed or scan.unreadable)
        if quiet and (scan.register_present or not args.project):
            continue
        print(f"\n{inv.name}")
        if not scan.register_present:
            print(f"    register missing: {scan.register}")
        elif not scan.register_readable:
            print(f"    register unreadable - applications unknown: {scan.register}")
        for a in scan.applications:
            label = " ".join(x for x in (a.agency, a.number) if x and x != "-")
            print(f"    [{a.court:6}] {label}: {describe(a, today)}")
            if a.next_action and a.next_action != "-":
                print(f"             next: {a.next_action}")
        for line in scan.findings:
            print(f"    finding: {line}")
        for line in scan.misnamed:
            print(f"    round folder not R<n>_YYMMDD: {line}")
        for line in scan.unreadable:
            print(f"    cannot read: {line}")
        total += len(scan.applications)
    print(f"\n{total} applications" if total else "\nno applications in any register")
    return 0


def cmd_tasks(args: argparse.Namespace) -> int:
    """The cross-project production queue (roadmap F5): every open task and
    its state, or with ``--next`` the one task an agent should pick up.
    Read-only: claiming is an edit to the project's TASKS.md and stays with
    the agent through ``/tasks``. ``--next`` exits 1 when nothing is pickable."""
    if args.with_prompt and not args.next:
        raise UsageError("--with-prompt only applies with --next")
    if args.next and args.lane in ("DECISION", "WAIT"):
        raise UsageError(f"--next picks AGENT or MODEL work; a {args.lane} task is never "
                         "picked up by an agent")
    root = _resolve_drive(args.drive)
    inventory = _scan(root)
    today = date.today()
    queues = collect_queue(inventory, today)
    if args.project:
        _resolve_project(root, args.project)
        queues = tuple(q for q in queues if q.project == args.project)
    # Work in a TASKS.md Atlas could not read is unknown, never absent: every
    # mode names those projects on stderr (ADR 0004).
    for q in queues:
        if not q.tasks_readable:
            print(f"warning: cannot read {q.project}/{TASKS_PATH} ({q.error}); "
                  "its tasks are unknown", file=sys.stderr)
    if args.next:
        lane = args.lane or "AGENT"
        task = next_task(queues, lane, today, with_prompt=args.with_prompt)
        path = next((q.path for q in queues if task and q.project == task.project), None)
        if args.json:
            print(json.dumps(task_dict(task, today, path) if task else None, indent=2))
        elif task is None:
            print(f"no pickable {lane} task")
        else:
            print(f"{task.project}\n    {task.item.text}")
            print(f"    file: {path / TASKS_PATH}")
            print("    claim it first: move it to In progress and append "
                  f"'claimed {today.isoformat()} by <name>'")
        return 0 if task else 1

    def keep(t) -> bool:
        if args.lane and t.item.lane != args.lane:
            return False
        return args.all or t.state not in (PARKED,)

    if args.json:
        print(json.dumps([
            {"project": q.project, "tasks_present": q.tasks_present,
             "tasks_readable": q.tasks_readable, "error": q.error or None,
             "revit_ready": q.revit_ready,
             "newest_run": q.newest_run.isoformat() if q.newest_run else None,
             "tasks": [task_dict(t, today) for t in q.tasks if keep(t)]}
            for q in queues
        ], indent=2))
        return 0
    counts = {s: 0 for s in QUEUE_STATES}
    for q in queues:
        shown = [t for t in q.tasks if keep(t)]
        if not q.tasks_readable:
            print(f"\n{q.project}\n    cannot read {TASKS_PATH}: {q.error} - its work is unknown")
            continue
        if not q.tasks_present:
            # doctor names a missing control file; say it here only when asked.
            if args.project:
                print(f"\n{q.project}\n    {TASKS_PATH} missing")
            continue
        if not shown:
            continue
        print(f"\n{q.project}")
        for t in shown:
            counts[t.state] += 1
            extra = []
            if t.blockers:
                extra.append("after " + ", ".join(t.blockers))
            if t.item.claim:
                age = t.claim_age(today)
                extra.append(t.item.claim + (f", {age}d" if age is not None else ""))
            if t.item.prompt:
                extra.append("prompt")
            tail = f"  ({'; '.join(extra)})" if extra else ""
            # The text is the whole line, ID and lane included.
            print(f"    [{t.state:11}] {t.item.text[:120]}{tail}")
    summary = ", ".join(f"{n} {s}" for s, n in counts.items() if n)
    unknown = sum(1 for q in queues if not q.tasks_readable)
    if unknown:
        summary = f"{summary or 'no open tasks read'}; {unknown} project(s) unreadable"
    print(f"\n{summary or 'no open tasks'}")
    return 0


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


def cmd_search(args: argparse.Namespace) -> int:
    """Drive-wide search: names over the session Name Index (ticket 33),
    contents over the per-machine Content Index (ticket 35, `--content`).

    The console's Search Overlay as a fact surface (ADR 0008): one bounded
    walk, and with `--content` a read of the local index - never a content
    read off the drive. Exit 0 with matches, 1 with none, 2 on error, like
    every fact producer. An absent index is said aloud and name matches are
    still served; a silent zero is never the answer (ADR 0004).

    Archived projects are searched too (plan Q3), read-only, tagged
    ``[archived]`` and ranked after every live hit; ``--no-archived`` leaves
    them out.
    """
    root = _resolve_drive(args.drive)
    if not args.query.strip():
        raise UsageError("pass something to search for; a blank query is a walk, "
                         "not a search")
    try:
        drive_map = load_map(find_map(root))
    except MapError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    include_archived = not args.no_archived
    index = build_name_index(root, archive_root=drive_map.archive_root,
                             archived=include_archived)
    result = search_names(index, args.query)
    content_index = None
    content_result = None
    if args.content:
        content_index = load_index(root)
        if content_index is not None:
            content_result = query_index(content_index, args.query,
                                         archived=include_archived)
    content_hits = content_result.hits if content_result is not None else ()

    def tag(hit) -> str:
        return "[archived] " if hit.archived else ""

    archived_note = f" ({result.archived} archived)" if result.archived else ""
    if args.json:
        # Each hit's project crm_id, read once per project and only for the
        # projects with hits - never a read of every dossier on the drive.
        crm_ids: dict[str, str | None] = {}

        def crm_id_of(hit) -> str | None:
            folder = hit.root or hit.project
            if folder not in crm_ids:
                crm_ids[folder] = read_crm_id(
                    root / folder, project_file=drive_map.project_file) or None
            return crm_ids[folder]

        payload: dict[str, object] = {
            "drive": drive_map.drive,
            "query": args.query,
            "total": result.total,
            "shown": len(result.hits),
            "cap": RESULT_CAP,
            "archived": result.archived,
            "results": [{"project": hit.project, "path": hit.path,
                         "name": hit.name, "kind": hit.kind,
                         "archived": hit.archived,
                         "crm_id": crm_id_of(hit)}
                        for hit in result.hits],
            "unreadable": [{"path": path, "error": why}
                           for path, why in index.unreadable],
        }
        if args.content:
            # null is the honest absent state: no stamp to show, and the build
            # is the pending work - never a silently empty result list.
            payload["content"] = None if content_result is None else {
                "indexed_at": content_index.indexed_at,
                "total": content_result.total,
                "shown": len(content_result.hits),
                "cap": RESULT_CAP,
                "stale": content_result.stale,
                "archived": content_result.archived,
                "results": [{"project": hit.project, "path": hit.path,
                             "kind": hit.kind, "snippet": hit.snippet,
                             "archived": hit.archived}
                            for hit in content_result.hits],
            }
        print(json.dumps(payload, indent=2))
    else:
        for hit in result.hits:
            print(f"{hit.kind}  {tag(hit)}{hit.path}")
        if not result.hits and not content_hits:
            print(f"no matches for '{args.query}'")
        elif not result.hits:
            print("no name matches - the content matches below")
        elif result.overflow:
            print(f"{result.total} matches{archived_note} - showing the first "
                  f"{len(result.hits)}; {result.overflow} more - refine the query")
        else:
            print(f"{result.total} match" + ("es" if result.total != 1 else "")
                  + archived_note)
        if args.content:
            if content_result is None:
                print("no content index for this drive - run `atlas index build` "
                      "to search file contents; the matches above are names only")
            else:
                stamp = content_index.indexed_at
                print(f"content matches (indexed at {stamp}):")
                for hit in content_hits:
                    snippet = f'  "{hit.snippet}"' if hit.snippet else ""
                    print(f"  {hit.kind}  {tag(hit)}{hit.path}{snippet}")
                if not content_hits:
                    print("  (none)")
                if content_result.stale:
                    noun = "match" if content_result.stale == 1 else "matches"
                    print(f"  {content_result.stale} stale {noun} excluded - "
                          "files changed since the index; "
                          "`atlas index build` refreshes")
        if index.unreadable:
            print(f"note: {len(index.unreadable)} folder(s) could not be read - "
                  "results may be incomplete", file=sys.stderr)
    return 0 if (result.hits or content_hits) else 1


def cmd_index_build(args: argparse.Namespace) -> int:
    """Build or top up the per-machine Content Index (ticket 34, ADR 0020).

    Incremental by path+size+mtime: the first build reads every PDF and
    Markdown file under the project roots; later runs re-read only what
    changed. Writes only to the local cache, never to the drive. Exit 0 on
    success, 2 on error - a build has no findings state.

    The Archived Projects are walked too (plan Q3), read-only. Their first
    extraction is the long one; ``--no-archived`` defers it, carrying the
    archive's stored entries forward unread.
    """
    root = _resolve_drive(args.drive)
    read = {"count": 0}

    def progress(done: int, total: int) -> None:
        read["count"] = done
        if not args.json and (done == total or done % 50 == 0):
            # Progress goes to stderr so --json stdout stays clean.
            print(f"indexing {done}/{total} files...", file=sys.stderr)

    index = build_index(root, progress=progress, save_every=50,
                        archived=not args.no_archived)
    skipped = len(index.skipped)
    unreadable = len(index.unreadable)
    if args.json:
        print(json.dumps({
            "drive": index.drive,
            "path": str(index_path(root)),
            "indexed_at": index.indexed_at,
            "files": len(index.files),
            "archived": index.archived_files,
            "read": read["count"],
            "skipped": skipped,
            "unreadable": unreadable,
        }, indent=2))
    else:
        noun = "file" if len(index.files) == 1 else "files"
        archived = (f", {index.archived_files} in archived projects"
                    if index.archived_files else "")
        print(f"indexed {len(index.files)} {noun} "
              f"({read['count']} read, {len(index.files) - read['count']} unchanged, "
              f"{skipped} skipped{archived}), indexed at {index.indexed_at}")
        if unreadable:
            print(f"note: {unreadable} folder(s) could not be read - "
                  "the index may be incomplete", file=sys.stderr)
    return 0


def cmd_index_status(args: argparse.Namespace) -> int:
    """Report the local Content Index: the Indexed-At Stamp and the counts.

    Exit 0 with an index, 1 when none exists yet (build is the pending work),
    2 on error.
    """
    root = _resolve_drive(args.drive)
    index = load_index(root)
    if args.json:
        payload = {"exists": index is not None,
                   "path": str(index_path(root))}
        if index is not None:
            payload.update({
                "drive": index.drive,
                "indexed_at": index.indexed_at,
                "files": len(index.files),
                "skipped": len(index.skipped),
                "unreadable": len(index.unreadable),
            })
        print(json.dumps(payload, indent=2))
        return 0 if index is not None else 1
    if index is None:
        print("no content index for this drive - run `atlas index build` "
              "(per-machine; the first build reads every PDF and Markdown file)")
        return 1
    noun = "file" if len(index.files) == 1 else "files"
    print(f"content index: {index_path(root)}")
    print(f"indexed at {index.indexed_at}; {len(index.files)} {noun}, "
          f"{len(index.skipped)} skipped, "
          f"{len(index.unreadable)} unreadable folder(s)")
    return 0


def cmd_dossier(args: argparse.Namespace) -> int:
    """One project's validated dossier facts (ticket 36; ticket 09, ADR 0008).

    The DOSSIER Companion Mode as a fact surface: the intake record, the
    contact snapshots and the decisions summary, always through
    ``load_project_record`` - the validated contract, never raw Markdown
    (`cat` is bytes; it can neither surface the validation failure nor give
    an agent the record as data). Read-only. Exit 0 with the record; a
    missing, malformed or legacy PROJECT.md exits 2 with the reason - never
    blanks (ADR 0001: blank means unknown).
    """
    root = _resolve_drive(args.drive)
    drive_map = load_map(find_map(root))
    project = _resolve_project(root, args.project)
    record = load_project_record(project, project_file=drive_map.project_file)
    intake = record.intake
    if args.json:
        def snapshot_dict(snapshot) -> dict[str, object]:
            return {"id": snapshot.id, "name": snapshot.full_name,
                    "email": snapshot.email, "phone": snapshot.phone,
                    "company": snapshot.company, "address": snapshot.address}
        print(json.dumps({
            "drive": drive_map.drive,
            "project": project.name,
            "path": str(project),
            "name": intake.project_name,
            "address": intake.project_address.formatted,
            "use_case": intake.project_use_case.display,
            "use_case_category": intake.project_use_case.category,
            "description": intake.description,
            "created": intake.created.isoformat(),
            "crm_id": record.crm_id or None,
            "billing_contact": snapshot_dict(record.billing_contact),
            "client_contact": snapshot_dict(record.client_contact),
            "decisions": {"count": record.decisions.count,
                          "latest": list(record.decisions.latest)},
            "source_digest": record.source_digest,
        }, indent=2))
        return 0
    print(f"{project.name} - the validated dossier facts "
          f"({drive_map.project_file})")
    for line in dossier_lines(record):
        print(line)
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
    if args.deep and args.revert:
        # A revert replays a manifest; there is nothing to walk for.
        print("error: --deep cannot be combined with --revert", file=sys.stderr)
        return 2
    if args.revert:
        return cmd_revert(args, root, m)
    if args.all and (args.project or args.node):
        # --all used to win silently, dropping --project and planning --node
        # in every project on the drive.
        print("error: --all cannot be combined with --project or --node", file=sys.stderr)
        return 2
    if args.deep and args.node:
        # A node repair is one action at a path the operator named; deep
        # findings never earn the inline repair key (ticket 26).
        print("error: --deep cannot be combined with --node", file=sys.stderr)
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
        if args.deep:
            scan = scan_deep(inv.path, m)
            report = report_project(inv, m, receipts=scan.hits,
                                    deep_unreadable=scan.unreadable,
                                    overlong=scan.overlong,
                                    depth_capped=scan.depth_capped,
                                    items=scan.items)
        else:
            report = report_project(inv, m)
        unreadable = report.unreadable + report.deep_unreadable
        if unreadable:
            unread[inv.name] = unreadable
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
        ("archive", cmd_archive, "archive a project to the archive root (dry run by default)"),
        ("unarchive", cmd_unarchive, "bring an archived project back, by name or --revert manifest"),
        ("tyler", cmd_tyler, "Tyler digest: open errands + DECISION blockers across projects "
                             "(read-only; --write regenerates _tools/TYLER-TODAY.md)"),
        ("meetings", cmd_meetings, "Meeting Inbox: recorded meetings and whether each has "
                                   "minutes (read-only; --pending for the ones that do not)"),
        ("tasks", cmd_tasks, "production queue: open tasks across projects and their state; "
                             "--next gives the task an agent should pick up (read-only)"),
        ("permits", cmd_permits, "permit tracker: each AHJ register application, whose court "
                                 "the ball is in and for how long (read-only)"),
        ("search", cmd_search, "drive-wide search: projects, folders and files by name, "
                               "plus PDF text and Markdown with --content (read-only)"),
        ("dossier", cmd_dossier, "one project's validated dossier facts: intake, contact "
                                 "snapshots, decisions summary (read-only)"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--drive", help="drive root (default: walk up from cwd, else auto-discover)")
        p.add_argument("--json", action="store_true", help="machine-readable output")
        p.set_defaults(fn=fn)

    sub.choices["tyler"].add_argument(
        "--write", action="store_true",
        help="write the digest to _tools/TYLER-TODAY.md instead of printing it")

    sub.choices["meetings"].add_argument("project", nargs="?",
                                         help="one project folder name (default: every project)")
    sub.choices["meetings"].add_argument(
        "--pending", action="store_true",
        help="only meetings with no minutes yet - the /meeting-closeout queue")

    sub.choices["tasks"].add_argument("project", nargs="?",
                                      help="one project folder name (default: every project)")
    sub.choices["tasks"].add_argument("--lane", choices=["AGENT", "MODEL", "DECISION", "WAIT"],
                                      help="only this lane (--next defaults to AGENT)")
    sub.choices["tasks"].add_argument("--all", action="store_true",
                                      help="also list parked tasks (outside Now and Next)")
    sub.choices["tasks"].add_argument(
        "--next", action="store_true",
        help="print the top pickable task: Now before Next, soonest due, prompt first, "
             "oldest; MODEL only where PROJECT.md names a Revit model. Exit 1 if none")
    sub.choices["tasks"].add_argument("--with-prompt", action="store_true",
                                      help="with --next: only tasks carrying an agent prompt")
    sub.choices["permits"].add_argument("project", nargs="?",
                                        help="one project folder name (default: every project)")

    sub.choices["tree"].add_argument("project", help="project folder name")
    sub.choices["tree"].add_argument(
        "--depth", type=int, default=1,
        help="levels to read below the project root (default 1). Each level is one "
             "enumeration per folder; the deepest level shown stays Unread")
    sub.choices["dossier"].add_argument("project", help="project folder name")
    sub.choices["search"].add_argument("query", help="case-folded substring matched against "
                                                     "every folder and file name and path")
    sub.choices["search"].add_argument(
        "--content", action="store_true",
        help="also search file contents via the local Content Index "
             "(`atlas index build` builds it; the Indexed-At Stamp is shown)")
    sub.choices["search"].add_argument(
        "--no-archived", action="store_true",
        help="leave archived projects out (by default they are searched, tagged "
             "[archived], and listed after every live match)")

    contacts =sub.add_parser("contacts", help="list, add, and edit shared contacts")
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

    index_cmd = sub.add_parser(
        "index", help="the per-machine Content Index: PDF text and Markdown, cached "
                      "locally, never on the drive")
    index_commands = index_cmd.add_subparsers(dest="index_command", required=True)
    index_build = index_commands.add_parser(
        "build", help="build or top up the index (incremental by path+size+mtime; "
                      "the first build reads every PDF and Markdown file)")
    index_build.add_argument(
        "--drive", help="drive root (default: walk up from cwd, else auto-discover)")
    index_build.add_argument("--json", action="store_true", help="machine-readable output")
    index_build.add_argument(
        "--no-archived", action="store_true",
        help="skip the archived projects this run; their stored entries are kept "
             "unread (the archive's first extraction is the long one)")
    index_build.set_defaults(fn=cmd_index_build)
    index_status = index_commands.add_parser(
        "status", help="report the index: Indexed-At Stamp and counts")
    index_status.add_argument(
        "--drive", help="drive root (default: walk up from cwd, else auto-discover)")
    index_status.add_argument("--json", action="store_true", help="machine-readable output")
    index_status.set_defaults(fn=cmd_index_status)

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
    project_link = project_commands.add_parser(
        "link", help="link a project to its CRM Project (writes crm_id)")
    project_link.add_argument("folder", help="project folder name")
    project_link.add_argument("--crm-id", required=True, help="the CRM's Project id")
    project_link.add_argument(
        "--drive", help="drive root (default: walk up from cwd, else auto-discover)")
    project_link.add_argument(
        "--json", action="store_true", help="machine-readable output; never prompts")
    project_link.add_argument("--yes", action="store_true",
                              help="confirm a non-interactive link")
    project_link.add_argument("--dry-run", action="store_true",
                              help="report what would change without writing")
    project_link.set_defaults(fn=cmd_project_link)

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
    refs_doctor = refs_commands.add_parser(
        "doctor", help="validate every set: card front matter, exemplar folders, "
                       "leak lists, .lnk files, stale review dates")
    refs_doctor.add_argument("--root", default=argparse.SUPPRESS)
    refs_doctor.add_argument("--drive", default=argparse.SUPPRESS)
    refs_doctor.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    refs_doctor.set_defaults(fn=cmd_refs_doctor)
    refs_index = refs_commands.add_parser(
        "index", help="rebuild the README atlas:contents block from card front "
                      "matter (dry run by default; --apply writes)")
    refs_index.add_argument("--apply", action="store_true", help="write the README")
    refs_index.add_argument("--root", default=argparse.SUPPRESS)
    refs_index.add_argument("--drive", default=argparse.SUPPRESS)
    refs_index.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    refs_index.set_defaults(fn=cmd_refs_index)
    refs_gallery = refs_commands.add_parser(
        "gallery", help="write the human-facing Reference Sets.html gallery beside "
                        "the sets README (self-contained, regenerable; always writes)")
    refs_gallery.add_argument("--root", default=argparse.SUPPRESS)
    refs_gallery.add_argument("--drive", default=argparse.SUPPRESS)
    refs_gallery.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    refs_gallery.set_defaults(fn=cmd_refs_gallery)

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
    sub.choices["new"].add_argument(
        "--date", help="creation date YYMMDD for the folder prefix and Created (default: today)")
    sub.choices["new"].add_argument(
        "--crm-id", help="the CRM Project id to record as crm_id in PROJECT.md")
    sub.choices["new"].add_argument(
        "--yes", action="store_true",
        help="accepted for scripted callers; new never prompts")
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
    sub.choices["archive"].add_argument("name", help="project folder name at the drive root")
    sub.choices["archive"].add_argument("--apply", action="store_true",
                                        help="move the project and stamp the project index row")
    sub.choices["unarchive"].add_argument("name", nargs="?",
                                          help="project folder name under the archive root")
    sub.choices["unarchive"].add_argument("--apply", action="store_true",
                                          help="move the project back and restore the index row")
    sub.choices["unarchive"].add_argument(
        "--revert", metavar="FILE",
        help="undo an applied archive from the JSON manifest `archive --apply --json` printed")
    sub.choices["doctor"].add_argument(
        "project", nargs="?",
        help="with --deep: the one project whose tree is walked")
    sub.choices["doctor"].add_argument(
        "--deep", action="store_true",
        help="opt-in deep pass: walk below one project's root. One enumeration "
             "per folder gathers Receipt Rule matches, over-long paths "
             "(already past Win32's 260, not ones Atlas would create), deep "
             "unreadable folders, and the item count against the 400,000 "
             "shared-drive cap - counting costs the same walk, which is why "
             "it rides this flag. Enumeration only, depth-guarded; with the "
             "map's meetings and fileBudgets keys it also warns on meetings "
             "with no minutes and control files past their budget (reading "
             "only those files). --deep --all pays the full drive walk by "
             "flag, never by default")
    sub.choices["doctor"].add_argument(
        "--all", action="store_true",
        help="with --deep: every project pays the deep walk")
    sub.choices["conform"].add_argument("--project", help="project folder name")
    sub.choices["conform"].add_argument(
        "--revert", metavar="FILE",
        help="undo an applied conform from the --json manifest it printed")
    sub.choices["conform"].add_argument(
        "--node",
        help="repair one node by its project-relative path; needs --project. "
             "Unlike --only, which filters by action class, this names a folder")
    sub.choices["conform"].add_argument("--all", action="store_true", help="every project on the drive")
    sub.choices["conform"].add_argument(
        "--deep", action="store_true",
        help="include Receipt Rule matches below the project root in the plan "
             "(opt-in; the default pass is root-only). One project's walk per "
             "project planned; --all --deep pays the full drive walk by flag")
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
