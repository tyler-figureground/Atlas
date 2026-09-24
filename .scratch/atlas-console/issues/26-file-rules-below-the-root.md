# Do File Rules reach below the project root

Type: grilling
Status: open
Blocked by: -
Parent: ../map.md

## Question

Ticket 25 deliberately stopped at the project root. A permit set sitting in
`01 Model` instead of `08 OUT/Transmittals` is the same mistake as one sitting at the
root, and Atlas cannot see it.

Three things stand in the way, and this ticket is to decide whether they are worth
paying:

- **Containment says it is already filed.** ADR 0007: a node under a canonical path is
  Mapped. A rule that overrode that would make Filing State depend on which rule ran
  last, which is exactly what the first-match order exists to prevent. Does a rule
  outrank containment, or only apply where containment has no opinion?
- **`doctor` does not descend, on purpose.** Its 4.24-second drive-wide cost (ticket
  12) is bounded precisely because it reads project roots only. A rule that reaches
  deeper turns one enumeration per project into a walk - and with a content filter, a
  download per candidate. Is this a `doctor` fact at all, or a tree-only one, computed
  for the folder actually on screen?
- **Moving a file someone filed by hand is a different act** from filing one nobody
  filed. The first overrules a person; the second helps them. Does it need a
  different confirmation, or a rule flag that opts in?

A defensible answer is "no, roots only" - in which case record why, and the studio
gets a `misfiled` finding some other way or not at all.

## Constraints

- ADR 0004, 0006, 0007, 0009 all bear on this. None may be quietly amended.
- Whatever is decided, it emits a Sweep or it emits nothing.
