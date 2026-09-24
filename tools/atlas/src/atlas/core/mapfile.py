"""Load and validate <drive>-map.json (schema v2).

The map is the only brain: Atlas hard-codes zero folder names. See the spec's
schema table (atlas-tui-spec.md section 8) for the contract this module reads.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


class MapError(Exception):
    """The map file is missing, unparseable, or structurally invalid."""


@dataclass(frozen=True)
class Section:
    id: str
    seed: bool = False
    children: tuple[str, ...] = ()


@dataclass(frozen=True)
class FileRule:
    """One rule filing a Loose file at a project root into a mapped folder.

    Every filter given must match; within one filter, any value may. Name filters
    are checked before content, so a PDF is only opened once its name has already
    qualified. Empty means "not a filter", never "matches nothing". See ADR 0009.
    """

    name: str
    target: str
    extensions: tuple[str, ...] = ()   # lowercased, no leading dot
    names: tuple[str, ...] = ()        # fnmatch globs, case-insensitive
    name_regex: str = ""               # re.search, case-insensitive
    pdf_text: tuple[str, ...] = ()     # any phrase, in the title or on page one


@dataclass(frozen=True)
class DriveMap:
    path: Path
    drive: str
    version: str
    project_naming: str
    sections: tuple[Section, ...]
    drift_map: dict[str, str] = field(default_factory=dict)
    relocations: dict[str, str] = field(default_factory=dict)
    control_plane: dict[str, str] = field(default_factory=dict)
    file_rules: tuple[FileRule, ...] = ()

    @property
    def section_ids(self) -> tuple[str, ...]:
        return tuple(s.id for s in self.sections)

    def section(self, section_id: str) -> Section | None:
        for s in self.sections:
            if s.id == section_id:
                return s
        return None

    # Control-plane accessors with the same defaults the PS1 tools use, so a
    # sparse map behaves identically across tool generations.
    @property
    def project_file(self) -> str:
        return self.control_plane.get("projectFile", "PROJECT.md")

    @property
    def decisions_dir(self) -> str:
        return self.control_plane.get("decisionsDir", "decisions")

    @property
    def claude_file(self) -> str:
        return self.control_plane.get("claudeFile", "CLAUDE.md")

    @property
    def agents_file(self) -> str:
        # Defaults on, unlike a PS1-era key: the house rule is that every
        # project carries AGENTS.md, whatever drive it is on. ADR 0010.
        return self.control_plane.get("agentsFile", "AGENTS.md")

    @property
    def analysis_dir(self) -> str:
        return self.control_plane.get("analysisDir", "")

    @property
    def handoffs_dir(self) -> str:
        return self.control_plane.get("handoffsDir", "")


def find_map(drive_root: Path) -> Path | None:
    """Locate the drive's map: _tools/*-map.json, ignoring _deprecated."""
    tools = drive_root / "_tools"
    if not tools.is_dir():
        return None
    candidates = sorted(
        p for p in tools.glob("*-map.json") if p.parent.name != "_deprecated"
    )
    return candidates[0] if candidates else None


