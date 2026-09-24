"""TUI pilot smoke tests - the wizards drive the same core the CLI uses, so
these verify wiring, not logic (logic is covered in test_ops/test_conform)."""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import date
from threading import Event

import atlas.tui.app as tui_app
from atlas.core.conform import SKIPPED, Plan
from atlas.core.contacts import ContactDraft, add_contact, load_contacts
from atlas.core.mapfile import find_map, load_map
from atlas.core.ops import new_project
from textual.widgets import Button, DataTable, Input, ListView, Select, SelectionList, Static

from atlas.tui.app import (
    AddSectionModal,
    AtlasApp,
    ConfirmListModal,
    ContactManagerModal,
    NewProjectModal,
    ResultModal,
)

from conftest import FIXTURE_MAP, make_intake, make_project, write_map


async def settle(app: AtlasApp, pilot) -> None:
    """Wait for a worker and any refresh worker it schedules."""

    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


async def test_tui_boots_and_lists_projects(fixture_drive):
    m = load_map(find_map(fixture_drive))
    new_project(fixture_drive, m, make_intake(fixture_drive, "Alpha", created=date(2026, 8, 13)))
    make_project(fixture_drive, "260813_Beta", sections=["01 Model"])

    app = AtlasApp(fixture_drive)
    async with app.run_test() as pilot:
        await settle(app, pilot)
        table = app.query_one("#projects")
        assert table.row_count == 2
        assert "TESTDRIVE" in app.sub_title


def test_new_project_action_is_visible_in_footer():
    binding = next(binding for binding in AtlasApp.BINDINGS if binding.action == "new_project")

    assert binding.description == "New project"
    assert binding.show


async def test_new_project_wizard_creates_complete_project(fixture_drive):
    contact = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    app = AtlasApp(fixture_drive)
    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("n")
        await pilot.pause()
        assert isinstance(app.screen, NewProjectModal)
        for field, value in (
            ("#name", "Wizard House"),
            ("#street", "1842 Oak Street"),
            ("#city", "Oakland"),
            ("#state", "CA"),
            ("#postal-code", "94612"),
            ("#desc", "ADU"),
        ):
            app.screen.query_one(field, Input).value = value
        app.screen.query_one("#use-case", Select).value = "Renovation"
        await pilot.pause()
        app.screen.query_one("#next-project", Button).press()
        await pilot.pause()
        app.screen.query_one("#billing-contact", Select).value = contact.id
        await pilot.pause()
        assert app.screen.query_one("#client-contact", Select).value == contact.id
        app.screen.query_one("#next-contacts", Button).press()
        await pilot.pause()
        assert "260" in str(app.screen.query_one("#review", Static).render())
        app.screen.query_one("#create-project", Button).press()
        await settle(app, pilot)

    stamp = date.today().strftime("%y%m%d")
    created = fixture_drive / f"{stamp}_1842 Oak Street-ADU"
    assert created.is_dir()
    dossier = (created / "PROJECT.md").read_text(encoding="utf-8")
    assert 'address: "1842 Oak Street, Oakland, CA 94612"' in dossier
    assert "| Billing Contact | Ada Lovelace |" in dossier
    assert (created / "11 Meetings").is_dir()


