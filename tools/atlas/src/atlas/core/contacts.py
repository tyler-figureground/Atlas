"""Shared contact directory for one mapped Atlas drive."""

from __future__ import annotations

import json
import hashlib
import os
import re
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping
from uuid import UUID, uuid4

from .intake import CONTROL_PATTERN, STREET_PATTERN, US_STATES, ZIP_PATTERN


_PO_BOX_PATTERN = re.compile(
    r"(?:PO|P\.O\.)\s+Box\s+[A-Za-z0-9][A-Za-z0-9-]*", re.IGNORECASE
)


class ContactError(Exception):
    """Contact data or persistence is invalid and needs user action."""


class DuplicateContactError(ContactError):
    """A contact with this email already exists."""

    def __init__(self, existing: "Contact") -> None:
        self.existing = existing
        super().__init__(
            f"contact email already exists for {existing.first_name} {existing.last_name} "
            f"({existing.email}); select that contact or use a different email"
        )


class _ConcurrentContactWrite(Exception):
    pass


@dataclass(frozen=True)
class MailingAddress:
    street: str
    city: str
    state: str
    postal_code: str
    unit: str = ""
    country: str = "US"

    def __post_init__(self) -> None:
        for field_name in ("street", "unit", "city", "state", "postal_code", "country"):
            object.__setattr__(self, field_name, getattr(self, field_name).strip())
        object.__setattr__(self, "state", self.state.upper())
        object.__setattr__(self, "country", self.country.upper())
        if any(
            CONTROL_PATTERN.search(getattr(self, field_name))
            for field_name in ("street", "unit", "city", "state", "postal_code", "country")
        ):
            raise ContactError("contact address fields cannot contain control characters")
        if not (
            STREET_PATTERN.match(self.street) or _PO_BOX_PATTERN.fullmatch(self.street)
        ):
            raise ContactError(
                "contact address is invalid: street must begin with a street number and name "
                "or be a PO Box"
            )
        if not self.city:
            raise ContactError("contact address is invalid: city is required")
        if self.state not in US_STATES:
            raise ContactError(
                "contact address is invalid: state must be a valid two-letter US abbreviation"
            )
        if not ZIP_PATTERN.fullmatch(self.postal_code):
            raise ContactError("contact address is invalid: ZIP must be 12345 or 12345-6789")
        if self.country != "US":
            raise ContactError("contact address country must be US")


@dataclass(frozen=True)
class ContactDraft:
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    company: str | None = None
    address: Mapping[str, str] | MailingAddress | None = None


@dataclass(frozen=True)
class Contact:
    id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    company: str | None
    address: dict[str, str] | None
    created_at: str
    updated_at: str
    # Keys this build does not know, carried through every write untouched so
    # a newer Atlas on another workstation never has its fields stripped.
    _extra: Mapping[str, object] = field(default_factory=dict, repr=False, compare=False)
    _address_extra: Mapping[str, object] = field(
        default_factory=dict, repr=False, compare=False
    )


@dataclass(frozen=True)
class ContactDirectory:
    contacts: tuple[Contact, ...] = ()
    _digest: str | None = field(default=None, repr=False, compare=False)
    _extra: Mapping[str, object] = field(default_factory=dict, repr=False, compare=False)


_CONTACT_KEYS = frozenset(
    ("id", "firstName", "lastName", "email", "phone", "company", "address", "createdAt", "updatedAt")
)
_ADDRESS_KEYS = frozenset(("street", "unit", "city", "state", "postalCode", "country"))
_DIRECTORY_KEYS = frozenset(("schemaVersion", "contacts"))


def _unknown(raw: Mapping[str, object], known: frozenset[str]) -> dict[str, object]:
    return {key: value for key, value in raw.items() if key not in known}


@dataclass(frozen=True)
class _ContactValues:
    first_name: str
    last_name: str
    email: str
    phone: str | None
    company: str | None
    address: dict[str, str] | None


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _record_error(path: Path, index: int, detail: str) -> ContactError:
    return ContactError(
        f"{path} contact {index} {detail}. Repair or restore the file, then retry; "
        "file not changed."
    )


def _required_record_text(
    item: dict[str, object], key: str, path: Path, index: int
) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _record_error(path, index, f"has missing or invalid '{key}'")
    return value.strip()


