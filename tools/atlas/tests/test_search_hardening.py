"""Issue #96: public search, cache and executor lifecycle regressions."""

import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
import json
from pathlib import Path
import threading

import pytest
from textual.widgets import Static

from atlas.cli import main
from atlas.core.contentindex import build_index, load_index
from atlas.core.search import build_name_index
from atlas.tui.app import AtlasApp
from atlas.tui.search import SearchOverlay
from atlas.tui.treeview import ProjectTreeView
from conftest import make_project


async def settle(app, pilot):
    for _ in range(3):
        await app.workers.wait_for_complete()
        await pilot.pause()


async def test_cancelled_queued_content_build_can_retry(fixture_drive):
    """Cancel at the executor boundary, before any content callable runs."""
    make_project(fixture_drive, "260813_Test", files={"note.md": "needle"})

    class QueueFirstContent(ThreadPoolExecutor):
        held = None

        def submit(self, fn, *args, **kwargs):
            if self.held is None and args and "_content_build_worker" in repr(args[0]):
                self.held = Future()
                return self.held
            return super().submit(fn, *args, **kwargs)

    loop = asyncio.get_running_loop()
    executor = QueueFirstContent(max_workers=4)
    loop.set_default_executor(executor)
    app = AtlasApp(fixture_drive, follow_debounce=0)
    try:
        async with app.run_test() as pilot:
            async with asyncio.timeout(10):
                while executor.held is None:
                    await asyncio.sleep(0.01)
            app.workers.cancel_group(app, "content-index")
            await pilot.pause()
            assert executor.held.cancelled()
            assert load_index(fixture_drive) is None
            app.action_refresh()
            await settle(app, pilot)
            stored = load_index(fixture_drive)
            assert stored is not None and stored.complete
            await pilot.press("g")
            await pilot.pause()
            line = str(app.screen.query_one("#search-content", Static).content)
            assert "indexed" in line and "building" not in line
    finally:
        loop.set_default_executor(ThreadPoolExecutor())
        executor.shutdown(wait=True, cancel_futures=True)


@pytest.mark.parametrize("interrupt", [False, True])
def test_live_checkpoint_cannot_downgrade_cli_complete_cache(fixture_drive, capsys, interrupt):
    make_project(fixture_drive, "260813_Test", files={
        f"note-{i}.md": "needle" for i in range(3)
    })
    checkpoint_seen = []

    def progress(done, total):
        if done == 1:
            assert main(["index", "build", "--drive", str(fixture_drive), "--json"]) == 0
            capsys.readouterr()
        if done == 2:
            # The first periodic save has happened after the CLI finished.
            assert main(["index", "status", "--drive", str(fixture_drive), "--json"]) == 0
            checkpoint_seen.append(json.loads(capsys.readouterr().out))
            if interrupt:
                raise InterruptedError("stop live build")

    if interrupt:
        with pytest.raises(InterruptedError):
            build_index(fixture_drive, progress=progress, save_every=1)
    else:
        build_index(fixture_drive, progress=progress, save_every=1)
    assert checkpoint_seen[0]["complete"] is True
    stored = load_index(fixture_drive)
    assert stored.complete and len(stored.files) == 3


