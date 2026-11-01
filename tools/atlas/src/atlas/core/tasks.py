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
from dataclasses import dataclass, replace
from datetime import date
from urllib.parse import unquote

_CHECKBOX = re.compile(r"^\s*- \[ \] (?P<body>.+)$")
_HEADING = re.compile(r"^## (?P<name>.+?)\s*$")
_ID = re.compile(r"(?:\*\*)?(?P<id>[YT]-\d+)")
_LANE = re.compile(r"`(?P<lane>AGENT|MODEL|DECISION|WAIT)`")
# A token starts where the free text ends: ready: values and claims stop before one.
_TOKEN_AHEAD = r"(?=\s+(?:added|due|after|ready|claimed):|\s*$)"
_CLAIM = re.compile(r"claimed \d{4}-\d{2}-\d{2} by [^.*]+?(?=[.*]|\s+(?:added|due|after|ready):|\s*$)")
_ISO = r"(\d{4})-(\d{2})-(\d{2})"
_ADDED = re.compile(r"\badded:\s*" + _ISO)
_DUE = re.compile(r"\bdue:\s*" + _ISO)
_AFTER = re.compile(r"\bafter:\s*(?P<ids>T-\d+(?:\s*,\s*T-\d+)*)")
_TASK_ID = re.compile(r"T-\d+")
_READY = re.compile(r"\bready:\s*(?P<value>.+?)" + _TOKEN_AHEAD)
# Markdown link target, plain or CommonMark angle-bracketed (spaces allowed inside <>).
_LINK = re.compile(r"\]\((?:<(?P<angle>[^>]+)>|(?P<target>[^)\s]+))\)")
# A ready: value is an artifact only if it looks like a path: a separator or an extension.
_PATHLIKE = re.compile(r"[/\\]|\.[A-Za-z0-9]{1,5}$")
_TICKS = re.compile(r"`(?P<path>[^`]+)`")
_YYMMDD = re.compile(r"^(\d{2})(\d{2})(\d{2})(?=[ _\-.]|$)")
# CommonMark-ish fences: optional list/number/quote markers, then ``` or ~~~.
# A backtick fence's info string has no backtick (else it is inline code); a
# tilde fence's may.
_FENCE_OPEN = re.compile(r"^\s*(?:(?:[-*+]|\d+[.)])\s+|>\s*)*"
                         r"(?:(?P<tick>`{3,})(?P<tinfo>[^`]*)|(?P<tilde>~{3,})(?P<info>.*))$")
_FENCE_CLOSE = re.compile(r"^\s*(?:(?:[-*+]\s+)|>\s*)*(?P<run>`{3,}|~{3,})\s*$")

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
    # An agent prompt sits indented under the line in a ```text fence (ADR 0023).
    prompt: bool = False

    @property
    def claimed_on(self) -> date | None:
        """The date in ``claimed YYYY-MM-DD by <name>``, when there is a claim."""
        return _iso(re.search(_ISO, self.claim)) if self.claim else None

    @property
    def since(self) -> date | None:
        """Best known filing date: ``added:`` first, then the linked source's date."""
        return self.added or self.source_date

    def age_days(self, today: date) -> int | None:
        since = self.since
        # A date in the future is a typo, not a negative age: unknown, never guessed.
        if since is None or since > today:
            return None
        return (today - since).days


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
        return _link_target(link)
    ticks = _TICKS.match(value)
    if ticks:
        return ticks.group("path")
    value = value.rstrip(".;, ")
    return value if _PATHLIKE.search(value) else ""


def _link_target(match: re.Match[str]) -> str:
    return match.group("angle") or unquote(match.group("target"))


def normalize_id(ident: str) -> str:
    """``T-7`` and ``T-007`` name the same task; compare in the three-digit form."""
    prefix, _, number = ident.partition("-")
    return f"{prefix}-{int(number):03d}" if number.isdigit() else ident


def _source_date(body: str, ready: str) -> date | None:
    paths = [_link_target(m) for m in _LINK.finditer(body)]
    paths += [m.group("path") for m in _TICKS.finditer(body)]
    if ready:
        paths.append(ready)
    for path in paths:
        # From the file name up: a dated project folder higher in the path is not
        # the source's date.
        for segment in reversed(path.replace("\\", "/").split("/")):
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
        for blocker in _TASK_ID.findall(match.group("ids")):
            blocker = normalize_id(blocker)
            if blocker not in after:
                after.append(blocker)
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


def fences(lines: list[str]) -> tuple[set[int], dict[int, str]]:
    """Closed code fences, CommonMark-style: the line numbers inside them
    (opener and closer included) and each opener's info string.

    An opener is three or more backticks or tildes, after optional list,
    number or quote markers, whose info string has no backtick (so inline
    ```code``` is not a fence). It closes on a bare run of the same character
    at least as long. A fence that never closes is not a fence: nothing
    below it is hidden, so a typo can never swallow the rest of a list.
    """
    inside: set[int] = set()
    openers: dict[int, str] = {}
    # Per fence character, the shortest run already shown to have no closer
    # anywhere below: a later, at-least-as-long opener cannot close either.
    dead: dict[str, int] = {}
    n = 0
    while n < len(lines):
        opened = _FENCE_OPEN.match(lines[n])
        if opened:
            run = opened.group("tick") or opened.group("tilde")
            info = opened.group("tinfo") if opened.group("tick") else opened.group("info")
            indent = len(lines[n]) - len(lines[n].lstrip())
            if len(run) < dead.get(run[0], len(run) + 1):
                bounded = False
                for close in range(n + 1, len(lines)):
                    line = lines[close]
                    # An indented fence lives inside its list item: a
                    # less-indented line ends the item, and the fence with it.
                    if indent and line.strip() and len(line) - len(line.lstrip()) < indent:
                        bounded = True
                        break
                    closed = _FENCE_CLOSE.match(line)
                    if (closed and closed.group("run")[0] == run[0]
                            and len(closed.group("run")) >= len(run)):
                        openers[n] = (info or "").strip()
                        inside.update(range(n, close + 1))
                        n = close
                        break
                else:
                    if not bounded:
                        dead[run[0]] = min(dead.get(run[0], len(run)), len(run))
        n += 1
    return inside, openers


def parse_open(text: str, *, lane: str | None = None) -> tuple[TaskItem, ...]:
    """Open checkbox items before ``## Done``; ``lane`` keeps only that lane tag."""
    items: list[TaskItem] = []
    section = ""
    # The last item kept, while the lines below it are still its own (indented
    # or blank); an indented ```text fence there is its prompt.
    under: int | None = None
    lines = text.splitlines()
    inside, openers = fences(lines)
    for n, line in enumerate(lines):
        # Inside a closed code fence nothing is a task or a heading: a prompt
        # may quote "- [ ]" lines of its own.
        if n in openers:
            if (under is not None and line[:1] in (" ", "\t")
                    and openers[n].split()[:1] == ["text"]):
                items[under] = replace(items[under], prompt=True)
            continue
        if n in inside:
            continue
        heading = _HEADING.match(line)
        if heading:
            under = None
            section = heading.group("name")
            if section.lower().startswith("done"):
                break
            continue
        checkbox = _CHECKBOX.match(line)
        if not checkbox:
            if not line.strip():
                continue
            if line[:1] not in (" ", "\t"):
                under = None
            continue
        body = checkbox.group("body").strip()
        if lane and f"`{lane}`" not in body:
            under = None
            continue
        items.append(_item(body, section))
        under = len(items) - 1
    return tuple(items)
