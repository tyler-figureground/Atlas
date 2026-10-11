# Global search scope

Type: grilling
Status: closed (2026-10-08)
Blocked by: -
Parent: ../map.md

## Question

Global search is in scope: one keystroke, search across the drive, jump to the
result. What it searches is undecided. Nothing is built - there is no search
overlay anywhere in `tools/atlas/src/atlas/tui/`.

What changed since this ticket opened:

- **The cost objection is gone.** Ticket 12 measured the live drive: 7,956
  folders, 18,536 files, walked in 4.24 s, cold p99 91 ms per folder. A
  drive-wide index is affordable; enumeration over the mount is no longer a
  reason to narrow the scope by fiat. `Path.rglob` remains banned (ticket 06:
  it suppresses every `OSError`).
- **The `/` filter grew.** Per ADR 0005 and the 2026-09 audit (#62), `/`
  filters the focused Region - the project list and, per project, the tree
  (`tui/app.py` `#filter` / `#tree-filter` inputs,
  `tui/treeview.py::set_filter`). It never leaves the selected project. The
  "existing `/` filter" this ticket asks about is that pair.

Resolve:

- What is searchable: project names only, project names plus dossier facts,
  folder and file names across all projects, or file contents?
- Drive-wide, or scoped to the selected project with a widen key?
- Live-as-you-type or submit-then-results? Live search over a network mount is
  a different engineering problem than a submitted query, even at 4.24 s.
- Does it need an index? If so, where does it live, when is it built, and how
  does it go stale? An index file on the drive is shared state that other
  studio machines will also read.
- What does a result look like, and what does selecting one do - reveal in the
  tree, open the project, open the file?
- Is the Region filter subsumed, kept alongside, or promoted into this?
- What happens with no results, with too many results, and while a slow search
  runs?

## Acceptance

- Each question above answered with the measured numbers from ticket 12, not
  assumed ones.
- Decision recorded in `docs/adr/` and one line on `../map.md`; new vocabulary
  in `/CONTEXT.md`.
- If the answer builds a fact-producing surface, ADR 0008 applies: it owes a
  CLI form with a `--json` shape in the same session.

## Decision

Q1 (Tyler, 2026-10-07) settled scope: the one-keystroke search searches
everything, including PDF text. What remained is mechanics, and the mechanics
split on the measured cost classes, not on file type.

**Names ship now; content waits for the index - and Markdown waits with the
PDFs.** A drive-wide name search (folders, files, and the project dossier
facts Atlas already parses) needs one enumeration pass and zero content reads:
the measured 4.24 s walk (ticket 12), run once per session on a background
worker. The tempting middle option - filenames plus Markdown text now - is not
real: on the streaming mount every content read is a download, and the plan's
own datum is 1,386 files zipped in 48 minutes. Markdown is exactly as
content-bound as PDF, so the split is names versus content, never file type.
Content search ships when the local index exists (ticket 34, 35), which serves
Markdown and PDF with the same machinery.

**The index lives on the local machine, never on the drive.** Per-machine
cache via `platformdirs` user cache path (the research report's own state
guidance). An index file on the shared drive is shared mutable state with no
locking story across studio machines, and pushing a bulk derived artifact onto
the drive is the preload finding (`atlas-tui-ux-evidence.md`: do not preload
files on the shared drive) in reverse. The drive map stays the only
folder-structure brain; the index is a cache of disk truth, not a structure
opinion.

**Freshness is rebuild and revalidate, never watching.** The name index is
rebuilt on session start and on `r` (4.24 s, background, non-blocking per the
research P0). The content index is keyed path+size+mtime - the cache key ADR
0009's File Rules already use - carries an indexed-at stamp the UI shows, and
revalidates a file's key at query time, re-extracting what changed.
Filesystem watching stays banned (ticket 06: not a dependable staleness
signal over the redirector).

**CLI parity is owed in the same session as the surface** (ADR 0008, a
fact-producer): `atlas search QUERY [--json] [--content]`. The `/` Region
filter stays alongside: it is navigation over already-loaded facts, exempt
from parity, and it is instant where the overlay is drive-wide.

**Search renders as an overlay, not a fourth Region.** ADR 0005 fixes exactly
three Regions on the simultaneity argument; search is episodic - asked,
answered, dismissed with Escape - and never has to coexist with anything.
The map's fog had already named it "the search overlay". Live-as-you-type
against the warm in-memory name index; a result row reveals the node in the
tree (the reveal machinery exists), selects the project in the list, or opens
the file on `o`. No results: one honest line. Too many: capped at 500 with
the overflow counted (ticket 12's count cap, reused). Slow: the loading state
appears past the 120 ms budget, never on a warm read.

Reasoning, three lines:

1. The 4.24 s walk removed the enumeration objection to names; the 48-minute
   zip datum is the content objection, and it applies to Markdown exactly as
   to PDF - so "filenames+Markdown now" was never an option on the mount.
2. A per-machine, mtime-keyed index turns content search from a per-query
   download storm into one background build plus incremental top-ups, with no
   Drive API credential story (ticket 11: no-build).
3. Three Regions are load-bearing (ADR 0005); an episodic surface earns an
   overlay, and the navigation rule survives intact because the overlay takes
   no Region's focus model.

Consequences:

- Becomes build tickets **33** (global name search), **34** (the local content
  index), **35** (content search over the index). Vocabulary (Search Overlay,
  Name Index, Content Index, Indexed-At Stamp) lands in `/CONTEXT.md` with
  those builds.
- **ADR 0005 needs a line.** Drafted amendment, to be added by ticket 33 (not
  created here):

  > **Amendment (ticket 08, 2026-10-08): drive-wide search is an overlay, not
  > a Region.** The three-Region model stands; search is episodic, takes the
  > screen while open, and dismisses with Escape without disturbing Region
  > focus or collapse state. It reads a session name index built from one
  > drive walk, and content matches from the per-machine content index; it
  > never enumerates or reads content at keystroke time. The `/` Region filter
  > is unchanged: navigation over loaded facts, not search.

- **The content index wants its own ADR** (0020, next free after ticket 30's
  reserved 0019) covering location, keying, and freshness; drafted by ticket
  34 per the ticket-30 convention, not created here.
- ADR 0008 is discharged, not amended: `atlas search` and `atlas search
  --content` land in the same sessions as their surfaces (tickets 33 and 35).
- Rejected alternatives, recorded: wait-for-PDF single ship (search stays
  absent for months behind the index); filenames+Markdown now (Markdown is a
  download per file on the mount, same class as PDF); index on the drive
  (shared mutable state, no locking, anti-preload finding); a fourth Region
  (breaks ADR 0005's simultaneity argument for an episodic surface).
