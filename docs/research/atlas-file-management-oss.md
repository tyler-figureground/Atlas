---
title: "Research: open-source file management and organization for Atlas"
date: 2026-09-10
generated_by: skills-for-architects
---

# Research: open-source file management and organization for Atlas

Research snapshot: September 2026. Question asked: which open-source projects could
Atlas download and use to become much stronger at managing, organizing and conforming
studio files and folders. Target is the Atlas Tyler runs: `tools/atlas`, Python 3.12,
`textual>=8.2,<9` (resolved 8.2.8), MIT-licensed repo, Windows 11, Google Shared
Drives through the Drive for Desktop mount.

This file is the pickup point. The **Implementation backlog** section at the end is
the living part: it says what has been built, what is next, and what is deliberately
deferred and why. Update its status column when a row moves.

## Confidence tiers

- **Primary** - the project's own repository, docs, or package index page, read this
  session.
- **Primary-local** - measured or executed here, against the Atlas venv.
- **Secondary** - third-party article or benchmark, read this session.
- **Memory** - not re-verified this session. Recheck before depending on it.

## Executive finding

- [HIGH | Primary-local] **The filter that decides everything is Atlas's write path,
  not the candidate's quality.** Every Atlas write crosses a `Plan`, is previewed,
  confirmed, re-checked by a `Guard`, logged, and reversible through its Move Manifest
  (ADR 0006, ADR 0007). A tool that mutates the drive on its own - its own rename, its
  own undo, its own delete - bypasses all of that and breaks `conform --revert`. So:
  - **Read-only tools plug in directly.** They produce facts; Atlas turns facts into
    Plans. PDF readers, DXF readers, type sniffers, duplicate *reporters*.
  - **Mutating tools get their design ported, never their code called.** organize's
    rule vocabulary, f2's preview-first rename, fclones' dedupe *actions*.
- [HIGH | Primary-local] **The best first move was `pypdf` plus an organize-style
  `fileRules` block in the drive map.** Built this session - see ADR 0009 and ticket
  25. It moves Atlas from conforming folders to conforming files, and it needed zero
  new write code because a rule's output is the SWEEP action conform already had.

## Candidates, by how they fit

### Adopt - read-only libraries under Atlas

