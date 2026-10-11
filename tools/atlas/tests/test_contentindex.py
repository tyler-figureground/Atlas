"""The per-machine Content Index and `atlas index` (ticket 34, ADR 0020).

PDF text and Markdown under the project roots, extracted over the mount and
cached on the local machine - never on the drive - keyed by path+size+mtime
(the ADR 0009 cache key). First build reads every candidate; later builds
re-read only what changed. Damaged and oversized files are skipped silently
(ADR 0009). Fixture drives only; the cache dir is always a test tmp path.
"""

from __future__ import annotations

import json
import os

import pytest

from atlas import cli
from atlas.cli import main
from atlas.core import contentindex
from atlas.core.contentindex import (
    READ_LIMIT,
    TOO_LARGE,
    UNREADABLE,
    build_index,
    index_path,
    load_index,
    query_index,
)

from conftest import make_pdf, make_project, write_map


@pytest.fixture()
def cache_dir(tmp_path, monkeypatch):
    """Every test's index lives in a tmp cache, and the CLI's env override
    points there too - the suite never touches the machine's real cache."""
    cache = tmp_path / "atlas-cache"
    monkeypatch.setenv(contentindex.CACHE_ENV_VAR, str(cache))
    return cache


def _drive(drive):
    make_project(drive, "260813_Alpha",
                 sections=["01 Model", "06 Research/Code"],
                 files={"06 Research/Code/zoning notes.md": "Zoning  Variance\n\nAPPROVED",
                        "01 Model/model notes.txt": "grid lines and levels",
                        "01 Model/site model.rvt": "x"})
    make_pdf(drive / "260813_Alpha" / "PERMIT-set.pdf",
             text="A-101 LEVEL ONE PLAN", title="ISSUED FOR PERMIT")
    make_project(drive, "260901_Beta",
                 sections=["11 Meetings"],
                 files={"11 Meetings/minutes.markdown": "client approved the scheme",
                        "BRIEF.md": "Now: schematic design"})


def _extract_spy(monkeypatch):
    """A counting wrapper over the one extraction chokepoint, ticket 05 probe
    style: a re-read the index did not need is a download on the real mount."""
    real = contentindex._extract
    reads = []

    def counting(path, kind):
        reads.append(path)
        return real(path, kind)

    monkeypatch.setattr(contentindex, "_extract", counting)
    return reads


# ------------------------------------------------------------- the build


def test_first_build_indexes_every_pdf_and_markdown(fixture_drive, cache_dir):
    _drive(fixture_drive)
    index = build_index(fixture_drive, cache_dir=cache_dir)
    by_path = {f.path: f for f in index.files}

    assert set(by_path) == {
        "260813_Alpha/06 Research/Code/zoning notes.md",
        "260813_Alpha/01 Model/model notes.txt",
        "260813_Alpha/PERMIT-set.pdf",
        "260901_Beta/11 Meetings/minutes.markdown",
        "260901_Beta/BRIEF.md",
    }
    # The `.rvt` is not a content candidate; it is never opened.
    assert by_path["260813_Alpha/PERMIT-set.pdf"].kind == "pdf"
    assert by_path["260813_Alpha/06 Research/Code/zoning notes.md"].kind == "markdown"
    assert by_path["260813_Alpha/01 Model/model notes.txt"].kind == "text"
    # Extraction is the ADR 0009 machinery: metadata plus page one, normalised.
    assert "issued for permit" in by_path["260813_Alpha/PERMIT-set.pdf"].text
    assert "a-101 level one plan" in by_path["260813_Alpha/PERMIT-set.pdf"].text
    assert by_path["260813_Alpha/06 Research/Code/zoning notes.md"].text == \
        "zoning variance approved"
    # The Indexed-At Stamp rides every build.
    assert index.indexed_at
    assert index.drive == "TESTDRIVE"


