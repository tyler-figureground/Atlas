"""`atlas project billing`: the PROJECT.md `billing:` block, and Pyvoid's contract.

Pyvoid's JDP time ledger (PRD-209) reads the block; the CRM writes it
through this command (CRM ADR 0004). The contract tests run every shape the
writer emits through a vendored copy of Pyvoid's reader under PyYAML.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from atlas.cli import main
from atlas.core.billing_block import BillingValues, check_billing, plan_billing
from atlas.core.project_data import ProjectDataError, load_project_record

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
from pyvoid_billing_reader import read_billing  # noqa: E402

FOLDER = "260415_1842 Oak Street-Kitchen"


def _new(drive: Path, capsys) -> Path:
    assert main(["contacts", "add", "--drive", str(drive), "--first-name", "Ada",
                 "--last-name", "Lovelace", "--email", "ada@example.com"]) == 0
    capsys.readouterr()
    assert main(["new", "--drive", str(drive), "--name", "Oak House", "--street",
                 "1842 Oak Street", "--city", "Oakland", "--state", "CA", "--zip", "94612",
                 "--use-case", "Renovation", "--billing-contact", "ada@example.com",
                 "--desc", "Kitchen", "--json"]) == 0
    created = json.loads(capsys.readouterr().out)["created"]
    return drive / created


def _project(drive: Path, front: str, body: str = "# body\n") -> Path:
    project = drive / FOLDER
    project.mkdir()
    (project / "PROJECT.md").write_bytes(f"---\n{front}---\n{body}".encode("utf-8"))
    return project


def _billing(drive: Path, folder: str, *args: str) -> int:
    return main(["project", "billing", folder, "--drive", str(drive), "--json", *args])


# -- writes ------------------------------------------------------------------


def test_writes_a_new_block_pyvoid_reads(fixture_drive, capsys):
    project = _new(fixture_drive, capsys)
    dossier = project / "PROJECT.md"
    before = dossier.read_bytes()

    assert _billing(fixture_drive, project.name, "--project", "260415", "--client",
                    "Acme Co", "--rate", "60", "--yes") == 0

    out = json.loads(capsys.readouterr().out)
    assert out["billing"] == {"project": "260415", "client": "Acme Co", "rate": 60}
    assert out["previous"] is None and out["changed"] and out["applied"]
    after = dossier.read_bytes()
    block = b'billing:\r\n  project: "260415"\r\n  client: "Acme Co"\r\n  rate: 60\r\n'
    assert block in after
    assert after.replace(block, b"") == before   # nothing else moved
    assert read_billing(after) == ({"project": "260415", "client": "Acme Co",
                                    "rate": 60.0}, None)
    load_project_record(project)   # Atlas still reads its own keys


def test_retry_is_a_no_op(fixture_drive, capsys):
    project = _new(fixture_drive, capsys)
    args = ("--project", "260415", "--client", "Acme", "--rate", "62.50", "--yes")
    assert _billing(fixture_drive, project.name, *args) == 0
    capsys.readouterr()
    written = (project / "PROJECT.md").read_bytes()

    assert _billing(fixture_drive, project.name, *args) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["changed"] is False and out["applied"] is False
    assert out["billing"]["rate"] == 62.5
    assert (project / "PROJECT.md").read_bytes() == written


def test_update_keeps_comments_other_keys_and_unrelated_lines(fixture_drive, capsys):
    project = _project(fixture_drive, (
        "project: Oak\n"
        "billing:   # owned by the CRM\n"
        "  # who pays\n"
        "  project: 250101  # old number\n"
        "  client: 'Old Client'\n"
        "  terms: net-15\n"
        "  notes:\n"
        "    - first\n"
        "  rate: 150\n"
        "occupancy_group: [B, \"S-1\"]\n"
        "# trailing comment\n"
    ))

    assert _billing(fixture_drive, project.name, "--project", "260415",
                    "--client", "O'Neil & Sons", "--rate", "175", "--yes") == 0

    out = json.loads(capsys.readouterr().out)
    assert out["previous"] == {"project": "250101", "client": "Old Client", "rate": "150"}
    text = (project / "PROJECT.md").read_bytes().decode("utf-8")
    assert text == (
        "---\r\n"
        "project: Oak\r\n"
        "billing:   # owned by the CRM\r\n"
        "  # who pays\r\n"
        '  project: "260415" # old number\r\n'
        '  client: "O\'Neil & Sons"\r\n'
        "  terms: net-15\r\n"
        "  notes:\r\n"
        "    - first\r\n"
        "  rate: 175\r\n"
        'occupancy_group: [B, "S-1"]\r\n'
        "# trailing comment\r\n"
        "---\r\n# body\r\n"
    )
    facts, why = read_billing(text.encode("utf-8"))
    assert why is None
    assert facts == {"project": "260415", "client": "O'Neil & Sons", "rate": 175.0}


def test_omitted_rate_keeps_the_current_rate(fixture_drive, capsys):
    project = _project(fixture_drive, "billing:\n  project: \"250101\"\n  rate: 80\n")

    assert _billing(fixture_drive, project.name, "--project", "260415",
                    "--client", "Acme", "--yes") == 0

    out = json.loads(capsys.readouterr().out)
    assert out["billing"] == {"project": "260415", "client": "Acme", "rate": 80}
    facts, _ = read_billing((project / "PROJECT.md").read_bytes())
    assert facts == {"project": "260415", "client": "Acme", "rate": 80.0}


@pytest.mark.parametrize("kept", ["abc", "1e-05", '"60"', "-5"])
def test_omitted_rate_refuses_a_rate_pyvoid_cannot_read(fixture_drive, capsys, kept):
    project = _project(fixture_drive, f"billing:\n  project: \"250101\"\n  rate: {kept}\n")
    before = (project / "PROJECT.md").read_bytes()

    assert _billing(fixture_drive, project.name, "--project", "260415",
                    "--client", "Acme", "--yes") == 2

    assert "pass --rate" in capsys.readouterr().err
    assert (project / "PROJECT.md").read_bytes() == before
    # Passing --rate replaces it with one Pyvoid reads.
    assert _billing(fixture_drive, project.name, "--project", "260415",
                    "--client", "Acme", "--rate", "60", "--yes") == 0
    assert read_billing((project / "PROJECT.md").read_bytes())[1] is None


def test_new_children_land_after_a_literal_tail_comment(fixture_drive, capsys):
    project = _project(fixture_drive, "billing:\n  note: |\n    text\n    # c\nname: x\n")

    assert _billing(fixture_drive, project.name, "--project", "260415",
                    "--client", "Acme", "--yes") == 0

    raw = (project / "PROJECT.md").read_bytes()
    assert b'    text\r\n    # c\r\n  project: "260415"\r\n' in raw
    facts, why = read_billing(raw)
    assert why is None and facts["project"] == "260415"


def test_non_ascii_digits_and_lone_surrogates_are_refused():
    with pytest.raises(ProjectDataError, match="six-digit"):
        check_billing("٢٦٠٤١٥", "Acme", None)
    with pytest.raises(ProjectDataError, match="Unicode"):
        check_billing("260415", "Ac\ud800me", None)


def test_missing_children_are_added_at_the_blocks_indent(fixture_drive, capsys):
    project = _project(fixture_drive, "billing:\n    project: \"250101\"\nname: x\n")

    assert _billing(fixture_drive, project.name, "--project", "260415",
                    "--client", "Acme", "--rate", "60", "--yes") == 0

    text = (project / "PROJECT.md").read_bytes().decode("utf-8")
    assert '    project: "260415"\r\n    client: "Acme"\r\n    rate: 60\r\nname: x' in text
    assert read_billing(text.encode("utf-8"))[1] is None


def test_lf_and_bom_input_is_written_back_as_crlf_without_bom(fixture_drive, capsys):
    project = fixture_drive / FOLDER
    project.mkdir()
    (project / "PROJECT.md").write_bytes(b"\xef\xbb\xbf---\nproject: Oak\n---\n")

    assert _billing(fixture_drive, project.name, "--project", "260415",
                    "--client", "Acme", "--yes") == 0

    raw = (project / "PROJECT.md").read_bytes()
    assert raw == b'---\r\nproject: Oak\r\nbilling:\r\n  project: "260415"\r\n  client: "Acme"\r\n---\r\n'
    assert read_billing(raw) == ({"project": "260415", "client": "Acme", "rate": None}, None)


def test_dry_run_and_missing_yes_write_nothing(fixture_drive, capsys):
    project = _new(fixture_drive, capsys)
    before = (project / "PROJECT.md").read_bytes()
    args = ("--project", "260415", "--client", "Acme", "--rate", "60")

    assert _billing(fixture_drive, project.name, *args, "--dry-run") == 0
    assert json.loads(capsys.readouterr().out)["applied"] is False
    assert _billing(fixture_drive, project.name, *args) == 2
    assert "--yes" in capsys.readouterr().err
    assert (project / "PROJECT.md").read_bytes() == before


# -- refusals ----------------------------------------------------------------


@pytest.mark.parametrize("front, message", [
    ("billing: {project: '1'}\n", "unsupported YAML for 'billing'"),
    ("billing: 260415\n", "unsupported YAML for 'billing'"),
    ("billing:\n  project:\n    nested: 1\n", "billing.project"),
    ("billing:\n\tproject: '1'\n", "tab"),
    ("billing:\n  project: '1'\n  project: '2'\n", "duplicate YAML key 'billing.project'"),
    ("billing:\n  a: 1\nbilling:\n  b: 2\n", "duplicate YAML key 'billing'"),
    ("billing:\n    project: '1'\n  client: x\n", "inconsistent indentation"),
    ("billing:\n- a\nzed: 1\n", "a list, not a mapping"),
    ("billing:\n  # c\n- a\n", "a list, not a mapping"),
    ('"billing":\n  project: "1"\n', "plain `billing:`"),
    ("billing :\n  project: '1'\n", "plain `billing:`"),
    ("a: 1\n...\nb: 2\n", "document marker"),
    ("a: 1\n  ---\n", "document marker"),
])
def test_unreadable_shapes_are_refused_untouched(fixture_drive, capsys, front, message):
    project = _project(fixture_drive, front)
    before = (project / "PROJECT.md").read_bytes()

    assert _billing(fixture_drive, project.name, "--project", "260415",
                    "--client", "Acme", "--yes") == 2

    assert message in capsys.readouterr().err
    assert (project / "PROJECT.md").read_bytes() == before


@pytest.mark.parametrize("project, client, rate, message", [
    ("2604", "Acme", None, "six-digit"),
    ("2604150", "Acme", None, "six-digit"),
    ("260415", "  ", None, "client is required"),
    ("260415", "Ac\nme", None, "control characters"),
    ("260415", "Acme", "-5", "non-negative number"),
    ("260415", "Acme", "1e3", "non-negative number"),
    ("260415", "Acme", "nan", "non-negative number"),
    ("260415", "Acme", "abc", "non-negative number"),
])
def test_invalid_values_are_refused(project, client, rate, message):
    with pytest.raises(ProjectDataError, match=message):
        check_billing(project, client, rate)


def test_rate_is_canonical_decimal_text():
    assert check_billing("260415", "Acme", "60.00").rate == "60"
    assert check_billing("260415", "Acme", "62.50").rate == "62.5"
    assert check_billing("260415", "Acme", "0").rate == "0"
    assert check_billing("260415", "Acme", "0.0001").rate == "0.0001"


# -- the Pyvoid contract ----------------------------------------------------


@pytest.mark.parametrize("client", [
    "Acme", "O'Neil", 'Say "hi"', "Ünïcode Café", "a: b # c", "- dash", "yes", "null",
    "260415", "back\\slash", "[x]", "50% & co, {ltd}",
])
@pytest.mark.parametrize("rate", [None, "0", "60", "62.5", "150.25", "999999999.9999"])
def test_every_written_shape_parses_in_pyvoid(fixture_drive, client, rate):
    project = _project(fixture_drive, "project: Oak\n")
    values = check_billing("260415", client, rate)
    plan = plan_billing(project, values)

    facts, why = read_billing(plan._rendered)

    assert why is None
    assert facts["project"] == "260415"
    assert facts["client"] == values.client.strip()
    assert facts["rate"] == (None if rate is None else float(rate))


def test_plan_on_a_real_atlas_dossier_keeps_atlas_and_pyvoid_happy(fixture_drive, capsys):
    project = _new(fixture_drive, capsys)

    plan = plan_billing(project, BillingValues("260415", "Acme", "60"))

    facts, why = read_billing(plan._rendered)
    assert why is None and facts == {"project": "260415", "client": "Acme", "rate": 60.0}
