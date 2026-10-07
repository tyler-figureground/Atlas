"""Shared project rules preserve model isolation without a machine-wide process ban."""

from dataclasses import replace

from atlas.core.mapfile import find_map, load_map
from atlas.core.projectmd import agents_block_lines, with_agents_block


def rules_map(drive):
    mapping = load_map(find_map(drive))
    return replace(
        mapping,
        control_plane={**mapping.control_plane, "agentsRules": "agents-rules.md"},
    )


def generated_rules(drive):
    return "\n".join(agents_block_lines(rules_map(drive)))


def test_model_exclusivity_is_not_machine_exclusivity(fixture_drive):
    rules = generated_rules(fixture_drive)
    assert "One writer per model, not one Revit process per machine" in rules
    assert "Exactly one `Revit.exe`" not in rules
    assert "second live writer on the same model blocks writes" in rules
    assert "even through a different local path" in rules
    assert "central-model lineage" in rules
    assert "never fall back to an unpinned connection" in rules
    assert "zero matches, multiple matches or drift means stop" in rules
    assert "Never close, kill or retarget another session" in rules
    assert "Multi-instance support is not operational acceptance" in rules


def test_worksets_precede_inventory_and_printed_backgrounds_are_checked(fixture_drive):
    rules = generated_rules(fixture_drive)
    assert "open/reopen, local creation, migration or restart" in rules
    assert (
        "user-workset `IsOpen` states before inventories, area calculations, edits or exports"
        in rules
    )
    assert "loaded link or visible category does not prove" in rules
    assert "Never infer missing/deleted geometry from a partial-load document" in rules
    assert "cancel Opening Worksets as generic dialog dismissal" in rules
    assert "preserve intentional visibility settings" in rules
    assert (
        "actual exported model viewports against the last accepted background content"
        in rules
    )


def test_capability_and_user_authority_boundaries_survive(fixture_drive):
    rules = generated_rules(fixture_drive)
    assert "connected runtime's actual capabilities" in rules
    assert (
        "not permission to draw an imitation or bypass targeting/trust checks" in rules
    )
    assert "never take or release another user's borrowed Revit elements" in rules
    assert "Sync only when he asks" in rules
    assert (
        "Recheck after reconnects, restarts, document switches and posted native commands"
        in rules
    )
    assert "a tool's explicit supported targeting contract" in rules


def test_recent_drafting_rulings_are_not_reversed(fixture_drive):
    rules = generated_rules(fixture_drive)
    for settled in (
        "Door marks `D01`, `D02`, `D03`",
        "Ceiling heights in the ceiling tag label",
        "No pricing on drawings",
        "Casework is dimensioned as the subject, never as a reference",
        "always on the sheet, never in a view",
        "sketched clockwise",
        "ALL CAPS everywhere on a sheet",
        "every other sheet from the lower-right corner, up then left",
        "one master on a G-series sheet, or level by level",
    ):
        assert settled in rules


def test_refresh_preserves_project_specific_standing_rulings(fixture_drive):
    from atlas.core.projectmd import AGENTS_BEGIN, AGENTS_END

    mapping = rules_map(fixture_drive)
    custom = "\n## Project ruling\nSync at natural checkpoints, per Tyler's standing instruction.\n"
    old = f"# Project\n{AGENTS_BEGIN}\nExactly one `Revit.exe`\n{AGENTS_END}\n{custom}"
    updated = "\n".join(with_agents_block(old.splitlines(), mapping)) + "\n"
    assert custom in updated
    assert "Exactly one `Revit.exe`" not in updated
    assert "One writer per model" in updated