def test_the_build_walks_project_roots_only(fixture_drive, cache_dir):
    _drive(fixture_drive)
    archived = fixture_drive / "_Archived Projects" / "260101_Old"
    archived.mkdir(parents=True)
    (archived / "keep.md").write_text("zoning", encoding="utf-8")

    index = build_index(fixture_drive, cache_dir=cache_dir)
    assert not any("_Archived Projects" in f.path or f.path.startswith("_")
                   for f in index.files)


def test_second_build_rereads_only_touched_files(fixture_drive, cache_dir, monkeypatch):
    """The whole point of the key: an incremental top-up never re-downloads an
    unchanged file. Asserted on read counts, not on timings."""
    _drive(fixture_drive)
    reads = _extract_spy(monkeypatch)

    build_index(fixture_drive, cache_dir=cache_dir)
    assert len(reads) == 5

    reads.clear()
    build_index(fixture_drive, cache_dir=cache_dir)
    assert reads == []

    # Touch one file, add one new: exactly those two are re-read.
    notes = fixture_drive / "260813_Alpha" / "06 Research/Code" / "zoning notes.md"
    notes.write_text("Zoning Variance APPROVED - revised", encoding="utf-8")
    make_pdf(fixture_drive / "260901_Beta" / "sketches.pdf", text="scheme b")

    reads.clear()
    index = build_index(fixture_drive, cache_dir=cache_dir)
    assert len(reads) == 2
    assert len(index.files) == 6
    assert "revised" in next(
        f.text for f in index.files if f.path.endswith("zoning notes.md"))


def test_a_touched_file_with_the_same_size_is_still_reread(
        fixture_drive, cache_dir, monkeypatch):
    """Size alone is not the key: same length, new mtime, new bytes."""
    _drive(fixture_drive)
    build_index(fixture_drive, cache_dir=cache_dir)
    notes = fixture_drive / "260901_Beta" / "BRIEF.md"
    assert notes.read_text(encoding="utf-8") == "Now: schematic design"
    notes.write_text("Now: DD pricing begins", encoding="utf-8")  # same length

    reads = _extract_spy(monkeypatch)
    index = build_index(fixture_drive, cache_dir=cache_dir)
    assert len(reads) == 1
    brief = next(f for f in index.files if f.path == "260901_Beta/BRIEF.md")
    assert "pricing" in brief.text


def test_a_damaged_pdf_is_skipped_silently(fixture_drive, cache_dir, capsys):
    _drive(fixture_drive)
    (fixture_drive / "260813_Alpha" / "scan.pdf").write_bytes(b"definitely not a pdf")
    (fixture_drive / "260813_Alpha" / "truncated.pdf").write_bytes(
        b"%PDF-1.4\n1 0 obj << /Type /Catalog >>")

    index = build_index(fixture_drive, cache_dir=cache_dir)
    skipped = {s.path: s for s in index.skipped}

    assert skipped["260813_Alpha/scan.pdf"].reason == UNREADABLE
    assert skipped["260813_Alpha/truncated.pdf"].reason == UNREADABLE
    assert not any(f.path.endswith(("scan.pdf", "truncated.pdf")) for f in index.files)
    # Silence: nothing on stdout or stderr, no exception (ADR 0009).
    assert capsys.readouterr() == ("", "")
    # And excluded from matches.
    assert query_index(index, "scan").hits == ()


def test_a_pdf_over_the_read_limit_is_skipped_never_opened(
        fixture_drive, cache_dir, monkeypatch):
    _drive(fixture_drive)
    big = fixture_drive / "260813_Alpha" / "as-builts.pdf"
    big.write_bytes(b"%PDF-1.4\n" + b"0" * (65 * 1024 * 1024))

    def forbidden(*args, **kwargs):  # a 65 MB download must never start
        raise AssertionError("PdfReader opened an over-limit file")

    monkeypatch.setattr(contentindex.content, "PdfReader", forbidden)
    contentindex.content.clear_cache()

    index = build_index(fixture_drive, cache_dir=cache_dir)
    skipped = {s.path: s for s in index.skipped}
    assert skipped["260813_Alpha/as-builts.pdf"].reason == TOO_LARGE
    assert skipped["260813_Alpha/as-builts.pdf"].size == big.stat().st_size