def _record_timestamp(value: str, key: str, path: Path, index: int) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise _record_error(path, index, f"'{key}' must be an ISO-8601 UTC timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise _record_error(path, index, f"'{key}' must be an ISO-8601 UTC timestamp")
    return value


def _address_from_storage(
    value: object, path: Path, index: int
) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise _record_error(path, index, "'address' must be an object or null")
    address = value
    required = ("street", "city", "state", "postalCode", "country")
    for key in required:
        if not isinstance(address.get(key), str) or not address[key].strip():
            raise _record_error(path, index, f"'address' has missing or invalid '{key}'")
    unit = address.get("unit", "")
    if not isinstance(unit, str):
        raise _record_error(path, index, "'address.unit' must be text")
    try:
        validated = MailingAddress(
            street=address["street"],
            unit=unit,
            city=address["city"],
            state=address["state"],
            postal_code=address["postalCode"],
            country=address["country"],
        )
    except ContactError as error:
        raise _record_error(path, index, f"'address' is invalid: {error}") from error
    return _address_to_contact(validated)


def _contact_from_storage(item: object, path: Path, index: int) -> Contact:
    if not isinstance(item, dict):
        raise _record_error(path, index, "must be an object")
    contact_id = _required_record_text(item, "id", path, index)
    try:
        UUID(contact_id)
    except ValueError as error:
        raise _record_error(path, index, "'id' must be a UUID") from error
    first_name = _required_record_text(item, "firstName", path, index)
    last_name = _required_record_text(item, "lastName", path, index)
    email = _required_record_text(item, "email", path, index)
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) is None:
        raise _record_error(path, index, "'email' is invalid")
    phone_value = item.get("phone")
    if phone_value is not None and not isinstance(phone_value, str):
        raise _record_error(path, index, "'phone' must be text or null")
    phone = _optional_text(phone_value)
    if phone is not None and not 7 <= sum(character.isdigit() for character in phone) <= 15:
        raise _record_error(path, index, "'phone' must contain between 7 and 15 digits")
    company_value = item.get("company")
    if company_value is not None and not isinstance(company_value, str):
        raise _record_error(path, index, "'company' must be text or null")
    created_at = _required_record_text(item, "createdAt", path, index)
    updated_at = _required_record_text(item, "updatedAt", path, index)
    raw_address = item.get("address")
    return Contact(
        _extra=_unknown(item, _CONTACT_KEYS),
        _address_extra=(
            _unknown(raw_address, _ADDRESS_KEYS) if isinstance(raw_address, dict) else {}
        ),
        id=contact_id,
        first_name=first_name,
        last_name=last_name,
        email=email.casefold(),
        phone=phone,
        company=_optional_text(company_value),
        address=_address_from_storage(item.get("address"), path, index),
        created_at=_record_timestamp(created_at, "createdAt", path, index),
        updated_at=_record_timestamp(updated_at, "updatedAt", path, index),
    )


def _address_to_storage(
    value: dict[str, str] | None, extra: Mapping[str, object] | None = None
) -> dict[str, object] | None:
    if value is None:
        return None
    return {
        "street": value["street"],
        "unit": value.get("unit", ""),
        "city": value["city"],
        "state": value["state"],
        "postalCode": value["postal_code"],
        "country": value["country"],
        **(extra or {}),
    }


def _address_to_contact(value: MailingAddress) -> dict[str, str]:
    return {
        "street": value.street,
        "unit": value.unit,
        "city": value.city,
        "state": value.state,
        "postal_code": value.postal_code,
        "country": value.country,
    }


def _normalize_address(
    value: Mapping[str, str] | MailingAddress | None,
) -> dict[str, str] | None:
    if value is None:
        return None
    if isinstance(value, MailingAddress):
        return _address_to_contact(value)
    address = {
        "street": value.get("street", "").strip(),
        "unit": value.get("unit", "").strip(),
        "city": value.get("city", "").strip(),
        "state": value.get("state", "").strip().upper(),
        "postal_code": value.get("postal_code", value.get("postalCode", "")).strip(),
        "country": value.get("country", "US").strip().upper(),
    }
    if not any(address[field] for field in ("street", "unit", "city", "state", "postal_code")):
        return None
    return address


def _validate_draft(draft: ContactDraft) -> _ContactValues:
    first_name = draft.first_name.strip()
    last_name = draft.last_name.strip()
    email = draft.email.strip()
    for field_name, value in (("first name", first_name), ("last name", last_name)):
        if not value:
            raise ContactError(f"{field_name} is required")
    if not email:
        raise ContactError("email is required")
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) is None:
        raise ContactError("email must look like name@example.com")
    phone = _optional_text(draft.phone)
    if phone is not None and not 7 <= sum(character.isdigit() for character in phone) <= 15:
        raise ContactError("phone must contain between 7 and 15 digits")
    address = _normalize_address(draft.address)
    if address is not None:
        missing = [
            field.replace("_", " ")
            for field in ("street", "city", "state", "postal_code", "country")
            if not address[field]
        ]
        if missing:
            raise ContactError(f"address missing required field(s): {', '.join(missing)}")
        address = _address_to_contact(
            MailingAddress(
                street=address["street"],
                unit=address["unit"],
                city=address["city"],
                state=address["state"],
                postal_code=address["postal_code"],
                country=address["country"],
            )
        )
    return _ContactValues(
        first_name=first_name,
        last_name=last_name,
        email=email.casefold(),
        phone=phone,
        company=_optional_text(draft.company),
        address=address,
    )


