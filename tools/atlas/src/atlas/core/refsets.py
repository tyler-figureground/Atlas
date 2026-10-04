"""Reference Sets: list them and check drafts for leaks (ADR 0015).

A Reference Set is one folder per Deliverable Type holding a Card (``SET.md``)
and up to three Exemplars plus a Near-miss, each a folder with a ``NOTES.md``.
Every NOTES.md front matter carries a ``leak_list`` - the facts its source
project owns. A draft that contains one of them copied it.

Read-only. Nothing here writes to a drive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

CARD = "SET.md"
NOTES = "NOTES.md"
MARKER = re.compile(r"<!--\s*architecture-studio:reference:\s*([a-z0-9-]+)\s*([A-Za-z0-9, ]*)-->")
MIN_LEAK_CHARS = 3
MIN_WORD_CHARS = 5  # a lone word without digits


class RefSetError(ValueError):
    pass


def front_matter(text: str) -> dict[str, object]:
    """The flat YAML subset the Card and NOTES templates use.

    ``key: value`` lines, ``# comments``, inline ``[a, "b"]`` lists, and block
    lists of ``- item`` lines. Inline ``{...}`` maps are kept as raw strings.
    No front matter is an empty dict, never an error: a Card being drafted is
    still listable.
    """
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: dict[str, object] = {}
    key = None
    for line in lines[1:]:
        if line.strip() == "---":
            return out
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and key is not None:
            current = out.get(key)
            if not isinstance(current, list):
                current = []
                out[key] = current
            current.append(_scalar(stripped[2:], 0, "")[0])
            continue
        if ":" not in line or line[0].isspace():
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("["):
            out[key] = _flow_list(value)
        elif value.startswith("{"):
            out[key] = _plain(value, 0, "")[0]
        else:
            out[key] = _scalar(value, 0, "")[0]
    return {}  # unterminated front matter is not front matter


# Leak strings are dimensions and names - 45' - 4", O'Brien - so quoting is
# where a naive split goes wrong. These follow YAML flow scalars: "..." with
# backslash escapes, '...' with '' for a quote, plain up to a delimiter or " #".

_ESCAPES = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/", "'": "'", "0": "\0"}


def _scalar(text: str, i: int, stops: str) -> tuple[str, int]:
    while i < len(text) and text[i] == " ":
        i += 1
    if i < len(text) and text[i] == '"':
        buf, i = [], i + 1
        while i < len(text) and text[i] != '"':
            if text[i] == "\\" and i + 1 < len(text):
                buf.append(_ESCAPES.get(text[i + 1], text[i + 1]))
                i += 2
            else:
                buf.append(text[i])
                i += 1
        return "".join(buf), i + 1
    if i < len(text) and text[i] == "'":
        buf, i = [], i + 1
        while i < len(text):
            if text[i] == "'":
                if text[i + 1:i + 2] == "'":
                    buf.append("'")
                    i += 2
                    continue
                break
            buf.append(text[i])
            i += 1
        return "".join(buf), i + 1
    return _plain(text, i, stops)


def _plain(text: str, i: int, stops: str) -> tuple[str, int]:
    start = i
    while i < len(text):
        if text[i] in stops:
            break
        if text[i] == "#" and (i == start or text[i - 1].isspace()):
            break
        i += 1
    return text[start:i].strip(), i


def _flow_list(text: str) -> list[str]:
    items, i = [], 1
    while i < len(text):
        while i < len(text) and text[i] in " ,":
            i += 1
        if i >= len(text) or text[i] == "]":
            break
        value, i = _scalar(text, i, ",]")
        if value:
            items.append(value)
        while i < len(text) and text[i] not in ",]":
            i += 1  # anything after a closing quote, up to the delimiter
    return items


@dataclass(frozen=True)
class Exemplar:
    id: str
    folder: Path
    source_path: str
    leak_list: tuple[str, ...]
    has_notes: bool


@dataclass(frozen=True)
class RefSet:
    type: str
    title: str
    status: str
    entity: str
    reviewed: str
    next_review: str
    folder: Path
    exemplars: tuple[Exemplar, ...] = field(default_factory=tuple)

    def stale(self, today: date) -> bool:
        try:
            return date.fromisoformat(self.next_review) < today
        except ValueError:
            return False

    def problems(self) -> list[str]:
        found = []
        if not self.type:
            found.append("SET.md has no type")
        if not self.exemplars:
            found.append("no exemplars")
        for ex in self.exemplars:
            if not ex.has_notes:
                found.append(f"{ex.id}: no NOTES.md")
            elif not ex.leak_list:
                found.append(f"{ex.id}: empty leak_list")
        if self.status == "approved" and not self.next_review:
            found.append("approved with no next_review")
        return found


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_set(folder: Path) -> RefSet:
    card = front_matter(_text(folder / CARD))
    exemplars = []
    for child in sorted(p for p in folder.iterdir() if p.is_dir()):
        notes = child / NOTES
        if not notes.is_file():
            if re.match(r"^[EN]\d\b", child.name):
                exemplars.append(Exemplar(child.name.split()[0], child, "", (), False))
            continue
        fm = front_matter(_text(notes))
        leaks = fm.get("leak_list", [])
        leaks = tuple(s for s in (leaks if isinstance(leaks, list) else [leaks]) if s)
        exemplars.append(Exemplar(
            id=str(fm.get("id") or child.name.split()[0]),
            folder=child,
            source_path=str(fm.get("source_path", "")),
            leak_list=leaks,
            has_notes=True,
        ))
    return RefSet(
        type=str(card.get("type", "")),
        title=str(card.get("title", folder.name)),
        status=str(card.get("status", "")),
        entity=str(card.get("entity", "")),
        reviewed=str(card.get("reviewed", "")),
        next_review=str(card.get("next_review", "")),
        folder=folder,
        exemplars=tuple(exemplars),
    )


def list_sets(root: Path) -> list[RefSet]:
    if not root.is_dir():
        raise RefSetError(f"reference sets folder not found: {root}")
    return [load_set(p) for p in sorted(root.iterdir()) if p.is_dir() and (p / CARD).is_file()]


@dataclass(frozen=True)
class Leak:
    set: str
    exemplar: str
    string: str
    line: int
    text: str


def _pattern(s: str) -> re.Pattern[str]:
    """Whole-word, whitespace-tolerant. Multi-word strings ignore case; a
    single word keeps it, so a first name like "Max" or "Tom" does not fire on
    "max 5 exemplars" or "tomorrow"."""
    body = re.escape(s).replace(r"\ ", r"\s+")
    left = r"(?<!\w)" if s[:1].isalnum() else ""
    right = r"(?!\w)" if s[-1:].isalnum() else ""
    flags = re.IGNORECASE if any(ch.isspace() for ch in s) else 0
    return re.compile(left + body + right, flags)


def _project_root(path: str) -> str:
    """The project folder a path sits in: the component after the drive's root
    folder. Used to skip an exemplar when the draft is for the same project -
    that project's facts are not leaks in its own documents."""
    parts = re.split(r"[\\/]+", path.strip())
    for i, part in enumerate(parts):
        if part.lower() == "shared drives" and i + 2 < len(parts):
            return "/".join(parts[i + 1:i + 3]).lower()
    return ""


