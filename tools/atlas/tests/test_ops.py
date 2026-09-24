from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

import atlas.core.ops as ops_module
from atlas.core.doctor import report_drive
from atlas.core.mapfile import Section, find_map, load_map
from atlas.core.naming import build_folder_name, clean_name_part
from atlas.core.ops import (
    OpsError,
    PartialProjectError,
    add_sections,
    find_empty_dirs,
    new_project,
    remove_empty_dirs,
)
from atlas.core.scan import scan_drive

from conftest import make_intake

CREATED = date(2026, 8, 13)


def load(fixture_drive):
    return load_map(find_map(fixture_drive))


# ------------------------------------------------------------------ naming

def test_clean_name_part_ps1_parity():
    assert clean_name_part('  a/b:c*d?e"f<g>h|i  ') == "a b c d e f g h i"
    assert clean_name_part("Two   Spaces") == "Two Spaces"
    assert clean_name_part("Trailing dot.") == "Trailing dot"
    assert clean_name_part(None) == ""


@pytest.mark.parametrize(
    "raw, cleaned",
    [
        ("Kitchen .", "Kitchen"),
        ("Kitchen. .", "Kitchen"),
        ("Kitchen |.", "Kitchen"),
        ("Kitchen ?", "Kitchen"),
        (" . Kitchen", ". Kitchen"),
        (". .", ""),
    ],
)
def test_clean_name_part_leaves_no_trailing_space_or_dot(raw, cleaned):
    # Windows drops a trailing space or dot when it makes the folder, so the
    # name Atlas computes must already be the name the disk will hold.
    assert clean_name_part(raw) == cleaned


def test_clean_name_part_never_ends_in_space_or_dot_for_any_input():
    import random

    alphabet = ' .\t|?*"<>:/\\ab1'
    generator = random.Random(33)
    for _ in range(5000):
        raw = "".join(generator.choice(alphabet) for _ in range(generator.randint(0, 12)))
        cleaned = clean_name_part(raw)
        assert cleaned == cleaned.strip(), raw
        assert not cleaned.endswith("."), raw


def test_build_folder_name():
    assert build_folder_name(CREATED, "House") == "260813_House"
    assert build_folder_name(CREATED, "House", "ADU") == "260813_House-ADU"


# ------------------------------------------------------------------ new

def test_new_project_creates_seeds_and_control_plane(fixture_drive):
    m = load(fixture_drive)
    intake = make_intake(
        fixture_drive, "Test House", "ADU", street="1842 Oak Street", created=CREATED
    )
    result = new_project(fixture_drive, m, intake)
    p = result.path
    assert result.folder_name == "260813_1842 Oak Street-ADU"
    assert (p / "01 Model").is_dir()
    assert (p / "11 Meetings").is_dir()
    assert not (p / "10 Legal").exists()  # seed=false stays JIT
    assert not any((p / "01 Model").iterdir())  # seed children NOT created (PS1 parity)
    assert (p / "PROJECT.md").is_file()
    assert (p / "decisions" / "README.md").is_file()
    assert (p / "CLAUDE.md").is_file()
    assert (p / "06 Research" / "Code").is_dir()
    index = (fixture_drive / "_Project Index.md").read_bytes().decode("utf-8")
    assert (
        "| 260813_1842 Oak Street-ADU | Test House | "
        "1842 Oak Street, Oakland, CA 94612 | Renovation | 2026-08-13 | ADU | Active |"
    ) in index