async def test_edit_project_prepopulates_and_confirms_folder_rename(fixture_drive):
    intake = make_intake(
        fixture_drive,
        "Typo House",
        street="1842 Oka Street",
        created=date(2026, 9, 2),
    )
    created = new_project(fixture_drive, load_map(find_map(fixture_drive)), intake)
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("e")
        await pilot.pause()
        assert isinstance(app.screen, NewProjectModal)
        assert app.screen.query_one("#name", Input).value == "Typo House"
        assert app.screen.query_one("#street", Input).value == "1842 Oka Street"
        app.screen.query_one("#street", Input).value = "1842 Oak Street"
        app.screen.query_one("#next-project", Button).press()
        await pilot.pause()
        app.screen.query_one("#next-contacts", Button).press()
        await pilot.pause()
        assert "Folder rename:" in str(app.screen.query_one("#review", Static).render())
        app.screen.query_one("#create-project", Button).press()
        # settle, not pause: the confirm modal can be the active screen a frame
        # before its buttons are mounted, which is the NoMatches this test used to
        # raise intermittently (session 8 handoff).
        await settle(app, pilot)
        assert isinstance(app.screen, ConfirmListModal)
        app.screen.query_one("#ok", Button).press()
        await settle(app, pilot)

    renamed = fixture_drive / "260902_1842 Oak Street"
    assert renamed.is_dir()
    assert not created.path.exists()
    assert 'address_street: "1842 Oak Street"' in (renamed / "PROJECT.md").read_text(
        encoding="utf-8"
    )


async def test_new_project_refuses_pasted_control_characters_inline(fixture_drive):
    # Two spreadsheet cells pasted into Project name used to leave "Next"
    # enabled and then crash the app at review, losing every entry.
    contact = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    app = AtlasApp(fixture_drive)
    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("n")
        await pilot.pause()
        for field, value in (
            ("#name", "Oak House\tRenovation\r\n"),
            ("#street", "1842 Oak Street"),
            ("#city", "Oakland"),
            ("#state", "CA"),
            ("#postal-code", "94612"),
        ):
            app.screen.query_one(field, Input).value = value
        app.screen.query_one("#use-case", Select).value = "Renovation"
        await pilot.pause()

        assert app.screen.query_one("#next-project", Button).disabled
        assert "control characters" in str(
            app.screen.query_one("#project-error", Static).render()
        )

        app.screen.query_one("#name", Input).value = "Oak House"
        app.screen.query_one("#desc", Input).value = "Kitchen\u2028Bath"
        await pilot.pause()
        assert app.screen.query_one("#next-project", Button).disabled

        # Even when a bad value reaches review, the error lands inline.
        app.screen.query_one("#next-project", Button).disabled = False
        app.screen.query_one("#next-project", Button).press()
        await pilot.pause()
        app.screen.query_one("#billing-contact", Select).value = contact.id
        await pilot.pause()
        app.screen.query_one("#next-contacts", Button).press()
        await pilot.pause()
        assert isinstance(app.screen, NewProjectModal)
        assert app.screen.query_one("#name", Input).value == "Oak House"
        assert "control characters" in str(
            app.screen.query_one("#project-error", Static).render()
        )


async def test_manage_contacts_edits_po_box_without_rewriting_projects(fixture_drive):
    contact = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    app = AtlasApp(fixture_drive)
    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("m")
        await pilot.pause()
        assert isinstance(app.screen, ContactManagerModal)
        app.screen.query_one("#manager-contact", Select).value = contact.id
        await pilot.pause()
        for field, value in (
            ("#manager-street", "PO Box 42"),
            ("#manager-city", "Oakland"),
            ("#manager-state", "CA"),
            ("#manager-zip", "94612"),
        ):
            app.screen.query_one(field, Input).value = value
        app.screen.query_one("#manager-save", Button).press()
        await pilot.pause()

    updated = load_contacts(fixture_drive).contacts[0]
    assert updated.id == contact.id
    assert updated.address["street"] == "PO Box 42"


async def test_new_project_hides_custom_use_case_until_other_selected(fixture_drive):
    app = AtlasApp(fixture_drive)
    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("n")
        await pilot.pause()
        assert not app.screen.query_one("#custom-use-case", Input).display
        app.screen.query_one("#use-case", Select).value = "Other"
        await pilot.pause()
        assert app.screen.query_one("#custom-use-case", Input).display


