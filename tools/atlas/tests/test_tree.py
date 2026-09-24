"""The ProjectTree seam (tickets 07 and 15, ADR 0007).

Core owns filesystem facts; the TUI owns interaction. These tests cross the
seam from the core side only - no Textual, fixture drives, one scandir per
displayed node.
"""

from __future__ import annotations

import os

from atlas.core.conform import apply_plan, build_repair_plan
from atlas.core.doctor import report_project
from atlas.core.scan import READ, UNREAD, UNREADABLE, scan_drive
from atlas.core.tree import (
    CONTROL_PLANE,
    DRIFTED,
    LOOSE,
    MAPPED,
    MISPLACED,
    SECTION,
    UNFILED,
    open_project_tree,
)

from conftest import make_project


def tree_for(drive, name, **kwargs):
    inventory = scan_drive(drive)
    m = inventory.map
    inv = next(p for p in inventory.projects if p.name == name)
    return open_project_tree(inv, m, report_project(inv, m), **kwargs)


# ------------------------------------------------------------ the mirror


def test_the_root_holds_exactly_what_is_on_disk(fixture_drive):
    """A filesystem mirror. What the map expects and disk lacks is an unmet
    Expectation, not a node (ADR 0004)."""
    make_project(
        fixture_drive, "260401_Mirror",
        sections=["01 Model", "11 Meetings"],
        files={"CLAUDE.md": "x", "note.txt": "y"},
    )
    tree = tree_for(fixture_drive, "260401_Mirror")

    assert [(n.key, n.name, n.is_dir) for n in tree.children()] == [
        ("01 Model", "01 Model", True),
        ("11 Meetings", "11 Meetings", True),
        ("CLAUDE.md", "CLAUDE.md", False),
        ("note.txt", "note.txt", False),
    ]


# ------------------------------------------------------------ Filing State


def test_filing_state_at_the_root_comes_from_the_report(fixture_drive):
    """One brain. doctor already decided what is Drifted, Misplaced, Loose and
    Unfiled for this project; the tree reads that verdict rather than deriving
    it a second way (ADR 0006's rule, applied to reads)."""
    make_project(
        fixture_drive, "260402_States",
        sections=["01 Model", "Meetings", "Scratch"],
        files={"Meetings/kickoff.md": "z", "HANDOFF-roof-01.md": "h",
               "Scratch/idea.md": "i"},
    )
    tree = tree_for(fixture_drive, "260402_States")

    assert {n.name: n.filing for n in tree.children()} == {
        "01 Model": MAPPED,
        "Meetings": DRIFTED,
        "Scratch": UNFILED,
        "HANDOFF-roof-01.md": LOOSE,
    }


def test_filing_state_below_the_root_is_decided_by_containment(fixture_drive):
    """doctor judges the project root; the map's reach below it is containment.
    A node under a canonical path is accounted for. A node under one nobody can
    explain is not, and saying otherwise would hide it."""
    make_project(
        fixture_drive, "260403_Deep",
        sections=["01 Model/01 Site Model", "08 OUT/Invoices", "10 Legal", "Scratch/sub"],
        files={"08 OUT/Invoices/inv.pdf": "y", "Scratch/sub/idea.md": "i",
               "01 Model/01 Site Model/site.rvt": "r"},
    )
    tree = tree_for(fixture_drive, "260403_Deep")

    # A path the map names explicitly keeps its own verdict, at any depth.
    assert tree.filing_state("08 OUT/Invoices") == MISPLACED
    # Under a canonical section: accounted for.
    assert tree.filing_state("01 Model/01 Site Model") == MAPPED
    assert tree.filing_state("01 Model/01 Site Model/site.rvt") == MAPPED
    # Under a folder nobody can explain: still nobody can explain it.
    assert tree.filing_state("Scratch") == UNFILED
    assert tree.filing_state("Scratch/sub") == UNFILED
    assert tree.filing_state("Scratch/sub/idea.md") == UNFILED


# -------------------------------------------------------------- Load State


