"""Project template files: the text Atlas copies into every project.

The map names which templates a project carries and where (``templates`` in the
drive map); this module supplies their words. The words live in the repo at
``tools/atlas/src/atlas/templates/project/`` and ship inside the wheel, so the
repo is the one place to edit them: an editable install picks an edit up at
once, and staff get it with the next release. ADR 0012.

``ATLAS_TEMPLATES`` points Atlas at another folder of templates - for tests, and
for trying a template change against a real drive before releasing it.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ENV_VAR = "ATLAS_TEMPLATES"

# {{name}} and nothing else: a template is Markdown, and Markdown is full of
# braces, brackets and angle brackets that must pass through untouched.
_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


class TemplateError(Exception):
    """A template the map names is missing or unreadable."""


def template_dir() -> Path:
    override = os.environ.get(ENV_VAR)
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "templates" / "project"


def template_path(name: str) -> Path:
    return template_dir() / name


def read_template(name: str) -> str:
    path = template_path(name)
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as error:
        raise TemplateError(f"template '{name}' cannot be read from {path.parent}: "
                            f"{error.strerror or error}") from error


def render(text: str, values: dict[str, str]) -> list[str]:
    """``text`` with every known ``{{name}}`` filled in, as lines.

    An unknown placeholder is left as written rather than blanked, so a typo in
    a template shows up in the project instead of silently vanishing.
    """
    def fill(match: re.Match[str]) -> str:
        return values.get(match.group(1), match.group(0))

    return _PLACEHOLDER.sub(fill, text).splitlines()


def render_template(name: str, values: dict[str, str]) -> list[str]:
    return render(read_template(name), values)


def template_values(folder_name: str, project_name: str = "", created: str = "") -> dict[str, str]:
    """The placeholders every template may use. ``project_name`` falls back to the
    folder name without its date prefix - all conform knows of an old project."""
    display = project_name or re.sub(r"^\d{6}_", "", folder_name)
    return {"project_folder": folder_name, "project_name": display, "created": created}