def load_map(path: Path) -> DriveMap:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise MapError(f"cannot read map: {path}: {e}") from e
    except json.JSONDecodeError as e:
        raise MapError(f"map is not valid JSON: {path}: {e}") from e

    if not isinstance(raw, dict):
        raise MapError(f"map must be a JSON object: {path}")
    for key in ("drive", "version", "sections"):
        if key not in raw:
            raise MapError(f"map missing required key '{key}': {path}")

    if not isinstance(raw["sections"], list):
        raise MapError(f"sections must be a list: {path}")
    sections: list[Section] = []
    for entry in raw["sections"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise MapError(f"section without a string 'id' in {path}")
        children = entry.get("children", [])
        if not isinstance(children, list) or not all(isinstance(c, str) for c in children):
            raise MapError(f"section '{entry['id']}' children must be a list of names: {path}")
        sections.append(
            Section(
                id=entry["id"],
                seed=bool(entry.get("seed", False)),
                children=tuple(children),
            )
        )

    # Keys beginning with "_" inside relocations are commentary, not rules.
    relocations = {
        k: v for k, v in _string_map(raw, "relocations", path).items()
        if not k.startswith("_")
    }

    return DriveMap(
        path=path,
        drive=raw["drive"],
        version=str(raw["version"]),
        project_naming=raw.get("projectNaming", ""),
        sections=tuple(sections),
        drift_map=_string_map(raw, "driftMap", path),
        relocations=relocations,
        control_plane=_string_map(raw, "controlPlane", path, strings=False),
        file_rules=_parse_file_rules(raw.get("fileRules", []), path),
    )


def _string_map(raw: dict, key: str, path: Path, *, strings: bool = True) -> dict[str, str]:
    """An optional object of name -> string. Anything else refuses the map.

    A list where an object belongs used to load and then fail later, as an
    AttributeError traceback in whichever command touched it first. Keys
    beginning with "_" are commentary and may hold anything. ``strings=False``
    checks the object only: controlPlane readers already tolerate other values.
    """
    value = raw.get(key, {})
    if not isinstance(value, dict):
        raise MapError(f"{key} must be an object of name -> path: {path}")
    for k, v in value.items():
        if strings and not k.startswith("_") and not isinstance(v, str):
            raise MapError(f"{key} '{k}' must map to a string: {path}")
    return dict(value)


# Match keys a File Rule may use, and the FileRule field each one fills.
_LIST_FILTERS = {"extensions": "extensions", "names": "names", "pdfText": "pdf_text"}
_MATCH_KEYS = (*_LIST_FILTERS, "nameRegex")


def _parse_file_rules(raw: object, path: Path) -> tuple[FileRule, ...]:
    """Strictly. Every problem refuses the whole map rather than being skipped.

    This is not lint's job, deliberately. A misspelled filter key that was merely
    ignored would leave its rule matching more than its author wrote - a rule
    with ``extension`` instead of ``extensions`` and nothing else would match
    every file at every root - and a rule that matches more moves more.
    """
    if not isinstance(raw, list):
        raise MapError(f"fileRules must be a list of rules: {path}")
    rules: list[FileRule] = []
    for index, entry in enumerate(raw):
        where = f"fileRules[{index}]"
        if not isinstance(entry, dict):
            raise MapError(f"{where} is not an object: {path}")
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise MapError(f"{where} needs a 'name': {path}")
        where = f"{where} '{name}'"
        target = _safe_target(entry.get("target"), where, path)
        match = entry.get("match")
        if not isinstance(match, dict) or not match:
            raise MapError(f"{where} needs a non-empty 'match' - an empty one matches every file: {path}")
        unknown = sorted(set(match) - set(_MATCH_KEYS))
        if unknown:
            raise MapError(
                f"{where}: unknown match key {', '.join(repr(k) for k in unknown)} "
                f"(expected one of {', '.join(_MATCH_KEYS)}): {path}"
            )
        fields: dict[str, object] = {}
        for key, attr in _LIST_FILTERS.items():
            if key in match:
                fields[attr] = _string_list(match[key], f"{where} {key}", path)
        if "extensions" in fields:
            fields["extensions"] = tuple(e.lower().lstrip(".") for e in fields["extensions"])
        if "nameRegex" in match:
            fields["name_regex"] = _regex(match["nameRegex"], f"{where} nameRegex", path)
        rules.append(FileRule(name=name, target=target, **fields))
    return tuple(rules)


def _safe_target(value: object, where: str, path: Path) -> str:
    """A project-relative folder. Never absolute, never above the project."""
    if not isinstance(value, str) or not value.strip():
        raise MapError(f"{where} needs a 'target' folder: {path}")
    normalised = value.replace("\\", "/")
    if (normalised.startswith("/") or re.match(r"^[A-Za-z]:", normalised)
            or ".." in normalised.split("/")):
        raise MapError(f"{where}: target '{value}' must stay inside the project: {path}")
    return value


def _string_list(value: object, where: str, path: Path) -> tuple[str, ...]:
    values = [value] if isinstance(value, str) else value
    if (not isinstance(values, list) or not values
            or not all(isinstance(v, str) and v.strip() for v in values)):
        raise MapError(f"{where} must be a non-empty string or list of non-empty strings: {path}")
    return tuple(values)


def _regex(value: object, where: str, path: Path) -> str:
    if not isinstance(value, str) or not value:
        raise MapError(f"{where} must be a non-empty string: {path}")
    try:
        re.compile(value)
    except re.error as e:
        raise MapError(f"{where} is not a valid regular expression ({e}): {path}") from e
    return value