def test_a_folder_is_unread_until_atlas_opens_it(fixture_drive):
    """Lazy: the parent's scandir gives a name and a type, never a count. The
    count is the length of an enumeration Atlas already holds, so it exists only
    once the folder has been read (ticket 13)."""
    make_project(
        fixture_drive, "260404_Lazy",
        sections=["01 Model/01 Site Model"],
        files={"01 Model/a.rvt": "x", "01 Model/b.rvt": "y"},
    )
    tree = tree_for(fixture_drive, "260404_Lazy")

    model = next(n for n in tree.children() if n.name == "01 Model")
    assert model.load == UNREAD
    assert (model.folders, model.files) == (0, 0)

    tree.children("01 Model")

    model = next(n for n in tree.children() if n.name == "01 Model")
    assert model.load == READ
    assert (model.folders, model.files) == (1, 2)


def test_a_file_has_no_load_state(fixture_drive):
    """Load State is what Atlas knows about a folder's children (ADR 0004). A
    file has none, and giving it one would invite a count on a thing with none."""
    make_project(fixture_drive, "260405_File", sections=["01 Model"],
                 files={"CLAUDE.md": "x"})
    tree = tree_for(fixture_drive, "260405_File")

    claude = next(n for n in tree.children() if n.name == "CLAUDE.md")
    assert claude.load == ""


def test_a_folder_atlas_cannot_open_is_never_shown_as_empty(fixture_drive, monkeypatch):
    """Two folders return zero entries; only one of them is actually empty. The
    tree carries the difference rather than flattening it (ADR 0004)."""
    project = make_project(
        fixture_drive, "260406_Denied",
        sections=["01 Model", "10 Legal"],
    )
    tree = tree_for(fixture_drive, "260406_Denied")

    real = os.scandir

    def deny(path, *a, **kw):
        if os.fspath(path) == os.fspath(project / "10 Legal"):
            raise PermissionError(13, "denied")
        return real(path, *a, **kw)

    monkeypatch.setattr(os, "scandir", deny)

    assert tree.children("10 Legal") == ()
    assert tree.load_state("10 Legal") == UNREADABLE
    assert tree.children("01 Model") == ()
    assert tree.load_state("01 Model") == READ

    denied = next(n for n in tree.children() if n.name == "10 Legal")
    empty = next(n for n in tree.children() if n.name == "01 Model")
    assert denied.load == UNREADABLE and empty.load == READ


# ------------------------------------------------------------ the cache


def count_scandirs(monkeypatch) -> list[int]:
    calls = [0]
    real = os.scandir

    def counted(path, *a, **kw):
        calls[0] += 1
        return real(path, *a, **kw)

    monkeypatch.setattr(os, "scandir", counted)
    return calls


def test_a_folder_is_never_read_twice_inside_the_ttl(fixture_drive, monkeypatch):
    """Ticket 06's rule: one scandir per displayed node, never re-touching an
    entry. Re-asking for the same children is free."""
    make_project(fixture_drive, "260407_Cache", sections=["01 Model/01 Site Model"])
    tree = tree_for(fixture_drive, "260407_Cache")
    calls = count_scandirs(monkeypatch)

    tree.children()
    tree.children()
    tree.children("01 Model")
    tree.children("01 Model")

    assert calls[0] == 2


def test_a_stale_folder_is_read_again(fixture_drive, monkeypatch):
    """No filesystem watching over a redirector (ticket 06), so a listing has a
    shelf life. Someone else's change reaches the tree when the TTL expires or
    the operator asks for a refresh, and never any sooner."""
    make_project(fixture_drive, "260408_Ttl", sections=["01 Model"])
    now = [1000.0]
    tree = tree_for(fixture_drive, "260408_Ttl", ttl=60.0, clock=lambda: now[0])
    calls = count_scandirs(monkeypatch)

    tree.children()
    assert calls[0] == 1

    now[0] += 59.0
    tree.children()
    assert calls[0] == 1, "still inside the shelf life"

    now[0] += 2.0
    tree.children()
    assert calls[0] == 2, "past it, so read again"


# --------------------------------------------------------- unmet Expectations


