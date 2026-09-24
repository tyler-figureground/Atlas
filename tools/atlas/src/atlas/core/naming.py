"""Project-folder sanitization and date-prefixed folder formatting."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

ILLEGAL = re.compile(r'[\\/:*?"<>|]')  # illegal Windows folder chars -> space
WHITESPACE = re.compile(r"\s+")
MAX_FOLDER_COMPONENT = 200
MAX_PROJECT_PATH = 240


class NamingError(ValueError):
    """A derived project folder cannot be created safely on Windows."""


def clean_name_part(s: str | None) -> str:
    if not s:
        return ""
    s = ILLEGAL.sub(" ", s.strip())
    s = WHITESPACE.sub(" ", s)
    # Spaces and dots together: "Kitchen ." must not leave "Kitchen ", a
    # trailing space Windows would silently drop from the folder it makes.
    return s.rstrip(" .").strip()


def build_folder_name(created: date, name: str, desc: str = "") -> str:
    """YYMMDD_<ShortAddress>[-<Description>]; parts are pre-cleaned."""
    stamp = created.strftime("%y%m%d")
    return f"{stamp}_{name}-{desc}" if desc else f"{stamp}_{name}"


def _validate_path_budget(path: Path) -> None:
    resolved = path.resolve(strict=False)
    if any(len(part) > MAX_FOLDER_COMPONENT for part in resolved.parts) or len(str(resolved)) > MAX_PROJECT_PATH:
        raise NamingError(
            f"project path is too long ({len(str(resolved))} characters); shorten Description or mapped names"
        )


def validate_project_folder_path(root: Path, folder_name: str) -> Path:
    """Return derived path or reject component/full paths unsafe on Windows."""

    project = Path(root) / folder_name
    _validate_path_budget(project)
    return project


def validate_project_child_path(project: Path, relative: str) -> Path:
    """Reject escaping, absolute, or overlong paths supplied by a drive map."""

    normalized = relative.replace("\\", "/")
    relative_path = Path(normalized)
    if not normalized or relative_path.is_absolute() or ".." in relative_path.parts:
        raise NamingError(f"mapped project path must stay below project root: {relative}")
    candidate = project.joinpath(*relative_path.parts)
    try:
        candidate.resolve(strict=False).relative_to(project.resolve(strict=False))
    except ValueError:
        raise NamingError(f"mapped project path escapes project root: {relative}") from None
    _validate_path_budget(candidate)
    return candidate