def _contacts_payload(
    contacts: tuple[Contact, ...], extra: Mapping[str, object] | None = None
) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        **(extra or {}),
        "contacts": [
            {
                "id": item.id,
                "firstName": item.first_name,
                "lastName": item.last_name,
                "email": item.email,
                "phone": item.phone,
                "company": item.company,
                "address": _address_to_storage(item.address, item._address_extra),
                "createdAt": item.created_at,
                "updatedAt": item.updated_at,
                **item._extra,
            }
            for item in contacts
        ],
    }


def _sort_key(contact: Contact) -> tuple[str, str, str, str, str]:
    return (
        contact.last_name.casefold(),
        contact.first_name.casefold(),
        (contact.company or "").casefold(),
        contact.email.casefold(),
        contact.id,
    )


def _current_digest(path: Path) -> str | None:
    try:
        contents = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ContactError(f"cannot verify {path} before writing: {error}; store unchanged") from error
    return hashlib.sha256(contents).hexdigest()


def _write_payload(
    path: Path, payload: dict[str, object], expected_digest: str | None
) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        if _current_digest(path) != expected_digest:
            raise _ConcurrentContactWrite
        try:
            os.replace(temporary, path)
        except OSError as error:
            raise ContactError(f"cannot atomically replace {path}: {error}; store unchanged") from error
        temporary = None
    except ContactError:
        raise
    except OSError as error:
        raise ContactError(f"cannot atomically write {path}: {error}; store unchanged") from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def load_contacts(drive_root: Path) -> ContactDirectory:
    """Load the drive contact directory; an absent store is empty."""
    path = Path(drive_root) / "_tools" / "billing-contacts.json"
    if not path.exists():
        return ContactDirectory()
    try:
        contents = path.read_bytes()
        raw = json.loads(contents.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ContactError(
            f"{path} is not UTF-8 ({error}); repair or restore the file, then retry; "
            "file not changed."
        ) from error
    except json.JSONDecodeError as error:
        raise ContactError(
            f"{path} is not valid JSON ({error.msg} at line {error.lineno}, "
            f"column {error.colno}). Repair or restore the file, then retry; file not changed."
        ) from error
    except OSError as error:
        raise ContactError(f"cannot read {path}: {error}; file not changed") from error
    if not isinstance(raw, dict):
        raise ContactError(f"{path} must contain a JSON object; file not changed")
    version = raw.get("schemaVersion")
    if type(version) is not int or version != 1:
        raise ContactError(
            f"{path} has unsupported schemaVersion {version!r}; expected 1. "
            "Upgrade Atlas or restore a schema v1 file; file not changed."
        )
    if "contacts" not in raw:
        raise ContactError(f"{path} is missing required 'contacts' list; file not changed")
    if not isinstance(raw["contacts"], list):
        raise ContactError(f"{path} 'contacts' must be a list; file not changed")
    parsed_contacts = [
        _contact_from_storage(item, path, index)
        for index, item in enumerate(raw["contacts"], start=1)
    ]
    seen_ids: set[str] = set()
    seen_emails: set[str] = set()
    for index, contact in enumerate(parsed_contacts, start=1):
        normalized_id = contact.id.casefold()
        normalized_email = contact.email.casefold()
        if normalized_id in seen_ids:
            raise _record_error(path, index, "has duplicate id")
        if normalized_email in seen_emails:
            raise _record_error(path, index, "has duplicate email")
        seen_ids.add(normalized_id)
        seen_emails.add(normalized_email)
    contacts = tuple(sorted(parsed_contacts, key=_sort_key))
    return ContactDirectory(
        contacts=contacts,
        _digest=hashlib.sha256(contents).hexdigest(),
        _extra=_unknown(raw, _DIRECTORY_KEYS),
    )


def find_contact(directory: ContactDirectory, id_or_email: str) -> Contact | None:
    """Find a contact by stable UUID or email, ignoring email case."""
    needle = id_or_email.strip().casefold()
    for contact in directory.contacts:
        if contact.id.casefold() == needle or contact.email.casefold() == needle:
            return contact
    return None


_STALE_LOCK_SECONDS = 600


@contextmanager
def _store_lock(path: Path):
    """Serialize writers; recover lock debris left by a terminated process."""

    lock_path = path.with_suffix(path.suffix + ".lock")
    descriptor: int | None = None
    for attempt in range(2):
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                stale = time.time() - lock_path.stat().st_mtime > _STALE_LOCK_SECONDS
            except FileNotFoundError:
                continue
            except OSError as error:
                raise ContactError(f"cannot inspect contact lock {lock_path}: {error}") from error
            if stale and attempt == 0:
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
                except OSError as error:
                    raise ContactError(
                        f"stale contact lock must be removed manually: {lock_path}: {error}"
                    ) from error
                continue
            raise ContactError(
                f"contact store is being updated. Wait a moment and retry. "
                f"If no Atlas operation is running after 10 minutes, remove {lock_path}."
            ) from None
        except OSError as error:
            raise ContactError(f"cannot lock contact store {path}: {error}") from error
    if descriptor is None:
        raise ContactError(f"cannot acquire contact lock {lock_path}")
    try:
        os.write(descriptor, f"pid={os.getpid()} created={time.time()}\n".encode("ascii"))
        os.close(descriptor)
        descriptor = None
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass


def add_contact(drive_root: Path, draft: ContactDraft) -> Contact:
    """Add one contact to a drive and return its stable directory record."""
    values = _validate_draft(draft)

    path = Path(drive_root) / "_tools" / "billing-contacts.json"
    contact: Contact | None = None
    path.parent.mkdir(parents=True, exist_ok=True)
    with _store_lock(path):
        for attempt in range(2):
            directory = load_contacts(drive_root)
            existing = next(
                (item for item in directory.contacts if item.email == values.email),
                None,
            )
            if existing is not None:
                raise DuplicateContactError(existing)
            if contact is None:
                stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                contact = Contact(
                    id=str(uuid4()),
                    first_name=values.first_name,
                    last_name=values.last_name,
                    email=values.email,
                    phone=values.phone,
                    company=values.company,
                    address=values.address,
                    created_at=stamp,
                    updated_at=stamp,
                )
            contacts = tuple(sorted((*directory.contacts, contact), key=_sort_key))
            try:
                _write_payload(
                    path, _contacts_payload(contacts, directory._extra), directory._digest
                )
            except _ConcurrentContactWrite:
                if attempt == 0:
                    continue
                raise ContactError(
                    f"contact store changed twice while adding; {path} was not overwritten. Retry."
                ) from None
            return contact
    raise AssertionError("unreachable")


def update_contact(drive_root: Path, contact_id: str, draft: ContactDraft) -> Contact:
    """Replace one contact's editable fields while preserving its identity."""
    values = _validate_draft(draft)

    path = Path(drive_root) / "_tools" / "billing-contacts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    needle = contact_id.strip().casefold()
    with _store_lock(path):
        for attempt in range(2):
            directory = load_contacts(drive_root)
            current = next(
                (item for item in directory.contacts if item.id.casefold() == needle),
                None,
            )
            if current is None:
                raise ContactError(
                    f"contact ID not found: {contact_id!r}. Choose an existing contact ID; "
                    "file not changed."
                )
            existing = next(
                (
                    item
                    for item in directory.contacts
                    if item.id.casefold() != needle
                    and item.email == values.email
                ),
                None,
            )
            if existing is not None:
                raise DuplicateContactError(existing)
            updated_at = datetime.now(timezone.utc)
            previous_updated_at = datetime.fromisoformat(
                current.updated_at.replace("Z", "+00:00")
            )
            if updated_at <= previous_updated_at:
                updated_at = previous_updated_at + timedelta(microseconds=1)
            updated = Contact(
                id=current.id,
                first_name=values.first_name,
                last_name=values.last_name,
                email=values.email,
                phone=values.phone,
                company=values.company,
                address=values.address,
                created_at=current.created_at,
                updated_at=updated_at.isoformat().replace("+00:00", "Z"),
                _extra=current._extra,
                _address_extra=current._address_extra if values.address else {},
            )
            contacts = tuple(
                sorted(
                    (updated if item.id.casefold() == needle else item for item in directory.contacts),
                    key=_sort_key,
                )
            )
            try:
                _write_payload(
                    path, _contacts_payload(contacts, directory._extra), directory._digest
                )
            except _ConcurrentContactWrite:
                if attempt == 0:
                    continue
                raise ContactError(
                    f"contact store changed twice while updating; {path} was not overwritten. "
                    "Retry."
                ) from None
            return updated
    raise AssertionError("unreachable")