def test_new_project_populates_project_intake_in_dossier(fixture_drive):
    m = load(fixture_drive)
    intake = make_intake(
        fixture_drive,
        "Oak House",
        "Kitchen",
        street="1842 Oak Street",
        use_case="Renovation + Addition",
        created=CREATED,
    )

    result = new_project(fixture_drive, m, intake)
    text = (result.path / "PROJECT.md").read_text(encoding="utf-8")

    for expected in (
        'project: "Oak House"',
        'address: "1842 Oak Street, Oakland, CA 94612"',
        'address_street: "1842 Oak Street"',
        'address_city: "Oakland"',
        'address_state: "CA"',
        'address_postal_code: "94612"',
        'description: "Kitchen"',
        'project_use_case: "Renovation + Addition"',
        'project_use_case_category: "Renovation + Addition"',
        f'billing_contact_id: "{intake.billing_contact_id}"',
        f'client_contact_id: "{intake.client_contact_id}"',
        "| Address / BBL | 1842 Oak Street, Oakland, CA 94612 |",
        "| Project Use Case | Renovation + Addition |",
        "| Billing Contact | Test Oak House |",
        "| Client Contact | Test Oak House |",
    ):
        assert expected in text


def test_new_project_refuses_overlong_path_before_creating_folder(fixture_drive):
    m = load(fixture_drive)
    intake = make_intake(fixture_drive, "Long", "x" * 300, created=CREATED)

    with pytest.raises(OpsError, match="path is too long"):
        new_project(fixture_drive, m, intake)

    assert not any(path.name.startswith("260813_100 Long Street") for path in fixture_drive.iterdir())


def test_new_project_refuses_escaping_or_overlong_mapped_paths_before_writing(fixture_drive):
    intake = make_intake(fixture_drive, "Unsafe", created=CREATED)
    base = load(fixture_drive)

    for section_id in ("../escaped", "A" * 220):
        unsafe = replace(base, sections=(Section(section_id, seed=True),))
        with pytest.raises(OpsError, match="project root|too long"):
            new_project(fixture_drive, unsafe, intake)

    assert not (fixture_drive.parent / "escaped").exists()
    assert not (fixture_drive / "_Project Index.md").exists()


def test_new_project_reports_partial_path_after_post_create_failure(fixture_drive, monkeypatch):
    m = load(fixture_drive)
    intake = make_intake(fixture_drive, "Partial", created=CREATED)

    def fail_seed(root, relative):
        raise OSError("simulated shared-drive failure")

    monkeypatch.setattr(ops_module, "mkdir_below", fail_seed)

    with pytest.raises(PartialProjectError, match="partially created") as caught:
        new_project(fixture_drive, m, intake)

    assert caught.value.path.is_dir()
    assert str(caught.value.path) in str(caught.value)


def test_new_project_refuses_existing(fixture_drive):
    m = load(fixture_drive)
    intake = make_intake(fixture_drive, "Twice", created=CREATED)
    new_project(fixture_drive, m, intake)
    with pytest.raises(OpsError, match="already exists"):
        new_project(fixture_drive, m, intake)


def test_new_project_is_doctor_conform(fixture_drive):
    # The P2 gate tying into P1: a freshly created project must report CONFORM.
    m = load(fixture_drive)
    intake = make_intake(fixture_drive, "Fresh", "New", created=CREATED)
    result = new_project(fixture_drive, m, intake)
    report = report_drive(scan_drive(fixture_drive))
    (p,) = [x for x in report.projects if x.name == result.folder_name]
    assert p.status == "conform", (p.missing_control_plane, p.unfiled, p.drift)


