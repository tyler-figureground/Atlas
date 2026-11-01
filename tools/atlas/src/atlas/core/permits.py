"""Permit tracker (roadmap F3, ADR 0024): every application in a project's AHJ
register, whose court the ball is in, and for how long.

The register's ``## Applications`` table is the source: one row per
application, kept by people and agents. Its Status cell opens with a word from
the template's vocabulary, which sets the Ball In Court. The round folders
(``R<n>_YYMMDD`` under the submissions and comments folders) are evidence:
they date the current state when a row's round matches, and they are checked
against the register - a newer round on disk than in the register, or round
folders beside an empty register, is a finding. Atlas never writes the
register.

Cost: one file read and two folder listings per project, no walk. A missing
register is missing, an unreadable one is unreadable, and a state with no date
has unknown days - never zero (ADR 0004).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .mapfile import PermitRule
from .scan import is_link, long_path

US = "US"
AHJ = "AHJ"
FIELD = "FIELD"
CLOSED = "CLOSED"
UNKNOWN = "?"

# The template's status vocabulary (AHJ-REGISTER.md) and whose move it is.
# "approved" is ours: the permit is ready to pull.
COURT = {
    "researching": US,
    "preparing": US,
    "comments": US,
    "approved": US,
    "submitted": AHJ,
    "in review": AHJ,
    "resubmitted": AHJ,
    "inspections": FIELD,
    "issued": CLOSED,
    "finaled": CLOSED,
    "withdrawn": CLOSED,
}
_TERMS = sorted(COURT, key=len, reverse=True)

ROUND_FOLDER = re.compile(r"^R(\d+)_(\d{6})(?!\d)")
_ROUND_CELL = re.compile(r"^R?(\d+)\b", re.IGNORECASE)
_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_APPLICATIONS = re.compile(r"^##\s+Applications\b", re.IGNORECASE)
_HEADING = re.compile(r"^#{1,2}\s")
_SEPARATOR = re.compile(r"^\|?\s*:?-{3,}")
_CELL_SPLIT = re.compile(r"(?<!\\)\|")

# Header text (casefolded prefix) -> field.
_COLUMNS = (
    ("agency", "agency"),
    ("application", "number"),
    ("permit", "number"),
    ("type", "type"),
    ("status", "status"),
    ("submitted", "submitted"),
    ("round", "round"),
    ("next", "next_action"),
    ("owner", "owner"),
)


@dataclass(frozen=True)
class Application:
    agency: str
    number: str
    type: str
    status: str            # the cell as written
    status_word: str | None
    court: str
    round: int | None
    next_action: str
    owner: str
    since: date | None     # when the current state began, when known
    since_source: str      # "folder" | "status" | "submitted" | ""

    def days(self, today: date) -> int | None:
        if self.since is None or self.since > today:
            return None
        return (today - self.since).days


@dataclass(frozen=True)
class Round:
    number: int
    date: date
    folder: str


@dataclass(frozen=True)
class PermitScan:
    register: str
    register_present: bool = True
    applications: tuple[Application, ...] = ()
    submissions: tuple[Round, ...] = ()
    comments: tuple[Round, ...] = ()
    # Folders under the round locations that are not R<n>_YYMMDD.
    misnamed: tuple[str, ...] = ()
    findings: tuple[str, ...] = ()
    unreadable: tuple[str, ...] = ()

    def by_court(self, court: str) -> tuple[Application, ...]:
        return tuple(a for a in self.applications if a.court == court)


def _date6(digits: str) -> date | None:
    try:
        return date(2000 + int(digits[:2]), int(digits[2:4]), int(digits[4:]))
    except ValueError:
        return None


def latest_iso(text: str) -> date | None:
    found: list[date] = []
    for match in _ISO.finditer(text):
        try:
            found.append(date(int(match.group(1)), int(match.group(2)), int(match.group(3))))
        except ValueError:
            continue
    return max(found) if found else None


def status_word(cell: str) -> str | None:
    """The vocabulary word the Status cell opens with, or None."""
    text = cell.strip().lstrip("*_`").casefold()
    return next((t for t in _TERMS if text.startswith(t)), None)


def _cells(line: str) -> list[str]:
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|") and not inner.endswith("\\|"):
        inner = inner[:-1]
    return [c.strip().replace("\\|", "|") for c in _CELL_SPLIT.split(inner)]


def parse_register(text: str) -> list[dict[str, str]]:
    """The ``## Applications`` table's rows as field dicts. Pure."""
    rows: list[dict[str, str]] = []
    in_section = False
    columns: list[str | None] | None = None
    for line in text.splitlines():
        if _HEADING.match(line):
            in_section = bool(_APPLICATIONS.match(line))
            columns = None
            continue
        if not in_section:
            continue
        if not line.lstrip().startswith("|"):
            if columns is not None and line.strip():
                columns = None     # the table ended; a later table is not this one
            continue
        if columns is None:
            columns = []
            for header in _cells(line):
                folded = header.casefold()
                columns.append(next((f for prefix, f in _COLUMNS if folded.startswith(prefix)),
                                    None))
            continue
        if _SEPARATOR.match(line.strip()):
            continue
        cells = _cells(line)
        row = {f: cells[i] for i, f in enumerate(columns) if f and i < len(cells)}
        if any(v and v != "-" for v in row.values()):
            rows.append(row)
    return rows