def test_unmet_expectations_sit_beside_the_tree_and_never_inside_it(fixture_drive):
    """The tree is a filesystem mirror. A folder the map wants and disk lacks is
    an Expectation, listed in the Companion, never drawn as a node (ADR 0004)."""
    make_project(fixture_drive, "260409_Missing",
                 sections=["01 Model/01 Site Model", "06 Research"],
                 files={"PROJECT.md": "---\nx: 1\n---\n"})
    tree = tree_for(fixture_drive, "260409_Missing")

    unmet = {e.path for e in tree.expectations()}
    assert "08 OUT" in unmet, "a whole section the project does not have"
    assert "01 Model/02 Design" in unmet, "a child of a section that does exist"
    assert "CLAUDE.md" in unmet, "control plane"
    assert "01 Model" not in unmet and "01 Model/01 Site Model" not in unmet
    assert "PROJECT.md" not in unmet, "present, and carrying the machine contract"

    on_disk = {n.key for n in tree.children()}
    assert not (unmet & on_disk)


def test_only_control_plane_expectations_offer_a_repair(fixture_drive):
    """ADR 0006 maps an unmet Expectation to BACKFILL. That holds for the control
    plane, which conform creates. It does not hold for a mapped section: conform
    has never created those, and claiming a repair Atlas will silently skip is
    worse than offering none."""
    make_project(fixture_drive, "260410_Kinds", sections=["01 Model"])
    tree = tree_for(fixture_drive, "260410_Kinds")

    by_path = {e.path: e for e in tree.expectations()}
    assert by_path["CLAUDE.md"].kind == CONTROL_PLANE
    assert by_path["CLAUDE.md"].repairable
    assert by_path["08 OUT"].kind == SECTION
    assert not by_path["08 OUT"].repairable


# ------------------------------------------------ after Atlas writes (ticket 15)


def applied_repair(drive, name, node):
    """Apply one node's Repair and hand back the applied Plan."""
    inventory = scan_drive(drive)
    m = inventory.map
    inv = next(p for p in inventory.projects if p.name == name)
    plan = build_repair_plan(report_project(inv, m), m, node, project=inv.path)
    return apply_plan(drive, inv.path, m, plan)


def test_reconcile_invalidates_exactly_the_folders_the_move_touched(fixture_drive):
    """Textual cannot re-parent a node, so something has to be rebuilt. The Move
    Manifest names which folders changed - the same two the scoped Guard watched -
    so the rebuild costs two enumerations rather than a walk of the subtree."""
    make_project(
        fixture_drive, "260411_Moved",
        sections=["01 Model", "08 OUT/Invoices", "10 Legal"],
        files={"08 OUT/Invoices/inv.pdf": "y"},
    )
    tree = tree_for(fixture_drive, "260411_Moved")
    tree.children()
    tree.children("08 OUT")
    tree.children("10 Legal")

    applied = applied_repair(fixture_drive, "260411_Moved", "08 OUT/Invoices")
    assert all(a.status == "done" for a in applied.actions), applied.actions

    assert tree.reconcile(applied) == ("08 OUT", "10 Legal")
    assert tree.load_state("08 OUT") == UNREAD
    assert tree.load_state("10 Legal") == UNREAD
    assert tree.load_state("") == READ, "the project root did not change"


def test_reconcile_forgets_the_folder_a_merge_consumed(fixture_drive):
    """Found by rendering ticket 23, not by the suite.

    A merge moves children one at a time, so every Move in the manifest names a
    child - and the parents of those children are the two merged folders, never
    the folder that lost `Meetings` from its own listing. That folder is the
    project root, its cached listing still held a `Meetings` entry, and the tree
    drew a row for a folder that no longer exists - as Mapped, because the fresh
    report has no complaint about a name that is gone.

    `follow` already knew this and says so in its own comment: nothing in the
    manifest names the merged folder itself, the Action does. `reconcile` did
    not, and a node that is not on disk is exactly what ADR 0004 rules out.
    """
    project = make_project(
        fixture_drive, "260415_Merged",
        sections=["01 Model", "Meetings/Agendas", "11 Meetings"],
        files={"Meetings/kickoff.md": "z"},
    )
    tree = tree_for(fixture_drive, "260415_Merged")
    assert "Meetings" in {node.name for node in tree.children()}

    applied = applied_repair(fixture_drive, "260415_Merged", "Meetings")
    assert all(a.status == "done" for a in applied.actions), applied.actions
    assert not (project / "Meetings").exists(), "the merge consumed the source"

    touched = tree.reconcile(applied)

    assert "" in touched, f"the root lost a child and must be re-read: {touched}"
    assert "Meetings" not in {node.name for node in tree.children()}