def test_markdown_over_the_limit_is_skipped(fixture_drive, cache_dir, monkeypatch):
    """The Read Limit is one number for every kind - no size surprise."""
    _drive(fixture_drive)
    huge = fixture_drive / "260901_Beta" / "log.md"
    huge.write_text("x" * 2048, encoding="utf-8")
    monkeypatch.setattr(contentindex, "READ_LIMIT", 1024)

    index = build_index(fixture_drive, cache_dir=cache_dir)
    skipped = {s.path: s for s in index.skipped}
    assert skipped["260901_Beta/log.md"].reason == TOO_LARGE


def test_skipped_files_are_not_retried_until_they_change(
        fixture_drive, cache_dir, monkeypatch):
    """A damaged file is skipped with its key, so a top-up does not download it
    again every run. It is retried when it changes - the fix might be a re-export."""
    _drive(fixture_drive)
    broken = fixture_drive / "260813_Alpha" / "scan.pdf"
    broken.write_bytes(b"definitely not a pdf")
    build_index(fixture_drive, cache_dir=cache_dir)

    reads = _extract_spy(monkeypatch)
    build_index(fixture_drive, cache_dir=cache_dir)
    assert reads == []

    make_pdf(broken, text="now it opens", title="REISSUED")
    build_index(fixture_drive, cache_dir=cache_dir)
    assert len(reads) == 1
    index = load_index(fixture_drive, cache_dir=cache_dir)
    assert any(f.path.endswith("scan.pdf") and "reissued" in f.text
               for f in index.files)


def test_nothing_is_written_to_the_drive(fixture_drive, cache_dir):
    _drive(fixture_drive)
    before = {os.path.relpath(p, fixture_drive): os.stat(p).st_size
              for p in fixture_drive.rglob("*") if p.is_file()}

    build_index(fixture_drive, cache_dir=cache_dir)

    after = {os.path.relpath(p, fixture_drive): os.stat(p).st_size
             for p in fixture_drive.rglob("*") if p.is_file()}
    assert after == before
    assert not str(index_path(fixture_drive, cache_dir)).startswith(str(fixture_drive))


def test_a_corrupt_index_rebuilds_never_crashes(fixture_drive, cache_dir, monkeypatch):
    _drive(fixture_drive)
    build_index(fixture_drive, cache_dir=cache_dir)
    path = index_path(fixture_drive, cache_dir)
    path.write_bytes(b"{ not json, honestly")

    assert load_index(fixture_drive, cache_dir=cache_dir) is None

    reads = _extract_spy(monkeypatch)
    index = build_index(fixture_drive, cache_dir=cache_dir)
    assert len(reads) == 5  # a full rebuild, not a failure
    assert len(index.files) == 5


def test_an_index_from_another_schema_or_root_is_ignored(fixture_drive, cache_dir):
    _drive(fixture_drive)
    build_index(fixture_drive, cache_dir=cache_dir)
    path = index_path(fixture_drive, cache_dir)
    payload = json.loads(path.read_text(encoding="utf-8"))

    payload["schema"] = 999
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_index(fixture_drive, cache_dir=cache_dir) is None

    payload["schema"] = contentindex.SCHEMA
    payload["root"] = "Z:\\somewhere\\else"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_index(fixture_drive, cache_dir=cache_dir) is None


