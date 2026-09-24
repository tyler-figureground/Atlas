"""What a repair key means on a node, and what the operation line says about it.

Pure, like ``tui/layout.py``: given a node, this decides whether the repair key
does anything and what to tell the operator when it does not. ``app.py`` applies
the answer and owns none of the rule.

The tree invents no action kinds (ADR 0006). Every repair it offers is a
one-Action slice of the Plan conform already builds, so this module never decides
*what* to do - only whether there is anything to offer and what to say.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.cells import cell_len, set_cell_size

from ..core.conform import (
    BACKFILL,
    RELOCATE,
    RENAME,
    SWEEP,
    WINDOWS_MAX_PATH,
    NotInvertible,
    Plan,
    invert_plan,
)
from ..core.tree import DRIFTED, LOOSE, MISPLACED, UNFILED, Expectation, TreeNode

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


def confirm_line(plan: Plan, width: int = 0) -> str:
    """What the operation line reads while a repair is armed.

    Truncates to ``width`` when one is given, keeping the keys: an operator who
    cannot see what commits the write is worse off than one who cannot see the
    whole path. 46 columns is the most common measured terminal (ticket 03), so
    this is the ordinary case rather than a degraded one.
    """
    action = plan.actions[0]
    verb = _VERB.get(action.kind, action.kind)
    subject = action.src or action.dst
    body = f"{verb} {subject} -> {action.dst}" if action.src else f"{verb} {action.dst}"
    if action.path_length > WINDOWS_MAX_PATH:
        body += f"  [path {action.path_length} > {WINDOWS_MAX_PATH}]"

    line = f"{body}   {_KEYS}"
    # Cells, not characters: a CJK character is one len() and two cells, and the
    # overflow pushed the cancel key onto a hidden second line.
    if width and cell_len(line) > width:
        room = max(0, width - len(_KEYS) - 4)
        body = set_cell_size(body, max(0, room - 1)).rstrip() + "\u2026" if room else ""
        line = f"{body}   {_KEYS}".strip()
    return line


def result_line(action: Action) -> str:
    """What the operation line reads once a repair has been applied.

    The same verb the armed line used. `sweep` and `relocate` are the model's
    words for these, and the operator was shown `file` and `move` one keystroke
    ago; reporting the result in a different vocabulary reads as a different
    operation. The project root is named rather than printed, because its path is
    the empty string and an arrow pointing at nothing is not a destination.
    """
    verb = _VERB.get(action.kind, action.kind)
    if not action.src:
        return f"Done: {verb} {action.dst}"
    return f"Done: {verb} {action.src} -> {action.dst or 'the project root'}"


# ------------------------------------------------------- the undo stack


class UndoStack:
    """One stack of applied Plans per Project, in memory, with no redo.

    ADR 0006. Redo is deliberately absent: undo restores the precondition that
    offered the repair, so re-pressing the repair key *is* redo. A second stack
    would be a second way to do the same thing, and the two would disagree the
    first time somebody edited the drive in between.

    The stack holds *applied* Plans - the ones carrying Move Manifests - and
    inverts them at pop time through ``invert_plan``. It does not hold inverses,
    because an inverse built at push time would be built against a drive that has
    not been re-read, and the scoped Guard is what re-reads it.
    """

    def __init__(self) -> None:
        self._stacks: dict[str, list[Plan]] = {}

    def push(self, project: str, plan: Plan) -> bool:
        """Record an applied Plan, if it can be reversed at all.

        Invertibility is checked here rather than at pop. A Plan holding a
        backfill or a file-empty removal has nothing to move back, and finding
        that out at pop time means refusing an undo for a write the operator made
        several steps ago - by which point the stack has been lying about its own
        depth. Returns whether it was kept.
        """
        try:
            invert_plan(plan)
        except NotInvertible:
            return False
        self._stacks.setdefault(project, []).append(plan)
        return True

    def pop(self, project: str) -> Plan | None:
        """The Plan that reverses this Project's most recent write, or None.

        Returns the *inverse*, ready for ``apply_plan``. The caller still has to
        guard it: the same scoped Guard that protects a repair protects its undo,
        which is what lets this stack be optimistic rather than eagerly
        invalidated on every external change.
        """
        stack = self._stacks.get(project)
        if not stack:
            return None
        return invert_plan(stack.pop())

    def depth(self, project: str) -> int:
        return len(self._stacks.get(project, ()))

    def forget(self, project: str) -> None:
        """Drop a Project's history - after a project-wide conform, whose
        manifest the per-node stack cannot describe."""
        self._stacks.pop(project, None)