def test_the_cursor_follows_what_it_just_repaired(fixture_drive):
    """A rebuild restores the cursor by line number, so the seam has to say where
    the node went. Otherwise pressing the repair key moves the selection to
    whatever happens to occupy that line afterwards (ticket 05)."""
    make_project(
        fixture_drive, "260412_Follow",
        sections=["01 Model", "Meetings/Agendas"],
        files={"Meetings/kickoff.md": "z", "Meetings/Agendas/a.md": "a"},
    )
    tree = tree_for(fixture_drive, "260412_Follow")
    applied = applied_repair(fixture_drive, "260412_Follow", "Meetings")

    assert tree.follow("Meetings", applied) == "11 Meetings"
    assert tree.follow("Meetings/kickoff.md", applied) == "11 Meetings/kickoff.md"
    assert tree.follow("01 Model", applied) == "01 Model", "untouched, so it stays"


def test_a_merged_folder_still_tells_the_cursor_where_to_go(fixture_drive):
    """A merge moves children one at a time and the source folder disappears.
    Nothing in the manifest names the folder itself, so the Action does."""
    make_project(
        fixture_drive, "260413_FollowMerge",
        sections=["01 Model", "Meetings/Agendas", "11 Meetings"],
        files={"Meetings/kickoff.md": "z", "Meetings/Agendas/a.md": "a",
               "11 Meetings/native.md": "n"},
    )
    tree = tree_for(fixture_drive, "260413_FollowMerge")
    applied = applied_repair(fixture_drive, "260413_FollowMerge", "Meetings")
    assert all(a.status == "done" for a in applied.actions), applied.actions

    assert tree.follow("Meetings", applied) == "11 Meetings"
    assert tree.follow("Meetings/Agendas", applied) == "11 Meetings/Agendas"
    assert tree.follow("Meetings/Agendas/a.md", applied) == "11 Meetings/Agendas/a.md"


def test_reconcile_takes_the_fresh_verdict_with_it(fixture_drive):
    """A repair changes what the map says about what is left. A tree still
    serving the pre-write report would keep offering a repair already done."""
    make_project(
        fixture_drive, "260414_Verdict", sections=["01 Model", "Meetings"],
        files={"Meetings/kickoff.md": "z"},
    )
    tree = tree_for(fixture_drive, "260414_Verdict")
    assert tree.filing_state("Meetings") == DRIFTED

    applied = applied_repair(fixture_drive, "260414_Verdict", "Meetings")
    inventory = scan_drive(fixture_drive)
    inv = next(p for p in inventory.projects if p.name == "260414_Verdict")
    tree.reconcile(applied, report_project(inv, inventory.map))

    assert tree.filing_state("Meetings") == MAPPED, "nothing drifted is left"
    assert tree.filing_state("11 Meetings") == MAPPED
    assert [n.name for n in tree.children()] == ["01 Model", "11 Meetings"]


def test_a_backfilled_file_shows_up_in_the_tree_at_once(fixture_drive):
    """Issue #22. A backfill has an empty manifest, so reconcile touched nothing
    and the created file sat in neither the tree nor the unmet list for 60 s."""
    make_project(fixture_drive, "260416_Backfill", sections=["01 Model"])
    tree = tree_for(fixture_drive, "260416_Backfill")
    assert "CLAUDE.md" not in {n.name for n in tree.children()}

    applied = applied_repair(fixture_drive, "260416_Backfill", "CLAUDE.md")
    assert [a.status for a in applied.actions] == ["done"], applied.actions

    tree.reconcile(applied)
    assert "CLAUDE.md" in {n.name for n in tree.children()}


def test_a_folder_a_move_had_to_create_shows_up_in_the_tree(fixture_drive):
    """Relocating into a parent that does not exist creates it. Nothing in the
    Move Manifest names that parent's parent, so the root stayed cached."""
    make_project(
        fixture_drive, "260417_Created",
        sections=["01 Model", "08 OUT/Invoices"],
        files={"08 OUT/Invoices/inv.pdf": "y"},
    )
    tree = tree_for(fixture_drive, "260417_Created")
    assert "10 Legal" not in {n.name for n in tree.children()}

    applied = applied_repair(fixture_drive, "260417_Created", "08 OUT/Invoices")
    (action,) = applied.actions
    assert action.created == ("10 Legal",), action

    tree.reconcile(applied)
    assert "10 Legal" in {n.name for n in tree.children()}