def _round_number(cell: str) -> int | None:
    match = _ROUND_CELL.match(cell.strip())
    return int(match.group(1)) if match else None


def build_application(row: dict[str, str], submissions: dict[int, date],
                      comments: dict[int, date]) -> Application:
    status = row.get("status", "")
    word = status_word(status)
    court = COURT.get(word, UNKNOWN) if word else UNKNOWN
    number = _round_number(row.get("round", ""))
    since, source = None, ""
    if number is not None and court == AHJ and number in submissions:
        since, source = submissions[number], "folder"
    elif number is not None and word == "comments" and number in comments:
        since, source = comments[number], "folder"
    if since is None:
        since = latest_iso(status)
        source = "status" if since else ""
    if since is None:
        since = latest_iso(row.get("submitted", ""))
        source = "submitted" if since else ""
    return Application(
        agency=row.get("agency", ""), number=row.get("number", ""), type=row.get("type", ""),
        status=status, status_word=word, court=court, round=number,
        next_action=row.get("next_action", ""), owner=row.get("owner", ""),
        since=since, since_source=source)


def _list_rounds(base: Path, rel: str) -> tuple[list[Round], list[str], list[str], bool]:
    """Round folders in one location: rounds, misnamed folder paths,
    unreadable lines, and whether anything at all is filed there."""
    rounds: list[Round] = []
    misnamed: list[str] = []
    try:
        with os.scandir(long_path(base / rel)) as it:
            entries = sorted(it, key=lambda e: e.name)
    except FileNotFoundError:
        return [], [], [], False
    except OSError as exc:
        return [], [], [f"{rel}  {type(exc).__name__}: {exc.strerror or exc}"], False
    anything = False
    for entry in entries:
        if entry.name.startswith((".", "_")):
            continue
        anything = True
        try:
            if is_link(entry) or not entry.is_dir(follow_symlinks=False):
                continue
        except OSError:
            continue
        match = ROUND_FOLDER.match(entry.name)
        when = _date6(match.group(2)) if match else None
        if match and when is not None:
            rounds.append(Round(number=int(match.group(1)), date=when,
                                folder=f"{rel}/{entry.name}"))
        else:
            misnamed.append(f"{rel}/{entry.name}")
    return rounds, misnamed, [], anything


