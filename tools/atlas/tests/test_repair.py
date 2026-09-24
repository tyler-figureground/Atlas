"""What a repair key means on a node, and what the operation line says about it.

Pure, like `tui/layout.py` and for the same reason: the rule is worth testing
without a widget in the way. `app.py` applies what this decides and owns none of
it.

ADR 0006 is the contract - the tree invents no action kinds, and confirmation
weight follows plan size. ADR 0007 carries the correction that bites hardest
here: only control-plane Expectations are repairable.
"""

from __future__ import annotations

from atlas.core.conform import (
    BACKFILL,
    DONE,
    RELOCATE,
    RENAME,
    SWEEP,
    Action,
    Move,
    Plan,
)
from atlas.core.tree import DRIFTED, LOOSE, MAPPED, MISPLACED, UNFILED, Expectation, TreeNode
from atlas.tui.layout import MIN_COLUMNS
from atlas.tui.repair import (
    UndoStack,
    confirm_line,
    confirms_inline,
    repair_offer,
    result_line,
)


def node(name: str, filing: str, *, is_dir: bool = True) -> TreeNode:
    return TreeNode(key=name, name=name, is_dir=is_dir, filing=filing)


def test_a_drifted_node_is_offered_a_repair():
    offer = repair_offer(node("Meetings", DRIFTED))

    assert offer.repairable
    assert offer.target == "Meetings"


def test_a_mapped_node_is_offered_nothing_and_says_why():
    offer = repair_offer(node("01 Model", MAPPED))

    assert not offer.repairable
    assert offer.reason, "an inert key has to say something"


def test_an_unfiled_node_can_never_be_repaired():
    """The one Filing State Atlas must never act on: only a person can decide
    where something the map knows nothing about belongs, or whether it should
    exist at all."""
    offer = repair_offer(node("Random Stuff", UNFILED))

    assert not offer.repairable
    assert "map" in offer.reason.lower()


def test_a_misplaced_and_a_loose_node_are_both_repairable():
    assert repair_offer(node("08 OUT/Invoices", MISPLACED)).repairable
    assert repair_offer(node("HANDOFF.md", LOOSE, is_dir=False)).repairable


def test_only_a_control_plane_expectation_is_repairable():
    """ADR 0007's correction to ADR 0006. Conform has never created a mapped
    section - it would report an unknown item and skip it - so offering a key
    that silently does nothing is worse than offering none."""
    assert repair_offer(Expectation(path="PROJECT.md", kind="control-plane")).repairable

    section = repair_offer(Expectation(path="10 Legal", kind="section"))
    assert not section.repairable
    assert section.reason


# ------------------------------------------------- confirmation weight


def plan_of(*actions: Action) -> Plan:
    return Plan(project="260813_120 Bowery-Loft", actions=actions)


def test_a_one_action_plan_confirms_inline():
    """ADR 0006: confirmation weight follows plan size. A single repair is not
    worth a modal, and a modal on every keystroke is what makes an operator stop
    pressing the key."""
    plan = plan_of(Action(kind=RENAME, src="Meetings", dst="11 Meetings"))

    assert confirms_inline(plan)


def test_a_longer_plan_keeps_the_modal():
    plan = plan_of(
        Action(kind=RENAME, src="Meetings", dst="11 Meetings"),
        Action(kind=SWEEP, src="HANDOFF.md", dst=".agent/handoff"),
    )

    assert not confirms_inline(plan)


def test_an_empty_plan_confirms_nothing():
    assert not confirms_inline(plan_of())


def test_the_confirm_names_the_action_and_the_key_that_commits_it():
    plan = plan_of(Action(kind=RENAME, src="Meetings", dst="11 Meetings"))

    line = confirm_line(plan)

    assert "Meetings" in line and "11 Meetings" in line
    assert "enter" in line.lower(), "the operator has to know what commits it"
    assert "esc" in line.lower(), "and what abandons it"


def test_the_confirm_fits_the_narrowest_terminal_atlas_supports():
    """46 columns is the most common measured width, not the fallback (ticket
    03). A confirm that runs off the end is a confirm nobody read."""
    plan = plan_of(Action(kind=RELOCATE, src="08 OUT/Invoices", dst="10 Legal/Invoices"))

    assert len(confirm_line(plan, width=MIN_COLUMNS)) <= MIN_COLUMNS


def test_a_path_that_would_break_the_limit_says_so_in_the_confirm():
    """ADR 0006: path length warns and obeys. long_path() is never applied on the
    write side, so the warning is the only thing standing between the operator
    and a path Explorer cannot open."""
    plan = plan_of(Action(kind=RELOCATE, src="a", dst="b", path_length=300))

    assert "260" in confirm_line(plan)


# ------------------------------------------------------- the undo stack


