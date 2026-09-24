# File Rules - the map files a loose file by what it is

Type: task
Status: resolved
Blocked by: -
Parent: ../map.md

## Question

Graduated from the fog item **file-level action set**, and from
`docs/research/atlas-file-management-oss.md`, which asked which open-source project
Atlas should adopt to get stronger at organizing files.

Atlas conforms folders. The only file it could move was one a glob in `relocations`
named. Everything else at a project root is Unfiled and waits for a person.

Give the map a way to say "a root file that looks like this belongs there", including
by what is **inside** the file - a permit set says ISSUED FOR PERMIT in its title
block, and no glob on a filename will ever catch that.

## Constraints

- The design comes from organize (tfeldmann/organize, MIT). Its **code** does not:
  it carries its own config file and performs its own moves, and the drive map is the
  only brain while every Atlas write crosses a Plan.
- ADR 0006 stands: no new Action kind. A rule's output is the SWEEP that Loose already
  earns, so conform, the repair key, the Guard, the Move Manifest and undo are
  untouched.
- ADR 0004 stands: Loose is a Filing State of *files*.
- Reading a file on the Drive mount downloads it. Content is the last thing evaluated
  and the first thing bounded.
- Never the control plane. A rule for `*.md` must not file `PROJECT.md` away.
- Fixture drives only.

## Resolution

Built test-first. 47 new tests, `docs/adr/0009`, vocabulary in `/CONTEXT.md` under
**Atlas File Rules**.

- `fileRules` in the map: `name`, `target`, and a `match` of `extensions`, `names`,
  `nameRegex`, `pdfText`. Filters AND, values within a filter OR, first rule wins,
  after the glob relocations.
- `core/content.py` - the one module that opens a file. pypdf, 64 MB limit, cached by
  path + size + mtime, `.pdf` only, silent on damaged input.
- `core/filerules.py` - matching, name filters before content, pure otherwise.
- A malformed rule refuses the whole map in `load_map` rather than being skipped by
  lint. A misspelled filter key that was merely ignored would widen its rule, and a
  rule that matches more moves more.
- `doctor` attributes each sweep to the rule that made it, in text, in `--json`, and
  in the console's project detail.

Two things found by building rather than deciding:

- **Most issued sets are encrypted.** Not with a password - with permissions, which
  Acrobat writes as AES. `pypdf[crypto]` is therefore a dependency, and an empty
  password is tried before giving up. Without it the headline use case silently
  matches nothing.
- **pytest cannot see a logging leak.** pypdf prints `EOF marker not found` to stderr
  through the last-resort handler, which under the console draws over the screen. An
  in-process test passes whether or not Atlas silences it, because pytest attaches its
  capture handlers to non-propagating loggers too. The regression test is a subprocess.

Also fixed while in the area: the operation line reported a finished repair in the
model's vocabulary (`sweep`) rather than the operator's (`file`), and undoing a sweep
printed an arrow pointing at an empty string instead of naming the project root.
`tui/repair.result_line`, with tests.