def test_project_md_bytes(fixture_drive):
    """Byte-level contract: UTF-8 no BOM, CRLF, trailing newline, front matter first."""
    m = load(fixture_drive)
    intake = make_intake(fixture_drive, "Golden", "Spec", created=CREATED)
    result = new_project(fixture_drive, m, intake)
    raw = (result.path / "PROJECT.md").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")           # no BOM, Norma requirement
    assert raw.startswith(b"---\r\n")                      # front matter first, CRLF
    assert raw.endswith(b"\r\n")                           # trailing newline
    assert b"\n" not in raw.replace(b"\r\n", b"")          # CRLF-only line endings

    text = raw.decode("utf-8")
    lines = text.split("\r\n")
    # Machine contract remains additive and Norma-compatible.
    assert 'project: "Golden"' in lines
    assert "tenancy:" in lines
    assert lines.index("---", 1) > lines.index('project: "Golden"')
    # Identity retains legacy rows alongside complete Atlas intake.
    for row in ("| Project | Golden |", "| Jurisdiction | |", "| Virtual tour | |", "| Descriptor | Spec |",
                "| Created | 2026-08-13 |", "| Drive | TESTDRIVE |", "| Status | Active |"):
        assert row in lines, row
    # Canonical map block remains marker-wrapped.
    assert "<!-- atlas:map-begin -->" in lines
    assert "<!-- atlas:map-end -->" in lines
    assert "- **01 Model** _[seed]_" in lines
    assert "- **10 Legal** _[on demand]_" in lines
    assert "  - Invoices" in lines
    # Atlas owns generated-file attribution.
    assert "_Naming: YYMMDD_<ShortAddress>-<Description>. Generated by Atlas._" in lines
    assert "Generated by New-Project" not in text


# ------------------------------------------------------------------ add

def test_add_sections_blessed_only(fixture_drive):
    m = load(fixture_drive)
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Adder", created=CREATED))
    created = add_sections(fixture_drive, m, result.path, ["10 Legal", "10 Legal/Invoices"])
    assert created == ["10 Legal", "10 Legal/Invoices"]
    assert (result.path / "10 Legal" / "Invoices").is_dir()
    # idempotent
    assert add_sections(fixture_drive, m, result.path, ["10 Legal"]) == []


def test_add_sections_rejects_unblessed(fixture_drive):
    m = load(fixture_drive)
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Strict", created=CREATED))
    with pytest.raises(OpsError, match="not a blessed child"):
        add_sections(fixture_drive, m, result.path, ["10 Legal/Random Folder"])
    with pytest.raises(OpsError, match="not a canonical section"):
        add_sections(fixture_drive, m, result.path, ["Random Section"])


def test_add_sections_never_recreates_missing_project_root(fixture_drive):
    m = load(fixture_drive)
    missing = fixture_drive / "260813_Deleted"

    with pytest.raises(OpsError, match="no longer available"):
        add_sections(fixture_drive, m, missing, ["10 Legal/Invoices"])

    assert not missing.exists()


# ------------------------------------------------------------------ clean

def test_clean_finds_and_removes_empty_chains(fixture_drive):
    m = load(fixture_drive)
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Cleaner", created=CREATED))
    p = result.path
    (p / "10 Legal" / "Invoices").mkdir(parents=True)          # empty chain
    (p / "08 OUT" / "RFI").mkdir()
    (p / "08 OUT" / "RFI" / "r1.pdf").write_text("x")           # has a file

    empties = find_empty_dirs(p, m)
    assert "10 Legal/Invoices" in empties and "10 Legal" in empties
    assert "08 OUT/RFI" not in empties
    assert "decisions" not in empties                            # protected
    assert "01 Model" not in empties                             # seed top kept by default

    removed = remove_empty_dirs(fixture_drive, p, empties)
    assert not (p / "10 Legal").exists()
    assert (p / "08 OUT" / "RFI" / "r1.pdf").exists()
    assert set(removed) == set(empties)


def test_clean_include_seeds_removes_empty_seed_tops(fixture_drive):
    m = load(fixture_drive)
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Seedless", created=CREATED))
    empties = find_empty_dirs(result.path, m, include_seeds=True)
    assert "01 Model" in empties and "11 Meetings" in empties
    # analysisDir is control plane: never removable, and it anchors its section.
    assert "06 Research/Code" not in empties
    assert "06 Research" not in empties


def test_clean_default_on_fresh_project_is_noop(fixture_drive):
    m = load(fixture_drive)
    result = new_project(fixture_drive, m, make_intake(fixture_drive, "Pristine", created=CREATED))
    assert find_empty_dirs(result.path, m) == []