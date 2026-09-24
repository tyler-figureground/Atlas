# A latency number for the tree

Type: task
Status: resolved
Blocked by: -
Parent: ../map.md

## Question

Raised by ticket 06. The map bans reading a production or shared drive, and the
research honoured that - so it returned a correctly shaped implementation shortlist
with no numbers in it.

Neither Microsoft nor Google publishes a latency figure for enumerating a directory
on a network-backed virtual drive. Microsoft says only that it "will be more
expensive than normal". That means the tree cannot currently be given:

- a spinner threshold - at what delay does a node expansion show a loading state
- a lazy-load budget - how many nodes may be prefetched ahead of the cursor
- a count cap - where "n+" replaces a real number
- a cache TTL - how long an enumeration stays trustworthy
- a cold-folder ceiling - how long a node expansion may run before the tree must
  show a loading state rather than appear frozen (raised by ticket 05)
- a concurrency cap - how many node loads may be in flight against the shared
  thread pool at once, given ticket 05 establishes they cannot be exclusive

Every one of those is a number, and none can come from documentation.

Do the work that produces one. Two routes, and the choice is the user's:

1. **Provision a synthetic fixture.** A throwaway Google Workspace shared drive,
   populated to resemble a real studio drive, mounted through Drive for Desktop.
   Costs a Workspace seat and setup time. Safe, repeatable, and reusable as a test
   fixture for the rest of this effort.
2. **Authorise a one-off read of the studio drive.** A read-only enumeration
   benchmark - no writes, no opens, `os.scandir` only - against a small number of
   real projects. Cheaper, faster, and needs explicit permission because it breaks
   the map's standing constraint.

Resolved when a measurement exists and the four numbers above are written down with
the conditions they were taken under. Record them where the tree implementation will
read them, not only in this ticket.

## Answer

Route 2 taken. The user authorised reading the studio drive, with no mutation and
nothing created. Measured with `os.scandir` only; no file or folder was created on
any shared drive, so nothing needed deleting afterwards.

Report: `docs/research/atlas-drive-latency-measurement.md`

### The numbers

Whole studio drive, uncapped: **7,956 folders and 18,536 files in 4.24 seconds**,
mean 0.53 ms per folder, p99 1.78 ms, zero calls over 50 ms. Depth barely moved
the median between depth 1 and depth 13.

Warm working drive vs a rarely-walked drive - the difference is entirely in the
tail, not the median:

| | warm | rarely walked |
|---|---|---|
| p50 | 0.49 ms | 0.77 ms |
| p90 | 0.98 ms | 1.74 ms |
| p99 | 2.47 ms | **91.49 ms** |
| max | 29.26 ms | **314.49 ms** |
| over 50 ms | 0 | 37 of 2500 |
| over 1 s | 0 | 0 |

Concurrency at 8 workers: 2.15x on the working drive, 1.82x on the other.
Sub-linear - the curve has already flattened by 8.

### The four budgets

- **Loading-state threshold: 120 ms.** Above the cold p99 of 91 ms, below the
  perceptual boundary. At p90 of 1.74 ms almost no expansion will ever show it.
- **Prefetch: one level ahead of the cursor, cap 50 nodes, cancellable.** Thirty
  siblings cost 11-20 ms typically and 9.4 s in the pathological tail, which is
  why the cap matters more than the number.
- **Concurrency cap: 4 in-flight node loads.** Most of the measured gain, and it
  leaves the pool free. Ticket 05 separately forbids `exclusive`.
- **Recursive count cap: 500 folders, then `n+`.** Roughly 0.3-1.6 s. Ticket 13
  may delete this entirely.
- **Cache TTL: 60 s.** Enumeration is cheap enough that short costs nothing, and
  short is what makes another machine's change visible.

### What this changes elsewhere

**A whole-drive walk costs 4.24 seconds.** The map's performance anxiety was aimed
at the wrong risk: throughput is a non-issue at this drive size. The real risks are
the 300 ms cold outlier and the failure modes below. Ticket 08 was written assuming
a drive-wide index might be prohibitive - it is not.

### Two live failures found while measuring

Two directories on the production drive raise `FileNotFoundError` from
`os.scandir` while their own parents list them fine. Both are `MAX_PATH`, at 259
and 273 characters, and both read correctly through the `\\?\` extended-length
prefix. One of them contains an entry that **Atlas currently reports as empty**.

That is ticket 16 confirmed on production data. `find_empty_dirs` is not at risk -
`os.walk` omits the failing directory entirely, so neither it nor its parent is
ever marked empty. The failure is false reporting, not destruction. Opened ticket
19 for the extended-length prefix decision, which is broader than enumeration.

### Honest limits

"Cold" is a proxy: Drive's cache cannot be cleared from user space, so these are a
floor, not a worst case. One machine, one network, one moment. This drive is small
at 7,956 folders; a much larger drive may exceed what Drive keeps cached. Mutation
cost was not measured because writes were not permitted.

## Built, 2026-09-23 (#46)

The measurement resolved this ticket; the budgets were only recorded until #46.
They now live where the tree reads them, in `core/tree.py`: `LOADING_DELAY` 120 ms,
`CONCURRENCY_CAP` 4, `COUNT_CAP` 500 (a larger folder lists as Partial), and
`DEFAULT_TTL` 60 s. `PREFETCH_CAP` 50 is recorded but moot: the tree reads a folder
only when it is opened (ADR 0007), so nothing is prefetched. The scoped Guard walks
nothing, and arming and committing a tree repair run off the UI thread.