def test_cli_partial_status_names_the_readable_checkpoint(fixture_drive, capsys):
    make_project(fixture_drive, "260813_Test", files={"note.md": "needle"})

    def stop(done, total):
        raise InterruptedError("checkpoint")

    with pytest.raises(InterruptedError):
        build_index(fixture_drive, progress=stop)
    assert main(["index", "status", "--drive", str(fixture_drive), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["exists"] and not payload["complete"]
    saved = json.loads(Path(payload["path"]).read_text(encoding="utf-8"))
    assert saved["complete"] is False and len(saved["files"]) == 1


def test_interrupted_topup_reuses_checkpoint_keys(fixture_drive, monkeypatch):
    import builtins

    project = make_project(fixture_drive, "260813_Test", files={"note.md": "old"})
    build_index(fixture_drive)
    (project / "note.md").write_text("new needle", encoding="utf-8")

    def stop(done, total):
        raise InterruptedError("after extraction")

    with pytest.raises(InterruptedError):
        build_index(fixture_drive, progress=stop)

    real_open = builtins.open

    def no_reread(path, *args, **kwargs):
        if str(path) == str(project / "note.md") and args and args[0] == "rb":
            pytest.fail("checkpoint key should avoid a second content read")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", no_reread)
    index = build_index(fixture_drive)
    assert index.complete and index.files[0].text == "new needle"


def test_concurrent_builds_publish_their_own_atomic_bytes(fixture_drive, monkeypatch):
    import os

    make_project(fixture_drive, "260813_Test", files={"note.md": "needle"})
    rendezvous = threading.Barrier(2)
    replace = os.replace
    publish = threading.Lock()

    def simultaneous_replace(source, destination):
        rendezvous.wait(timeout=10)
        with publish:
            return replace(source, destination)

    monkeypatch.setattr(os, "replace", simultaneous_replace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        builds = [pool.submit(build_index, fixture_drive) for _ in range(2)]
        for build in builds:
            assert build.result(timeout=15).complete
    assert load_index(fixture_drive).complete


async def test_cancelled_running_thread_keeps_single_builder(fixture_drive, monkeypatch):
    import builtins

    project = make_project(fixture_drive, "260813_Test", files={"note.md": "needle"})
    started, release = threading.Event(), threading.Event()
    reads = []
    real_open = builtins.open

    def blocked_open(path, *args, **kwargs):
        if str(path) == str(project / "note.md") and args and args[0] == "rb":
            reads.append(path)
            started.set()
            assert release.wait(15)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", blocked_open)
    app = AtlasApp(fixture_drive, follow_debounce=0)
    try:
        async with app.run_test() as pilot:
            async with asyncio.timeout(10):
                while not started.is_set():
                    await asyncio.sleep(0.01)
            app.workers.cancel_group(app, "content-index")
            await pilot.pause()
            app.action_refresh()
            await settle(app, pilot)
            assert len(reads) == 1
            release.set()
            async with asyncio.timeout(10):
                while load_index(fixture_drive) is None:
                    await asyncio.sleep(0.01)
            await pilot.press("g")
            await pilot.pause()
            assert "indexed" in str(app.screen.query_one("#search-content", Static).content)
            assert len(reads) == 1
    finally:
        release.set()


async def test_refresh_after_failed_callback_can_retry_before_thread_returns(fixture_drive, monkeypatch):
    import builtins

    project = make_project(fixture_drive, "260813_Test", files={"note.md": "needle"})
    failed, release = threading.Event(), threading.Event()
    real_open = builtins.open
    first = True

    def fail_once(path, *args, **kwargs):
        nonlocal first
        if first and str(path) == str(project / "note.md") and args and args[0] == "rb":
            first = False
            raise RuntimeError("injected extraction failure")
        return real_open(path, *args, **kwargs)

    app = AtlasApp(fixture_drive, follow_debounce=0)
    dispatch = app.call_from_thread

    def hold_after_failure(callback, *args, **kwargs):
        result = dispatch(callback, *args, **kwargs)
        if callback.__name__ == "_content_failed":
            failed.set()
            assert release.wait(15)
        return result

    monkeypatch.setattr(builtins, "open", fail_once)
    monkeypatch.setattr(app, "call_from_thread", hold_after_failure)
    try:
        async with app.run_test() as pilot:
            async with asyncio.timeout(10):
                while not failed.is_set():
                    await asyncio.sleep(0.01)
            app.workers.cancel_group(app, "content-index")
            await pilot.pause()
            app.action_refresh()
            await settle(app, pilot)
            assert load_index(fixture_drive).complete
    finally:
        release.set()


@pytest.mark.parametrize("width", [46, 77, 120])
async def test_stale_and_unchecked_counts_survive_narrow_search(fixture_drive, width, monkeypatch):
    import os

    project = make_project(fixture_drive, "260813_Test", files={
        f"note-{i:03}.md": "needle" for i in range(300)
    })
    index = build_index(fixture_drive)
    names = build_name_index(fixture_drive)
    for i in range(200):
        (project / f"note-{i:03}.md").unlink()
    app = AtlasApp(fixture_drive, follow_debounce=0)
    async with app.run_test(size=(width, 24)) as pilot:
        await settle(app, pilot)
        overlay = SearchOverlay(names, content_index=index)
        app.push_screen(overlay)
        await pilot.pause()
        stats = []
        stat = os.stat

        def count(path, *args, **kwargs):
            if "note-" in str(path):
                stats.append(path)
            return stat(path, *args, **kwargs)

        monkeypatch.setattr(os, "stat", count)
        await pilot.press("n")
        await pilot.pause()
        assert len(stats) == 200, "bounded stale-match budget per keystroke"
        line = str(overlay.query_one("#search-content", Static).content)
        assert "200 stale" in line and "100 unchecked" in line
        assert "…" not in line
        assert len(line) <= overlay.query_one("#search-content").size.width


@pytest.mark.parametrize("hours, expected", [
    (-8, "2026-11-09 17:30 -0800"),
    (0, "2026-11-10 01:30 +0000"),
    (5.5, "2026-11-10 07:00 +0530"),
])
async def test_index_stamp_identifies_its_display_timezone(fixture_drive, monkeypatch, hours, expected):
    from dataclasses import replace
    from datetime import datetime, timedelta, timezone
    import atlas.tui.search as search

    class LocalClock(datetime):
        def astimezone(self, tz=None):
            return super().astimezone(timezone(timedelta(hours=hours)))

    monkeypatch.setattr(search, "datetime", LocalClock)
    make_project(fixture_drive, "260813_Test", files={"note.md": "needle"})
    index = replace(build_index(fixture_drive), indexed_at="2026-11-10T01:30:00+00:00")
    app = AtlasApp(fixture_drive, follow_debounce=0)
    async with app.run_test(size=(120, 24)) as pilot:
        await settle(app, pilot)
        overlay = SearchOverlay(build_name_index(fixture_drive), content_index=index)
        app.push_screen(overlay)
        await pilot.pause()
        assert expected in str(overlay.query_one("#search-content", Static).content)


async def test_follow_callback_with_screen_present_but_tree_removed(fixture_drive, monkeypatch):
    make_project(fixture_drive, "260813_Alpha", sections=["01 Model"])
    make_project(fixture_drive, "260813_Beta", sections=["01 Model"])
    app = AtlasApp(fixture_drive, follow_debounce=60)
    callbacks = []
    set_timer = app.set_timer

    def record_timer(delay, callback, *args, **kwargs):
        if delay == 60:
            callbacks.append(callback)
        return set_timer(delay, callback, *args, **kwargs)

    monkeypatch.setattr(app, "set_timer", record_timer)
    async with app.run_test() as pilot:
        await settle(app, pilot)
        await pilot.press("down")
        await pilot.pause()
        assert callbacks
        screen = app.screen
        await screen.query_one(ProjectTreeView).remove()
        assert app.screen is screen and not screen.query(ProjectTreeView)
        callbacks[-1]()
        await pilot.pause()
        assert app.screen is screen
        assert app.query_one("#projects").row_count == 2