async def test_add_contact_duplicate_email_requires_explicit_choice(fixture_drive):
    existing = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    app = AtlasApp(fixture_drive)
    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("n")
        app.screen.query_one("#use-case", Select).value = "Renovation"
        app.screen.query_one("#billing-contact", Select).value = NewProjectModal.ADD_NEW
        await pilot.pause()
        for field, value in (
            ("#contact-first", "Wrong"),
            ("#contact-last", "Person"),
            ("#contact-email", existing.email.upper()),
        ):
            app.screen.query_one(field, Input).value = value
        app.screen.query_one("#add-contact-ok", Button).press()
        await pilot.pause()
        error = str(app.screen.query_one("#contact-error", Static).content)
        assert "already belongs to Ada Lovelace" in error
        assert app.screen.query_one("#contact-first", Input).value == "Wrong"


async def test_wizard_adds_shared_contact_and_defaults_client(fixture_drive):
    app = AtlasApp(fixture_drive)
    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("n")
        for field, value in (
            ("#name", "Contact Test"),
            ("#street", "100 Main Street"),
            ("#city", "Oakland"),
            ("#state", "CA"),
            ("#postal-code", "94612"),
        ):
            app.screen.query_one(field, Input).value = value
        app.screen.query_one("#use-case", Select).value = "Feasibility"
        await pilot.pause()
        app.screen.query_one("#next-project", Button).press()
        await pilot.pause()
        app.screen.query_one("#billing-contact", Select).value = NewProjectModal.ADD_NEW
        await pilot.pause()
        app.screen.query_one("#contact-first", Input).value = "Grace"
        app.screen.query_one("#contact-last", Input).value = "Hopper"
        app.screen.query_one("#contact-email", Input).value = "grace@example.com"
        app.screen.query_one("#add-contact-ok", Button).press()
        await pilot.pause()

        wizard = app.screen
        assert isinstance(wizard, NewProjectModal)
        billing = wizard.query_one("#billing-contact", Select).value
        assert isinstance(billing, str)
        assert wizard.query_one("#client-contact", Select).value == billing
        assert load_contacts(fixture_drive).contacts[0].email == "grace@example.com"


async def test_conform_modal_applies_plan(fixture_drive):
    make_project(
        fixture_drive, "260813_Fixit", sections=["01 Model", "Meetings"],
        files={"Meetings/kickoff.md": "x"},
    )
    app = AtlasApp(fixture_drive)
    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("f")
        await pilot.pause()
        await pilot.click("#ok")
        await settle(app, pilot)

    project = fixture_drive / "260813_Fixit"
    assert (project / "11 Meetings" / "kickoff.md").is_file()
    assert (project / "PROJECT.md").is_file()


async def test_filter_is_fast_and_escape_restores_all_projects(fixture_drive):
    make_project(fixture_drive, "260813_Alpha", sections=["01 Model"])
    make_project(fixture_drive, "260813_Beta", sections=["01 Model"])
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("/")
        filter_input = app.query_one("#filter", Input)
        assert filter_input.display
        await pilot.press("b", "e", "t", "a")
        await pilot.pause()
        assert app.query_one("#projects", DataTable).row_count == 1
        assert "Beta" in str(app.query_one("#workspace-title", Static).content)

        await pilot.press("escape")
        await pilot.pause()
        assert not filter_input.display
        assert app.query_one("#projects", DataTable).row_count == 2


async def test_enter_drills_into_the_workspace_and_escape_unwinds(fixture_drive):
    """Enter used to push a project-health modal. ADR 0005 reclaims it: health is
    a Companion Mode now, and Enter drills toward the tree without leaving the
    screen. Nothing about the console is behind a modal any more."""
    make_project(
        fixture_drive,
        "260813_Review",
        sections=["01 Model"],
        files={"loose.pdf": "x"},
    )
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        assert app._focus_region == "projects"

        await pilot.press("enter")
        await pilot.pause()
        assert app.screen is app.screen_stack[0], "no modal"
        assert app._focus_region == "tree"

        await pilot.press("enter")
        await pilot.pause()
        assert app._focus_region == "companion"

        await pilot.press("escape")
        await pilot.press("escape")
        await pilot.pause()
        assert app._focus_region == "projects"