def _checkable(s: str) -> bool:
    """A lone word needs MIN_WORD_CHARS: a bare first name ("Max", "Anna")
    fires on ordinary prose and is weak evidence anyway - the full name on
    the same list catches the real copy."""
    s = s.strip()
    if any(ch.isspace() for ch in s):
        return len(s) >= MIN_LEAK_CHARS
    return len(s) >= (MIN_LEAK_CHARS if any(ch.isdigit() for ch in s) else MIN_WORD_CHARS)


def shared_strings(sets: list[RefSet]) -> set[str]:
    """Leak strings listed by exemplars from two or more source projects.

    A consultant, contractor or reviewer who works across projects belongs to
    none of them, so naming them in a new draft is not a copy."""
    owners: dict[str, set[str]] = {}
    for refset in sets:
        for ex in refset.exemplars:
            project = _project_root(ex.source_path) or ex.source_path.lower()
            for s in ex.leak_list:
                owners.setdefault(s.strip().lower(), set()).add(project)
    return {s for s, projects in owners.items() if len(projects) > 1}


def parse_marker(text: str) -> tuple[str, tuple[str, ...]] | None:
    match = MARKER.search(text)
    if not match:
        return None
    ids = tuple(s.strip() for s in match.group(2).split(",") if s.strip())
    return match.group(1), ids


def check_draft(draft: Path, sets: list[RefSet], *, set_type: str | None = None,
                exemplar_ids: tuple[str, ...] = ()) -> tuple[list[Leak], list[str]]:
    """Every leak-list string found in the draft, and the exemplars checked.

    Scope, narrowest first: the flags, then the draft's own reference marker,
    then every exemplar of every set. Exemplars from the draft's own project
    are skipped.
    """
    text = _text(draft)
    if set_type is None:
        marker = parse_marker(text)
        if marker:
            set_type, marker_ids = marker
            exemplar_ids = exemplar_ids or marker_ids
    chosen = [s for s in sets if set_type is None or s.type == set_type]
    if set_type is not None and not chosen:
        raise RefSetError(f"no reference set of type {set_type!r}")
    own = _project_root(str(draft.resolve()))
    shared = shared_strings(sets)
    lines = text.splitlines()
    leaks, checked = [], []
    for refset in chosen:
        for ex in refset.exemplars:
            if not ex.has_notes or (exemplar_ids and ex.id not in exemplar_ids):
                continue
            if own and _project_root(ex.source_path) == own:
                continue
            checked.append(f"{refset.type} {ex.id}")
            for s in ex.leak_list:
                if not _checkable(s) or s.strip().lower() in shared:
                    continue
                pattern = _pattern(s.strip())
                for number, line in enumerate(lines, 1):
                    if pattern.search(line):
                        leaks.append(Leak(refset.type, ex.id, s, number, line.strip()[:200]))
    return leaks, checked