- [HIGH | Primary] **pypdf** - BSD-3-Clause, pure Python (py3-none-any wheel).
  Resolved 6.18.0 (2026-09-07). Reads PDF metadata and page text.
  **Adopted** as `pypdf[crypto]>=6.18,<7`; used by `atlas.core.content`.
  [PyPI](https://pypi.org/project/pypdf/) ·
  [license comparison](https://www.nutrient.io/blog/best-python-pdf-libraries/)
- [HIGH | Primary-local] pypdf behaviour measured against the Atlas venv:
  - A hand-built one-page PDF with a Type1 Helvetica content stream extracts exactly
    (`'ISSUED FOR PERMIT  Sheet A-101'`), and `/Title` reads from the Info dict.
  - Malformed and truncated files raise `PdfStreamError`. Any exception type is
    possible on damaged input, so `content.pdf_text` catches broadly and returns None.
  - **pypdf prints `EOF marker not found` to stderr on a damaged file** through the
    `logging` module's last-resort handler. Under the Textual console that draws over
    the screen. Silenced in `atlas.core.content` on import (NullHandler plus
    `propagate = False`), each line proven necessary by a test that fails without it.
  - **pytest cannot see that leak.** It attaches its capture handlers to
    non-propagating loggers too, so an in-process test passes whether or not Atlas
    silenced pypdf. The regression test runs a subprocess.
  - RC4 encryption works without extra dependencies; AES needs `cryptography`. An
    empty-password (permission-only) lock is the normal state of an issued drawing set,
    and Acrobat locks with AES by default, hence the `[crypto]` extra
    (`cryptography` 50.0.1, Apache-2.0/BSD, wheels for Windows).
- [HIGH | Secondary] **Avoid PyMuPDF.** AGPL-3.0: shipping it inside Atlas would force
  AGPL terms on Atlas or require a commercial licence from Artifex. It is 8-12x faster
  than pdfplumber on text extraction, which does not matter for first-page reads.
  [AGPL explainer](https://www.file2markdown.ai/blog/is-pymupdf-free-for-commercial-use) ·
  [speed vs licence](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/)
- [HIGH | Secondary] **pdfplumber** - MIT. Tables and positioned text. Only worth adding
  if a rule ever needs *where* on the page a phrase sits (title block region), which
  pypdf's flat text cannot say.
- [HIGH | Primary] **ezdxf** - MIT, 1.4.x. Reads DXF headers, layers, blocks, and
  attributes (title block ATTRIBs). **DXF only** - DWG needs the ODA File Converter
  add-on (`ezdxf.addons.odafc`), which is a separate free-but-proprietary install.
  Pulls numpy, pyparsing, fontTools. Candidate for a `dxf*` content filter.
  [docs](https://ezdxf.readthedocs.io/en/stable/introduction.html)
- [MEDIUM | Memory] **puremagic** - MIT, pure Python. Content type from magic bytes.
  Would catch a file whose extension lies. Low value until a rule needs it.
- [HIGH | Primary] **Send2Trash** - BSD-3-Clause, 2.1.0 (2026-01-14). Native recycle bin
  on Windows via `IFileOperation`. Atlas today only removes *Fileless* folders by rmdir
  (`ops.remove_empty_dirs`, `conform._remove_if_file_empty`), where a trash adds nothing.
  Relevant the day Atlas deletes a file.
  [repo](https://github.com/arsenetar/send2trash)

### Port the design - mutating tools

- [HIGH | Primary] **organize** (tfeldmann/organize) - MIT, ~3.1k stars, v3. Hazel for
  the terminal: YAML rules of `locations` + `filters` + `actions`, simulate-first,
  conflict modes. Filters include extension, name/regex, size, dates, EXIF, PDF/DOCX
  text, duplicate, empty. Actions include move, copy, rename (templated), delete,
  shell, python.
  [repo](https://github.com/tfeldmann/organize) ·
  [rules docs](https://tfeldmann.github.io/organize/rules/)
  - **What Atlas took:** the filter vocabulary (extensions, names, regex, content),
    AND across filters, rules in order, simulate-first. Expressed in the drive map,
    evaluated in `atlas.core`, emitted as SWEEP actions. ADR 0009.
  - **What Atlas did not take, and why:** organize's own config file (the drive map is
    the only brain), its actions (they bypass the Plan), its multi-rule chaining (Atlas
    resolves every Filing State by first match), and its inline Python/shell filters
    (an executable map is a security surface on a shared drive).
  - [LOW | Primary] Whether organize v3 has a stable Python API is unverified - the v3
    migration page 404'd this session. Irrelevant now that Atlas ports rather than calls.
- [MEDIUM | Secondary] **f2** (ayoisaiah/f2, Go) - bulk rename: dry-run by default,
  regex, EXIF variables, CSV-driven renames, conflict detection, its own undo.
  Licence not verified this session. Borrow its preview and conflict screen for any
  future Atlas rename feature; never run it, because its undo is not Atlas's.
  [Show HN](https://news.ycombinator.com/item?id=44081850)

### Shell out - read-only use of a binary

- [HIGH | Primary] **fclones** - MIT, Rust, 0.12.x. Duplicate finder with JSON and CSV
  output. Published benchmark: fclones 0:34.59, rmlint 2:28.43, jdupes 5:01.91 on the
  same tree. Works on Windows; copy-on-write dedupe (reflink) is Linux-only, which does
  not matter for report mode. Use `fclones group --format json` as a **doctor finding**
  ("the same PDF in four folders"), never its `remove`/`link` actions.
  [repo](https://github.com/pkolaczk/fclones)
- [HIGH | Primary] **jdupes** is MIT but ~9x slower. **rmlint** is GPL-3 - fine to shell
  out to, but fclones is faster and permissive, so there is no reason to.
  [rmlint](https://github.com/sahib/rmlint)

### Console widgets

- [MEDIUM | Primary] **textual-fspicker** (davep) - FileOpen, FileSave, SelectDirectory
  dialogs for Textual. Useful when Atlas gains a "move this to..." action that needs a
  destination picker. Licence from memory: MIT.
  [repo](https://github.com/davep/textual-fspicker)
- [MEDIUM | Primary] **textual-autocomplete** - dropdown completion for an `Input`.
  Useful in the intake wizard (contact email, city). Licence from memory: MIT.
  [PyPI](https://pypi.org/project/textual-autocomplete)
- [HIGH | Primary] **textual-universal-directorytree** (juftin) - MIT. `DirectoryTree`
  over fsspec (one Python API over S3, GCS, Azure, GitHub, SSH/SFTP). **Does not fit**:
  ticket 05 ruled out `DirectoryTree` as a base for three measured reasons, and Atlas
  reads a mounted drive, not an object store. Only relevant if ticket 11 (a Drive API
  read path) ever lands.
  [repo](https://github.com/juftin/textual-universal-directorytree)
- [HIGH | Primary] Wider ecosystem index for later lookups:
  [awesome-textualize-projects](https://github.com/oleksis/awesome-textualize-projects) ·
  [transcendent-textual](https://github.com/davep/transcendent-textual)

### Skip - with the reason

- [HIGH | Primary-local] **rapidfuzz** (MIT, C++) is unnecessary for the console:
  Textual 8.2.8 ships `textual.fuzzy.Matcher` and `FuzzySearch` (verified importable in
  the Atlas venv). Add rapidfuzz only if the CLI needs fuzzy matching outside Textual.
  [repo](https://github.com/rapidfuzz/RapidFuzz)
- [HIGH | Primary-local] **watchdog** and any filesystem watcher: ticket 06 already
  established filesystem watching is not a dependable staleness signal over the Drive
  redirector. Atlas uses a 60-second Shelf Life plus explicit refresh instead
  (ADR 0007). Do not reopen without new evidence.
- [HIGH | Primary] **Licence blockers** for an MIT repo: PyMuPDF (AGPL-3.0), rmlint
  (GPL-3). [MEDIUM | Memory] dupeGuru and ranger are GPL-3 too.
- [MEDIUM | Primary] **yazi, broot, superfile, nnn** - reference for interaction ideas
  only. Not dependencies, not ports.

## Hidden variables and contradictions

- [MEDIUM | Primary-local] **Reading a file on the Drive mount downloads it.** Opening a
  placeholder hydrates it. Whether a pypdf read of page one fetches byte ranges or the
  whole file is **not measured** - Atlas never touches the studio drive during
  development. Mitigations in code: content is read only after a rule's name filters
  pass, only for files named `*.pdf`, never over `content.PDF_READ_LIMIT` (64 MB), and
  cached by path + size + mtime so a Guard re-check does not download twice. **Measure
  before writing a broad content rule on the real drive.**
- [HIGH | Primary] **This cost was already on the record.** `atlas-tui-ux-evidence.md`
  carries "do not preload project files on the shared drive", from Yazi's own guidance
  that previewing downloads remote content. A Content Filter is a preview by another
  name. It is allowed here only because a rule's name filters gate it, which a
  previewer's cursor does not.
- [MEDIUM | Primary-local] `DirEntry.stat()` is free on Windows for size and mtime, but
  `atlas.core.scan` deliberately never stats (ticket 06). The content module stats one
  file, only when a content filter is about to run. The scan stays dirent-only.
- [LOW | Memory] Recycle-bin support on the Drive virtual drive is unverified; a delete
  there may go to Drive's own trash or be permanent. Matters only once Atlas deletes
  files - verify at that point, read-only first.

## Implementation backlog

Ordered by value per unit of risk. Status is the column to maintain.

| # | Item | Uses | Status | Where |
|---|------|------|--------|-------|
| 1 | File Rules in the drive map: extensions, names, nameRegex, pdfText; root files only; emits SWEEP | pypdf, organize's design | **Done** 2026-09-10 | ADR 0009, ticket 25, `core/filerules.py`, `core/content.py` |
| 2 | File Rules below the project root - a file inside a section that belongs in another | - | **Decided** 2026-10-07: opt-in `receiptRules` class, name filters only, deep pass, Sweep-only; build pending | ticket 26 (decision), ticket 31 (build) |
| 3 | Duplicate files as a `doctor` finding, read-only | fclones JSON | Open | ticket 27 |
| 4 | More content filters: DXF title-block attributes, true content type | ezdxf, puremagic | Open | ticket 28 |
| 5 | Intake autocomplete for contact and city | textual-autocomplete | Open, small | - |
| 6 | Destination picker for a future "move this to..." action | textual-fspicker | Deferred until that action exists | fog: file-level action set |
| 7 | Recycle bin on file delete | Send2Trash | Deferred until Atlas deletes files | - |
| 8 | Bulk rename with preview and conflicts | f2's design | Fog | - |
| 9 | Title-block region matching (phrase at a page position) | pdfplumber | Only if item 1 proves too coarse on real sets | - |

## How to continue

1. Read ADR 0009 for the File Rules contract and what it deliberately does not do.
2. Read `CONTEXT.md` under **Atlas File Rules** for the vocabulary.
3. Take the lowest open ticket in the table above. Tickets live in
   `.scratch/atlas-console/issues/`; the frontier lives in
   `.scratch/atlas-console/map.md`.
4. Before any content rule goes on the real `_tools/<drive>-map.json`, run a read-only
   `atlas doctor --json` against the drive and measure item 1's hydration cost. The
   feature is inert until a map carries a `fileRules` block.