def test_the_index_is_keyed_per_drive_root(tmp_path, cache_dir):
    drive_a = tmp_path / "DRIVEA"
    drive_b = tmp_path / "DRIVEB"
    for drive, word in ((drive_a, "alpha zoning"), (drive_b, "beta zoning")):
        drive.mkdir()
        write_map(drive)
        make_project(drive, "260813_Proj", files={"notes.md": word})

    index_a = build_index(drive_a, cache_dir=cache_dir)
    index_b = build_index(drive_b, cache_dir=cache_dir)

    assert index_path(drive_a, cache_dir) != index_path(drive_b, cache_dir)
    assert "alpha" in index_a.files[0].text and "beta" in index_b.files[0].text
    # Loading one never returns the other.
    assert load_index(drive_a, cache_dir=cache_dir).files[0].text.startswith("alpha")


def test_unreadable_folders_are_recorded_never_swallowed(
        fixture_drive, cache_dir, monkeypatch):
    _drive(fixture_drive)
    target = str(fixture_drive / "260813_Alpha" / "06 Research")
    real_scandir = os.scandir

    def denying(path, *args, **kwargs):
        if os.fspath(path) == target:
            raise PermissionError(5, "Access is denied", target)
        return real_scandir(path, *args, **kwargs)

    monkeypatch.setattr(os, "scandir", denying)
    index = build_index(fixture_drive, cache_dir=cache_dir)

    unreadable = dict(index.unreadable)
    assert "260813_Alpha/06 Research" in unreadable
    # The rest of the drive was still indexed.
    assert any(f.path == "260901_Beta/BRIEF.md" for f in index.files)


def test_an_interrupted_build_saves_what_it_extracted(
        fixture_drive, cache_dir, monkeypatch):
    """Resumable by key: a build cut off mid-run leaves a partial index, and
    the next run re-reads only what the interrupted one never reached."""
    _drive(fixture_drive)
    real = contentindex._extract
    calls = []

    def dying(path, kind):
        if len(calls) == 2:
            raise KeyboardInterrupt
        calls.append(path)
        return real(path, kind)

    monkeypatch.setattr(contentindex, "_extract", dying)
    with pytest.raises(KeyboardInterrupt):
        build_index(fixture_drive, cache_dir=cache_dir)

    partial = load_index(fixture_drive, cache_dir=cache_dir)
    assert partial is not None
    assert len(partial.files) == 2
    assert partial.indexed_at  # the stamp is honest: a partial build, stamped

    monkeypatch.setattr(contentindex, "_extract", real)
    reads = _extract_spy(monkeypatch)
    index = build_index(fixture_drive, cache_dir=cache_dir)
    assert len(reads) == 3
    assert len(index.files) == 5


def test_progress_is_reported_as_done_over_total(fixture_drive, cache_dir):
    _drive(fixture_drive)
    seen = []
    build_index(fixture_drive, cache_dir=cache_dir,
                progress=lambda done, total: seen.append((done, total)))
    assert seen[-1] == (5, 5)
    assert all(total == 5 for _done, total in seen)


# ------------------------------------------------------------- the query


def test_query_matches_normalised_text_across_kinds(fixture_drive, cache_dir):
    _drive(fixture_drive)
    index = build_index(fixture_drive, cache_dir=cache_dir)

    pdf = query_index(index, "ISSUED FOR   PERMIT")
    assert [h.path for h in pdf.hits] == ["260813_Alpha/PERMIT-set.pdf"]
    assert pdf.hits[0].kind == "pdf" and pdf.hits[0].project == "260813_Alpha"

    md = query_index(index, "zoning variance")
    assert [h.path for h in md.hits] == ["260813_Alpha/06 Research/Code/zoning notes.md"]

    # The scheme is in minutes.markdown and nowhere else.
    assert [h.path for h in query_index(index, "approved the scheme").hits] == [
        "260901_Beta/11 Meetings/minutes.markdown"]


