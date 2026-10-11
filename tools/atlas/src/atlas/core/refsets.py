"""Reference Sets: list them and check drafts for leaks (ADR 0015).

A Reference Set is one folder per Deliverable Type holding a Card (``SET.md``)
and up to three Exemplars plus a Near-miss, each a folder with a ``NOTES.md``.
Every NOTES.md front matter carries a ``leak_list`` - the facts its source
project owns. A draft that contains one of them copied it.

The only write here is the README contents block (``refs index``), rebuilt
from card front matter between ``atlas:contents`` markers, like the
``atlas:agents`` block in every project's AGENTS.md. Everything else is
read-only.
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
    # First line of the NOTES "Why this one" section - the one-line reason the
    # exemplar was chosen. "" when the section is absent or still a placeholder.
    why: str = ""


@dataclass(frozen=True)
class RefSet:
    type: str
    title: str
    status: str
    entity: str
    skill: str
    reviewed: str
    next_review: str
    folder: Path
    exemplars: tuple[Exemplar, ...] = field(default_factory=tuple)
    retired: tuple[str, ...] = field(default_factory=tuple)  # ids kept for lineage, never checked

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


def _why_summary(text: str) -> str:
    """The first content line of the NOTES '## Why this one' section.

    "" when the section is absent or holds only the template's HTML-comment
    placeholder - the caller falls back to the folder's own descriptor.
    """
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines)
                  if line.strip() == "## Why this one"), None)
    if start is None:
        return ""
    for line in lines[start + 1:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if not stripped or stripped.startswith("<!--"):
            continue
        return stripped
    return ""


def load_set(folder: Path) -> RefSet:
    card = front_matter(_text(folder / CARD))
    exemplars, retired = [], []
    for child in sorted(p for p in folder.iterdir() if p.is_dir()):
        notes = child / NOTES
        if not notes.is_file():
            if re.match(r"^[EN]\d\b", child.name):
                exemplars.append(Exemplar(child.name.split()[0], child, "", (), False))
            continue
        fm = front_matter(_text(notes))
        if str(fm.get("status", "")).lower() == "retired":
            retired.append(str(fm.get("id") or child.name.split()[0]))
            continue
        leaks = fm.get("leak_list", [])
        leaks = tuple(s for s in (leaks if isinstance(leaks, list) else [leaks]) if s)
        exemplars.append(Exemplar(
            id=str(fm.get("id") or child.name.split()[0]),
            folder=child,
            source_path=str(fm.get("source_path", "")),
            leak_list=leaks,
            has_notes=True,
            why=_why_summary(_text(notes)),
        ))
    return RefSet(
        type=str(card.get("type", "")),
        title=str(card.get("title", folder.name)),
        status=str(card.get("status", "")),
        entity=str(card.get("entity", "")),
        skill=str(card.get("skill", "")),
        reviewed=str(card.get("reviewed", "")),
        next_review=str(card.get("next_review", "")),
        folder=folder,
        exemplars=tuple(exemplars),
        retired=tuple(retired),
    )


def list_sets(root: Path) -> list[RefSet]:
    if not root.is_dir():
        raise RefSetError(f"reference sets folder not found: {root}")
    return [load_set(p) for p in sorted(root.iterdir()) if p.is_dir() and (p / CARD).is_file()]


def studio_ignore(root: Path) -> set[str]:
    """``leak_ignore:`` in the root README's front matter: names that belong to
    the studio, not to any one project - its entities, people, survey and
    software vendors."""
    readme = root / "README.md"
    if not readme.is_file():
        return set()
    value = front_matter(_text(readme)).get("leak_ignore", [])
    return {s.strip() for s in (value if isinstance(value, list) else [value]) if s.strip()}


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


# Strings every project has its own of: a date, a time, a sum, a dimension, a
# short serial ID (DR-019, T-050, A-101). On a leak list they collide with the
# new project's own facts, and the pilot showed agents bending true facts to
# clear the hit (2026-10-04). A copy is caught by the identity facts beside them.
_GENERIC = re.compile(
    r"^(\d{6}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(/\d{2,4})?"          # dates
    r"|\d{1,2}:\d{2}(:\d{2})?(-\d{1,2}:\d{2})?"                       # times
    r"|\$[\d,.]+[kKmM]?"                                               # money
    r"|[\d\s/.-]*\d['\"][\d\s'\"/.-]*"                                # dimensions: 15'-7", 48"
    r"|[\d,.]+\s*(sf|SF|ft|in|psf|%)"                                  # quantities with a unit
    r"|\d{1,5}"                                                        # plain short numbers
    r"|[A-Z]{1,3}-?\d{1,4})$"                                          # short serial IDs
)


def is_generic(s: str) -> bool:
    return bool(_GENERIC.match(s.strip()))


def _checkable(s: str) -> bool:
    """A lone word needs MIN_WORD_CHARS: a bare first name ("Max", "Anna")
    fires on ordinary prose and is weak evidence anyway - the full name on
    the same list catches the real copy. Generic strings are never checked."""
    s = s.strip()
    if is_generic(s):
        return False
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
                exemplar_ids: tuple[str, ...] = (), project: str | None = None,
                ignore: set[str] = frozenset()) -> tuple[list[Leak], list[str]]:
    """Every leak-list string found in the draft, and the exemplars checked.

    Scope, narrowest first: the flags, then the draft's own reference marker,
    then every exemplar of every set. Exemplars from the draft's own project -
    the folder it sits in, or ``project`` for a draft kept elsewhere - are
    skipped. ``ignore`` holds studio-wide names (``studio_ignore``).
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
    own = _project_root(project) if project else _project_root(str(draft.resolve()))
    shared = shared_strings(sets)
    studio = [_pattern(term) for term in ignore]
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
                if any(term.search(s) for term in studio):
                    continue  # "iGUIDE survey" names the studio's vendor, not the project
                pattern = _pattern(s.strip())
                for number, line in enumerate(lines, 1):
                    if pattern.search(line):
                        leaks.append(Leak(refset.type, ex.id, s, number, line.strip()[:200]))
    return leaks, checked


