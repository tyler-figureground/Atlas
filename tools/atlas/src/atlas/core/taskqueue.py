"""The cross-project production queue (roadmap F5): every open task in every
project's ``00 Tasks/TASKS.md``, and which ones an agent may pick up.

Each project's ``TASKS.md`` already says how work is picked (the template's
"Picking up work" rule): the top unblocked ``AGENT`` or ``MODEL`` item from
**Now**, then **Next**; never a ``DECISION`` or ``WAIT`` item; claim it before
starting; a claim stale more than 7 days with no run receipt may be reclaimed.
This module applies that rule across projects so a scheduled run (nightshift,
``claude --bg``) can ask for the next task without opening every project.

States, one per task:

- ``pickable`` - in Now or Next, unclaimed, every ``after:`` blocker closed.
- ``blocked`` - an ``after:`` blocker is still open in the same file.
- ``claimed`` - carries ``claimed YYYY-MM-DD by <name>``.
- ``stale-claim`` - claimed more than 7 days ago and no run folder in the
  project's runs dir dated on or after the claim. Reported, never released:
  releasing is an edit to the project's file and goes through ``/tasks``.
- ``decision`` / ``waiting`` - the lane is Tyler's or someone outside's.
- ``parked`` - open but outside Now and Next (Holds, Waiting on others...).

``MODEL`` work needs a live Revit seat: ``next_task`` offers it only in a
project whose ``PROJECT.md`` ``revit:`` block names a model.

Read-only. A project whose ``TASKS.md`` is missing or unreadable is named,
never counted as having no work (ADR 0004).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .scan import DriveInventory, long_path
from .tasks import TaskItem, normalize_id, parse_open

TASKS_PATH = "00 Tasks/TASKS.md"
# The template's own reclaim rule ("A claim stale more than 7 days with no run
# receipt may be reclaimed"). Claims carry a date, not a time.
STALE_CLAIM_DAYS = 7
PICK_SECTIONS = ("now", "next")

PICKABLE = "pickable"
BLOCKED = "blocked"
CLAIMED = "claimed"
STALE = "stale-claim"
DECISION = "decision"
WAITING = "waiting"
PARKED = "parked"
STATES = (PICKABLE, BLOCKED, CLAIMED, STALE, DECISION, WAITING, PARKED)

_RUN_DATE = re.compile(r"^(\d{2})(\d{2})(\d{2})(?!\d)")
_FRONT = re.compile(r"^---\s*$")


@dataclass(frozen=True)
class QueuedTask:
    project: str
    item: TaskItem
    state: str
    blockers: tuple[str, ...] = ()     # open after: ids
    order: int = 0                     # line order in the file

    def claim_age(self, today: date) -> int | None:
        when = self.item.claimed_on
        return (today - when).days if when and when <= today else None


@dataclass(frozen=True)
class ProjectQueue:
    project: str
    path: Path
    tasks: tuple[QueuedTask, ...] = ()
    tasks_present: bool = True
    tasks_readable: bool = True
    revit_ready: bool = False
    newest_run: date | None = None
    error: str = ""


def _read(path: Path) -> tuple[str | None, str]:
    try:
        return Path(long_path(path)).read_text(encoding="utf-8-sig"), ""
    except FileNotFoundError:
        return None, ""
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"{type(exc).__name__}: {getattr(exc, 'strerror', None) or exc}"


def newest_run_date(folder: Path, *, zips: bool = False) -> tuple[date | None, bool]:
    """The latest ``YYMMDD``-named run in ``folder`` - run folders, or with
    ``zips`` the closed runs ``atlas runs`` archived as ``YYMMDD-slug.zip``.
    Undated names (legacy-*) do not count. Returns (date, known): a folder
    that is not there is known-empty; one that cannot be read is unknown."""
    best: date | None = None
    try:
        with os.scandir(long_path(folder)) as it:
            for entry in it:
                match = _RUN_DATE.match(entry.name)
                if not match:
                    continue
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                    wanted = (not is_dir and entry.name.lower().endswith(".zip")) if zips \
                        else is_dir
                    if not wanted:
                        continue
                    when = date(2000 + int(match.group(1)), int(match.group(2)),
                                int(match.group(3)))
                except (OSError, ValueError):
                    continue
                best = when if best is None or when > best else best
    except FileNotFoundError:
        return None, True
    except OSError:
        return None, False
    return best, True


def revit_ready(project_md: str | None) -> bool:
    """Whether the dossier's front matter ``revit:`` block names a model
    (``  model: <something>``). No YAML parser: the block is Atlas's own
    six-key shape (projectmd.REVIT_BLOCK)."""
    if not project_md:
        return False
    lines = project_md.splitlines()
    if not lines or not _FRONT.match(lines[0]):
        return False
    in_revit = False
    for line in lines[1:]:
        if _FRONT.match(line):
            break
        if not line.strip():
            continue          # a blank line does not end the block
        if not line.startswith((" ", "\t")):
            in_revit = line.split("#", 1)[0].strip() == "revit:"
            continue
        # Only the block's own keys: two-space indent, nothing deeper.
        if in_revit and line.startswith("  ") and not line.startswith("   "):
            key, _, value = line.strip().partition(":")
            value = value.split("#", 1)[0].strip().strip("'\"")
            if (key == "model" and value and value.lower() not in ("null", "~")
                    and value[0] not in "|>"):
                return True
    return False


def classify(items: tuple[TaskItem, ...], today: date, newest_run: date | None,
             runs_known: bool = True) -> list[tuple[TaskItem, str, tuple[str, ...]]]:
    """Each open item's state. Pure. With ``runs_known`` False (the runs
    folder could not be read) no claim is called stale: no receipt seen is not
    no receipt."""
    open_ids = {normalize_id(i.id) for i in items if i.id}
    out = []
    for item in items:
        blockers = tuple(b for b in item.after if b in open_ids
                         and b != normalize_id(item.id or ""))
        if item.lane == "DECISION":
            state = DECISION
        elif item.lane == "WAIT":
            state = WAITING
        elif item.claim:
            when = item.claimed_on
            stale = (runs_known and when is not None
                     and (today - when).days > STALE_CLAIM_DAYS
                     and (newest_run is None or newest_run < when))
            state = STALE if stale else CLAIMED
        elif blockers:
            state = BLOCKED
        elif item.section.strip().lower() in PICK_SECTIONS:
            state = PICKABLE
        else:
            state = PARKED
        out.append((item, state, blockers))
    return out


def project_queue(name: str, path: Path, runs_dir: str, project_file: str,
                  today: date, archive_dir: str = "") -> ProjectQueue:
    text, error = _read(path / TASKS_PATH)
    newest, runs_known = (newest_run_date(path / runs_dir) if runs_dir else (None, True))
    if archive_dir:
        # A closed run zipped by `atlas runs` is still a receipt.
        archived, archive_known = newest_run_date(path / archive_dir, zips=True)
        runs_known = runs_known and archive_known
        if archived and (newest is None or archived > newest):
            newest = archived
    dossier, _ = _read(path / project_file)
    if text is None:
        # No error means the file is not there; an error means it is there and
        # could not be read - unknown work, never no work.
        return ProjectQueue(project=name, path=path, tasks_present=bool(error),
                            tasks_readable=not error, error=error,
                            revit_ready=revit_ready(dossier), newest_run=newest)
    tasks = tuple(
        QueuedTask(project=name, item=item, state=state, blockers=blockers, order=n)
        for n, (item, state, blockers) in enumerate(
            classify(parse_open(text), today, newest, runs_known)))
    return ProjectQueue(project=name, path=path, tasks=tasks,
                        revit_ready=revit_ready(dossier), newest_run=newest)


def collect(inventory: DriveInventory, today: date | None = None) -> tuple[ProjectQueue, ...]:
    today = today or date.today()
    m = inventory.map
    return tuple(
        project_queue(p.name, p.path, m.runs_dir, m.project_file, today, m.archive_dir)
        for p in sorted(inventory.projects, key=lambda p: p.name)
    )


def _rank(task: QueuedTask, today: date) -> tuple:
    item = task.item
    section = 0 if item.section.strip().lower() == "now" else 1
    due = item.due.toordinal() if item.due else date.max.toordinal()
    age = item.age_days(today)
    return (section, due, 0 if item.prompt else 1,
            -(age if age is not None else -1), task.project, task.order)


def next_task(queues: tuple[ProjectQueue, ...], lane: str, today: date | None = None,
              *, with_prompt: bool = False) -> QueuedTask | None:
    """The top pickable task in ``lane`` across projects: Now before Next, then
    soonest due, then one with a prompt, then oldest, then project and line
    order. ``MODEL`` only where the dossier names a Revit model."""
    today = today or date.today()
    candidates = [
        t for q in queues for t in q.tasks
        if t.state == PICKABLE and t.item.lane == lane
        and (lane != "MODEL" or q.revit_ready)
        and (t.item.prompt or not with_prompt)
    ]
    return min(candidates, key=lambda t: _rank(t, today)) if candidates else None


def task_dict(task: QueuedTask, today: date, path: Path | None = None) -> dict[str, object]:
    item = task.item
    out: dict[str, object] = {
        "project": task.project,
        "id": item.id, "lane": item.lane, "section": item.section, "state": task.state,
        "text": item.text, "prompt": item.prompt,
        "blockers": list(task.blockers),
        "claim": item.claim or None,
        "claim_age_days": task.claim_age(today),
        "added": item.added.isoformat() if item.added else None,
        "due": item.due.isoformat() if item.due else None,
        "age_days": item.age_days(today),
    }
    if path is not None:
        out["tasks_file"] = str(path / TASKS_PATH)
    return out
