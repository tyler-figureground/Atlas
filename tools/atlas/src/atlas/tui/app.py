"""Atlas operations console - thin, safe views over the core modules.

The TUI owns interaction state, background work, and durable feedback. Filesystem
rules stay in ``atlas.core`` so CLI and TUI mutations follow the same plan and
safety contracts.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    SelectionList,
    Static,
)

from ..core.conform import (
    CONFLICT,
    DONE,
    SKIPPED,
    Guard,
    Plan,
    apply_plan,
    build_plan,
    build_repair_plan,
)
from ..core.contacts import (
    Contact,
    ContactDraft,
    ContactError,
    DuplicateContactError,
    add_contact,
    find_contact,
    load_contacts,
    update_contact,
)
from ..core.doctor import DriveReport, report_project
from ..core.intake import IntakeError, ProjectAddress, ProjectIntake, ProjectUseCase, USE_CASES
from ..core.mapfile import DriveMap, MapError, find_map, load_map
from ..core.naming import (
    NamingError,
    build_folder_name,
    clean_name_part,
    validate_project_folder_path,
)
from ..core.ops import OpsError, add_sections, find_empty_dirs, new_project, remove_empty_dirs
from ..core.project_data import (
    ProjectDataError,
    apply_project_update,
    load_project_record,
    preview_project_update,
)
from ..core.scan import (
    DriveInventory,
    ProjectInventory,
    discover_drives,
    list_entries,
    scan_drive,
)
from ..core.tree import ProjectTree, open_project_tree
from . import tokens
from .wordmark import BAR, composition_for, mark_width, render_mark
from .layout import (
    ABBREVIATE_COLUMNS,
    COMPANION,
    DEFAULT_MODE,
    SPLIT_COLUMNS,
    EXPECTATIONS,
    HEALTH,
    MODE_LABELS,
    PROJECT_LIST,
    REFUSED,
    TREE,
    drill,
    footer_actions,
    layout_for,
    next_mode,
    next_region,
    summary_line,
    unwind,
)
from .model import ProjectRow, project_detail, project_rows, visible_rows
from .repair import (
    UndoStack,
    confirm_line,
    confirms_inline,
    repair_offer,
    result_line,
)
from .treeview import ProjectTreeView

@dataclass(frozen=True)
class _ArmedRepair:
    """A one-Action repair waiting on the operation line for Enter.

    The Guard is captured when the repair is armed, not when it is confirmed:
    what it holds is what the preview saw, and its whole job is to notice that
    the drive has moved on since. Rebuilding it at confirm time would guard the
    write against itself.
    """

    project: str
    plan: Plan
    guard: Guard
    node: str


# What `#operation`'s `padding: 0 2` costs, in columns. Anything sized against
# that line subtracts this from the terminal width first. Ticket 17 needed the
# same correction for the wordmark and named it MARGIN there; getting it wrong
# does not error, it just quietly clips the last few characters - which on a
# confirm is the cancel key.
OPERATION_MARGIN = 4

STATUS_STYLES = {name: f"bold {hex_}" for name, hex_ in tokens.PALETTE.status.items()}

MODAL_CSS = tokens.stylesheet()


# What the narrow chrome names, in the order layout.footer_actions returns them.
KEY_HINTS = {
    "show_help_panel": "? Help",
    "next_region": "Tab Region",
    "drill": "Enter Open",
}


def _project_token(project: ProjectInventory) -> tuple[tuple[str, bool], ...]:
    """Shallow project state reviewed by plans without hydrating remote file contents."""

    return tuple(sorted((entry.name, entry.is_dir) for entry in project.root_entries))


@dataclass(frozen=True)
class OperationOutcome:
    """Durable summary and inspectable detail from one filesystem operation."""

    title: str
    summary: str
    lines: tuple[str, ...]
    severity: str = "information"
    marks_after: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ReviewedProjectCreation:
    intake: ProjectIntake
    drive_map: DriveMap


class AddContactModal(ModalScreen[Contact | None]):
    """Validate and store one reusable contact without losing entered fields."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, drive_root: Path) -> None:
        super().__init__()
        self._drive_root = drive_root

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="dialog"):
            yield Label("Add contact", classes="dialog-title")
            for label, field_id, placeholder in (
                ("First name *", "contact-first", "Ada"),
                ("Last name *", "contact-last", "Lovelace"),
                ("Email *", "contact-email", "ada@example.com"),
                ("Phone", "contact-phone", "+1 510 555 0100"),
                ("Company", "contact-company", "Company name"),
                ("Mailing street or PO box", "contact-street", "123 Main Street or PO Box 42"),
                ("Unit", "contact-unit", "Suite 4"),
                ("Mailing city", "contact-city", "Oakland"),
                ("Mailing state", "contact-state", "CA"),
                ("Mailing ZIP", "contact-zip", "94612"),
            ):
                yield Label(label, classes="field-label")
                yield Input(placeholder=placeholder, id=field_id)
            yield Static("", id="contact-error", classes="supporting", markup=False)
            with Horizontal(classes="actions"):
                yield Button("Add contact", variant="primary", id="add-contact-ok")
                yield Button("Cancel", id="add-contact-cancel")

    def on_mount(self) -> None:
        self.query_one("#contact-first", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-contact-cancel":
            self.action_cancel()
            return
        address_values = {
            "street": self.query_one("#contact-street", Input).value,
            "unit": self.query_one("#contact-unit", Input).value,
            "city": self.query_one("#contact-city", Input).value,
            "state": self.query_one("#contact-state", Input).value,
            "postal_code": self.query_one("#contact-zip", Input).value,
            "country": "US",
        }
        address = address_values if any(value.strip() for value in address_values.values() if value != "US") else None
        draft = ContactDraft(
            first_name=self.query_one("#contact-first", Input).value,
            last_name=self.query_one("#contact-last", Input).value,
            email=self.query_one("#contact-email", Input).value,
            phone=self.query_one("#contact-phone", Input).value,
            company=self.query_one("#contact-company", Input).value,
            address=address,
        )
        try:
            contact = add_contact(self._drive_root, draft)
        except DuplicateContactError as error:
            existing = error.existing
            self.query_one("#contact-error", Static).update(
                f"Email already belongs to {existing.first_name} {existing.last_name}. "
                "Cancel and select that contact, or enter a different email."
            )
            return
        except ContactError as error:
            self.query_one("#contact-error", Static).update(str(error))
            return
        self.dismiss(contact)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ContactManagerModal(ModalScreen[Contact | None]):
    """Edit one shared contact while preserving its stable identity."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, drive_root: Path) -> None:
        super().__init__()
        self._drive_root = drive_root
        self._contacts: tuple[Contact, ...] = ()

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="dialog"):
            yield Label("Manage contacts", classes="dialog-title")
            yield Label("Contact", classes="field-label")
            yield Select([], prompt="Select contact to edit", id="manager-contact")
            for label, field_id, placeholder in (
                ("First name *", "manager-first", "Ada"),
                ("Last name *", "manager-last", "Lovelace"),
                ("Email *", "manager-email", "ada@example.com"),
                ("Phone", "manager-phone", "+1 510 555 0100"),
                ("Company", "manager-company", "Company name"),
                ("Mailing street or PO box", "manager-street", "PO Box 42"),
                ("Unit", "manager-unit", "Suite 4"),
                ("Mailing city", "manager-city", "Oakland"),
                ("Mailing state", "manager-state", "CA"),
                ("Mailing ZIP", "manager-zip", "94612"),
            ):
                yield Label(label, classes="field-label")
                yield Input(placeholder=placeholder, id=field_id, disabled=True)
            yield Static("", id="manager-error", classes="supporting", markup=False)
            with Horizontal(classes="actions"):
                yield Button("Save contact", variant="primary", id="manager-save", disabled=True)
                yield Button("Cancel", id="manager-cancel")

    def on_mount(self) -> None:
        try:
            self._contacts = load_contacts(self._drive_root).contacts
        except ContactError as error:
            self.query_one("#manager-error", Static).update(str(error))
            return
        self.query_one("#manager-contact", Select).set_options([
            (f"{contact.first_name} {contact.last_name} · {contact.email}", contact.id)
            for contact in self._contacts
        ])
        self.query_one("#manager-contact", Select).focus()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "manager-contact" or not isinstance(event.value, str):
            return
        try:
            contact = find_contact(load_contacts(self._drive_root), event.value)
        except ContactError as error:
            self.query_one("#manager-error", Static).update(str(error))
            return
        if contact is None:
            self.query_one("#manager-error", Static).update("Contact is no longer available.")
            return
        address = contact.address or {}
        values = {
            "manager-first": contact.first_name,
            "manager-last": contact.last_name,
            "manager-email": contact.email,
            "manager-phone": contact.phone or "",
            "manager-company": contact.company or "",
            "manager-street": address.get("street", ""),
            "manager-unit": address.get("unit", ""),
            "manager-city": address.get("city", ""),
            "manager-state": address.get("state", ""),
            "manager-zip": address.get("postal_code", ""),
        }
        for field_id, value in values.items():
            field = self.query_one(f"#{field_id}", Input)
            field.disabled = False
            field.value = value
        self.query_one("#manager-save", Button).disabled = False
        self.query_one("#manager-error", Static).update("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "manager-cancel":
            self.action_cancel()
            return
        selected = self.query_one("#manager-contact", Select).value
        if not isinstance(selected, str):
            return
        address_values = {
            "street": self.query_one("#manager-street", Input).value,
            "unit": self.query_one("#manager-unit", Input).value,
            "city": self.query_one("#manager-city", Input).value,
            "state": self.query_one("#manager-state", Input).value,
            "postal_code": self.query_one("#manager-zip", Input).value,
            "country": "US",
        }
        address = address_values if any(
            value.strip() for key, value in address_values.items() if key != "country"
        ) else None
        try:
            updated = update_contact(
                self._drive_root,
                selected,
                ContactDraft(
                    first_name=self.query_one("#manager-first", Input).value,
                    last_name=self.query_one("#manager-last", Input).value,
                    email=self.query_one("#manager-email", Input).value,
                    phone=self.query_one("#manager-phone", Input).value,
                    company=self.query_one("#manager-company", Input).value,
                    address=address,
                ),
            )
        except ContactError as error:
            self.query_one("#manager-error", Static).update(str(error))
            return
        self.dismiss(updated)

    def action_cancel(self) -> None:
        self.dismiss(None)


class NewProjectModal(ModalScreen[ReviewedProjectCreation | None]):
    """Three-step project intake: project, contacts, and exact review."""

    ADD_NEW = "__add_new_contact__"
    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(
        self,
        drive_root: Path,
        drive_map: DriveMap,
        *,
        initial: ProjectIntake | None = None,
        existing_folder: str | None = None,
    ) -> None:
        super().__init__()
        self._drive_root = drive_root
        self._drive_map = drive_map
        self._initial = initial
        self._existing_folder = existing_folder
        self._created = initial.created if initial else date.today()
        self._contacts: tuple[Contact, ...] = ()
        self._step = 1
        self._client_overridden = False
        self._setting_client = False

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="dialog", classes="intake-dialog"):
            title = "Edit project" if self._initial else "New project"
            yield Label(f"{title} · 1 of 3", classes="dialog-title", id="intake-title")
            with Vertical(id="step-project"):
                for label, field_id, placeholder in (
                    ("Project name *", "name", "Oak House"),
                    ("Street address *", "street", "1842 Oak Street"),
                    ("Unit", "unit", "Apt 4B"),
                    ("City *", "city", "Oakland"),
                    ("State *", "state", "CA"),
                    ("ZIP *", "postal-code", "94612"),
                    ("Description", "desc", "Kitchen renovation"),
                ):
                    yield Label(label, classes="field-label")
                    yield Input(placeholder=placeholder, id=field_id)
                yield Label("Project Use Case *", classes="field-label")
                yield Select([(choice, choice) for choice in USE_CASES], prompt="Select use case", id="use-case")
                yield Label(
                    "Custom use case *",
                    classes="field-label",
                    id="custom-use-case-label",
                )
                yield Input(
                    placeholder="Describe project use case",
                    id="custom-use-case",
                )
                yield Static("Enter required project details.", id="project-error", classes="supporting", markup=False)
                yield Static("", id="preview", markup=False)
                with Horizontal(classes="actions"):
                    yield Button("Next: contacts", variant="primary", id="next-project", disabled=True)
                    yield Button("Cancel", id="cancel-project")
            with Vertical(id="step-contacts"):
                yield Label("Billing Contact *", classes="field-label")
                yield Select([], prompt="Select billing contact", id="billing-contact")
                yield Label("Client Contact *", classes="field-label")
                yield Static("Defaults to Billing Contact. Override when client and billing contacts differ.", classes="supporting", markup=False)
                yield Select([], prompt="Select client contact", id="client-contact")
                yield Static("", id="contact-selection-error", classes="supporting", markup=False)
                with Horizontal(classes="actions"):
                    yield Button("Back", id="back-project")
                    yield Button("Next: review", variant="primary", id="next-contacts", disabled=True)
                    yield Button("Cancel", id="cancel-contacts")
            with Vertical(id="step-review"):
                yield Static("", id="review", markup=False)
                yield Static("", id="review-error", classes="supporting", markup=False)
                with Horizontal(classes="actions"):
                    yield Button("Back", id="back-contacts")
                    yield Button(
                        "Save changes" if self._initial else "Create project",
                        variant="primary",
                        id="create-project",
                    )
                    yield Button("Cancel", id="cancel-review")

    def on_mount(self) -> None:
        try:
            self._contacts = load_contacts(self._drive_root).contacts
        except ContactError as error:
            self.query_one("#contact-selection-error", Static).update(str(error))
        self._refresh_contact_selects()
        if self._initial is not None:
            initial = self._initial
            for field, value in (
                ("#name", initial.project_name),
                ("#street", initial.project_address.street),
                ("#unit", initial.project_address.unit),
                ("#city", initial.project_address.city),
                ("#state", initial.project_address.state),
                ("#postal-code", initial.project_address.postal_code),
                ("#desc", initial.description),
            ):
                self.query_one(field, Input).value = value
            self.query_one("#use-case", Select).value = initial.project_use_case.category
            if initial.project_use_case.category == "Other":
                self.query_one("#custom-use-case", Input).value = initial.project_use_case.custom_label
            contact_ids = {contact.id for contact in self._contacts}
            if initial.billing_contact_id in contact_ids:
                self.query_one("#billing-contact", Select).value = initial.billing_contact_id
            if initial.client_contact_id in contact_ids:
                self.query_one("#client-contact", Select).value = initial.client_contact_id
            self._client_overridden = initial.client_contact_id != initial.billing_contact_id
        self._show_step(1)
        self._sync_project()
        self.query_one("#name", Input).focus()

    def _options(self) -> list[tuple[str, str]]:
        options = [
            (f"{contact.first_name} {contact.last_name} · {contact.email}", contact.id)
            for contact in self._contacts
        ]
        options.append(("Add new contact…", self.ADD_NEW))
        return options

    def _refresh_contact_selects(self, selected_role: str | None = None, contact_id: str | None = None) -> None:
        valid_ids = {contact.id for contact in self._contacts}
        for role in ("billing", "client"):
            select = self.query_one(f"#{role}-contact", Select)
            previous = select.value
            select.set_options(self._options())
            value = contact_id if role == selected_role else previous
            if isinstance(value, str) and value in valid_ids:
                select.value = value

    def on_input_changed(self, _: Input.Changed) -> None:
        if self._step == 1:
            self._sync_project()

    def on_select_changed(self, event: Select.Changed) -> None:
        select_id = event.select.id or ""
        if select_id == "use-case":
            other = event.value == "Other"
            self.query_one("#custom-use-case", Input).display = other
            self.query_one("#custom-use-case-label", Label).display = other
            self._sync_project()
            return
        if select_id not in {"billing-contact", "client-contact"}:
            return
        role = "billing" if select_id.startswith("billing") else "client"
        if event.value == self.ADD_NEW:
            event.select.value = Select.NULL
            self.app.push_screen(
                AddContactModal(self._drive_root),
                lambda contact: self._contact_added(role, contact),
            )
            return
        if role == "billing" and isinstance(event.value, str) and not self._client_overridden:
            self._setting_client = True
            self.query_one("#client-contact", Select).value = event.value
            self._setting_client = False
        elif role == "client" and not self._setting_client and isinstance(event.value, str):
            billing_value = self.query_one("#billing-contact", Select).value
            if event.value != billing_value:
                self._client_overridden = True
        self._sync_contacts()

    def _contact_added(self, role: str, contact: Contact | None) -> None:
        if contact is None:
            return
        try:
            self._contacts = load_contacts(self._drive_root).contacts
        except ContactError as error:
            self.query_one("#contact-selection-error", Static).update(str(error))
            return
        self._refresh_contact_selects(role, contact.id)
        if role == "billing" and not self._client_overridden:
            self._setting_client = True
            self.query_one("#client-contact", Select).value = contact.id
            self._setting_client = False
        self._sync_contacts()

    def _project_values(self) -> tuple[ProjectAddress, ProjectUseCase] | None:
        try:
            address = ProjectAddress(
                street=self.query_one("#street", Input).value,
                unit=self.query_one("#unit", Input).value,
                city=self.query_one("#city", Input).value,
                state=self.query_one("#state", Input).value,
                postal_code=self.query_one("#postal-code", Input).value,
            )
            use_value = self.query_one("#use-case", Select).value
            if not isinstance(use_value, str):
                raise IntakeError("Project Use Case is required")
            use_case = ProjectUseCase(
                use_value,
                self.query_one("#custom-use-case", Input).value if use_value == "Other" else "",
            )
            if not self.query_one("#name", Input).value.strip():
                raise IntakeError("Project Name is required")
            return address, use_case
        except IntakeError as error:
            self.query_one("#project-error", Static).update(str(error))
            return None

    def _sync_project(self) -> None:
        values = self._project_values()
        button = self.query_one("#next-project", Button)
        button.disabled = values is None
        if values is None:
            self.query_one("#preview", Static).update("")
            return
        address, _ = values
        folder = build_folder_name(
            self._created,
            clean_name_part(address.short),
            clean_name_part(self.query_one("#desc", Input).value),
        )
        try:
            validate_project_folder_path(self._drive_root, folder)
        except NamingError as error:
            button.disabled = True
            self.query_one("#project-error", Static).update(str(error))
            self.query_one("#preview", Static).update("")
            return
        self.query_one("#project-error", Static).update("")
        self.query_one("#preview", Static).update(f"Folder name: {folder}")

    def _sync_contacts(self) -> None:
        billing = self.query_one("#billing-contact", Select).value
        client = self.query_one("#client-contact", Select).value
        self.query_one("#next-contacts", Button).disabled = not (
            isinstance(billing, str) and isinstance(client, str)
        )

    def _request(self) -> ProjectIntake:
        values = self._project_values()
        if values is None:
            raise IntakeError("project details are incomplete")
        address, use_case = values
        billing = self.query_one("#billing-contact", Select).value
        client = self.query_one("#client-contact", Select).value
        if not isinstance(billing, str) or not isinstance(client, str):
            raise IntakeError("Billing Contact and Client Contact are required")
        return ProjectIntake(
            project_name=self.query_one("#name", Input).value,
            project_address=address,
            project_use_case=use_case,
            billing_contact_id=billing,
            client_contact_id=client,
            description=self.query_one("#desc", Input).value,
            created=self._created,
        )

    def _show_step(self, step: int) -> None:
        self._step = step
        for number, name in ((1, "project"), (2, "contacts"), (3, "review")):
            self.query_one(f"#step-{name}", Vertical).display = number == step
        title = "Edit project" if self._initial else "New project"
        self.query_one("#intake-title", Label).update(f"{title} · {step} of 3")

    def _show_review(self) -> None:
        request = self._request()
        billing = next(item for item in self._contacts if item.id == request.billing_contact_id)
        client = next(item for item in self._contacts if item.id == request.client_contact_id)
        folder = build_folder_name(
            request.created,
            clean_name_part(request.project_address.short),
            clean_name_part(request.description),
        )
        folder_line = f"Folder: {self._drive_root / folder}"
        if self._existing_folder and self._existing_folder != folder:
            folder_line = f"Folder rename: {self._existing_folder} → {folder}"
        elif self._existing_folder:
            folder_line = f"Folder unchanged: {folder}"
        self.query_one("#review", Static).update("\n".join((
            folder_line,
            f"Project: {request.project_name}",
            f"Address: {request.project_address.formatted}",
            f"Description: {request.description or '(none)'}",
            f"Use case: {request.project_use_case.display}",
            f"Billing Contact: {billing.first_name} {billing.last_name} · {billing.email}",
            f"Client Contact: {client.first_name} {client.last_name} · {client.email}",
            "Contact details will be copied into PROJECT.md.",
        )))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id.startswith("cancel"):
            self.action_cancel()
        elif button_id == "next-project":
            self._show_step(2)
            self._sync_contacts()
        elif button_id == "back-project":
            self._show_step(1)
        elif button_id == "next-contacts":
            self._show_review()
            self._show_step(3)
        elif button_id == "back-contacts":
            self._show_step(2)
        elif button_id == "create-project":
            request = self._request()
            map_path = find_map(self._drive_root)
            if map_path is None:
                self.query_one("#review-error", Static).update(
                    "Drive map is no longer available. Project was not created."
                )
                return
            try:
                fresh_map = load_map(map_path)
                directory = load_contacts(self._drive_root)
            except (ContactError, MapError, OSError) as error:
                self.query_one("#review-error", Static).update(
                    f"Could not recheck project data: {error}. Project was not created."
                )
                return
            if fresh_map != self._drive_map:
                self._drive_map = fresh_map
                self.query_one("#review-error", Static).update(
                    "Drive map changed. Your entries are preserved; review and choose Create project again."
                )
                return
            billing = find_contact(directory, request.billing_contact_id)
            client = find_contact(directory, request.client_contact_id)
            reviewed_billing = next(
                (item for item in self._contacts if item.id == request.billing_contact_id), None
            )
            reviewed_client = next(
                (item for item in self._contacts if item.id == request.client_contact_id), None
            )
            if (
                billing is None
                or client is None
                or billing != reviewed_billing
                or client != reviewed_client
            ):
                self._contacts = directory.contacts
                self._refresh_contact_selects()
                self.query_one("#contact-selection-error", Static).update(
                    "A selected contact changed or was removed. Your project entries are preserved; review contacts again."
                )
                self._show_step(2)
                self._sync_contacts()
                return
            self.dismiss(ReviewedProjectCreation(request, self._drive_map))

    def action_cancel(self) -> None:
        self.dismiss(None)


class AddSectionModal(ModalScreen[list[str] | None]):
    """Choose map-approved folders that do not exist yet."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, project: str, options: list[str]) -> None:
        super().__init__()
        self._project = project
        self._options = options

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog", classes="selection-dialog"):
            yield Label(f"Add folders - {self._project}", classes="dialog-title")
            yield Static(
                "Only folders approved by the drive map appear here.",
                classes="supporting",
                markup=False,
            )
            yield SelectionList[str](
                *[(self._option_label(option), option) for option in self._options]
            )
            with Horizontal(classes="actions"):
                yield Button("Create selected", variant="primary", id="ok", disabled=True)
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one(SelectionList).focus()

    @staticmethod
    def _option_label(option: str) -> str:
        if "/" not in option:
            return f"{option}  (section)"
        section, child = option.split("/", 1)
        return f"  {section} / {child}"

    def on_selection_list_selected_changed(self, _: SelectionList.SelectedChanged) -> None:
        selected = self.query_one(SelectionList).selected
        self.query_one("#ok", Button).disabled = not bool(selected)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss(list(self.query_one(SelectionList).selected))
        else:
            self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmListModal(ModalScreen[bool]):
    """Show an exact plan before a filesystem mutation."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

    def __init__(self, title: str, lines: list[str], ok_label: str) -> None:
        super().__init__()
        self._title = title
        self._lines = lines
        self._ok = ok_label

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._title, classes="dialog-title")
            yield Static(
                "Move destinations are never replaced. Concurrent control-file changes stop the plan.",
                classes="supporting",
                markup=False,
            )
            with VerticalScroll(id="plan"):
                yield Static("\n".join(self._lines) or "Nothing to do.", markup=False)
            with Horizontal(classes="actions"):
                if self._lines:
                    yield Button(self._ok, variant="warning", id="ok")
                yield Button("Close", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "ok")

    def action_cancel(self) -> None:
        self.dismiss(False)


class ResultModal(ModalScreen[None]):
    """Persistent, copyable operation or project detail."""

    BINDINGS = [Binding("escape", "close", "Close", show=False)]

    def __init__(self, title: str, lines: Iterable[str]) -> None:
        super().__init__()
        self._title = title
        self._lines = tuple(lines)

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._title, classes="dialog-title")
            with VerticalScroll(id="plan"):
                yield Static("\n".join(self._lines), markup=False)
            with Horizontal(classes="actions"):
                yield Button("Close", variant="primary", id="cancel")

    def on_button_pressed(self, _: Button.Pressed) -> None:
        self.action_close()

    def action_close(self) -> None:
        self.dismiss(None)


class AtlasApp(App):
    TITLE = "Atlas"
    HORIZONTAL_BREAKPOINTS = [(0, "-tiny"), (40, "-narrow"), (100, "-wide")]
    # Colour lives in tokens.stylesheet(); this block is geometry only. Keeping
    # them apart is what stops the tree - which takes no CSS at all and must read
    # its colours from Python - drifting away from everything around it.
    CSS = MODAL_CSS + """
    Screen { layout: vertical; }
    #mark { height: auto; padding: 1 2 0 2; }
    #drives { height: 1fr; padding: 1 2; }
    #filter { display: none; margin: 0 1; }
    #custom-use-case-label, #custom-use-case { display: none; }
    #console { height: 1fr; }
    #projects { width: 2fr; height: 1fr; }
    #workspace { width: 3fr; height: 1fr; }
    #workspace-title { height: 1; padding: 0 2; }
    #tree { height: 1fr; padding: 0 2; }
    #tree-body { height: 1fr; }
    #companion { height: 1fr; padding: 0 2; }
    #companion-title { height: auto; }
    #companion-body { height: auto; }
    #refusal { height: 1fr; padding: 1 2; }
    #summary { height: 1; padding: 0 2; }
    #operation { height: 1; padding: 0 2; }
    #keys { dock: bottom; height: 1; padding: 0 2; }
    Footer { dock: bottom; }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit", show=False),
        Binding("r", "refresh", "Refresh", show=False),
        Binding("slash", "filter_projects", "Filter"),
        Binding("tab", "next_region", "Region", priority=True),
        # Priority for the same reason tab is: a widget binding beats an App one,
        # and Textual's Tree binds enter to select_cursor. ADR 0005 makes Enter
        # Atlas's own key in every Region, so the tree does not get to take it.
        Binding("enter", "drill", "Open", priority=True),
        Binding("d", "cycle_companion", "Companion", show=False),
        Binding("left_square_bracket", "collapse_list", "Collapse list", show=False),
        Binding("right_square_bracket", "collapse_companion", "Collapse companion", show=False),
        Binding("z", "zoom_region", "Zoom", show=False),
        Binding("n", "new_project", "New project"),
        Binding("e", "edit_project", "Edit project"),
        Binding("m", "manage_contacts", "Contacts"),
        Binding("a", "add_section", "Add folders"),
        Binding("c", "clean", "Clean", show=False),
        Binding("f", "conform", "Conform"),
        Binding("u", "undo", "Undo", show=False),
        Binding("o", "open_folder", "Open", show=False),
        Binding("space", "toggle_mark", "Mark", show=False),
        Binding("x", "conform_marked", "Conform marked", show=False),
        Binding("s", "cycle_sort", "Sort", show=False),
        Binding("l", "show_last_result", "Last result", show=False),
        Binding("question_mark", "show_help_panel", "Help"),
        Binding("escape", "back", "Back", show=False),
    ]

    def __init__(self, drive: Path | None = None, *,
                 follow_debounce: float = 0.15) -> None:
        super().__init__()
        self._initial_drive = drive
        # Region state. Collapse is sticky for the session and outranks the
        # breakpoint default; the width overrides it only when it cannot carry it.
        self._focus_region = PROJECT_LIST
        self._collapsed: set[str] = set()
        self._zoomed: str | None = None
        self._companion_mode = DEFAULT_MODE
        self._showing = "drives"
        self._summary_text = ""
        self._operation_text = "Ready"
        self._trees: dict[str, ProjectTree] = {}
        # A repair armed on the operation line, waiting for Enter (ADR 0006:
        # confirmation weight follows plan size), and the per-Project history
        # that Undo pops. Both are session state and neither reaches the CLI.
        self._armed: _ArmedRepair | None = None
        self._undo = UndoStack()
        self._follow_debounce = follow_debounce
        self._follow_timer = None
        self._workspace_project = ""
        self._drives: list[Path] = []
        self._inventory: DriveInventory | None = None
        self._rows: tuple[ProjectRow, ...] = ()
        self._visible_rows: tuple[ProjectRow, ...] = ()
        self._marked: set[str] = set()
        self._sort_column = "health"
        self._sort_reverse = False
        self._busy = False
        self._work_kind: str | None = None
        self._inventory_fresh = False
        self._scan_generation = 0
        self._announced_scan_generation = 0
        self._last_result: OperationOutcome | None = None

    # ------------------------------------------------------------- lifecycle

    def compose(self) -> ComposeResult:
        yield Static("", id="mark", markup=False)
        yield ListView(id="drives")
        yield Input(placeholder="Filter by project name or health", id="filter")
        with Horizontal(id="console"):
            yield DataTable(id="projects")
            with Vertical(id="workspace"):
                yield Static("", id="workspace-title", markup=False)
                with Vertical(id="tree"):
                    yield ProjectTreeView(id="tree-body")
                with VerticalScroll(id="companion"):
                    yield Static("", id="companion-title", markup=False)
                    yield Static("", id="companion-body", markup=False)
        yield Static("", id="refusal", markup=False)
        yield Static("", id="summary", markup=False)
        yield Static("Ready", id="operation", markup=False)
        yield Static("", id="keys", markup=False)
        yield Footer()

    def _identity(self) -> str:
        """The line under the mark: which drive, which map, what needs attention."""
        if self._inventory is None:
            return self.sub_title or ""
        drive = self._inventory.map
        parts = [drive.drive, f"map v{drive.version}", f"{len(self._rows)} projects"]
        attention = sum(1 for r in self._rows if r.report.status != "conform")
        if attention:
            parts.append(f"{attention} need attention")
        return "   ".join(parts)

    def _refresh_mark(self) -> None:
        """Pick the widest composition the terminal can hold, then draw it.

        Called on mount, on resize, and whenever the inventory changes, so the
        mark collapses as the window narrows instead of clipping.
        """
        width = self.size.width or mark_width(BAR)
        mark = render_mark(composition_for(width))
        mark.append(self._identity(), style=tokens.PALETTE.muted)
        self.query_one("#mark", Static).update(mark)

    def on_resize(self, _: object) -> None:
        self._refresh_mark()
        self._apply_layout()

    # ------------------------------------------------------------- the shell

    def _apply_layout(self) -> None:
        """Draw the Composition this terminal size earns.

        The rule lives in ``tui.layout``; this only applies it. Regions are shown
        and hidden rather than shrunk, because a Region too narrow to read is
        worse than one that is not there.
        """
        layout = layout_for(
            self.size.width or 80, self.size.height or 24,
            focus=self._focus_region, collapsed=self._collapsed, zoomed=self._zoomed,
        )
        refusing = layout.composition == REFUSED
        refusal = self.query_one("#refusal", Static)
        refusal.display = refusing
        if refusing:
            refusal.update(layout.refusal)
        self.query_one("#mark", Static).display = not refusing
        self.query_one("#operation", Static).display = not refusing
        self.query_one("#drives", ListView).display = (
            not refusing and self._showing == "drives")
        self.query_one("#console", Horizontal).display = (
            not refusing and self._showing == "projects")
        if not refusing:
            self.query_one("#projects", DataTable).display = PROJECT_LIST in layout.visible
            workspace = self.query_one("#workspace", Vertical)
            workspace.display = bool({TREE, COMPANION} & set(layout.visible))
            self.query_one("#tree").display = TREE in layout.visible
            self.query_one("#companion", VerticalScroll).display = COMPANION in layout.visible
        self._merge_status = layout.merge_status
        self._render_chrome(refusing)
        self._render_status()

    def _render_chrome(self, refusing: bool = False) -> None:
        """Textual's footer where there is room for it, three keys where there
        is not, and neither when Atlas is asking for a bigger window.

        Which bindings exist never changes with width - only how many of them the
        chrome has room to name. Sizing the chrome through ``check_action`` would
        have been tidier and is wrong: returning None there disables the key as
        well as hiding it, so a narrow terminal would have lost the actions rather
        than only their labels.
        """
        permitted = None if refusing else footer_actions(self.size.width or 80)
        narrow = permitted is not None
        self.query_one(Footer).display = not narrow and not refusing
        keys = self.query_one("#keys", Static)
        keys.display = narrow
        if narrow:
            keys.update("  ".join(KEY_HINTS[action] for action in permitted))

    def _render_status(self) -> None:
        """Summary and operation, merged onto one line when rows run short."""
        merged = getattr(self, "_merge_status", False)
        summary = self.query_one("#summary", Static)
        summary.display = not merged and self.query_one("#operation", Static).display
        summary.update(self._summary_text)
        text = self._operation_text
        if merged and self._summary_text:
            text = f"{text}  |  {self._summary_text}"
        self.query_one("#operation", Static).update(text)

    def _focus_current_region(self) -> None:
        """Move keyboard focus to whatever Region is current, if it is drawn.

        The focusable widget, not the Region's container. `#tree` is a `Vertical`
        holding a title and the tree; a `Vertical` cannot take focus, so calling
        `focus()` on it silently does nothing and the keyboard stays wherever it
        was. Ticket 20 shipped exactly that: the app believed it had drilled into
        the tree while the arrow keys still drove the project list. Found by
        rendering the screen, not by a test - which is why one exists now.
        """
        target = {PROJECT_LIST: "#projects", TREE: "#tree", COMPANION: "#companion"}
        region = self.query_one(target[self._focus_region])
        if not region.display:
            return
        widget = region if region.focusable else next(
            (child for child in region.query("*") if child.focusable), None)
        if widget is not None:
            widget.focus()

    def on_mount(self) -> None:
        self._refresh_mark()
        table = self.query_one("#projects", DataTable)
        table.add_column("Mark", key="mark", width=4)
        table.add_column("Health", key="health")
        table.add_column("Project", key="project")
        table.add_column("Sections", key="sections")
        table.add_column("Fixes", key="fixes")
        table.add_column("Review", key="review")
        table.cursor_type = "row"
        table.display = False
        self._showing = "drives"
        if self._initial_drive:
            self._open_drive(self._initial_drive)
        else:
            self._show_drives(auto_open=True)

    # ------------------------------------------------------------- commands

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)
        if screen is not self.screen_stack[0] or self._busy:
            return
        if self._inventory is not None:
            yield SystemCommand("Filter projects", "Find a project or health state", self.action_filter_projects)
            yield SystemCommand("Refresh drive", "Rescan project health", self.action_refresh)
            if self._inventory_fresh:
                yield SystemCommand("New project", "Create a mapped project", self.action_new_project)
                yield SystemCommand("Manage contacts", "Edit shared contact details", self.action_manage_contacts)
        if self._selected_row() is not None:
            yield SystemCommand("Project health", "Show exact findings in the Companion", self.action_show_health)
            yield SystemCommand("Edit project", "Correct project intake fields", self.action_edit_project)
            yield SystemCommand("Open project folder", "Open in the default file manager", self.action_open_folder)
            yield SystemCommand("Mark or unmark project", "Build a batch selection", self.action_toggle_mark)
            if self._inventory_fresh:
                yield SystemCommand("Add project folders", "Create map-approved folders", self.action_add_section)
                yield SystemCommand("Clean empty folders", "Preview removable empty folders", self.action_clean)
                yield SystemCommand("Conform project", "Preview mapped repairs", self.action_conform)
        if self._marked and self._inventory_fresh:
            yield SystemCommand(
                "Conform marked projects",
                f"Preview repairs for {len(self._marked)} marked project(s)",
                self.action_conform_marked,
            )
        if self._last_result is not None:
            yield SystemCommand("Show last result", "Review the latest operation", self.action_show_last_result)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        has_drive = self._inventory is not None
        has_project = self._selected_row() is not None
        if action == "refresh":
            return True if not self._busy else None
        if action in {"filter_projects", "cycle_sort"}:
            return True if has_drive and not self._busy else None
        if action in {"new_project", "manage_contacts"}:
            return True if has_drive and self._inventory_fresh and not self._busy else None
        if action == "edit_project":
            return True if has_project and self._inventory_fresh and not self._busy else None
        if action in {"add_section", "clean", "conform"}:
            return True if has_project and self._inventory_fresh and not self._busy else None
        if action == "conform_marked":
            return True if self._marked and self._inventory_fresh and not self._busy else None
        if action in {"open_folder", "toggle_mark"}:
            return True if has_project and not self._busy else None
        if action in {"drill", "next_region", "cycle_companion"}:
            return True if self._showing == "projects" else None
        if action == "show_last_result":
            return True if self._last_result is not None else False
        return super().check_action(action, parameters)

    # ------------------------------------------------------------- drives and scans

    def _show_drives(self, *, auto_open: bool) -> None:
        self._scan_generation += 1
        self._busy = False
        self._work_kind = None
        self._inventory_fresh = False
        self._inventory = None
        self._rows = ()
        self._visible_rows = ()
        self._marked.clear()
        self.sub_title = "Drive picker"
        try:
            self._drives = discover_drives()
        except OSError as error:
            self._drives = []
            self._set_operation(f"Drive discovery failed: {error}. Press r to retry.", "error")
        drive_list = self.query_one("#drives", ListView)
        drive_list.clear()
        for drive in self._drives:
            drive_list.append(ListItem(Static(str(drive), markup=False)))
        self._showing = "drives"
        self.query_one("#filter", Input).display = False
        self._drive_summary = (
            f"{len(self._drives)} mapped drive(s) - Enter to open"
            if self._drives
            else "No mapped drives - set ATLAS_MOUNT_ROOT or launch with --drive"
        )
        self._focus_region = PROJECT_LIST
        self._refresh_summary()
        self._apply_layout()
        if auto_open and len(self._drives) == 1:
            self._open_drive(self._drives[0])
        else:
            drive_list.focus()
        self._refresh_mark()
        self.refresh_bindings()

    def on_list_view_selected(self, _: ListView.Selected) -> None:
        index = self.query_one("#drives", ListView).index
        if index is not None and 0 <= index < len(self._drives):
            self._open_drive(self._drives[index])

    def _open_drive(self, root: Path, *, announce: bool = True) -> None:
        self._busy = True
        self._work_kind = "scan"
        self._inventory_fresh = False
        self._scan_generation += 1
        generation = self._scan_generation
        table = self.query_one("#projects", DataTable)
        table.loading = True
        if announce:
            self._announced_scan_generation = generation
            self._set_operation(f"Scanning {root.name}...")
        self.refresh_bindings()
        self._scan_drive_worker(root, generation)

    @work(thread=True, exclusive=True, group="scan", exit_on_error=False)
    def _scan_drive_worker(self, root: Path, generation: int) -> None:
        try:
            inventory = scan_drive(root)
            if not inventory.readable:
                # Zero projects from a root Atlas could not list is a failure,
                # never a healthy empty drive (ADR 0004).
                raise OSError(f"cannot read the drive root ({inventory.error})")
            report = DriveReport(
                root=inventory.root,
                drive=inventory.map.drive,
                map_version=inventory.map.version,
                projects=tuple(
                    report_project(project, inventory.map) for project in inventory.projects
                ),
            )
            rows = project_rows(report.projects, inventory.map)
        except Exception as error:  # filesystem, map, permissions, disconnected drive
            self.call_from_thread(self._scan_failed, generation, root, error)
            return
        self.call_from_thread(self._scan_succeeded, generation, inventory, report, rows)

    def _scan_succeeded(
        self,
        generation: int,
        inventory: DriveInventory,
        report: DriveReport,
        rows: tuple[ProjectRow, ...],
    ) -> None:
        if generation != self._scan_generation:
            return
        self._inventory = inventory
        self._rows = rows
        current_names = {row.key for row in rows}
        self._marked.intersection_update(current_names)
        self._busy = False
        self._work_kind = None
        self._inventory_fresh = True
        table = self.query_one("#projects", DataTable)
        table.loading = False
        table.display = True
        self._showing = "projects"
        self._apply_layout()
        self.sub_title = f"{report.drive} - map v{report.map_version}"
        self._refresh_mark()
        self._fill()
        if generation == self._announced_scan_generation:
            self._set_operation(f"Scan complete - {len(self._rows)} project(s)")
        table.focus()
        self.refresh_bindings()

    def _scan_failed(self, generation: int, root: Path, error: Exception) -> None:
        if generation != self._scan_generation:
            return
        self._busy = False
        self._work_kind = None
        self.query_one("#projects", DataTable).loading = False
        message = f"Could not scan {root.name}: {error}. Press r to retry."
        self._set_operation(message, "error")
        self.notify(message, title="Scan failed", severity="error", timeout=10)
        self.refresh_bindings()

    # ------------------------------------------------------------- table and detail

    def _fill(self, preserve: str | None = None) -> None:
        if self._inventory is None:
            return
        selected = preserve or (self._selected_row().key if self._selected_row() else None)
        query = self.query_one("#filter", Input).value
        self._visible_rows = visible_rows(
            self._rows,
            query=query,
            sort_column=self._sort_column,
            reverse=self._sort_reverse,
        )
        table = self.query_one("#projects", DataTable)
        table.clear()
        for row in self._visible_rows:
            table.add_row(
                "*" if row.key in self._marked else "",
                Text(row.health, style=STATUS_STYLES.get(row.health, "bold")),
                row.report.name,
                row.sections,
                str(row.fixes) if row.fixes else "-",
                str(row.review) if row.review else "-",
                key=row.key,
            )

        if self._visible_rows:
            selected_index = next(
                (index for index, row in enumerate(self._visible_rows) if row.key == selected),
                0,
            )
            table.move_cursor(row=selected_index)
            self._follow_cursor(self._visible_rows[selected_index])
        else:
            self._workspace_project = ""
            self._companion_count = 0
            self.query_one(ProjectTreeView).set_source(None)
            self.query_one("#workspace-title", Static).update("No matching projects")
            self.query_one("#companion-title", Static).update("")
            self.query_one("#companion-body", Static).update(
                "Change the filter or press Esc to show every project."
                if query
                else "No project folders found on this drive. Press n to create one."
            )

        counts = DriveReport(
            root=self._inventory.root,
            drive=self._inventory.map.drive,
            map_version=self._inventory.map.version,
            projects=tuple(row.report for row in self._rows),
        ).summary()
        direction = "desc" if self._sort_reverse else "asc"
        filter_note = f" | Filter: {query}" if query else ""
        self._drive_summary = (
            f"{len(self._rows)} projects | {counts['conform']} ready | "
            f"{counts['drift']} action | {counts['unfiled']} review | "
            f"{counts['stub']} setup | {len(self._marked)} marked | "
            f"{self._sort_column} {direction}{filter_note}"
        )
        self._refresh_summary()
        self.refresh_bindings()

    def _refresh_summary(self) -> None:
        """One line, answering for whichever Region has focus."""
        self._summary_text = summary_line(
            self._focus_region,
            drive_summary=getattr(self, "_drive_summary", ""),
            project=self._workspace_project,
            companion_mode=self._companion_mode,
            companion_count=getattr(self, "_companion_count", 0),
        )
        self._render_status()

    def _selected_row(self) -> ProjectRow | None:
        if not self._visible_rows:
            return None
        cursor_row = self.query_one("#projects", DataTable).cursor_row
        if cursor_row is None or cursor_row >= len(self._visible_rows):
            return None
        return self._visible_rows[cursor_row]

    def _selected_project(self) -> tuple[Path, str] | None:
        row = self._selected_row()
        if row is None or self._inventory is None:
            return None
        return self._inventory.root / row.key, row.key

    # ---- the Workspace follows the Project List cursor -------------------

    def _project_tree(self, row: ProjectRow) -> ProjectTree | None:
        """The tree handle for one project, built once and kept."""
        if self._inventory is None:
            return None
        if row.key not in self._trees:
            inv = next((p for p in self._inventory.projects if p.name == row.key), None)
            if inv is None:
                return None
            self._trees[row.key] = open_project_tree(inv, self._inventory.map, row.report)
        return self._trees[row.key]

    def _follow_cursor(self, row: ProjectRow) -> None:
        """Populate the Workspace for the Selected Project, debounced.

        The title is free and moves at once. Everything under it costs an
        enumeration, so it waits out a rest on the cursor - unless this project
        has been read before, in which case there is nothing to wait for.
        """
        if self._follow_timer is not None:
            self._follow_timer.stop()
            self._follow_timer = None
        changed = row.key != self._workspace_project
        self._workspace_project = row.key
        self.query_one("#workspace-title", Static).update(row.key)
        if changed:
            # A new project answers a new question; the Companion goes back to
            # the mode that has to be readable beside the tree (ADR 0005).
            self._companion_mode = DEFAULT_MODE
        if row.key in self._trees or not self._follow_debounce:
            self._update_workspace(row)
            return
        self._follow_timer = self.set_timer(
            self._follow_debounce, lambda: self._update_workspace(row))

    def _update_workspace(self, row: ProjectRow) -> None:
        self._follow_timer = None
        if row.key != self._workspace_project:
            return      # the cursor moved on while this was pending
        tree = self._project_tree(row)
        self.query_one(ProjectTreeView).set_source(
            tree, narrow=(self.size.width or 80) < ABBREVIATE_COLUMNS)
        mode = self._companion_mode
        self.query_one("#companion-title", Static).update(MODE_LABELS[mode])
        if mode == HEALTH:
            body = project_detail(row)
            count = row.fixes + row.review
        elif mode == EXPECTATIONS:
            unmet = tree.expectations() if tree is not None else ()
            count = len(unmet)
            body = "\n".join(
                f"  {e.path}" + ("" if e.repairable else "   (add folders)")
                for e in unmet
            ) or "  Nothing missing - the project has what the map expects."
        else:
            body = "  The dossier lands here."
            count = 0
        self._companion_count = count
        self.query_one("#companion-body", Static).update(body)
        self._refresh_summary()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        name = str(event.row_key.value)
        row = next((candidate for candidate in self._visible_rows if candidate.key == name), None)
        if row is not None:
            self._follow_cursor(row)
            self.refresh_bindings()

    def on_data_table_row_selected(self, _: DataTable.RowSelected) -> None:
        self.action_drill()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        column = str(event.column_key.value)
        if column not in {"health", "project", "sections", "fixes", "review"}:
            return
        selected = self._selected_row()
        preserve = selected.key if selected else None
        if column == self._sort_column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            self._sort_reverse = column in {"sections", "fixes", "review"}
        self._fill(preserve)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter":
            self._fill()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter":
            self.query_one("#projects", DataTable).focus()

    # ------------------------------------------------------------- feedback and workers

    def _set_operation(self, message: str, severity: str = "information") -> None:
        status = self.query_one("#operation", Static)
        status.remove_class("-warning", "-error")
        if severity in {"warning", "error"}:
            status.add_class(f"-{severity}")
        self._operation_text = message
        self._render_status()

    def _start_operation(
        self,
        label: str,
        root: Path,
        operation: Callable[[], OperationOutcome],
    ) -> None:
        if self._busy or not self._inventory_fresh:
            return
        self._busy = True
        self._work_kind = "operation"
        self._set_operation(f"{label}...")
        self.refresh_bindings()
        self._operation_worker(root, operation)

    @work(thread=True, exclusive=True, group="operation", exit_on_error=False)
    def _operation_worker(
        self,
        root: Path,
        operation: Callable[[], OperationOutcome],
    ) -> None:
        try:
            outcome = operation()
        except Exception as error:  # core errors plus filesystem/permission failures
            outcome = OperationOutcome(
                title="Operation stopped",
                summary=f"Operation stopped: {error}",
                lines=(
                    str(error),
                    "Some changes may have completed before the failure.",
                    "Atlas will rescan the project. Review current health before retrying.",
                ),
                severity="error",
            )
        self.call_from_thread(self._operation_finished, root, outcome)

    def _operation_finished(self, root: Path, outcome: OperationOutcome) -> None:
        self._busy = False
        self._work_kind = None
        self._last_result = outcome
        if outcome.marks_after is not None:
            self._marked = set(outcome.marks_after)
        self._set_operation(f"Last result: {outcome.summary} - press l for details", outcome.severity)
        self.notify(
            outcome.summary,
            title=outcome.title,
            severity=outcome.severity,
            timeout=10 if outcome.severity != "information" else 5,
        )
        if outcome.severity in {"warning", "error"}:
            self.push_screen(ResultModal(outcome.title, outcome.lines))
        self._open_drive(root, announce=False)

    def _preparation_failed(self, label: str, error: Exception) -> None:
        self._busy = False
        self._work_kind = None
        message = f"Could not {label}: {error}. Review access and retry."
        self._set_operation(message, "error")
        self.notify(message, title="Preparation failed", severity="error", timeout=10)
        self.refresh_bindings()

    # ------------------------------------------------------------- actions

    def action_refresh(self) -> None:
        if self._busy:
            return
        if self._inventory is not None:
            self._open_drive(self._inventory.root)
        elif self._initial_drive:
            self._open_drive(self._initial_drive)
        else:
            self._show_drives(auto_open=False)

    def action_back(self) -> None:
        """Escape unwinds: out of the filter, out through the Regions, out to the
        drive picker. One key, one direction, the same in both Compositions."""
        if self._busy and self._work_kind != "scan":
            self.notify("Wait for the current operation to finish", title="Atlas is working")
            return
        if self._work_kind == "scan":
            self._show_drives(auto_open=False)
            return
        if self._cancel_repair():
            # Escape unwinds, and the innermost thing to unwind out of is an
            # armed write. Nothing has happened on disk, so this costs nothing.
            return
        filter_input = self.query_one("#filter", Input)
        if filter_input.display:
            filter_input.value = ""
            filter_input.display = False
            self.query_one("#projects", DataTable).focus()
            return
        if self._zoomed is not None:
            self._zoomed = None
            self._apply_layout()
            return
        outward = unwind(self._focus_region)
        if outward is not None:
            self._move_to_region(outward)
            return
        if self._inventory is not None:
            self._show_drives(auto_open=False)

    def _move_to_region(self, region: str) -> None:
        self._focus_region = region
        if self._zoomed is not None:
            self._zoomed = region
        self._apply_layout()
        self._focus_current_region()
        self._refresh_summary()
        self.refresh_bindings()

    def action_next_region(self) -> None:
        if self._showing != "projects":
            return
        self._move_to_region(next_region(self._focus_region, collapsed=self._collapsed))

    def action_drill(self) -> None:
        """Enter drills toward the tree - or commits an armed repair.

        Enter is the confirm key precisely because it is already the "yes, this
        one" key. While a repair is armed the operation line says so, so the
        overload is announced rather than latent.
        """
        if self._busy or self._showing != "projects":
            return
        if self._armed is not None:
            self._commit_repair()
            return
        self._move_to_region(drill(self._focus_region))

    def action_show_health(self) -> None:
        """Project health, in the Companion rather than in a modal (ADR 0005).

        The palette entry that used to push a modal now switches a mode. The
        finding is the same; what changed is that it no longer covers the screen
        the operator was reading it against.
        """
        if self._showing != "projects":
            return
        self._companion_mode = HEALTH
        row = self._selected_row()
        if row is not None:
            self._update_workspace(row)
        self._refresh_summary()

    def action_cycle_companion(self) -> None:
        if self._showing != "projects":
            return
        self._companion_mode = next_mode(self._companion_mode)
        row = self._selected_row()
        if row is not None:
            self._update_workspace(row)
        self._refresh_summary()

    def _toggle_collapse(self, region: str) -> None:
        if region in self._collapsed:
            self._collapsed.discard(region)
        else:
            self._collapsed.add(region)
            if self._focus_region == region:
                self._focus_region = next_region(region, collapsed=self._collapsed)
        self._apply_layout()
        self._focus_current_region()

    def action_collapse_list(self) -> None:
        self._toggle_collapse(PROJECT_LIST)

    def action_collapse_companion(self) -> None:
        self._toggle_collapse(COMPANION)

    def action_zoom_region(self) -> None:
        """Explicit Single-Region, at any width. Outranks the breakpoint."""
        self._zoomed = None if self._zoomed is not None else self._focus_region
        self._apply_layout()
        self._focus_current_region()

    def action_filter_projects(self) -> None:
        if self._busy or self._inventory is None:
            return
        filter_input = self.query_one("#filter", Input)
        filter_input.display = True
        filter_input.focus()

    def action_cycle_sort(self) -> None:
        if self._busy or self._inventory is None:
            return
        columns = ("health", "project", "fixes", "review")
        selected = self._selected_row()
        preserve = selected.key if selected else None
        index = (columns.index(self._sort_column) + 1) % len(columns) if self._sort_column in columns else 0
        self._sort_column = columns[index]
        self._sort_reverse = self._sort_column in {"fixes", "review"}
        self._fill(preserve)

    def action_toggle_mark(self) -> None:
        if self._busy:
            return
        row = self._selected_row()
        if row is None:
            return
        if row.key in self._marked:
            self._marked.remove(row.key)
        else:
            self._marked.add(row.key)
        self._fill(row.key)

    def action_conform_marked(self) -> None:
        if self._busy or not self._inventory_fresh or self._inventory is None or not self._marked:
            return
        inventory = self._inventory
        root = inventory.root
        drive_map = inventory.map
        rows_by_name = {row.key: row for row in self._rows}
        names = sorted(name for name in self._marked if name in rows_by_name)
        inventory_projects = {project.name: project for project in inventory.projects}
        plans: dict[str, Plan] = {
            name: build_plan(rows_by_name[name].report, drive_map,
                             project=inventory_projects[name].path)
            for name in names
        }
        initial_tokens = {name: _project_token(inventory_projects[name]) for name in names}
        lines: list[str] = []
        for name in names:
            plan = plans[name]
            lines.append(name)
            if plan.empty:
                lines.append("  No mapped repairs pending")
            for action in plan.actions:
                source = f"{action.src} -> " if action.src else ""
                files = f" ({action.file_count} files)" if action.file_count else ""
                lines.append(f"  {action.kind.title()}: {source}{action.dst}{files}")

        def done(confirmed: bool) -> None:
            if not confirmed:
                return

            def conform_batch() -> OperationOutcome:
                fresh_inventory = scan_drive(root)
                fresh_map = fresh_inventory.map
                fresh_projects = {project.name: project for project in fresh_inventory.projects}
                fresh_plans: dict[str, Plan] = {}
                fresh_tokens: dict[str, tuple[tuple[str, bool], ...]] = {}
                changed: list[str] = []
                for name in names:
                    project = fresh_projects.get(name)
                    if project is None:
                        changed.append(f"{name}: project no longer available")
                        continue
                    fresh_plan = build_plan(report_project(project, fresh_map), fresh_map,
                                            project=project.path)
                    fresh_plans[name] = fresh_plan
                    fresh_tokens[name] = _project_token(project)
                    if (
                        fresh_plan.actions != plans[name].actions
                        or fresh_tokens[name] != initial_tokens[name]
                    ):
                        changed.append(f"{name}: project contents changed")
                if fresh_map != drive_map:
                    changed.insert(0, "Drive map changed")
                if changed:
                    return OperationOutcome(
                        title="Batch plan changed",
                        summary="Marked projects changed since preview - nothing moved",
                        lines=tuple(changed) + ("Run Conform marked again to review current plans.",),
                        severity="warning",
                        marks_after=tuple(names),
                    )

                detail: list[str] = []
                done_count = 0
                skipped = 0
                conflicts = 0
                ready = 0
                completed = 0
                unresolved: set[str] = set()
                for index, name in enumerate(names):
                    immediate_inventory = scan_drive(root)
                    immediate_projects = {
                        project.name: project for project in immediate_inventory.projects
                    }
                    immediate_project = immediate_projects.get(name)
                    immediate_plan = (
                        build_plan(report_project(immediate_project, immediate_inventory.map),
                                   immediate_inventory.map, project=immediate_project.path)
                        if immediate_project is not None
                        else None
                    )
                    immediate_token = (
                        _project_token(immediate_project) if immediate_project is not None else None
                    )
                    if (
                        immediate_inventory.map != fresh_map
                        or immediate_plan != fresh_plans[name]
                        or immediate_token != fresh_tokens[name]
                    ):
                        detail.extend((name, "  STOPPED: project or drive map changed"))
                        remaining = unresolved | set(names[index:])
                        return OperationOutcome(
                            title="Batch conform stopped",
                            summary=f"Batch stopped after {completed} project(s) - review remaining marks",
                            lines=tuple(detail),
                            severity="warning",
                            marks_after=tuple(sorted(remaining)),
                        )

                    project_path = root / name
                    try:
                        result = apply_plan(root, project_path, immediate_inventory.map, immediate_plan)
                    except Exception as error:
                        detail.extend(
                            (
                                name,
                                f"  FAILED: {error}",
                                "  Some changes may have completed in this project.",
                            )
                        )
                        remaining = unresolved | set(names[index:])
                        return OperationOutcome(
                            title="Batch conform stopped",
                            summary=f"Batch failed after {completed} project(s) - review remaining marks",
                            lines=tuple(detail),
                            severity="error",
                            marks_after=tuple(sorted(remaining)),
                        )

                    completed += 1
                    detail.append(name)
                    if result.empty:
                        ready += 1
                        detail.append("  READY: no mapped repairs pending")
                    project_unresolved = False
                    for action in result.actions:
                        source = f"{action.src} -> " if action.src else ""
                        note = f" - {action.note}" if action.note else ""
                        detail.append(
                            f"  {(action.status or 'planned').upper()}: "
                            f"{action.kind} {source}{action.dst}{note}"
                        )
                        done_count += int(action.status == DONE)
                        skipped += int(action.status == SKIPPED)
                        conflicts += int(action.status == CONFLICT)
                        project_unresolved |= action.status != DONE
                    if project_unresolved:
                        unresolved.add(name)

                severity = "warning" if unresolved else "information"
                summary = (
                    f"Batch complete: {completed} project(s), {done_count} done, "
                    f"{skipped} skipped, {conflicts} conflict(s), {ready} already ready"
                )
                return OperationOutcome(
                    title="Batch conform result",
                    summary=summary,
                    lines=tuple(detail),
                    severity=severity,
                    marks_after=tuple(sorted(unresolved)),
                )

            self._start_operation("Conforming marked projects", root, conform_batch)

        total_repairs = sum(len(plan.actions) for plan in plans.values())
        if total_repairs == 0:
            self._set_operation("Marked projects have no mapped repairs pending")
            self.notify("Marked projects are already ready", title="Nothing to conform")
            return
        self.push_screen(
            ConfirmListModal(
                f"Conform {len(names)} marked project(s)",
                lines,
                f"Apply {total_repairs} repair(s) across {len(names)} project(s)",
            ),
            done,
        )

    def action_show_last_result(self) -> None:
        if self._last_result is not None:
            self.push_screen(ResultModal(self._last_result.title, self._last_result.lines))

    def action_open_folder(self) -> None:
        if self._busy:
            return
        selected = self._selected_project()
        if selected is None:
            return
        project_path, name = selected
        try:
            if not hasattr(os, "startfile"):
                raise OSError("default folder opening is available on Windows only")
            os.startfile(project_path)  # type: ignore[attr-defined]
        except OSError as error:
            self._set_operation(f"Could not open {name}: {error}", "error")
            self.notify(str(error), title="Open folder failed", severity="error", timeout=10)
            return
        self._set_operation(f"Opened {name} in the default file manager")

    def action_new_project(self) -> None:
        if self._busy or not self._inventory_fresh or self._inventory is None:
            return

        def done(result: ReviewedProjectCreation | None) -> None:
            if not result or self._inventory is None:
                return
            root = self._inventory.root
            drive_map = result.drive_map
            request = result.intake

            def create() -> OperationOutcome:
                fresh_map = scan_drive(root).map
                if fresh_map != drive_map:
                    return OperationOutcome(
                        title="Project plan changed",
                        summary="Drive map changed - no project created",
                        lines=("Open New project again to review the current folder rules.",),
                        severity="warning",
                    )
                created = new_project(root, fresh_map, request)
                return OperationOutcome(
                    title="Project created",
                    summary=f"Created {created.folder_name}",
                    lines=(
                        f"Created: {created.path}",
                        f"Seeded: {', '.join(created.seeded)}",
                        "Next: run /project-dossier in the new project folder.",
                    ),
                )

            self._start_operation("Creating project", root, create)

        self.push_screen(NewProjectModal(self._inventory.root, self._inventory.map), done)

    def action_manage_contacts(self) -> None:
        if self._busy or not self._inventory_fresh or self._inventory is None:
            return

        def done(contact: Contact | None) -> None:
            if contact is None:
                return
            summary = f"Updated {contact.first_name} {contact.last_name}"
            self._last_result = OperationOutcome(
                title="Contact updated",
                summary=summary,
                lines=(
                    summary,
                    "Existing project snapshots remain unchanged.",
                    "Edit a project to refresh its assigned contact snapshot.",
                ),
            )
            self._set_operation(f"Last result: {summary} - press l for details")
            self.notify(summary, title="Contact updated")

        self.push_screen(ContactManagerModal(self._inventory.root), done)

    def action_edit_project(self) -> None:
        if self._busy or not self._inventory_fresh or self._inventory is None:
            return
        selected = self._selected_project()
        if selected is None:
            return
        project_path, folder_name = selected
        try:
            record = load_project_record(project_path)
        except ProjectDataError as error:
            self.notify(str(error), title="Cannot edit project", severity="error", timeout=10)
            return
        root = self._inventory.root
        drive_map = self._inventory.map

        def reviewed(result: ReviewedProjectCreation | None) -> None:
            if result is None:
                return
            try:
                plan = preview_project_update(root, project_path, result.intake)
            except ProjectDataError as error:
                self.notify(str(error), title="Cannot preview project edit", severity="error", timeout=10)
                return

            def save(allow_rename: bool) -> None:
                def apply() -> OperationOutcome:
                    updated = apply_project_update(
                        root,
                        result.drive_map,
                        plan,
                        allow_rename=allow_rename,
                    )
                    action = "Renamed and updated" if updated.renamed else "Updated"
                    return OperationOutcome(
                        title="Project updated",
                        summary=f"{action} {updated.path.name}",
                        lines=(
                            f"Previous folder: {updated.old_path}",
                            f"Current folder: {updated.path}",
                            "PROJECT.md and project index updated.",
                        ),
                    )

                self._start_operation("Updating project", root, apply)

            if not plan.rename_required:
                save(False)
                return

            def confirmed(choice: bool | None) -> None:
                if choice:
                    save(True)

            self.push_screen(
                ConfirmListModal(
                    "Confirm project-folder rename",
                    [
                        f"Old: {plan.old_path}",
                        f"New: {plan.new_path}",
                        "PROJECT.md and project index will be updated together.",
                        "An existing destination blocks the operation.",
                    ],
                    "Rename and save",
                ),
                confirmed,
            )

        self.push_screen(
            NewProjectModal(
                root,
                drive_map,
                initial=record.intake,
                existing_folder=folder_name,
            ),
            reviewed,
        )

    def action_add_section(self) -> None:
        if self._busy or not self._inventory_fresh:
            return
        selected = self._selected_project()
        if selected is None or self._inventory is None:
            return
        project_path, name = selected
        drive_map = self._inventory.map
        self._busy = True
        self._work_kind = "prepare"
        self._set_operation(f"Checking available folders for {name}...")
        self.refresh_bindings()
        self._prepare_add_worker(project_path, name, drive_map)

    @work(thread=True, exclusive=True, group="prepare", exit_on_error=False)
    def _prepare_add_worker(self, project_path: Path, name: str, drive_map: DriveMap) -> None:
        try:
            options: list[str] = []
            for section in drive_map.sections:
                if not (project_path / section.id).is_dir():
                    options.append(section.id)
                for child in section.children:
                    if not (project_path / section.id / child).is_dir():
                        options.append(f"{section.id}/{child}")
        except Exception as error:
            self.call_from_thread(self._preparation_failed, "check available folders", error)
            return
        self.call_from_thread(self._show_add_plan, project_path, name, drive_map, options)

    def _show_add_plan(
        self,
        project_path: Path,
        name: str,
        drive_map: DriveMap,
        options: list[str],
    ) -> None:
        self._busy = False
        self._work_kind = None
        self.refresh_bindings()
        if not options:
            self._set_operation(f"{name} already has every mapped folder")
            self.notify("Every mapped folder already exists", title=name)
            return

        def done(picked: list[str] | None) -> None:
            if not picked or self._inventory is None:
                return
            root = self._inventory.root

            def create() -> OperationOutcome:
                fresh_inventory = scan_drive(root)
                fresh_map = fresh_inventory.map
                project_exists = any(project.name == name for project in fresh_inventory.projects)
                if not project_exists:
                    return OperationOutcome(
                        title="Add-folders plan changed",
                        summary=f"{name} is no longer available - no folders created",
                        lines=("Return to the project list and refresh the drive.",),
                        severity="warning",
                    )
                valid = {
                    section.id
                    for section in fresh_map.sections
                } | {
                    f"{section.id}/{child}"
                    for section in fresh_map.sections
                    for child in section.children
                }
                changed = fresh_map != drive_map or any(
                    item not in valid or (project_path / item).is_dir() for item in picked
                )
                if changed:
                    return OperationOutcome(
                        title="Add-folders plan changed",
                        summary=f"{name} changed since preview - no folders created",
                        lines=(
                            "The drive map or project folders changed while the preview was open.",
                            "Run Add folders again to review the current choices.",
                        ),
                        severity="warning",
                    )
                created = add_sections(root, fresh_map, project_path, picked)
                return OperationOutcome(
                    title="Folders created",
                    summary=f"Created {len(created)} folder(s) in {name}",
                    lines=tuple(f"Created: {item}" for item in created) or ("Nothing changed.",),
                )

            self._start_operation("Creating folders", root, create)

        self.push_screen(AddSectionModal(name, options), done)

    def action_clean(self) -> None:
        if self._busy or not self._inventory_fresh:
            return
        selected = self._selected_project()
        if selected is None or self._inventory is None:
            return
        project_path, name = selected
        drive_map = self._inventory.map
        self._busy = True
        self._work_kind = "prepare"
        self._set_operation(f"Finding removable empty folders in {name}...")
        self.refresh_bindings()
        self._prepare_clean_worker(project_path, name, drive_map)

    @work(thread=True, exclusive=True, group="prepare", exit_on_error=False)
    def _prepare_clean_worker(self, project_path: Path, name: str, drive_map: DriveMap) -> None:
        try:
            empties = find_empty_dirs(project_path, drive_map)
        except Exception as error:
            self.call_from_thread(self._preparation_failed, "inspect empty folders", error)
            return
        self.call_from_thread(self._show_clean_plan, project_path, name, empties)

    def _show_clean_plan(self, project_path: Path, name: str, empties: list[str]) -> None:
        self._busy = False
        self._work_kind = None
        self.refresh_bindings()

        def done(confirmed: bool) -> None:
            if not confirmed or self._inventory is None:
                return
            root = self._inventory.root

            def clean() -> OperationOutcome:
                fresh_inventory = scan_drive(root)
                fresh_empties = find_empty_dirs(project_path, fresh_inventory.map)
                if fresh_inventory.map != drive_map or sorted(fresh_empties) != sorted(empties):
                    return OperationOutcome(
                        title="Clean plan changed",
                        summary=f"{name} changed since preview - nothing removed",
                        lines=(
                            "Empty-folder state changed while the preview was open.",
                            "Run Clean again to review the current plan.",
                        ),
                        severity="warning",
                    )
                removed = remove_empty_dirs(root, project_path, fresh_empties)
                return OperationOutcome(
                    title="Empty folders cleaned",
                    summary=f"Removed {len(removed)} empty folder(s) from {name}",
                    lines=tuple(f"Removed: {item}" for item in removed) or ("Nothing changed.",),
                )

            self._start_operation("Removing empty folders", root, clean)

        self.push_screen(
            ConfirmListModal(
                f"Clean empty folders - {name}",
                [f"Remove {item}" for item in empties],
                f"Remove {len(empties)} empty folder(s)",
            ),
            done,
        )

    # ------------------------------------------------- the tree's writes
    #
    # ADR 0006's other half. The tree invents no action kinds: every repair here
    # is a one-Action slice of the Plan conform already builds, guarded at the
    # scope of that action rather than by the 4.24-second rescan a project-wide
    # conform pays for. The rule about what a key means lives in `tui/repair.py`;
    # what is here is the applying of it.

    def _arm_repair(self) -> None:
        """Offer a repair for the Tree Node under the cursor, or say why not."""
        row = self._selected_row()
        tree = self._trees.get(self._workspace_project)
        facts = self.query_one(ProjectTreeView).selected_facts()
        if row is None or tree is None or self._inventory is None:
            return
        if facts is None:
            # The cursor is on nothing - an empty project, or a tree still
            # loading. Say so; an inert key that stays quiet reads as broken.
            self._set_operation("Select a folder or file first", "warning")
            return

        offer = repair_offer(facts)
        if not offer.repairable:
            self._set_operation(offer.reason, "warning")
            return

        inventory = self._inventory
        project = next(
            (p for p in inventory.projects if p.name == row.key), None)
        if project is None:
            return
        plan = build_repair_plan(row.report, inventory.map, offer.target,
                                 project=project.path)
        if plan.empty:
            self._set_operation(f"{facts.name} needs no repair", "warning")
            return
        if not confirms_inline(plan):
            # Not reachable from a single node today, and not silently widened
            # into an inline confirm if it ever becomes so: ADR 0006 gives a
            # longer plan the modal because the modal is what can show a list.
            self.action_conform()
            return

        self._armed = _ArmedRepair(
            project=row.key,
            plan=plan,
            guard=Guard.for_action(inventory.root, row.key, inventory.map, plan),
            node=offer.target,
        )
        room = (self.size.width or 0) - OPERATION_MARGIN
        self._set_operation(confirm_line(plan, max(0, room)))

    def _cancel_repair(self) -> bool:
        """Abandon an armed repair. True if there was one to abandon."""
        if self._armed is None:
            return False
        self._armed = None
        self._set_operation("Repair cancelled")
        return True

    def _commit_repair(self) -> None:
        """Apply the armed repair, after the scoped Guard agrees it is still
        the same work."""
        armed = self._armed
        self._armed = None
        if armed is None or self._inventory is None:
            return
        self._apply_repair(armed.project, armed.plan, armed.guard, armed.node,
                           remember=True)

    def action_undo(self) -> None:
        """Put the last repair in this Project back.

        One stack per Project, no redo (ADR 0006): undo restores the precondition
        that offered the repair, so re-pressing the repair key is redo. The
        inverse is guarded exactly as the repair was, which is what lets the
        stack be optimistic rather than eagerly invalidated.
        """
        if self._busy or self._showing != "projects" or self._inventory is None:
            return
        self._cancel_repair()
        row = self._selected_row()
        if row is None:
            return
        inverse = self._undo.pop(row.key)
        if inverse is None:
            self._set_operation(f"Nothing to undo in {row.key}", "warning")
            return
        node = inverse.actions[0].src if inverse.actions else ""
        # for_undo, not for_action: an inverse cannot be re-derived from the map,
        # so the guard that rebuilds and compares would refuse every undo.
        guard = Guard.for_undo(self._inventory.root, row.key,
                               self._inventory.map, inverse)
        self._apply_repair(row.key, inverse, guard, node, remember=False)

    def _apply_repair(self, project_name: str, plan: Plan, guard: Guard,
                      node: str, *, remember: bool) -> None:
        """Guard, apply, remember, reconcile. The one write path for both the
        repair key and its undo - they differ only in which Plan they carry and
        whether the result goes on the stack."""
        inventory = self._inventory
        if inventory is None:
            return
        root = inventory.root
        stale = guard.check(root)
        if stale is not None:
            self._set_operation(f"Nothing moved - {stale}", "warning")
            return

        project = next((p for p in inventory.projects if p.name == project_name), None)
        if project is None:
            self._set_operation(f"Nothing moved - {project_name} is no longer available",
                                "warning")
            return
        try:
            applied = apply_plan(root, project.path, inventory.map, plan)
        except OpsError as error:
            self._set_operation(f"Repair stopped: {error}", "error")
            return

        conflicts = [a for a in applied.actions if a.status == CONFLICT]
        if remember:
            self._undo.push(project_name, applied)
        self._reconcile_after(project_name, applied, node)

        action = applied.actions[0] if applied.actions else None
        if conflicts:
            self._set_operation(
                f"{conflicts[0].kind} left in place - {conflicts[0].note or 'conflict'}",
                "warning")
        elif len(applied.actions) > 1:
            # Inverting a merge yields one action per child moved. Naming only
            # the first would report a third of what happened as all of it.
            self._set_operation(f"Done: {len(applied.actions)} moves in {node or project_name}")
        elif action is not None:
            self._set_operation(result_line(action))

    def _reconcile_after(self, project_name: str, applied: Plan, node: str) -> None:
        """Forget the folders the Move Manifest names and follow the cursor to
        where the node went (ADR 0007). Two enumerations, not a walk."""
        tree = self._trees.get(project_name)
        if tree is None:
            return
        inv = next((p for p in (self._inventory.projects if self._inventory else ())
                    if p.name == project_name), None)
        report = None
        if inv is not None and self._inventory is not None:
            fresh = ProjectInventory(path=inv.path, name=inv.name,
                                     root_entries=list_entries(inv.path))
            report = report_project(fresh, self._inventory.map)
        landed = tree.follow(node, applied)
        tree.reconcile(applied, report)
        view = self.query_one(ProjectTreeView)
        view.set_source(tree, narrow=(self.size.width or 80) < ABBREVIATE_COLUMNS)
        view.select_key(landed)

    def action_conform(self) -> None:
        if self._busy or not self._inventory_fresh:
            return
        if self._focus_region == TREE and self._showing == "projects":
            # The key means "conform what has focus". On the project list that is
            # the whole project; in the tree it is the node under the cursor.
            self._arm_repair()
            return
        selected = self._selected_project()
        row = self._selected_row()
        if selected is None or row is None or self._inventory is None:
            return
        project_path, name = selected
        inventory = self._inventory
        drive_map = inventory.map
        original_project = next(project for project in inventory.projects if project.name == name)
        original_token = _project_token(original_project)
        plan = build_plan(row.report, drive_map, project=project_path)
        lines = [
            f"{action.kind.title()}: {action.src + ' -> ' if action.src else ''}{action.dst}"
            + (f" ({action.file_count} files)" if action.file_count else "")
            for action in plan.actions
        ]

        def done(confirmed: bool) -> None:
            if not confirmed:
                return
            root = inventory.root

            def conform() -> OperationOutcome:
                fresh_inventory = scan_drive(root)
                fresh_project = next(
                    (project for project in fresh_inventory.projects if project.name == name),
                    None,
                )
                if fresh_project is None:
                    return OperationOutcome(
                        title="Conform plan changed",
                        summary=f"{name} is no longer available - nothing changed",
                        lines=("Return to the project list and refresh the drive.",),
                        severity="warning",
                    )
                fresh_map = fresh_inventory.map
                fresh_plan = build_plan(report_project(fresh_project, fresh_map), fresh_map,
                                        project=fresh_project.path)
                if (
                    fresh_map != drive_map
                    or fresh_plan.actions != plan.actions
                    or _project_token(fresh_project) != original_token
                ):
                    changed_lines = tuple(
                        f"{action.kind.title()}: "
                        f"{action.src + ' -> ' if action.src else ''}{action.dst}"
                        for action in fresh_plan.actions
                    )
                    return OperationOutcome(
                        title="Conform plan changed",
                        summary=f"{name} changed since preview - nothing moved",
                        lines=changed_lines
                        or ("Project now follows the current drive map.",),
                        severity="warning",
                    )
                result = apply_plan(root, project_path, fresh_map, fresh_plan)
                done_count = sum(1 for action in result.actions if action.status == DONE)
                skipped = sum(1 for action in result.actions if action.status == SKIPPED)
                conflicts = sum(1 for action in result.actions if action.status == CONFLICT)
                detail = []
                for action in result.actions:
                    source = f"{action.src} -> " if action.src else ""
                    note = f" - {action.note}" if action.note else ""
                    detail.append(
                        f"{(action.status or 'planned').upper()}: "
                        f"{action.kind} {source}{action.dst}{note}"
                    )
                severity = "warning" if conflicts or skipped else "information"
                summary = f"Conformed {name}: {done_count} done, {skipped} skipped"
                if conflicts:
                    summary += f", {conflicts} conflict(s) need review"
                return OperationOutcome(
                    title="Conform result",
                    summary=summary,
                    lines=tuple(detail) or ("Project already follows the drive map.",),
                    severity=severity,
                )

            self._start_operation("Applying conform plan", root, conform)

        self.push_screen(
            ConfirmListModal(
                f"Conform plan - {name}",
                lines,
                f"Apply {len(plan.actions)} repair(s)",
            ),
            done,
        )


def run_tui(drive: Path | None = None) -> int:
    AtlasApp(drive).run()
    return 0