# ---- refs doctor: is every set well-formed (robustness plan 1.1) ----------

# The card's governance keys (README "How a card is approved"): present at all
# times, and non-empty once a card is approved - Tyler alone promotes, and an
# approved card with no approver or review date is a breach, not a gap.
CARD_REQUIRED = ("type", "title", "status", "owner", "approved_by", "approved",
                 "reviewed", "next_review")
CARD_STATUSES = ("candidate", "approved", "retired")
CARD_MAX_LINES = 150    # a card is read whole, every time; it stays short
MAX_LINE_CHARS = 2000   # the file reader's own cut-off (agents-rules.md)
SET_FOLDER = re.compile(r"^([ENRX]\d+)(?=\s|$)")  # exemplar, near-miss, redline pair, retired
# An id is "named in the card" where it introduces the exemplar: a table row's
# first cell (| E1 |) or a line-start declaration (**N1 - ...**, "R1 - ...",
# "N1, ..."). Prose mentions ("E1 section 3", "No N1 folder") and code section
# numbers (CRC R309.2) are deliberately not matches.
CARD_TABLE_ID = re.compile(r"^\s*\|\s*([ENRX]\d{1,2})\s*\|")
CARD_DECL_ID = re.compile(r"^(?:\*\*)?([ENRX]\d{1,2})\s*[-\u2013\u2014,]")


@dataclass(frozen=True)
class SetProblem:
    """One thing wrong with one set: the file (set-relative) and what is wrong."""
    file: str
    message: str


@dataclass(frozen=True)
class SetReport:
    type: str
    title: str
    status: str
    folder: Path
    stale: bool   # next_review passed; a warning, never a problem
    problems: tuple[SetProblem, ...] = ()


def _lnk_files(folder: Path) -> list[Path]:
    """Every ``.lnk`` under a set. Agents cannot follow shortcuts, so a frozen
    copy is a file, never a pointer. Iterdir recursion, not rglob: the drive
    walk rules ban rglob over Drive File Stream."""
    found, stack = [], [folder]
    while stack:
        for child in stack.pop().iterdir():
            if child.is_dir():
                stack.append(child)
            elif child.suffix.lower() == ".lnk":
                found.append(child)
    return sorted(found)


def _is_date(value: object) -> bool:
    try:
        date.fromisoformat(str(value))
        return True
    except ValueError:
        return False


