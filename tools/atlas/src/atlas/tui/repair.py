"""What a repair key means on a node, and what the operation line says about it.

Pure, like ``tui/layout.py``: given a node, this decides whether the repair key
does anything and what to tell the operator when it does not. ``app.py`` applies
the answer and owns none of the rule.

The tree invents no action kinds (ADR 0006). Every repair it offers is a
one-Action slice of the Plan conform already builds, so this module never decides
*what* to do - only whether there is anything to offer and what to say.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from rich.cells import cell_len, set_cell_size

from ..core.conform import (
    BACKFILL,
    CONFLICT,
    DONE,
    MERGE,
    RELOCATE,
    REMOVE,
    RENAME,
    SKIPPED,
    SWEEP,
    WINDOWS_MAX_PATH,
    Action,
    NotInvertible,
    Plan,
    invert_plan,
)
from ..core.tree import CONTRACT, DRIFTED, LOOSE, MISPLACED, UNFILED, Expectation, TreeNode

# The Filing States a repair key acts on. Mapped has nothing wrong with it, and
# Unfiled is the one state Atlas must never act on.
REPAIRABLE = (DRIFTED, MISPLACED, LOOSE)


@dataclass(frozen=True)
class Offer:
    """What pressing the repair key on this node would do.

    An Offer that is not repairable carries a reason, because a key that does
    nothing and says nothing is indistinguishable from a key that is broken.
    """

    target: str
    repairable: bool
    reason: str = ""


def repair_offer(subject: TreeNode | Expectation) -> Offer:
    """Whether this node or Expectation earns a repair, and why not if it does not."""
    if isinstance(subject, Expectation):
        if subject.repairable:
            return Offer(target=subject.path, repairable=True)
        if subject.kind == CONTRACT:
            # Backfill leaves an existing PROJECT.md unchanged, as a conflict:
            # offering it would appear to work and do nothing.
            return Offer(
                target=subject.path,
                repairable=False,
                reason=f"{subject.path} has no front matter - Atlas never rewrites it; add the YAML by hand",
            )
        # ADR 0007's correction to ADR 0006: conform has never created a mapped
        # section. It would report an unknown item and skip it, so the key would
        # appear to work and do nothing.
        return Offer(
            target=subject.path,
            repairable=False,
            reason=f"Atlas does not create {subject.path} - add it with a (add folders)",
        )

    if subject.filing in REPAIRABLE:
        return Offer(target=subject.key, repairable=True)
    if subject.filing == UNFILED:
        return Offer(
            target=subject.key,
            repairable=False,
            reason=f"{subject.name} is not in the map - only you can decide where it belongs",
        )
    return Offer(
        target=subject.key,
        repairable=False,
        reason=f"{subject.name} is filed correctly",
    )


# ------------------------------------------------- confirmation weight

# What each action kind reads as on the operation line. The operator's words,
# not the model's - the same register the Fault Word uses in the tree.
_VERB = {
    BACKFILL: "create",
    RENAME: "rename",
    RELOCATE: "move",
    SWEEP: "file",
}

_KEYS = "Enter confirm  Esc cancel"


def confirms_inline(plan: Plan) -> bool:
    """Whether this Plan is small enough to confirm on the operation line.

    ADR 0006: confirmation weight follows plan size. One action confirms inline;
    anything longer keeps the modal, which is the surface that can actually show
    a list. An empty Plan confirms nothing at all.
    """
    return len(plan.actions) == 1


def confirm_line(plan: Plan, width: int = 0, *, project: str = "",
                 prefix: str = "", effect: str = "") -> str:
    """What the operation line reads while a repair is armed.

    Names the project as well as the path: every project has a ``Meetings``, and
    a confirm that does not say whose is one the operator cannot check (issue
    #2). The project goes last, so a narrow terminal clips it before the path.

    Truncates to ``width`` when one is given, keeping the keys: an operator who
    cannot see what commits the write is worse off than one who cannot see the
    whole path. 46 columns is the most common measured terminal (ticket 03), so
    this is the ordinary case rather than a degraded one.
    """
    action = plan.actions[0]
    verb = _VERB.get(action.kind, action.kind)
    subject = action.src or action.dst
    body = f"{verb} {subject} -> {action.dst}" if action.src else f"{verb} {action.dst}"
    # ``effect`` is core's move_effect: what the move will actually do on disk.
    # A move into an existing folder merges, and a file-empty source is removed
    # outright; the line has to say so rather than promise a rename (#20, #5).
    if effect == MERGE:
        body = f"merge {action.src} -> {action.dst}"
    elif effect == REMOVE:
        body = f"remove empty {action.src} ({action.dst} exists)"
    if action.path_length > WINDOWS_MAX_PATH:
        body += f"  [path {action.path_length} > {WINDOWS_MAX_PATH}]"
    if project:
        body += f"  in {project}"
    if prefix:
        # "undo: ..." - an undo arms exactly like a repair, and has to read as
        # the reversal it is rather than as a fresh repair (#7).
        body = f"{prefix}: {body}"

    line = f"{body}   {_KEYS}"
    # Cells, not characters: a CJK character is one len() and two cells, and the
    # overflow pushed the cancel key onto a hidden second line.
    if width and cell_len(line) > width:
        room = max(0, width - len(_KEYS) - 4)
        body = set_cell_size(body, max(0, room - 1)).rstrip() + "\u2026" if room else ""
        line = f"{body}   {_KEYS}".strip()
    return line


_REMOVED = "removed file-empty source"


def result_line(action: Action, *, undoable: bool = True) -> str:
    """What the operation line reads once a repair has been applied.

    The same verb the armed line used. `sweep` and `relocate` are the model's
    words for these, and the operator was shown `file` and `move` one keystroke
    ago; reporting the result in a different vocabulary reads as a different
    operation. The project root is named rather than printed, because its path is
    the empty string and an arrow pointing at nothing is not a destination.

    It reports what happened, not what was previewed (#20): the status leads, a
    note rides along, a removal says removal, and a write the undo stack could
    not keep says it cannot be undone.
    """
    verb = _VERB.get(action.kind, action.kind)
    if action.note == _REMOVED:
        what = f"removed empty {action.src}"
        note = ""
    else:
        what = (f"{verb} {action.src} -> {action.dst or 'the project root'}"
                if action.src else f"{verb} {action.dst}")
        note = action.note
    lead = {SKIPPED: "Skipped", CONFLICT: "Conflict"}.get(action.status, "Done")
    line = f"{lead}: {what}"
    if note:
        line += f" - {note}"
    if not undoable and action.status == DONE:
        line += " (cannot be undone)"
    return line


def results_line(applied: Plan, where: str, *, undoable: bool = True) -> str:
    """The same, for a Plan of several actions - a merge's undo. Counted by
    status, because naming only the first would report part as all of it."""
    if len(applied.actions) == 1:
        return result_line(applied.actions[0], undoable=undoable)
    counts = {status: sum(1 for a in applied.actions if a.status == status)
              for status in (DONE, SKIPPED, CONFLICT)}
    parts = [f"{counts[DONE]} moved"]
    parts += [f"{n} {status}" for status, n in ((SKIPPED, counts[SKIPPED]),
                                               (CONFLICT, counts[CONFLICT])) if n]
    lead = "Done" if counts[DONE] == len(applied.actions) else "Partly done"
    return f"{lead}: {', '.join(parts)} in {where}"


# ------------------------------------------------------- the undo stack


@dataclass(frozen=True)
class UndoEntry:
    """One undoable write: what applied, what reverses it, and the Guard that
    says whether the folders are still as that write left them."""

    applied: Plan
    inverse: Plan
    guard: object = None
    # The write was a merge that met a name collision. Its undo reverses only
    # what moved, which restores the drive exactly, and the confirm says so.
    partial: bool = False


class UndoStack:
    """One stack of applied Plans per Project, in memory, with no redo.

    ADR 0006. Redo is deliberately absent: undo restores the precondition that
    offered the repair, so re-pressing the repair key *is* redo. A second stack
    would be a second way to do the same thing, and the two would disagree the
    first time somebody edited the drive in between.

    Each entry holds the applied Plan, its inverse, and the undo's Guard - all
    three built at push time, the moment the repair applied (issue #6). The
    Guard has to be: its snapshot is "the folders as the repair left them", and
    one taken when `u` is pressed is taken seconds before it is checked, so it
    could never see what a colleague did in between. The caller peeks, guards,
    applies, and only then drops the entry, so a refused undo can be retried.
    """

    CAP = 50    # ADR 0006 and ticket 04: in memory, capped

    def __init__(self, cap: int = CAP) -> None:
        self.cap = cap
        self._stacks: dict[str, list[UndoEntry]] = {}

    def push(self, project: str, plan: Plan,
             guard_for: Callable[[Plan], object] | None = None) -> bool:
        """Record an applied Plan, if it can be reversed at all.

        Invertibility is checked here rather than at pop. A Plan holding a
        backfill or a file-empty removal has nothing to move back, and finding
        that out at pop time means refusing an undo for a write the operator made
        several steps ago - by which point the stack has been lying about its own
        depth. Returns whether it was kept. ``guard_for`` builds the undo's Guard
        from the inverse, now.
        """
        try:
            inverse = invert_plan(plan)
        except NotInvertible:
            return False
        if inverse.empty:
            return False    # nothing moved, so there is nothing to put back
        guard = guard_for(inverse) if guard_for is not None else None
        partial = any(a.status == CONFLICT for a in plan.actions)
        stack = self._stacks.setdefault(project, [])
        stack.append(UndoEntry(applied=plan, inverse=inverse, guard=guard, partial=partial))
        del stack[:-self.cap]
        return True

    def peek(self, project: str) -> UndoEntry | None:
        """This Project's most recent write, still on the stack."""
        stack = self._stacks.get(project)
        return stack[-1] if stack else None

    def drop(self, project: str, entry: UndoEntry) -> None:
        """Take ``entry`` off the stack once its undo has actually applied."""
        stack = self._stacks.get(project)
        if stack and stack[-1] is entry:
            stack.pop()

    def pop(self, project: str) -> Plan | None:
        """The Plan that reverses this Project's most recent write, or None,
        consumed. The TUI peeks and drops instead; this is the short form."""
        entry = self.peek(project)
        if entry is None:
            return None
        self.drop(project, entry)
        return entry.inverse

    def depth(self, project: str) -> int:
        return len(self._stacks.get(project, ()))

    def forget(self, project: str) -> None:
        """Drop a Project's history - after a project-wide conform, whose
        manifest the per-node stack cannot describe."""
        self._stacks.pop(project, None)