def test_query_revalidates_candidates_by_key(fixture_drive, cache_dir):
    """Query-time freshness: a file whose key changed since the build is
    excluded and counted stale, never silently trusted (ticket 08)."""
    _drive(fixture_drive)
    index = build_index(fixture_drive, cache_dir=cache_dir)

    notes = fixture_drive / "260813_Alpha" / "06 Research/Code" / "zoning notes.md"
    notes.write_text("appeal filed", encoding="utf-8")
    result = query_index(index, "zoning variance")
    assert result.hits == ()
    assert result.stale == 1

    # A deleted file is stale too - absence is a failed revalidation.
    index = build_index(fixture_drive, cache_dir=cache_dir)
    notes.unlink()
    result = query_index(index, "appeal")
    assert result.hits == () and result.stale == 1

    # Untouched candidates still hit.
    assert query_index(index, "issued for permit").total == 1


def test_a_blank_query_matches_nothing(fixture_drive, cache_dir):
    _drive(fixture_drive)
    result = query_index(build_index(fixture_drive, cache_dir=cache_dir), "   ")
    assert result.hits == () and result.total == 0 and result.stale == 0


def test_query_results_cap_and_count_the_overflow(fixture_drive, cache_dir):
    project = make_project(fixture_drive, "260813_Full", sections=["08 OUT"])
    for i in range(12):
        (project / "08 OUT" / f"sheet {i:02}.md").write_text(
            f"transmittal sheet {i}", encoding="utf-8")

    index = build_index(fixture_drive, cache_dir=cache_dir)
    result = query_index(index, "transmittal", cap=5)
    assert len(result.hits) == 5
    assert result.total == 12
    assert result.overflow == 7


# ------------------------------------------------------------- the CLI


def _build(drive, capsys, *extra):
    status = main(["index", "build", *extra, "--drive", str(drive)])
    return status, capsys.readouterr()


def test_cli_status_before_any_build_exits_1(fixture_drive, cache_dir, capsys):
    _drive(fixture_drive)
    status = main(["index", "status", "--drive", str(fixture_drive)])
    out = capsys.readouterr().out
    assert status == 1
    assert "no content index" in out.casefold()
    assert "atlas index build" in out


def test_cli_build_then_status(fixture_drive, cache_dir, capsys):
    _drive(fixture_drive)
    status, captured = _build(fixture_drive, capsys)
    assert status == 0
    assert "5 files" in captured.out
    assert "indexed at" in captured.out.casefold()

    status = main(["index", "status", "--drive", str(fixture_drive)])
    out = capsys.readouterr().out
    assert status == 0
    assert "5 files" in out

    # A second build is a top-up: it says so.
    status, captured = _build(fixture_drive, capsys)
    assert status == 0
    assert "0 read" in captured.out


def test_cli_build_writes_nothing_to_the_drive(fixture_drive, cache_dir, capsys):
    _drive(fixture_drive)
    before = {os.path.relpath(p, fixture_drive) for p in fixture_drive.rglob("*")}
    assert _build(fixture_drive, capsys)[0] == 0
    after = {os.path.relpath(p, fixture_drive) for p in fixture_drive.rglob("*")}
    assert after == before


def test_cli_json_shapes(fixture_drive, cache_dir, capsys):
    _drive(fixture_drive)
    status = main(["index", "status", "--json", "--drive", str(fixture_drive)])
    payload = json.loads(capsys.readouterr().out)
    assert status == 1
    assert payload["exists"] is False

    status = main(["index", "build", "--json", "--drive", str(fixture_drive)])
    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["drive"] == "TESTDRIVE"
    assert payload["files"] == 5 and payload["read"] == 5
    assert payload["skipped"] == 0 and payload["unreadable"] == 0
    assert payload["indexed_at"]
    assert payload["path"].endswith(".json")
    assert not payload["path"].startswith(str(fixture_drive))

    status = main(["index", "status", "--json", "--drive", str(fixture_drive)])
    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["exists"] is True and payload["files"] == 5


def test_cli_errors_exit_2(fixture_drive, cache_dir, capsys, tmp_path):
    stray = tmp_path / "STRAY"
    stray.mkdir()
    assert main(["index", "build", "--drive", str(stray)]) == 2
    capsys.readouterr()
    assert main(["index", "status", "--drive", str(stray)]) == 2