async def test_add_folders_requires_a_selection(fixture_drive):
    make_project(fixture_drive, "260813_Add", sections=["01 Model"])
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("a")
        await settle(app, pilot)
        assert isinstance(app.screen, AddSectionModal)
        create = app.screen.query_one("#ok", Button)
        assert create.disabled

        choices = app.screen.query_one(SelectionList)
        choices.select(choices.get_option_at_index(0).value)
        await pilot.pause()
        assert not create.disabled


async def test_scan_failure_stays_visible_and_does_not_crash(fixture_drive, monkeypatch):
    def fail_scan(_root):
        raise PermissionError("shared drive unavailable")

    monkeypatch.setattr("atlas.tui.app.scan_drive", fail_scan)
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        operation = str(app.query_one("#operation", Static).content)
        assert "shared drive unavailable" in operation
        assert "Press r to retry" in operation
        assert app.check_action("new_project", ()) is None


async def test_back_reaches_single_drive_picker_without_reopening(fixture_drive, monkeypatch):
    monkeypatch.setattr("atlas.tui.app.discover_drives", lambda: [fixture_drive])
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("escape")
        await pilot.pause()
        assert app.query_one("#drives", ListView).display
        assert app._inventory is None


async def test_back_during_slow_scan_ignores_late_result(fixture_drive, monkeypatch):
    real_scan = tui_app.scan_drive
    started = Event()
    release = Event()

    def slow_scan(root):
        started.set()
        release.wait(timeout=2)
        return real_scan(root)

    monkeypatch.setattr(tui_app, "scan_drive", slow_scan)
    monkeypatch.setattr(tui_app, "discover_drives", lambda: [fixture_drive])
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await pilot.pause()
        assert started.wait(timeout=1)
        await pilot.press("escape")
        await pilot.pause()
        release.set()
        await settle(app, pilot)
        assert app.query_one("#drives", ListView).display
        assert not app.query_one("#workspace").display
        assert app._inventory is None


async def test_failed_refresh_keeps_diagnosis_but_disables_mutation(fixture_drive, monkeypatch):
    make_project(fixture_drive, "260813_Stale", sections=["01 Model"])
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        assert app._inventory_fresh

        monkeypatch.setattr(tui_app, "scan_drive", lambda _root: (_ for _ in ()).throw(PermissionError("offline")))
        await pilot.press("r")
        await settle(app, pilot)

        assert app.query_one("#projects", DataTable).row_count == 1
        assert not app._inventory_fresh
        assert app.check_action("conform", ()) is None
        assert "offline" in str(app.query_one("#operation", Static).content)


async def test_busy_state_hides_palette_mutations_and_direct_actions(fixture_drive):
    make_project(fixture_drive, "260813_Busy", sections=["01 Model"])
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        app._busy = True
        app._work_kind = "operation"
        commands = {command.title for command in app.get_system_commands(app.screen)}
        app.action_conform()
        await pilot.pause()

        assert "Conform project" not in commands
        assert app.screen is app.screen_stack[0]


async def test_add_modal_fits_and_focuses_choices_at_80_by_24(fixture_drive):
    make_project(fixture_drive, "260813_Compact", sections=[])
    app = AtlasApp(fixture_drive)

    async with app.run_test(size=(80, 24)) as pilot:
        await settle(app, pilot)
        await pilot.press("a")
        await settle(app, pilot)
        assert isinstance(app.screen, AddSectionModal)
        choices = app.screen.query_one(SelectionList)
        actions = app.screen.query_one(".actions")
        assert app.focused is choices
        assert actions.region.bottom <= app.size.height
        assert choices.region.height > 0


async def test_add_folders_does_not_recreate_deleted_project(fixture_drive):
    project = make_project(fixture_drive, "260813_Deleted", sections=[])
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("a")
        await settle(app, pilot)
        choices = app.screen.query_one(SelectionList)
        choices.select(choices.get_option_at_index(0).value)
        await pilot.pause()
        project.rmdir()
        await pilot.click("#ok")
        await settle(app, pilot)

        assert app._last_result is not None
        assert app._last_result.title == "Add-folders plan changed"
        assert not project.exists()


