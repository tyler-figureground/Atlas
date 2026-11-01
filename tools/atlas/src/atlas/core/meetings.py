"""The Meeting Inbox (roadmap F4): meetings in a project's meetings folder
that have no minutes yet.

`/meeting-closeout` is what files a meeting's action items into both task
lists, the decisions and the brief. It runs only when someone remembers, so a
transcript (or a bare recording) with no minutes beside it is a meeting whose
action items were never filed. This module names those meetings; it never
writes, never opens a file, and never changes a Filing State or a status.

What counts is the map's (``meetings``): which folder, which names are
transcripts, recordings and minutes. Naming on the drive varies by tool and
by hand - ``.transcript.md``, ``- Transcript.md``, ``_Transcript-Excerpt.md``,
a Dicta hash before the extension, minutes dated two days after the
recording - so pairing never relies on a matching file name:

- Files group into one meeting by date plus a normalised stem (case, the
  extensions, a 12-hex Dicta hash and a trailing "transcript"/"minutes"
  word removed), so ``x.m4a`` and ``x-<hash>.transcript.md`` are one meeting.
- A meeting pairs with minutes dated the same day first, then with the
  nearest minutes up to ``window_days`` later. Each minutes document closes
  at most one meeting; the same minutes saved as .md, .docx and .pdf is one
  document.
- An undated meeting pairs only with minutes of the same stem; otherwise it
  is pending with an unknown date, never a guessed one.

Dot folders (Dicta's ``.dicta`` working state) are skipped. A folder that
cannot be listed is reported, never read as empty (ADR 0004); a folder past
``max_depth`` is named in ``skipped``.

Cost: one listing per folder of one small subtree per project. The digest
pays it on every run (hourly), about a dozen listings per project.
"""

from __future__ import annotations

import fnmatch
import os
import re
import stat
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .mapfile import MeetingRule
from .scan import is_link, long_path

_DATE = re.compile(r"^(\d{8}|\d{6})(?!\d)")
_EXTENSION = re.compile(r"\.[a-z0-9]{1,10}$")
_HASH = re.compile(r"[\s\-_]+[0-9a-f]{12}$")
# Only a trailing word, plus the copy and version tags people add after it:
# "minutes review with client" is a meeting's name, "Minutes v2" is minutes.
_SUFFIX = re.compile(
    r"[\s\-_]*(transcript|meeting[\s\-_]*minutes|minutes)"
    r"(?:[\s\-_]*(?:excerpt|final|draft|copy|rev\d*|v\d+|\(\d+\)))*$")
_NOT_WORD = re.compile(r"[^a-z0-9]+")
_FILLER = frozenset({"meeting", "meetings", "mtg"})


@dataclass(frozen=True)
class Meeting:
    """One meeting: its date (None when the name carries none), the
    normalised stem it was grouped by, and the meetings-folder-relative files
    that make it up. ``minutes`` is the paired minutes file, or None."""

    date: date | None
    stem: str
    transcripts: tuple[str, ...] = ()
    recordings: tuple[str, ...] = ()
    minutes: str | None = None

    @property
    def closed(self) -> bool:
        return self.minutes is not None

    @property
    def transcribed(self) -> bool:
        return bool(self.transcripts)

    @property
    def label(self) -> str:
        """A file name to show for the meeting: its transcript, else its
        recording."""
        return (self.transcripts or self.recordings)[0]


@dataclass(frozen=True)
class MeetingScan:
    folder: str
    # False when the project has no meetings folder at all - nothing to
    # report, which is different from a folder that could not be read.
    present: bool = True
    meetings: tuple[Meeting, ...] = ()
    unreadable: tuple[str, ...] = ()
    # Folders below maxDepth, never listed: a truncated scan is a fact, never
    # a silent zero.
    skipped: tuple[str, ...] = ()

    @property
    def pending(self) -> tuple[Meeting, ...]:
        return tuple(m for m in self.meetings if not m.closed)

    def oldest_pending(self) -> date | None:
        dated = [m.date for m in self.pending if m.date is not None]
        return min(dated) if dated else None


def file_date(name: str) -> date | None:
    """The leading YYMMDD (or YYYYMMDD) date of a file name, or None."""
    match = _DATE.match(name)
    if not match:
        return None
    digits = match.group(1)
    if len(digits) == 6:
        digits = "20" + digits
    try:
        return date(int(digits[:4]), int(digits[4:6]), int(digits[6:]))
    except ValueError:
        return None


def stem(name: str) -> str:
    """The grouping key: the name with date, extensions, Dicta hash and a
    trailing transcript/minutes word removed, folded to letters and digits."""
    s = name.casefold()
    while True:
        cut = _EXTENSION.sub("", s)
        if cut == s:
            break
        s = cut
    s = _DATE.sub("", s)
    s = _HASH.sub("", s)
    s = _SUFFIX.sub("", s)
    s = _HASH.sub("", s)
    # Filler words drop out, so Dicta's raw "<date> - X meeting Y-<hash>" and
    # the renamed "<date> - X Y" are one meeting, not a closed one and a
    # phantom pending one. A name that is nothing but filler keeps it.
    words = [w for w in _NOT_WORD.split(s) if w]
    return "".join(w for w in words if w not in _FILLER) or "".join(words)


def _matches(globs: tuple[str, ...], name: str) -> bool:
    folded = name.casefold()
    return any(fnmatch.fnmatchcase(folded, g.casefold()) for g in globs)


