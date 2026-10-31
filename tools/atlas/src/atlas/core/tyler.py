"""Tyler digest: open errands and decision blockers rolled up across projects.

ADR 0016. Each project's ``00 Tasks/TYLER.md`` is the source of truth for Tyler's
personal errands; the production ``00 Tasks/TASKS.md`` ``DECISION`` lane holds the
calls only Tyler can make that block production. This module reads both, never
writes them, and renders one Markdown digest (``_tools/TYLER-TODAY.md`` when the
CLI writes it). The digest is a view: regenerated, never edited.

The digest opens with the **Action Queue** - one screen, at most 15 lines, of what
to do first: drafts ready to send, decisions ranked by how much production they
block, what is due, what is oldest. The per-project detail follows, unchanged.

Parsing lives in ``core.tasks`` (one parser for every reader). A missing file is
reported as missing, not as empty - absence and "nothing to do" must never read
alike (ADR 0004). Unknown is shown as unknown: an undated item has no age, and a
decision in a project that never writes ``after:`` blocks ``?``, never ``0``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .scan import DriveInventory
from .tasks import TaskItem, normalize_id, parse_open

TYLER_PATH = "00 Tasks/TYLER.md"
TASKS_PATH = "00 Tasks/TASKS.md"
DIGEST_NAME = "TYLER-TODAY.md"

# The digest's item type is the shared task line (fields id/text/section/claim kept).
DigestItem = TaskItem

# Lines per Action Queue section; 15 in all, so the queue stays one screen.
QUEUE_CAPS = {"send_now": 4, "decide": 4, "due": 4, "oldest": 3}
QUEUE_TITLES = {
    "send_now": "Send now",
    "decide": "Decide",
    "due": "Due",
    "oldest": "Oldest",
}


@dataclass(frozen=True)
class ProjectDigest:
    name: str
    errands: tuple[TaskItem, ...] = ()
    decisions: tuple[TaskItem, ...] = ()
    tyler_missing: bool = False
    tasks_missing: bool = False
    # Open production tasks per decision id that names it with ``after:``.
    blocked_by: dict[str, int] = field(default_factory=dict)
    # Whether this project's TASKS.md uses ``after:`` at all; without it a
    # decision's blocked count is unknown rather than zero.
    tracks_blocks: bool = False

    def blocks(self, decision: TaskItem) -> int | None:
        if not decision.id:
            return None
        count = self.blocked_by.get(normalize_id(decision.id), 0)
        return count if (count or self.tracks_blocks) else None


@dataclass(frozen=True)
class Digest:
    drive: str
    projects: tuple[ProjectDigest, ...] = ()

    @property
    def errand_count(self) -> int:
        return sum(len(p.errands) for p in self.projects)

    @property
    def decision_count(self) -> int:
        return sum(len(p.decisions) for p in self.projects)


@dataclass(frozen=True)
class QueueEntry:
    project: str
    item: TaskItem
    kind: str  # "errand" or "decision"
    age: int | None = None
    blocks: int | None = None
    overdue: bool = False


@dataclass(frozen=True)
class QueueSection:
    name: str
    entries: tuple[QueueEntry, ...]
    total: int

    @property
    def title(self) -> str:
        return QUEUE_TITLES[self.name]


@dataclass(frozen=True)
class Queue:
    sections: tuple[QueueSection, ...]

    def _get(self, name: str) -> QueueSection:
        return next(s for s in self.sections if s.name == name)

    @property
    def send_now(self) -> QueueSection:
        return self._get("send_now")

    @property
    def decide(self) -> QueueSection:
        return self._get("decide")

    @property
    def due(self) -> QueueSection:
        return self._get("due")

    @property
    def oldest(self) -> QueueSection:
        return self._get("oldest")


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None


def open_items(text: str, *, lane: str | None = None) -> tuple[TaskItem, ...]:
    """The open checkbox items in a task list's text. Public seam over the
    shared parser, so the archive preview counts open work by exactly the rule
    the Tyler digest rolls it up - one parse, two readers (ticket 32)."""
    return parse_open(text, lane=lane)


def _project(name: str, tyler_text: str | None, tasks_text: str | None) -> ProjectDigest:
    tasks = parse_open(tasks_text) if tasks_text is not None else ()
    blocked_by: dict[str, int] = {}
    for task in tasks:
        for blocker in task.after:
            blocked_by[blocker] = blocked_by.get(blocker, 0) + 1
    return ProjectDigest(
        name=name,
        errands=parse_open(tyler_text) if tyler_text is not None else (),
        # Same rule as before the queue: a `DECISION` tag anywhere on the line.
        decisions=parse_open(tasks_text, lane="DECISION") if tasks_text is not None else (),
        tyler_missing=tyler_text is None,
        tasks_missing=tasks_text is None,
        blocked_by=blocked_by,
        tracks_blocks=any(t.after for t in tasks),
    )


def collect(inventory: DriveInventory) -> Digest:
    # Sorted by name: scan order is the filesystem's, which differs by OS.
    projects = [
        _project(inv.name, _read(inv.path / TYLER_PATH), _read(inv.path / TASKS_PATH))
        for inv in sorted(inventory.projects, key=lambda p: p.name)
    ]
    return Digest(drive=inventory.map.drive, projects=tuple(projects))


def _undated_last(entry: QueueEntry) -> tuple[int, int]:
    # Oldest first; an unknown age sorts after every known one.
    return (1, 0) if entry.age is None else (0, -entry.age)


def _decision_rank(entry: QueueEntry) -> tuple[int, int, int, int]:
    # Known blockers first (most first), then unknown, then known zero; age breaks ties.
    if entry.blocks is None:
        band, count = 1, 0
    elif entry.blocks > 0:
        band, count = 0, -entry.blocks
    else:
        band, count = 2, 0
    return (band, count, *_undated_last(entry))


def _section(name: str, entries: list[QueueEntry]) -> QueueSection:
    return QueueSection(name=name, entries=tuple(entries[: QUEUE_CAPS[name]]), total=len(entries))


def _overdue(item: TaskItem, today: date) -> bool:
    return item.due is not None and item.due < today


def build_queue(digest: Digest, today: date) -> Queue:
    """Rank open work into the four Action Queue sections. Every item belongs to
    exactly one section - the first that claims it, cap or no cap - so totals never
    double count: ready errands are Send now, decisions are Decide, other errands
    with a due date are Due, the rest with a known age are Oldest. Overdue items
    lead Send now and Decide."""
    errands: list[QueueEntry] = []
    decisions: list[QueueEntry] = []
    for project in digest.projects:
        for item in project.errands:
            errands.append(QueueEntry(project.name, item, "errand", age=item.age_days(today),
                                      overdue=_overdue(item, today)))
        for item in project.decisions:
            decisions.append(QueueEntry(project.name, item, "decision",
                                        age=item.age_days(today), blocks=project.blocks(item),
                                        overdue=_overdue(item, today)))

    send_now = sorted((e for e in errands if e.item.ready),
                      key=lambda e: (not e.overdue, *_undated_last(e)))
    decide = sorted(decisions, key=lambda e: (not e.overdue, *_decision_rank(e)))
    rest = [e for e in errands if not e.item.ready]
    due = sorted((e for e in rest if e.item.due is not None), key=lambda e: e.item.due)
    oldest = sorted((e for e in rest if e.item.due is None and e.age is not None),
                    key=_undated_last)
    return Queue(sections=(
        _section("send_now", send_now),
        _section("decide", decide),
        _section("due", due),
        _section("oldest", oldest),
    ))


_DATED_PREFIX = re.compile(r"^\d{6}_")
_NAME_CUT = re.compile(r"(?<=\D)\s*-")
_QUEUE_CLIP = 110


def short_name(project: str) -> str:
    """Scan label for a project: ``260527_211 centre street ny-Montez Radio (MPR)``
    reads ``211 centre street ny``. The full name stays in the detail below."""
    # Cut at the first hyphen after a letter, so a street number like 80-23 survives.
    name = _NAME_CUT.split(_DATED_PREFIX.sub("", project), maxsplit=1)[0].strip() or project
    return name if len(name) <= 24 else name[:23].rstrip() + "…"


def _entry_line(entry: QueueEntry, today: date) -> str:
    text = entry.item.text
    if len(text) > _QUEUE_CLIP:
        text = text[: _QUEUE_CLIP - 1].rstrip() + "…"
    parts = []
    if entry.kind == "decision":
        parts.append(f"blocks {'?' if entry.blocks is None else entry.blocks}")
    if entry.item.due is not None:
        late = (today - entry.item.due).days
        parts.append(f"OVERDUE {late}d" if late > 0 else f"due {entry.item.due.isoformat()}")
    if entry.age is not None:
        parts.append(f"{entry.age}d old")
    meta = f" ({', '.join(parts)})" if parts else ""
    return f"- [ ] **{short_name(entry.project)}**{meta} {text}"


def _render_queue(digest: Digest, today: date) -> list[str]:
    queue = build_queue(digest, today)
    lines = ["", "## Action queue", ""]
    if not any(s.total for s in queue.sections):
        lines.append("Nothing queued.")
    for section in queue.sections:
        if not section.total:
            continue
        lines.append(f"**{section.title}** ({section.total})")
        lines += [_entry_line(e, today) for e in section.entries]
        if section.total > len(section.entries):
            lines.append(f"- … {section.total - len(section.entries)} more below")
        lines.append("")
    dated = sum(1 for p in digest.projects for i in p.errands if i.since is not None)
    loads = sorted(((len(p.errands), p.name) for p in digest.projects if p.errands),
                   key=lambda t: (-t[0], t[1]))
    if loads:
        lines.append("Errands by project: "
                     + ", ".join(f"{short_name(n)} {c}" for c, n in loads) + ".")
    lines.append(
        f"Age known for {dated} of {digest.errand_count} errands - agents add "
        "`added:YYYY-MM-DD` to new items, `due:YYYY-MM-DD` when there is a date, "
        "and `after:T-NNN` on tasks a decision blocks."
    )
    return lines


def render(digest: Digest, *, generated: date | None = None) -> str:
    generated = generated or date.today()
    lines = [
        f"# Tyler today - {generated.isoformat()}",
        "",
        f"Generated by `atlas tyler` from each project's `00 Tasks/TYLER.md` and the "
        f"`DECISION` lane of `00 Tasks/TASKS.md` ({digest.drive}). "
        "Never edit this file - edit the project list and regenerate.",
        "",
        f"**{digest.errand_count} errands / {digest.decision_count} decisions blocking production**",
    ]
    lines += _render_queue(digest, generated)
    for project in digest.projects:
        lines += ["", f"## {project.name}"]
        if project.tyler_missing:
            lines.append("- TYLER.md missing - run conform to backfill it")
        elif not project.errands:
            lines.append("- no open errands")
        else:
            for item in project.errands:
                where = f" _({item.section})_" if item.section not in ("Now", "") else ""
                lines.append(f"- [ ] {item.text}{where}")
        if project.tasks_missing:
            lines.append("- TASKS.md missing")
        elif project.decisions:
            lines.append("")
            lines.append("**Blocked on your call:**")
            for item in project.decisions:
                lines.append(f"- [ ] {item.text}")
    lines.append("")
    return "\n".join(lines)


def item_dict(item: TaskItem) -> dict[str, object]:
    """JSON shape of a task line: dates as ISO strings or null."""
    return {
        "id": item.id, "text": item.text, "section": item.section, "claim": item.claim,
        "lane": item.lane, "ready": item.ready, "after": list(item.after),
        "added": item.added.isoformat() if item.added else None,
        "due": item.due.isoformat() if item.due else None,
        "source_date": item.source_date.isoformat() if item.source_date else None,
    }


def queue_dict(digest: Digest, today: date) -> list[dict[str, object]]:
    return [
        {"name": s.name, "title": s.title, "total": s.total,
         "entries": [
             {"project": e.project, "kind": e.kind, "age_days": e.age,
              "blocks": e.blocks, "overdue": e.overdue, **item_dict(e.item)}
             for e in s.entries
         ]}
        for s in build_queue(digest, today).sections
    ]


def digest_path(root: Path) -> Path:
    return root / "_tools" / DIGEST_NAME
