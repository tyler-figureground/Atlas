"""Load and validate <drive>-map.json (schema v2, v3 keys optional).

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
    # Children a new project gets with the section. A child entry in the map
    # is a name, or {"name": ..., "seed": true}; only seeded sections seed
    # children. Clean leaves a seeded child alone, as it does a seeded top.
    seed_children: tuple[str, ...] = ()


@dataclass(frozen=True)
class TemplateFile:
    """A file every project carries, copied from a bundled template.

    ``path`` is project-relative; ``template`` names a file in the template
    folder (core/templates.py); ``index`` is the AGENTS.md index row's text, and
    empty keeps the file out of the index. Doctor reports a missing one, and
    conform creates it - with its folder - but never overwrites one. ADR 0012.
    """

    path: str
    template: str
    index: str = ""


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
    templates: tuple[TemplateFile, ...] = ()

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

    # The agent workspace (ADR 0011). Scratch from one agent run lives in a
    # folder under runs_dir; closed runs are zipped into archive_dir.
    @property
    def runs_dir(self) -> str:
        return self.control_plane.get("runsDir", "")

    @property
    def backups_dir(self) -> str:
        return self.control_plane.get("backupsDir", "")

    @property
    def archive_dir(self) -> str:
        return self.control_plane.get("archiveDir", "")

    @property
    def run_retention_days(self) -> int:
        value = self.control_plane.get("runRetentionDays", 14)
        return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 14

    @property
    def agents_rules(self) -> str:
        """Template whose words go into the AGENTS.md Atlas block, after the
        working style. Empty: no rules section, as before map v3."""
        value = self.control_plane.get("agentsRules", "")
        return value if isinstance(value, str) else ""

    @property
    def agent_dirs(self) -> tuple[str, ...]:
        """Every agent-workspace folder the map names, handoffs included."""
        return tuple(d for d in (self.handoffs_dir, self.runs_dir, self.backups_dir,
                                 self.archive_dir) if d)

    @property
    def workspace_dirs(self) -> tuple[str, ...]:
        """The agent folders AGENTS.md tells agents to write into - runs and
        backups. Conform backfills these; handoffs and archive stay on demand."""
        return tuple(d for d in (self.runs_dir, self.backups_dir) if d)

    def seed_child_paths(self) -> tuple[str, ...]:
        return tuple(f"{s.id}/{c}" for s in self.sections if s.seed for c in s.seed_children)


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
        names, seeded = _parse_children(entry.get("children", []), entry["id"], path)
        sections.append(
            Section(
                id=entry["id"],
                seed=bool(entry.get("seed", False)),
                children=names,
                seed_children=seeded,
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
        templates=_parse_templates(raw.get("templates", []), path),
    )


def _parse_children(raw: object, section_id: str, path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(every child name, the seeded ones). A child is a name or an object
    with a name and an optional ``seed``; anything else refuses the map."""
    where = f"section '{section_id}' children"
    if not isinstance(raw, list):
        raise MapError(f"{where} must be a list of names: {path}")
    names: list[str] = []
    seeded: list[str] = []
    for child in raw:
        if isinstance(child, str):
            names.append(child)
            continue
        if not isinstance(child, dict) or not isinstance(child.get("name"), str) or not child["name"].strip():
            raise MapError(f"{where}: each child must be a name or {{\"name\": ...}}: {path}")
        unknown = sorted(set(child) - {"name", "seed"})
        if unknown:
            raise MapError(f"{where} '{child['name']}': unknown key {', '.join(repr(k) for k in unknown)}: {path}")
        names.append(child["name"])
        if child.get("seed") is True:
            seeded.append(child["name"])
    return tuple(names), tuple(seeded)


def _parse_templates(raw: object, path: Path) -> tuple[TemplateFile, ...]:
    """Strictly, like File Rules: a template entry writes into every project."""
    if not isinstance(raw, list):
        raise MapError(f"templates must be a list: {path}")
    out: list[TemplateFile] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw):
        where = f"templates[{index}]"
        if not isinstance(entry, dict):
            raise MapError(f"{where} is not an object: {path}")
        unknown = sorted(set(entry) - {"path", "template", "index"})
        if unknown:
            raise MapError(f"{where}: unknown key {', '.join(repr(k) for k in unknown)}: {path}")
        target = _safe_target(entry.get("path"), where, path).replace("\\", "/").strip("/")
        template = entry.get("template")
        if not isinstance(template, str) or not template.strip() or "/" in template or "\\" in template:
            raise MapError(f"{where} needs a 'template' file name: {path}")
        note = entry.get("index", "")
        if not isinstance(note, str):
            raise MapError(f"{where} 'index' must be text: {path}")
        if target.lower() in seen:
            raise MapError(f"{where}: '{target}' is listed twice: {path}")
        seen.add(target.lower())
        out.append(TemplateFile(path=target, template=template, index=note))
    return tuple(out)


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