async def test_new_project_refuses_changed_drive_map(fixture_drive):
    contact = add_contact(
        fixture_drive,
        ContactDraft(first_name="Ada", last_name="Lovelace", email="ada@example.com"),
    )
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("n")
        for field, value in (
            ("#name", "Changed Map"),
            ("#street", "100 Changed Street"),
            ("#city", "Oakland"),
            ("#state", "CA"),
            ("#postal-code", "94612"),
        ):
            app.screen.query_one(field, Input).value = value
        app.screen.query_one("#use-case", Select).value = "Renovation"
        await pilot.pause()
        app.screen.query_one("#next-project", Button).press()
        await pilot.pause()
        app.screen.query_one("#billing-contact", Select).value = contact.id
        await pilot.pause()
        app.screen.query_one("#next-contacts", Button).press()
        await pilot.pause()
        changed_map = copy.deepcopy(FIXTURE_MAP)
        changed_map["version"] = "2.1"
        write_map(fixture_drive, changed_map)
        app.screen.query_one("#create-project", Button).press()
        await settle(app, pilot)

        assert isinstance(app.screen, NewProjectModal)
        assert "Drive map changed" in str(app.screen.query_one("#review-error", Static).render())
        assert app.screen.query_one("#name", Input).value == "Changed Map"
        assert not any("100 Changed Street" in path.name for path in fixture_drive.iterdir())

        app.screen.query_one("#create-project", Button).press()
        await settle(app, pilot)
        assert any("100 Changed Street" in path.name for path in fixture_drive.iterdir())


async def test_marked_projects_share_one_safe_conform_plan(fixture_drive):
    for name in ("260813_Alpha", "260813_Beta"):
        make_project(
            fixture_drive,
            name,
            sections=["01 Model", "Meetings"],
            files={"Meetings/kickoff.md": name},
        )
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("space", "down", "space", "x")
        await pilot.pause()
        assert len(app._marked) == 2
        assert "2 marked project" in str(app.screen.query_one(".dialog-title", Static).content)
        await pilot.click("#ok")
        await settle(app, pilot)

        assert app._last_result is not None
        assert app._last_result.title == "Batch conform result"
        assert not app._marked
        for name in ("260813_Alpha", "260813_Beta"):
            assert (fixture_drive / name / "11 Meetings" / "kickoff.md").is_file()


async def test_batch_conform_refuses_if_any_preview_becomes_stale(fixture_drive):
    for name in ("260813_Alpha", "260813_Beta"):
        make_project(
            fixture_drive,
            name,
            sections=["01 Model", "Meetings"],
            files={"Meetings/kickoff.md": name},
        )
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("space", "down", "space", "x")
        await pilot.pause()
        (fixture_drive / "260813_Beta" / "CLAUDE.md").write_text("@PROJECT.md\n", encoding="utf-8")
        await pilot.click("#ok")
        await settle(app, pilot)

        assert app._last_result is not None
        assert app._last_result.title == "Batch plan changed"
        assert app._marked == {"260813_Alpha", "260813_Beta"}
        for name in ("260813_Alpha", "260813_Beta"):
            assert (fixture_drive / name / "Meetings" / "kickoff.md").is_file()


async def test_batch_rechecks_each_project_immediately_before_apply(fixture_drive, monkeypatch):
    for name in ("260813_Alpha", "260813_Beta"):
        make_project(
            fixture_drive,
            name,
            sections=["01 Model", "Meetings"],
            files={"Meetings/kickoff.md": name},
        )
    real_apply = tui_app.apply_plan

    def change_later_project(root, project, drive_map, plan):
        result = real_apply(root, project, drive_map, plan)
        if plan.project == "260813_Alpha":
            (fixture_drive / "260813_Beta" / "CLAUDE.md").write_text(
                "@PROJECT.md\n", encoding="utf-8"
            )
        return result

    monkeypatch.setattr(tui_app, "apply_plan", change_later_project)
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("space", "down", "space", "x")
        await pilot.pause()
        await pilot.click("#ok")
        await settle(app, pilot)

        assert app._last_result is not None
        assert app._last_result.title == "Batch conform stopped"
        assert app._marked == {"260813_Beta"}
        assert (fixture_drive / "260813_Alpha" / "11 Meetings" / "kickoff.md").is_file()
        assert (fixture_drive / "260813_Beta" / "Meetings" / "kickoff.md").is_file()