def _walk(base: Path, rule: MeetingRule) -> tuple[list[str], list[str], list[str]]:
    """Every file below ``base`` to ``rule.max_depth`` folder levels, as
    sorted base-relative paths, plus what could not be read and the folders
    past the depth limit."""
    files: list[str] = []
    unreadable: list[str] = []
    skipped: list[str] = []
    stack: list[tuple[str, int]] = [("", 0)]
    while stack:
        rel, depth = stack.pop()
        try:
            with os.scandir(long_path(base / rel if rel else base)) as it:
                entries = list(it)
        except OSError as exc:
            unreadable.append(f"{rel or '.'}  {type(exc).__name__}: {exc.strerror or exc}")
            continue
        for entry in sorted(entries, key=lambda e: e.name):
            if entry.name.startswith("."):
                continue
            child = f"{rel}/{entry.name}" if rel else entry.name
            try:
                if is_link(entry):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if depth < rule.max_depth:
                        stack.append((child, depth + 1))
                    else:
                        skipped.append(child)
                    continue
            except OSError as exc:
                unreadable.append(f"{child}  {type(exc).__name__}: {exc.strerror or exc}")
                continue
            files.append(child)
    return sorted(files), unreadable, skipped


def pair(files: list[str], rule: MeetingRule) -> tuple[Meeting, ...]:
    """Group files into meetings and pair each with its minutes. Pure: the
    tests drive it with names alone."""
    groups: dict[tuple[date | None, str], dict[str, list[str]]] = {}
    minutes: dict[tuple[date | None, str], str] = {}
    for rel in sorted(files):
        name = rel.rsplit("/", 1)[-1]
        key = (file_date(name), stem(name))
        if _matches(rule.minutes, name):
            # One document per date and stem, whatever formats and copy tags
            # it was saved with; the first sorted path stands for it.
            minutes.setdefault(key, rel)
        elif _matches(rule.transcripts, name):
            groups.setdefault(key, {"t": [], "r": []})["t"].append(rel)
        elif _matches(rule.recordings, name):
            groups.setdefault(key, {"t": [], "r": []})["r"].append(rel)

    order = sorted(groups, key=lambda k: (k[0] is None, k[0] or date.min, k[1]))
    unused = dict(minutes)
    paired: dict[tuple[date | None, str], str] = {}

    def take(key: tuple[date | None, str], candidates: list[tuple[date | None, str]]) -> None:
        if not candidates:
            return
        # Prefer the same stem, then the earliest date, then the name.
        best = min(candidates, key=lambda c: (c[1] != key[1], c[0] or date.min, c[1]))
        paired[key] = unused.pop(best)

    # Exact date and stem first, so of two meetings on one day the one the
    # minutes are named for claims them. Then same day, so a later meeting's
    # minutes never close an earlier one that has its own.
    for key in order:
        if key in unused:
            paired[key] = unused.pop(key)
    for key in order:
        if key[0] is not None and key not in paired:
            take(key, [m for m in unused if m[0] == key[0]])
    def in_window(key: tuple[date | None, str], m: tuple[date | None, str]) -> bool:
        return (key[0] is not None and m[0] is not None
                and 0 < (m[0] - key[0]).days <= rule.window_days)

    # Minutes named for a meeting, inside the window, before any nearest-date
    # guess - so an older meeting never takes a newer one's minutes.
    for key in order:
        if key not in paired:
            take(key, [m for m in unused if m[1] == key[1]
                       and (key[0] is None or in_window(key, m))])
    for key in order:
        if key not in paired and key[0] is not None:
            take(key, [m for m in unused if in_window(key, m)])

    return tuple(
        Meeting(date=key[0], stem=key[1], transcripts=tuple(groups[key]["t"]),
                recordings=tuple(groups[key]["r"]), minutes=paired.get(key))
        for key in order
    )


def scan_meetings(project: Path, rule: MeetingRule) -> MeetingScan:
    """One project's meetings folder: every meeting, closed or not."""
    base = project / rule.dir
    # Only a folder that is not there is absent. Any other failure - a
    # permission error, a Drive hiccup, a file where the folder should be -
    # is unreadable, never "no meetings" (ADR 0004).
    try:
        info = os.stat(long_path(base))
    except FileNotFoundError:
        return MeetingScan(folder=rule.dir, present=False)
    except OSError as exc:
        return MeetingScan(folder=rule.dir, unreadable=(
            f".  {type(exc).__name__}: {exc.strerror or exc}",))
    if not stat.S_ISDIR(info.st_mode):
        return MeetingScan(folder=rule.dir, unreadable=(".  not a folder",))
    files, unreadable, skipped = _walk(base, rule)
    return MeetingScan(folder=rule.dir, meetings=pair(files, rule),
                       unreadable=tuple(unreadable), skipped=tuple(skipped))


def scan_dict(scan: MeetingScan) -> dict[str, object]:
    """JSON shape of one project's scan, with absence and unreadability
    spelled out so an empty ``pending`` never stands for "could not look"."""
    return {
        "folder": scan.folder,
        "present": scan.present,
        "unreadable": list(scan.unreadable),
        "skipped": list(scan.skipped),
        "closed": sum(1 for m in scan.meetings if m.closed),
        "pending": [meeting_dict(m) for m in scan.pending],
    }


def meeting_dict(m: Meeting) -> dict[str, object]:
    return {
        "date": m.date.isoformat() if m.date else None,
        "closed": m.closed,
        "transcribed": m.transcribed,
        "transcripts": list(m.transcripts),
        "recordings": list(m.recordings),
        "minutes": m.minutes,
    }
