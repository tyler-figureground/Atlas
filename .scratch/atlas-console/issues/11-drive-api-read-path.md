# An authenticated Drive API read path

Type: grilling
Status: closed (2026-10-08)
Blocked by: -
Parent: ../map.md

## Question

Raised by ticket 06, which the map had no slot for.

Everything Atlas does today reads the mounted filesystem. Ticket 06 establishes
that this is the only case Atlas faces - Google shared drives are streaming-only
and cannot be mirrored - and that the filesystem gives no authoritative way to
know a displayed tree has gone stale.

An OAuth-authenticated Google Drive API read path would change that. It is the only
documented route to authoritative staleness detection (`changes.list`) and to
sub-linear whole-drive listing: one paged `files.list` scoped to a `driveId` builds
the entire tree in `ceil(N/1000)` requests, rather than one enumeration per folder.

It also costs a great deal. Resolve:

- Is an authenticated API path acceptable for Atlas at all, or is filesystem-only a
  standing constraint of the tool?
- It introduces a second source of truth about folder structure. The map's standing
  constraint is that `_tools/<drive>-map.json` is the only folder-structure brain -
  does an API listing violate that, or is it a cache of the same disk truth?
- Credentials: where does a token live on a studio machine, who provisions it, what
  happens when it expires, and what does Atlas do offline or unauthenticated?
- Would it be read-only, always? Writes must keep crossing filesystem core plans.
- Is it worth it only for search and staleness, or does the tree read from it too?

A defensible answer is "no, filesystem only" - in which case record why, and the
tree accepts TTL-based staleness and a per-folder enumeration cost forever.

## Decision

**No build. Filesystem-only is promoted to a standing constraint of the tool,
and the PDF-text index builds over the mount.**

**The API's two unique gifts solve measured non-problems.** Sub-linear
whole-drive listing (`files.list` with `corpora=drive` + `driveId`,
`ceil(N/1000)` requests) replaces a full drive walk measured at 4.24 s -
already affordable, already shipped against. `changes.list` replaces the 60 s
Shelf Life plus the write-side Guards, which already cover Atlas's real
staleness needs: display staleness is cosmetic and TTL'd, and every write
revalidates what it is about to touch. Neither gift is on the critical path
of any decided feature.

**The one new need - PDF-text indexing - is byte-bound, and bytes do not
change paths.** A mount read is a download; a `files.get` is a download.
Content extraction costs the same over the wire either way, so the promoted
question (Q1, 2026-10-07: search includes PDF text, which needs an index)
does not change the answer. The index is incremental and mtime-keyed (ticket
34), so the one-time download cost is paid once per file, ever, per machine -
not per query.

**The real cost is the auth story, and nothing is provisioned.** Checked
2026-10-08, read-only: no Google credentials exist on any studio machine -
nothing in the environment, no `gcloud` config, no `.credentials`, nothing in
`_tools`. Staff run a pinned wheel through `Atlas.bat`, so an API path means
a Google Cloud project, an OAuth consent screen or service account, token
storage, refresh, expiry and revocation handling on every studio machine,
and a defined offline story - maintained forever. Quota is not the blocker
(100 units per `files.list` against 325,000/min/user is generous); the
credential lifecycle on machines Atlas does not control is. Google
shared-drive scaffolding (`corpora=drive`, `supportsAllDrives`, per-drive
scoping) is real but minor beside it.

**The hybrid is rejected by name.** Mount for enumeration plus API only for
content fetch pays the entire auth cost and saves zero bytes - the worst of
both. The inverse hybrid (API enumeration, mount content) is worse still:
rclone documents that whole-drive fast-listing lags reality on shared drives
(~an hour), so the API listing is *less* fresh than the mount read it would
replace, while the Guards and Shelf Life it would displace are fresher.

**The second-source-of-truth question is answered even though it is moot:**
an API listing would have been a cache of the same disk truth, like the
tree's enumeration cache - the drive map's standing constraint was never
threatened, because the map holds structure *judgment*, not structure
*observation*. Recorded so the argument does not have to be rebuilt if the
decision is revisited.

**Reversal trigger, written down:** revisit only if (a) multi-machine
staleness causes a measured incident - two operators acting on trees Atlas
showed stale, with the TTL and Guards demonstrably insufficient - or (b) the
studio adopts Workspace service accounts for another reason, making the auth
story free. Until either, the tree accepts Shelf-Life staleness and
per-folder enumeration forever, and the constraint is lifted only by a new
grilling ticket, not by a build ticket's convenience.

Reasoning, three lines:

1. Measure first: every motivating problem (enumeration cost, staleness) has
   a measured mount answer already shipped; the new need (PDF text) is
   byte-bound, and bytes are identical on both paths.
2. Auth is the true price and it is studio-wide - credentials and their
   lifecycle on every machine, against a benefit measured in seconds per
   session, for a tool whose operators number in the single digits.
3. Promoting filesystem-only to a standing constraint makes the decision
   load-bearing rather than re-litigated: it joins "never touch a production
   drive" on the map, with its reversal trigger beside it.

Consequences:

- The PDF/Markdown content index builds over the mount as ticket **34**,
  reusing ADR 0009's extraction machinery (64 MB Read Limit, damaged-file
  silence, path+size+mtime keying). Ticket 08's phasing stands on this
  foundation.
- **The map gains a standing-constraint line** (added with this decision):
  Atlas reads the mounted filesystem only; the Drive API read path was
  evaluated and declined (ticket 11) with its reversal trigger recorded here.
- **No ADR is amended and none is drafted**: no accepted ADR asserts a read
  path, so there is nothing to correct; the index's own ADR (0020) is drafted
  by ticket 34 per the ticket-30 convention.
- Ticket 27 (duplicate hashing) stays parked on the same byte-bound logic -
  the 48-min zip datum already covers it; ticket 28 (content filters at
  depth) untouched.
- Rejected alternatives, recorded: full API read path (auth cost against
  measured non-problems); hybrid mount-enumeration + API-content (pays auth,
  saves nothing); hybrid API-enumeration + mount-content (documented *less*
  fresh than the mount on shared drives); "API only for staleness" (the
  Shelf Life plus Guards already cover every write Atlas performs).
