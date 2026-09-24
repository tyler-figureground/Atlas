"""Validated project-intake values shared by Atlas CLI and TUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re


US_STATES = frozenset(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS "
    "MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split()
)
ZIP_PATTERN = re.compile(r"^\d{5}(?:-\d{4})?$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# C0, DEL, C1 (which holds NEL, U+0085), and the Unicode line and paragraph
# separators: every character a line-oriented reader may split on or a YAML
# parser refuses as non-printable.
CONTROL_PATTERN = re.compile("[\x00-\x1f\x7f-\x9f\u2028\u2029]")
STREET_PATTERN = re.compile(r"^\d+(?:-\d+)?[A-Za-z]?\s+\S")
USE_CASES = (
    "Renovation",
    "Addition",
    "Renovation + Addition",
    "Ground Up",
    "Feasibility",
    "Existing Conditions",
    "Code Compliance",
    "Other",
)


class IntakeError(ValueError):
    """Project intake contains an invalid or incomplete value."""


@dataclass(frozen=True)
class ContactSnapshot:
    id: str
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    company: str = ""
    address: str = ""

    def __post_init__(self) -> None:
        for field_name in ("id", "first_name", "last_name", "email", "phone", "company", "address"):
            object.__setattr__(self, field_name, getattr(self, field_name).strip())
        object.__setattr__(self, "email", self.email.casefold())
        if not self.id:
            raise IntakeError("contact ID is required")
        if not self.first_name and not self.last_name:
            raise IntakeError("contact name is required")
        if not EMAIL_PATTERN.fullmatch(self.email):
            raise IntakeError("contact email is invalid")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


@dataclass(frozen=True)
class ProjectUseCase:
    category: str
    custom_label: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "category", self.category.strip())
        object.__setattr__(self, "custom_label", self.custom_label.strip())
        if self.category not in USE_CASES:
            raise IntakeError("Project Use Case must be one of the supported choices")
        if self.category == "Other" and not self.custom_label:
            raise IntakeError("Other requires a custom Project Use Case label")
        if self.category != "Other" and self.custom_label:
            raise IntakeError("custom Project Use Case applies only to Other")

    @property
    def display(self) -> str:
        return self.custom_label if self.category == "Other" else self.category


@dataclass(frozen=True)
class ProjectAddress:
    street: str
    city: str
    state: str
    postal_code: str
    unit: str = ""

    def __post_init__(self) -> None:
        for field_name in ("street", "unit", "city", "state", "postal_code"):
            object.__setattr__(self, field_name, getattr(self, field_name).strip())
        object.__setattr__(self, "state", self.state.upper())
        if any(CONTROL_PATTERN.search(getattr(self, field_name)) for field_name in ("street", "unit", "city", "state", "postal_code")):
            raise IntakeError("address fields cannot contain control characters")
        if not STREET_PATTERN.match(self.street):
            raise IntakeError("street must begin with a street number and name")
        if not self.city:
            raise IntakeError("city is required")
        if self.state not in US_STATES:
            raise IntakeError("state must be a valid two-letter US abbreviation")
        if not ZIP_PATTERN.fullmatch(self.postal_code):
            raise IntakeError("ZIP must be 12345 or 12345-6789")

    @property
    def formatted(self) -> str:
        parts = [self.street]
        if self.unit:
            parts.append(self.unit)
        parts.append(f"{self.city}, {self.state} {self.postal_code}")
        return ", ".join(parts)

    @property
    def short(self) -> str:
        return self.street


@dataclass(frozen=True)
class ProjectIntake:
    project_name: str
    project_address: ProjectAddress
    project_use_case: ProjectUseCase
    billing_contact_id: str
    client_contact_id: str
    description: str = ""
    created: date = field(default_factory=date.today)

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_name", self.project_name.strip())
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "billing_contact_id", self.billing_contact_id.strip())
        object.__setattr__(self, "client_contact_id", self.client_contact_id.strip())
        if not self.project_name:
            raise IntakeError("Project Name is required")
        if CONTROL_PATTERN.search(self.project_name) or CONTROL_PATTERN.search(self.description):
            raise IntakeError("Project Name and Description cannot contain control characters")
        if not self.billing_contact_id:
            raise IntakeError("Billing Contact is required")
        if not self.client_contact_id:
            raise IntakeError("Client Contact is required")


@dataclass(frozen=True)
class ResolvedProjectIntake:
    """Validated intake with directory contacts frozen for project rendering."""

    request: ProjectIntake
    billing_contact: ContactSnapshot
    client_contact: ContactSnapshot

    def __post_init__(self) -> None:
        if self.billing_contact.id != self.request.billing_contact_id:
            raise IntakeError("Billing Contact snapshot does not match selected contact")
        if self.client_contact.id != self.request.client_contact_id:
            raise IntakeError("Client Contact snapshot does not match selected contact")

    @property
    def project_name(self) -> str:
        return self.request.project_name

    @property
    def project_address(self) -> ProjectAddress:
        return self.request.project_address

    @property
    def project_use_case(self) -> ProjectUseCase:
        return self.request.project_use_case

    @property
    def description(self) -> str:
        return self.request.description