def test_a_removed_duplicate_leaves_the_tree(fixture_drive):
    make_project(
        fixture_drive, "260418_Removed",
        sections=["01 Model", "08 OUT/Invoices", "10 Legal/Invoices"],
    )
    tree = tree_for(fixture_drive, "260418_Removed")
    assert "Invoices" in {n.name for n in tree.children("08 OUT")}

    applied = applied_repair(fixture_drive, "260418_Removed", "08 OUT/Invoices")
    assert "file-empty" in applied.actions[0].note

    tree.reconcile(applied)
    assert "Invoices" not in {n.name for n in tree.children("08 OUT")}


def test_undo_removes_the_folder_the_move_created(fixture_drive):
    """Undoing a relocate into a created parent left that parent behind, empty -
    a state that existed neither before the repair nor after it."""
    from atlas.core.conform import invert_plan

    project = make_project(
        fixture_drive, "260419_Pruned",
        sections=["01 Model", "08 OUT/Invoices"],
        files={"08 OUT/Invoices/inv.pdf": "y"},
    )
    tree = tree_for(fixture_drive, "260419_Pruned")
    applied = applied_repair(fixture_drive, "260419_Pruned", "08 OUT/Invoices")
    tree.reconcile(applied)
    assert "10 Legal" in {n.name for n in tree.children()}

    inventory = scan_drive(fixture_drive)
    undone = apply_plan(fixture_drive, project, inventory.map, invert_plan(applied))
    assert [a.status for a in undone.actions] == ["done"], undone.actions

    assert (project / "08 OUT" / "Invoices" / "inv.pdf").is_file()
    assert not (project / "10 Legal").exists()
    tree.reconcile(undone)
    assert "10 Legal" not in {n.name for n in tree.children()}


def test_a_project_wide_conform_invalidates_the_project(fixture_drive):
    """Guard strength scales with action scope, and so does invalidation. A
    conform's manifest can span the whole project; rebuilding it wholesale is
    cheaper than chasing every parent it touched."""
    make_project(
        fixture_drive, "260415_Wholesale",
        sections=["01 Model", "Meetings", "08 OUT/Invoices", "10 Legal"],
        files={"Meetings/k.md": "z", "08 OUT/Invoices/inv.pdf": "y"},
    )
    tree = tree_for(fixture_drive, "260415_Wholesale")
    tree.children()
    tree.children("01 Model")
    assert tree.load_state("01 Model") == READ

    tree.invalidate_all()

    assert tree.load_state("") == UNREAD
    assert tree.load_state("01 Model") == UNREAD


def test_a_node_cannot_hold_a_load_state_adr_0004_forbids():
    """A folder Atlas has not opened is Unread, never blank; a file has no Load
    State at all. Both are enforced on the record, not at the call sites."""
    from atlas.core.tree import TreeNode

    assert TreeNode(key="01 Model", name="01 Model", is_dir=True).load == UNREAD
    assert TreeNode(key="a.md", name="a.md", is_dir=False, load=READ).load == ""


def test_filing_state_is_decided_by_the_first_rule_conform_applies(fixture_drive):
    """Drift, then relocations, then sweeps: the first match wins (#60), so the
    tree's word agrees with the action conform will actually take."""
    import json

    from conftest import FIXTURE_MAP, write_map

    data = json.loads(json.dumps(FIXTURE_MAP))
    data["driftMap"]["Stuff"] = "11 Meetings"
    data["relocations"]["Stuff"] = "10 Legal/Stuff"
    write_map(fixture_drive, data)
    make_project(fixture_drive, "260402_Both", sections=["01 Model"],
                 files={"Stuff/a.txt": "x"})
    tree = tree_for(fixture_drive, "260402_Both")

    assert tree.filing_state("Stuff") == DRIFTED
    plan = build_repair_plan(tree.report, tree.drive_map, "Stuff")
    assert plan.actions[0].kind == "rename"
