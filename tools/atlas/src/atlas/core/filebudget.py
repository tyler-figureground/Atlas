"""Control-file budgets (roadmap F6): control files grown past what an agent
should read at the start of every session.

Every agent run opens ``BRIEF.md`` and ``PROJECT.md`` first; a 1,300-line
dossier costs tokens on every run and buries the facts. The map's
``fileBudgets`` names each file, its limit and the skill that fixes a breach:

- ``maxLines``: the file has more lines than this.
- ``doneMaxAgeDays``: the file's ``## Done`` section still holds items whose
  date (the first YYYY-MM-DD on the item's line) is older than this - a
  prune is due. An item with no date is never guessed old.

Report-only and deep pass only: a breach is a warning that never changes a
Filing State or status. A file that is absent is skipped - a missing control
file is doctor's control-plane finding, not a budget one. A file that cannot
be read is reported, never treated as empty (ADR 0004).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .mapfile import FileBudget
from .scan import long_path

_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_DONE = re.compile(r"^##\s+Done\b", re.IGNORECASE)
_HEADING = re.compile(r"^##\s")
_ITEM = re.compile(r"^- ")


@dataclass(frozen=True)
class BudgetBreach:
    file: str
    kind: str          # "lines" | "done"
    value: int         # line count, or number of stale Done items
    limit: int         # maxLines, or doneMaxAgeDays
    fix: str
    oldest: date | None = None   # "done" only: the oldest stale item's date

    @property
    def message(self) -> str:
        if self.kind == "lines":
            return f"{self.file} is {self.value} lines (budget {self.limit}) - {self.fix}"
        since = f", oldest {self.oldest.isoformat()}" if self.oldest else ""
        noun = "item" if self.value == 1 else "items"
        return (f"{self.file} Done holds {self.value} {noun} older than "
                f"{self.limit} days{since} - {self.fix}")


@dataclass(frozen=True)
class BudgetScan:
    breaches: tuple[BudgetBreach, ...] = ()
    unreadable: tuple[str, ...] = ()


def line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _item_date(line: str) -> date | None:
    match = _ISO.search(line)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def stale_done(text: str, today: date, max_age_days: int) -> list[date]:
    """Dates of top-level ``## Done`` items older than ``max_age_days``."""
    stale: list[date] = []
    in_done = False
    for line in text.splitlines():
        if _HEADING.match(line):
            in_done = bool(_DONE.match(line))
            continue
        if in_done and _ITEM.match(line):
            when = _item_date(line)
            if when is not None and (today - when).days > max_age_days:
                stale.append(when)
    return stale


def check(budget: FileBudget, text: str, today: date) -> list[BudgetBreach]:
    """The breaches one file's text makes against one budget. Pure."""
    out: list[BudgetBreach] = []
    if budget.max_lines is not None:
        lines = line_count(text)
        if lines > budget.max_lines:
            out.append(BudgetBreach(file=budget.file, kind="lines", value=lines,
                                    limit=budget.max_lines, fix=budget.fix))
    if budget.done_max_age_days is not None:
        stale = stale_done(text, today, budget.done_max_age_days)
        if stale:
            out.append(BudgetBreach(file=budget.file, kind="done", value=len(stale),
                                    limit=budget.done_max_age_days, fix=budget.fix,
                                    oldest=min(stale)))
    return out


def scan_budgets(project: Path, budgets: tuple[FileBudget, ...],
                 today: date) -> BudgetScan:
    breaches: list[BudgetBreach] = []
    unreadable: list[str] = []
    for budget in budgets:
        path = project / budget.file
        try:
            raw = Path(long_path(path)).read_bytes()
        except FileNotFoundError:
            continue
        except OSError as exc:
            unreadable.append(f"{budget.file}  {type(exc).__name__}: {exc.strerror or exc}")
            continue
        text = raw.decode("utf-8-sig", errors="replace")
        breaches.extend(check(budget, text, today))
    return BudgetScan(breaches=tuple(breaches), unreadable=tuple(unreadable))


def breach_dict(b: BudgetBreach) -> dict[str, object]:
    return {
        "file": b.file,
        "kind": b.kind,
        "value": b.value,
        "limit": b.limit,
        "fix": b.fix,
        "oldest": b.oldest.isoformat() if b.oldest else None,
    }
