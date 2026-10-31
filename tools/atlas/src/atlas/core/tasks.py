"""Task lines: the one parser for ``TASKS.md`` and ``TYLER.md`` checkbox items.

ADR 0016 / 0023 give both files the same line shape - ``- [ ] <ID> [`LANE`] <task>``
under headings, with ``## Done`` closing the open part. The Tyler digest, its Action
Queue and the archive preview all read open work through ``parse_open``, so they can
never disagree about what is open.

Parsing stays shallow and forgiving: a line that ignores the template still parses.
Optional tokens anywhere on the line add structure when agents write them:

- ``added:YYYY-MM-DD`` - when the item was filed (its age).
- ``due:YYYY-MM-DD`` - when it must be done.
- ``after:T-NNN`` - blocked by that task; repeatable, or ``after:T-1, T-2``.
- ``ready: <path or [link](path)>`` - an artifact an agent already prepared.

A malformed date is ignored, never guessed. Without ``added:``, age falls back to
the ``YYMMDD`` date of a file the line links (minutes, a draft) - the age of the
source. Bare digits outside a link never date a line: part numbers look like dates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import unquote

_CHECKBOX = re.compile(r"^\s*- \[ \] (?P<body>.+)$")
_HEADING = re.compile(r"^## (?P<name>.+?)\s*$")
_ID = re.compile(r"(?:\*\*)?(?P<id>[YT]-\d+)")
_LANE = re.compile(r"`(?P<lane>AGENT|MODEL|DECISION|WAIT)`")
_CLAIM = re.compile(r"claimed \d{4}-\d{2}-\d{2} by [^.*]+")
_ISO = r"(\d{4})-(\d{2})-(\d{2})"
_ADDED = re.compile(r"\badded:\s*" + _ISO)
_DUE = re.compile(r"\bdue:\s*" + _ISO)
_AFTER = re.compile(r"\bafter:\s*(?P<ids>T-\d+(?:\s*,\s*T-\d+)*)")
_TASK_ID = re.compile(r"T-\d+")
_READY = re.compile(r"\bready:\s*(?P<value>.+)$")
_LINK = re.compile(r"\]\((?P<target>[^)\s]+)\)")
_TICKS = re.compile(r"`(?P<path>[^`]+)`")
_YYMMDD = re.compile(r"^(\d{2})(\d{2})(\d{2})(?=[ _\-.]|$)")

# Item text runs long on real lists (211 Centre lines carry full audit detail);
# views scan, they do not replace the list, so bodies are clipped.
CLIP = 160


@dataclass(frozen=True)
class TaskItem:
    id: str  # Y-NNN / T-NNN when present, else ""
    text: str  # whitespace-collapsed, clipped to CLIP
    section: str  # heading the item sat under: Now, Next, In progress, ...
    claim: str = ""  # "claimed YYYY-MM-DD by <name>" when present
    lane: str = ""  # AGENT / MODEL / DECISION / WAIT when tagged
    added: date | None = None
    due: date | None = None
    after: tuple[str, ...] = ()
    ready: str = ""
    source_date: date | None = None

    @property
    def since(self) -> date | None:
        """Best known filing date: ``added:`` first, then the linked source's date."""
        return self.added or self.source_date

    def age_days(self, today: date) -> int | None:
        since = self.since
        return None if since is None else (today - since).days


def clip(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= CLIP else text[: CLIP - 1].rstrip() + "…"


def _iso(match: re.Match[str] | None) -> date | None:
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _ready(body: str) -> str:
    match = _READY.search(body)
    if not match:
        return ""
    value = match.group("value").strip()
    link = _LINK.search(value)
    if link:
        return unquote(link.group("target"))
    ticks = _TICKS.match(value)
    if ticks:
        return ticks.group("path")
    return value.rstrip(".;, ")


def _source_date(body: str, ready: str) -> date | None:
    paths = [unquote(m.group("target")) for m in _LINK.finditer(body)]
    paths += [m.group("path") for m in _TICKS.finditer(body)]
    if ready:
        paths.append(ready)
    for path in paths:
        for segment in path.replace("\\", "/").split("/"):
            match = _YYMMDD.match(segment)
            if not match:
                continue
            try:
                return date(2000 + int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                continue
    return None


def _item(body: str, section: str) -> TaskItem:
    ident = _ID.match(body)
    lane = _LANE.search(body)
    claim = _CLAIM.search(body)
    after: list[str] = []
    for match in _AFTER.finditer(body):
        after += [i for i in _TASK_ID.findall(match.group("ids")) if i not in after]
    ready = _ready(body)
    return TaskItem(
        id=ident.group("id") if ident else "",
        text=clip(body),
        section=section,
        claim=claim.group(0).strip() if claim else "",
        lane=lane.group("lane") if lane else "",
        added=_iso(_ADDED.search(body)),
        due=_iso(_DUE.search(body)),
        after=tuple(after),
        ready=ready,
        source_date=_source_date(body, ready),
    )


def parse_open(text: str, *, lane: str | None = None) -> tuple[TaskItem, ...]:
    """Open checkbox items before ``## Done``; ``lane`` keeps only that lane tag."""
    items: list[TaskItem] = []
    section = ""
    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading:
            section = heading.group("name")
            if section.lower().startswith("done"):
                break
            continue
        checkbox = _CHECKBOX.match(line)
        if not checkbox:
            continue
        body = checkbox.group("body").strip()
        if lane and f"`{lane}`" not in body:
            continue
        items.append(_item(body, section))
    return tuple(items)
