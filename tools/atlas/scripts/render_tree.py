"""Render the Tree Region headless at the measured widths.

Drills from the Project List into the Tree so the tree is actually on screen,
which the generic console renderer does not do.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from atlas.tui.app import AtlasApp

SIZES = [(179, 51), (153, 51), (120, 51), (87, 51), (77, 51), (59, 51), (46, 51),
         (120, 30), (120, 29), (46, 29)]


async def render(drive: Path, width: int, height: int) -> str:
    app = AtlasApp(drive, follow_debounce=0)
    async with app.run_test(size=(width, height)) as pilot:
        for _ in range(3):
            await app.workers.wait_for_complete()
            await pilot.pause()
        await pilot.press("enter")          # Project List -> Tree Region
        for _ in range(3):
            await app.workers.wait_for_complete()
            await pilot.pause()
        lines = []
        for strip_ in app.screen._compositor.render_strips():
            lines.append("".join(seg.text for seg in strip_).rstrip())
        return "\n".join(lines)


async def main() -> None:
    drive = Path(sys.argv[1])
    for width, height in SIZES:
        body = await render(drive, width, height)
        print("=" * min(width, 100))
        print(f"### {width} x {height}")
        print("=" * min(width, 100))
        print(body)
        print()


asyncio.run(main())