def applied(kind: str, src: str, dst: str, *, is_dir: bool = True) -> Action:
    """An Action as it comes back from apply_plan: status filled in, and a Move
    Manifest saying what actually moved."""
    return Action(kind=kind, src=src, dst=dst, status=DONE,
                  moved=(Move(src=src, dst=dst, is_dir=is_dir),))


def test_the_stack_is_per_project():
    """ADR 0006: one stack per Project. Undoing in one project must never reach
    into another - the operator's mental model is 'the last thing I did here'."""
    stack = UndoStack()
    stack.push("A", plan_of(applied(RENAME, "Meetings", "11 Meetings")))

    assert stack.depth("A") == 1
    assert stack.depth("B") == 0
    assert stack.pop("B") is None


def test_undo_pops_the_last_write_first_and_pops_it_reversed():
    """pop returns the Plan that *reverses* the write, ready for apply_plan - so
    its src is where the folder is now and its dst is where it came from. The
    caller never inverts anything itself; there is one inversion and it is
    invert_plan's."""
    stack = UndoStack()
    stack.push("A", plan_of(applied(RENAME, "Meetings", "11 Meetings")))
    stack.push("A", plan_of(applied(RELOCATE, "08 OUT/Invoices", "10 Legal/Invoices")))

    first = stack.pop("A").actions[0]
    assert (first.src, first.dst) == ("10 Legal/Invoices", "08 OUT/Invoices")

    second = stack.pop("A").actions[0]
    assert (second.src, second.dst) == ("11 Meetings", "Meetings")

    assert stack.pop("A") is None


def test_there_is_no_redo():
    """ADR 0006 rules redo out on purpose: undo restores the precondition that
    offered the repair, so re-pressing the repair key *is* redo. A separate redo
    stack would be a second way to do the same thing, and they would disagree."""
    stack = UndoStack()
    stack.push("A", plan_of(applied(RENAME, "Meetings", "11 Meetings")))
    stack.pop("A")

    assert stack.depth("A") == 0
    assert not hasattr(stack, "redo")


def test_a_plan_that_cannot_be_reversed_is_refused_at_push_not_at_pop():
    """A backfill creates and has nothing to move back. Discovering that at pop
    time means the operator pressed undo and got a refusal for a write they made
    three steps ago; discovering it at push means the stack never claims a depth
    it cannot honour."""
    stack = UndoStack()

    stack.push("A", plan_of(Action(kind=BACKFILL, src="", dst="PROJECT.md", status=DONE)))

    assert stack.depth("A") == 0


def test_the_stack_is_capped():
    """ADR 0006 and ticket 04: in memory, capped at 50. The oldest goes first."""
    stack = UndoStack()
    for n in range(51):
        stack.push("A", plan_of(applied(RENAME, f"old{n}", f"new{n}")))

    assert stack.depth("A") == 50
    assert stack.peek("A").inverse.actions[0].src == "new50"


def test_peeking_does_not_consume_the_entry():
    """Issue #6. The entry was popped before the guard ran, so a refused undo
    lost it. The caller peeks, guards, applies, and only then drops."""
    stack = UndoStack()
    stack.push("A", plan_of(applied(RENAME, "Meetings", "11 Meetings")))

    entry = stack.peek("A")
    assert stack.depth("A") == 1
    stack.drop("A", entry)
    assert stack.depth("A") == 0


def test_push_snapshots_the_guard_for_the_undo_at_push_time():
    seen = []
    stack = UndoStack()
    stack.push("A", plan_of(applied(RENAME, "Meetings", "11 Meetings")),
               guard_for=lambda inverse: seen.append(inverse) or "guard")

    assert len(seen) == 1, "built once, when the repair applied"
    assert stack.peek("A").guard == "guard"


# ------------------------------------------------------- what an apply reports


def test_a_finished_repair_reports_in_the_operator_s_words():
    """Same register as the armed line. `sweep` is the model's word for it;
    the operator was shown `file` a keystroke ago."""
    action = Action(kind=SWEEP, src="A-101.pdf", dst="08 OUT/Transmittals", status=DONE)

    assert result_line(action) == "Done: file A-101.pdf -> 08 OUT/Transmittals"


def test_a_repair_that_lands_at_the_project_root_names_the_root():
    """Undoing a sweep files the file back to the root, whose path is the empty
    string. Printed raw it left the line ending in an arrow pointing nowhere."""
    action = Action(kind=SWEEP, src="08 OUT/Transmittals/A-101.pdf", dst="", status=DONE)

    assert result_line(action) == "Done: file 08 OUT/Transmittals/A-101.pdf -> the project root"


def test_a_backfill_reports_what_it_created():
    action = Action(kind=BACKFILL, src="", dst="decisions", status=DONE)

    assert result_line(action) == "Done: create decisions"