async def test_batch_partial_failure_preserves_progress_and_remaining_mark(fixture_drive, monkeypatch):
    for name in ("260813_Alpha", "260813_Beta"):
        make_project(
            fixture_drive,
            name,
            sections=["01 Model", "Meetings"],
            files={"Meetings/kickoff.md": name},
        )
    real_apply = tui_app.apply_plan

    def fail_second(root, project, drive_map, plan):
        if plan.project == "260813_Beta":
            raise PermissionError("Beta became read-only")
        return real_apply(root, project, drive_map, plan)

    monkeypatch.setattr(tui_app, "apply_plan", fail_second)
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("space", "down", "space", "x")
        await pilot.pause()
        await pilot.click("#ok")
        await settle(app, pilot)

        assert app._last_result is not None
        assert app._last_result.title == "Batch conform stopped"
        assert "Beta became read-only" in "\n".join(app._last_result.lines)
        assert app._marked == {"260813_Beta"}
        assert (fixture_drive / "260813_Alpha" / "11 Meetings" / "kickoff.md").is_file()
        assert (fixture_drive / "260813_Beta" / "Meetings" / "kickoff.md").is_file()


async def test_batch_conflict_remains_marked_for_review(fixture_drive):
    make_project(
        fixture_drive,
        "260813_Conflict",
        sections=["01 Model", "Meetings", "11 Meetings"],
        files={"Meetings/kickoff.md": "source", "11 Meetings/kickoff.md": "target"},
    )
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("space", "x")
        await pilot.pause()
        await pilot.click("#ok")
        await settle(app, pilot)

        assert app._last_result is not None
        assert "1 conflict(s)" in app._last_result.summary
        assert app._marked == {"260813_Conflict"}
        assert (fixture_drive / "260813_Conflict" / "Meetings" / "kickoff.md").is_file()


async def test_single_conform_reports_skipped_actions_as_warning(fixture_drive, monkeypatch):
    make_project(fixture_drive, "260813_Skipped", sections=["01 Model", "Meetings"])

    def skip_all(_root, _project, _drive_map, plan):
        return Plan(
            project=plan.project,
            actions=tuple(
                replace(action, status=SKIPPED, note="changed concurrently")
                for action in plan.actions
            ),
        )

    monkeypatch.setattr(tui_app, "apply_plan", skip_all)
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("f")
        await pilot.pause()
        await pilot.click("#ok")
        await settle(app, pilot)

        assert app._last_result is not None
        assert app._last_result.severity == "warning"
        assert "skipped" in app._last_result.summary


async def test_conform_refuses_when_preview_becomes_stale(fixture_drive):
    make_project(
        fixture_drive,
        "260813_Changed",
        sections=["01 Model", "Meetings"],
        files={"Meetings/kickoff.md": "x"},
    )
    app = AtlasApp(fixture_drive)

    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("f")
        await pilot.pause()
        project_md = fixture_drive / "260813_Changed" / "PROJECT.md"
        project_md.write_text("# Human notes\n", encoding="utf-8")
        await pilot.click("#ok")
        await settle(app, pilot)

        assert app._last_result is not None
        assert app._last_result.title == "Conform plan changed"
        assert project_md.read_text(encoding="utf-8") == "# Human notes\n"
        assert (fixture_drive / "260813_Changed" / "Meetings" / "kickoff.md").is_file()
        assert not (fixture_drive / "260813_Changed" / "11 Meetings" / "kickoff.md").exists()