def _by_round(rounds: list[Round]) -> dict[int, date]:
    # Two folders for one round: the later one dates it.
    out: dict[int, date] = {}
    for r in rounds:
        out[r.number] = max(out.get(r.number, r.date), r.date)
    return out


def scan_permits(project: Path, rule: PermitRule) -> PermitScan:
    unreadable: list[str] = []
    try:
        raw = Path(long_path(project / rule.register)).read_bytes()
        text: str | None = raw.decode("utf-8-sig", errors="replace")
    except FileNotFoundError:
        text = None
    except OSError as exc:
        return PermitScan(register=rule.register, unreadable=(
            f"{rule.register}  {type(exc).__name__}: {exc.strerror or exc}",))

    subs, sub_bad, sub_err, sub_any = _list_rounds(project, rule.submissions)
    coms, com_bad, com_err, _ = _list_rounds(project, rule.comments)
    unreadable += sub_err + com_err
    sub_dates, com_dates = _by_round(subs), _by_round(coms)

    rows = parse_register(text) if text is not None else []
    # Round folders carry no agency, so they can only date an application when
    # exactly one row has a round: with two, R1 could be either one's.
    with_round = [r for r in rows if (_round_number(r.get("round", "")) or 0) >= 1]
    if len(with_round) != 1:
        sub_dates, com_dates = {}, {}
    apps = tuple(build_application(r, sub_dates, com_dates) for r in rows)

    # A missing register is not a finding here: doctor's control-plane check
    # already names it, and register_present carries it in every report.
    findings: list[str] = []
    folder_rounds = subs + coms
    if folder_rounds:
        newest = max(folder_rounds, key=lambda r: (r.number, r.date))
        known = [a.round for a in apps if a.round is not None]
        if not apps:
            findings.append(f"round folders on file (newest {newest.folder}) but the "
                            "register has no applications")
        elif not known or newest.number > max(known):
            said = f"round {max(known)}" if known else "no round"
            findings.append(f"{newest.folder} is newer than the register ({said}) - "
                            "update the register")
    elif sub_any and text is not None and not apps:
        findings.append(f"submissions on file in {rule.submissions} but the register "
                        "has no applications")
    return PermitScan(
        register=rule.register, register_present=text is not None, applications=apps,
        submissions=tuple(subs), comments=tuple(coms),
        misnamed=tuple(sub_bad + com_bad), findings=tuple(findings),
        unreadable=tuple(unreadable))


def application_dict(a: Application, today: date) -> dict[str, object]:
    return {
        "agency": a.agency, "number": a.number, "type": a.type, "status": a.status,
        "status_word": a.status_word, "court": a.court, "round": a.round,
        "next_action": a.next_action, "owner": a.owner,
        "since": a.since.isoformat() if a.since else None,
        "since_source": a.since_source or None, "days": a.days(today),
    }


def scan_dict(scan: PermitScan, today: date) -> dict[str, object]:
    return {
        "register": scan.register,
        "register_present": scan.register_present,
        "applications": [application_dict(a, today) for a in scan.applications],
        "submissions": [{"round": r.number, "date": r.date.isoformat(), "folder": r.folder}
                        for r in scan.submissions],
        "comments": [{"round": r.number, "date": r.date.isoformat(), "folder": r.folder}
                     for r in scan.comments],
        "misnamed": list(scan.misnamed),
        "findings": list(scan.findings),
        "unreadable": list(scan.unreadable),
    }


def describe(a: Application, today: date) -> str:
    """``AHJ 50d (resubmitted, round 4)`` - the state in a few words."""
    days = a.days(today)
    where = {US: "we owe", AHJ: "at AHJ", FIELD: "inspections", CLOSED: "closed",
             UNKNOWN: "status unclear"}[a.court]
    age = f" {days}d" if days is not None else ""
    bits = [a.status_word or "unrecognised status"]
    if a.round is not None:
        bits.append(f"round {a.round}")
    return f"{where}{age} ({', '.join(bits)})"
