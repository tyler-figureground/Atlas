# Render scripts

Headless renders of the console, for looking at the screen rather than asserting
on what the app believes about it.

**These are not tests and they are not Atlas code.** They exist because a green
suite has now missed a real defect in three consecutive sessions, and every one of
those was invisible to a test and obvious in one look:

- Session 8 - readness and expansion shared a glyph, so every closed folder the
  Companion had prefetched drew an open triangle.
- Session 9, ticket 10 - a Loose file and an Unfiled file were separated by hue
  alone at every width, because `node_label` returned early for a file.
- Session 9, ticket 23 - the Tree Region could not take keyboard focus at all, so
  the tree widget was unreachable by keyboard while sixteen widget tests passed.

The pattern is consistent: tests assert on the state the app *believes*
(`_focus_region`, `display`, a Filing State) and not on what the screen draws or
what the keyboard actually reaches.

## Use

Never point these at the studio drive or any shared drive. Build a throwaway
fixture first.

```bash
cd tools/atlas
PYTHONUTF8=1 uv run python scripts/build_fixture_drive.py /tmp/testdrive

# the tree at the measured widths - 179, 153, 120, 87, 77, 59, 46 - and either
# side of the 30-row boundary where summary and operation merge
PYTHONUTF8=1 uv run python scripts/render_tree.py /tmp/testdrive

# the whole repair flow, keys only, operation line after each step
PYTHONUTF8=1 uv run python scripts/render_repair_flow.py /tmp/testdrive 87
```

`uv run` is required: `atlas` is not importable otherwise.

The fixture drive carries one project with all four repairable Filing States on
it - a Drifted folder, a Misplaced one, a Loose file, and an Unfiled folder - plus
a second, near-empty project. `11 Meetings` exists alongside `Meetings`
deliberately, so the rename is a **merge**: the plain-rename case hides the bug
class where an Action's manifest names children rather than the folder itself.