def doctor_set(folder: Path, today: date) -> SetReport:
    """Validate one set folder. A missing card ends the check for that set."""
    problems: list[SetProblem] = []
    card_path = folder / CARD
    if not card_path.is_file():
        return SetReport("", folder.name, "", folder, False,
                         (SetProblem(CARD, "no SET.md"),))
    text = _text(card_path)
    lines = text.splitlines()
    if len(lines) > CARD_MAX_LINES:
        problems.append(SetProblem(CARD, f"{len(lines)} lines (cap {CARD_MAX_LINES})"))
    for number, line in enumerate(lines, 1):
        if len(line) > MAX_LINE_CHARS:
            problems.append(SetProblem(CARD, f"line {number}: {len(line)} characters "
                                             f"(cap {MAX_LINE_CHARS})"))
    card = front_matter(text)
    if not card:
        problems.append(SetProblem(CARD, "no front matter"))
    else:
        for key in CARD_REQUIRED:
            if key not in card:
                problems.append(SetProblem(CARD, f"front matter missing {key}"))
        for key in ("type", "title", "status"):
            if key in card and not str(card[key]).strip():
                problems.append(SetProblem(CARD, f"front matter {key} is empty"))
        status = str(card.get("status", "")).strip()
        if status and status not in CARD_STATUSES:
            problems.append(SetProblem(CARD, f"status {status!r} is not "
                                             "candidate|approved|retired"))
        if status == "approved":
            for key in ("approved_by", "approved", "reviewed", "next_review"):
                if not str(card.get(key) or "").strip():
                    problems.append(SetProblem(CARD, f"approved card has no {key}"))
        for key in ("approved", "reviewed", "next_review"):
            value = str(card.get(key) or "").strip()
            if value and not _is_date(value):
                problems.append(SetProblem(CARD, f"{key} {value!r} is not an ISO date"))
    # Exemplar, near-miss, redline-pair and retired folders on disk: each needs
    # a NOTES.md with a non-empty leak_list, retired included - lineage is the
    # point of keeping it.
    folder_ids: set[str] = set()
    for child in sorted(p for p in folder.iterdir() if p.is_dir()):
        match = SET_FOLDER.match(child.name)
        if not match:
            continue
        folder_ids.add(match.group(1))
        notes = child / NOTES
        if not notes.is_file():
            problems.append(SetProblem(child.name, "no NOTES.md"))
            continue
        rel = f"{child.name}/{NOTES}"
        fm = front_matter(_text(notes))
        folder_ids.add(str(fm.get("id") or ""))
        leaks = fm.get("leak_list", [])
        leaks = leaks if isinstance(leaks, list) else [leaks]
        if not [s for s in leaks if str(s).strip()]:
            problems.append(SetProblem(rel, "empty leak_list"))
    folder_ids.discard("")
    named = {m.group(1) for line in text.splitlines()
             for m in (CARD_TABLE_ID.match(line) or CARD_DECL_ID.match(line),) if m}
    for ex_id in sorted(named - folder_ids):
        problems.append(SetProblem(CARD, f"card names {ex_id} but no such folder"))
    for link in _lnk_files(folder):
        problems.append(SetProblem(str(link.relative_to(folder)),
                                   "shortcut - agents cannot follow .lnk"))
    next_review = str(card.get("next_review", "") or "").strip()
    stale = _is_date(next_review) and date.fromisoformat(next_review) < today
    return SetReport(
        type=str(card.get("type", "")),
        title=str(card.get("title", folder.name)),
        status=str(card.get("status", "")),
        folder=folder,
        stale=stale,
        problems=tuple(problems),
    )


def doctor_sets(root: Path, today: date) -> list[SetReport]:
    """Every set under the root, plus any folder there that is not a set."""
    if not root.is_dir():
        raise RefSetError(f"reference sets folder not found: {root}")
    return [doctor_set(p, today) for p in sorted(root.iterdir()) if p.is_dir()]


# ---- refs index: the README contents block (robustness plan 1.2) ----------

# The library's atlas:contents pattern, mirroring atlas:agents in AGENTS.md:
# Atlas owns the lines between the markers and nothing outside them.
CONTENTS_BEGIN = "<!-- atlas:contents-begin -->"
CONTENTS_END = "<!-- atlas:contents-end -->"


def _descriptor(ex: Exemplar) -> str:
    """The folder's own words when NOTES has no Why line: the folder named
    'E1 Monte Vista - CRC' describes itself as 'Monte Vista - CRC'."""
    parts = ex.folder.name.split(None, 1)
    return parts[1] if len(parts) == 2 else ex.folder.name


def contents_lines(sets: list[RefSet], today: date) -> list[str]:
    """The regenerable contents block: one row per set, from card front matter
    and the exemplars' NOTES summaries.

    Deterministic - same cards, same day, same bytes - so a regenerate with no
    changes is byte-identical and the dry run says so. The stale flag is a
    word in the Status column: text, never colour or glyph alone (ADR 0008).
    Entity and Skill come from card front matter; the Exemplars cell is each
    id with its folder descriptor ("E1 Monte Vista - CRC addition"), which is
    the curated one-line summary - NOTES prose proved too long and clipped
    mid-sentence on the first real generate.
    """
    lines = [
        CONTENTS_BEGIN,
        "",
        "| Type | Set | Entity | Status | Reviewed | Exemplars | Skill | Card |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for refset in sets:
        status = refset.status or "?"
        if refset.stale(today):
            status += " (STALE)"
        exemplars = "; ".join(f"{ex.id} {_descriptor(ex)}"
                               for ex in refset.exemplars) or "-"
        lines.append(f"| `{refset.type}` | {refset.title} | {refset.entity or '-'} | "
                     f"{status} | {refset.reviewed or '-'} | {exemplars} | "
                     f"{refset.skill or '-'} | `{refset.folder.name}\\{CARD}` |")
    lines += ["", CONTENTS_END]
    return lines


def splice_contents(lines: list[str], block: list[str]) -> list[str]:
    """``lines`` with the atlas:contents block replaced by ``block``.

    No markers means the README is hand-maintained: an error, never an insert.
    Broken markers are fixed by hand, as in AGENTS.md (AgentsBlockError).
    """
    begins = [i for i, line in enumerate(lines) if line.strip() == CONTENTS_BEGIN]
    ends = [i for i, line in enumerate(lines) if line.strip() == CONTENTS_END]
    if not begins and not ends:
        raise RefSetError("README.md has no atlas:contents markers - wrap the contents "
                          f"block in {CONTENTS_BEGIN} / {CONTENTS_END}")
    if len(begins) != 1 or len(ends) != 1 or ends[0] < begins[0]:
        raise RefSetError("atlas:contents markers in README.md are broken; fix them by hand")
    return lines[:begins[0]] + block + lines[ends[0] + 1:]
