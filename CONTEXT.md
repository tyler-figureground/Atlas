# Domain Glossary

## Atlas Project Intake

**Project**  
An architecture engagement represented by one mapped project folder and one `PROJECT.md` dossier.

**Project Name**  
Human-facing name of the engagement. Required. Distinct from its folder name and address.

**Project Address**  
Required full US site address: physical numbered street, optional unit, city, state, and ZIP code. Distinct from any contact's mailing address. Never a PO box.

**Short Address**  
Street number plus street name and suffix from the Project Address. Excludes unit, city, state, and ZIP. Used in the project folder name.

**Description**  
Optional short qualifier appended to the project folder name. Distinct from Project Use Case.

**Project Use Case**  
Required classification of the engagement: Renovation, Addition, Renovation + Addition, Ground Up, Feasibility, Existing Conditions, Code Compliance, or Other. Other requires a custom label. Project Use Case is not an IBC occupancy or building use group.

**Contact**  
Reusable person in the firm's shared contact directory. Identified by a stable ID. Email is unique case-insensitively. A contact has required first name, last name, and email; phone, company, and mailing address are optional.

**Contact Mailing Address**  
Optional US correspondence address for a Contact. May use either a physical numbered street or a PO box. Distinct from Project Address.

**Billing Contact**  
Required Contact responsible for billing correspondence on a Project.

**Client Contact**  
Required Contact representing the client relationship on a Project. Defaults to the Billing Contact during intake but may be overridden.

**Contact Snapshot**  
Copy of a Contact's details stored in the Project dossier at creation or explicit Project edit. Preserves project history when the shared Contact later changes. Shared Contact edits never rewrite snapshots automatically.

**Project Update**  
Explicit correction of an existing Project's intake fields. Address or Description changes may derive a new folder name; Atlas previews and confirms that rename, rejects collisions, and updates the dossier and project index together.

## Atlas Project Tree

**Tree Node**
One folder or file that exists on disk inside a Project folder. Only things on
disk are Tree Nodes. A folder the drive map expects but disk lacks is an unmet
Expectation, not a Tree Node.

**Expectation**
A folder the drive map requires a Project to have. Met when a Tree Node exists at
that path; unmet otherwise. Unmet Expectations are listed beside the tree, never
drawn inside it.

**Contract Expectation**
A control-plane file that is on disk but lacks its machine contract - a
`PROJECT.md` with no YAML front matter. Listed in the Companion with what is
wrong (`PROJECT.md - no front matter`), never as missing, and never offered as a
Repair: backfill leaves an existing `PROJECT.md` unchanged.

**Filing State**
What the drive map says about a Tree Node that exists. Exactly one of Mapped,
Drifted, Misplaced, Loose, or Unfiled, decided by the first map rule that matches
in the order conform applies them. Distinct from Load State.

**Mapped**
Filing State of a Tree Node the drive map accounts for, at the path it occupies.
Nothing to do.

**Drifted**
Filing State of a Tree Node whose name the drive map renames to a canonical one.
Atlas can repair it without a human decision.

**Misplaced**
Filing State of a Tree Node the drive map relocates to a different path. Atlas can
repair it without a human decision.

**Loose**
Filing State of a file sitting at a Project root that the drive map files into a
target folder, by a glob relocation or by a File Rule. Atlas can repair it without
a human decision.

**Unfiled**
Filing State of a Tree Node the drive map knows nothing about. Atlas can never
repair it, because only a person can decide where it belongs or whether it should
exist.

**Load State**
What Atlas knows about a folder Tree Node's children. One of Unread, Read,
Unreadable, or Partial. Orthogonal to Filing State: a Mapped folder can be
Unreadable, and an Unfiled folder can be Unread.

**Unread**
Load State of a folder whose children have not been enumerated yet. The starting
state of every folder below the one in view.

**Read**
Load State of a folder whose children were enumerated completely.

**Unreadable**
Load State of a folder whose enumeration failed. Never presented as empty; an
empty folder and a folder Atlas could not open are different facts.

**Partial**
Load State of a folder whose enumeration returned an incomplete list, either
because a cap was reached or because the filesystem returned fewer entries than
exist. Never presented as complete.

**Empty Folder**
A folder Tree Node whose Load State is Read and which has no children of its own.
Only a Read folder can be known to be empty. Distinct from Fileless.

**Fileless**
A folder with no file anywhere beneath it, however deep. This is what Clean
removes, by rmdir cascade. A Fileless folder is often not an Empty Folder - it may
contain a chain of subfolders that themselves contain no files - and an Empty
Folder is always Fileless. The tree reports Empty; Clean acts on Fileless.

**Child Count**
The number of a folder Tree Node's own children, split into folders and files.
Free, because it is the length of the enumeration already held. Never recursive:
a recursive count is a walk of the whole subtree, and Atlas does not spend that to
draw a label.

## Atlas Console Layout

**Region**
A named area of the console that can take focus, be collapsed, and be maximized.
Exactly three exist: the Project List, the Tree Region, and the Companion Region.
_Avoid_: pane, panel, sidebar.

**Project List**
The Region listing every Project on the mapped drive. The console's landing
surface: focus starts here, and the Selected Project is whichever row its cursor
rests on.

**Workspace**
The container holding one Project's Tree Region and Companion Region, under a
title carrying the Project Name. Not itself a Region - it takes no focus and
collapses only by collapsing what it holds.

**Tree Region**
The Region drawing the Tree Nodes of the Selected Project.

**Companion Region**
The Region under the Tree Region, showing one Companion Mode at a time. Under,
not beside: the console has rows to spend and columns it does not.

**Companion Mode**
One of the three things the Companion Region can show - unmet Expectations,
project health, or the dossier. Unmet Expectations is the default, because it is
the only one that has to be readable at the same time as the tree.

**Selected Project**
The Project the Project List cursor rests on, and therefore the Project the
Workspace draws. Distinct from a marked Project, which is a batch selection and
does not move the cursor.

**Split Composition**
The console arrangement showing the Project List and the Workspace side by side.
The arrangement at wide terminal widths.

**Single-Region Composition**
The console arrangement showing exactly one Region at a time, the others hidden
rather than shrunk. The arrangement at narrow terminal widths, and the common one
rather than the degraded one. The navigation model is identical in both
Compositions; only what is on screen differs.

## Atlas Writes

**Plan**
The complete description of a set of writes, built in core, shown to a person
before anything happens, and applied only after they confirm it. Atlas has no
other way to change a drive.

**Action**
One write inside a Plan. Exactly one of Backfill (create a folder the drive map
expects), Rename (a Drifted Tree Node to its canonical name), Relocate (a
Misplaced Tree Node to its mapped path), or Sweep (a Loose file into its target
folder). The one-Action slice a single Tree Node earns is a Repair, defined under
Atlas Tree Repairs.

**Move Manifest**
The record of every source-and-destination pair an Action actually moved, filled
in at the moment it is applied. What makes a move into an existing folder
reversible: without it, Atlas cannot tell which items it moved in and which were
already there.

**Stale Plan**
A Plan whose preview no longer describes the drive, because something changed
between the preview and the confirmation. A Stale Plan is never applied - Atlas
abandons it and says what changed.

**Guard**
What a preview saw, and what has to still be true before Atlas writes. Guard
strength scales with the scope of what it protects: a project-wide conform re-reads
the whole drive and the project root, while a one-Action Plan from a Tree Node
re-reads only the drive map and the directories that Action touches. Both abort
identically - nothing moves, and the operator is told what changed. A guard
deliberately does not see a change it cannot be affected by; that is what makes the
narrow one affordable on a keystroke.

**Path Length Warning**
The longest absolute path an Action would create, measured while the Plan is still
a preview. Atlas warns above 260 characters and never refuses, and never applies
the extended-length prefix on the write side - routing around the limit would let
Atlas create a path Explorer and Revit cannot open, which is the opposite of
warning about it.

## Atlas Project Tree Seam

**Node Key**
A Tree Node's project-relative path, forward-slashed, with `""` for the project
root. The node's stable identity: it survives a refresh, and Atlas can say where a
Node Key went after a write. Necessary because Textual restores the tree cursor by
line number rather than by node identity, so a rebuild with a different child list
would otherwise move the selection silently.

**Project Tree**
The handle core gives the TUI for one Project. Expands lazily - one enumeration per
folder actually displayed - hands out immutable Tree Nodes, and keeps the cache
behind them. It owns filesystem facts; the widget owns interaction.

**Containment**
The rule that decides Filing State below the project root, where the drive map has
no rule of its own. A Tree Node at or under a canonical path is Mapped; one under
an Unfiled node is Unfiled. A path the map names explicitly keeps its own verdict
at any depth.

**Shelf Life**
How long a folder's enumeration may be trusted before Atlas reads it again: 60
seconds. There is no filesystem watching over the Drive redirector, so somebody
else's change reaches the tree when the shelf life expires or when the operator
refreshes, and never sooner.

**Reconcile**
What the tree does after Atlas applies a Plan: forget the folders the Move Manifest
names, take the fresh report with it, and move the cursor to where the repaired
node went. Scoped like the Guard is - a one-node repair forgets two folders, a
project-wide conform forgets the project.

## Atlas Interface Contract

**CLI Obligation**
The rule deciding which console capabilities owe a CLI form: every capability that
writes, and every capability that produces a fact. Navigation is exempt - an agent
wants the facts and the writes, never the cursor. Discharged in the same session as
the surface it belongs to, in either order, never in a later ticket.

**Agent Interface**
`--json` output. The documented machine-readable path into every fact and every
write Atlas can perform. Distinct from the TUI, which is for a person, and from a
CLI's plain-text output, which is for a person reading a terminal.

**Fault Word**
The word on a tree row naming what is wrong with a Tree Node - its Filing State,
in the operator's language rather than the model's: `wrong name`, `wrong place`,
`not filed yet`, `not in the map`. A Mapped node has none, because a solid glyph
already says nothing is wrong. Carried by files as well as folders.

**Short Form**
The abbreviated Fault Word a narrow row uses instead: `NAME`, `PLACE`, `LOOSE`,
`UNMAPPED`. Substituted for the long form below `ABBREVIATE_COLUMNS`, never
dropped. Dropping it was the defect that made this vocabulary necessary - Drifted,
Misplaced and Loose share a glyph and a colour by design, so the word is the only
thing between them.

**Colour-Alone Rule**
Colour may reinforce a distinction and may never be the only thing carrying one.
Tested by asserting that no two Filing States render identically once colour is
stripped, at either width, rather than by pinning any colour value.

## Atlas Tree Repairs

**Repair**
The one-Action write the tree offers for a single Tree Node: RENAME for a Drifted
node, RELOCATE for a Misplaced one, SWEEP for a Loose one - and, from the
Companion, BACKFILL for an unmet control-plane Expectation. Never a new action kind
- a Repair is a slice of the Plan conform already builds. A Mapped node earns none
because nothing is wrong; an Unfiled node earns none because only a person can
decide where it belongs; a missing section earns none because conform never
creates sections.

**Offer**
What the repair key would do on the node under the cursor. An Offer that is not
repairable carries a reason, because a key that does nothing and says nothing is
indistinguishable from a key that is broken.

**Armed**
A Repair previewed on the operation line and waiting for Enter. Nothing has touched
disk. Escape abandons it. The Guard is captured when the Repair is armed, not when
it is confirmed - what it holds is what the preview saw.

**Inline Confirm**
The confirmation a one-Action Plan gets: the operation line, not a modal.
Confirmation weight follows plan size, so a longer Plan still gets the modal, which
is the surface that can show a list.

**Undo Stack**
The applied Plans for one Project, in memory for this session, most recent first,
with no redo, capped at 50. Each entry holds its inverse Plan and its Undo Guard,
both built when the write applies. Undoing previews the inverse and applies it only
on confirm - inline for one Action, the modal for several - so an undo is a write
like any other; the entry leaves the stack only once the undo has moved something,
so a refused undo can be retried. Undo restores the precondition that offered the
Repair, so re-pressing the repair key is redo. A Plan that cannot be inverted is
refused when it is pushed, never when it is popped - a stack that cannot honour a
depth it advertised is worse than one that never advertised it. A project-wide or
batch conform forgets that Project's history; a drive switch forgets all of it.

**Undo Guard**
The check that runs before an undo: the drive map, and the folders the inverse
touches, as they stood when the Repair applied - so it sees anything changed after
the repair, not only after the undo was pressed. Distinct from the guard on a
Repair, which additionally re-derives the Plan from the map and compares. An undo's
Plan reverses the map rather than following it, so re-deriving it can only ever
disagree.

## Atlas File Rules

**File Rule**
A drive map entry that makes a file at a Project root Loose, by what its name says
and, optionally, what its content says. Its only output is a Sweep: a File Rule
never adds an Action kind or a Filing State. Tried in map order, after the glob
relocations; the first that matches decides. Never applies to the control plane,
to a tolerated file, or to a folder.
_Avoid_: organize rule, automation, smart folder.

**Filter**
One test inside a File Rule: `extensions`, `names`, `nameRegex`, or `pdfText`.
Every Filter a rule gives must match; within one Filter any value may. An absent
Filter is no test at all, never "matches nothing".

**Name Filter**
A Filter decided by the file's name alone - `extensions`, `names`, `nameRegex`.
Free: it reads nothing beyond the listing Atlas already holds. Always evaluated
before any Content Filter on the same rule.

**Content Filter**
A Filter decided by what is inside the file - today only `pdfText`. Costs a read,
and on the Drive mount a read is a download, so it runs only after the rule's Name
Filters pass, only on a file named for its format, and never past the Read Limit.
A file it cannot evaluate - damaged, truncated, password-locked, not what its name
claims - does not match. Uncertainty never moves a file.

**Read Limit**
The size above which Atlas never opens a file for a Content Filter: 64 MB. A cost
limit, not folder structure, so it lives in code rather than in the drive map.

**Rule Attribution**
The name of the File Rule that made a file Loose. Carried beside the Sweep and shown
wherever the Sweep is shown - `doctor` text, `--json`, the console's project
detail. A Sweep from a glob relocation has none; the relocation explains itself.


## Atlas Agent Files

**Agent Files**
The two files at a project root that tell a coding agent where it is: AGENTS.md and
CLAUDE.md. Control plane, like PROJECT.md and decisions/ - Atlas writes them at
creation and backfills them on conform. ADR 0010.

**AGENTS.md**
The instructions and the index. What every coding agent reads. Carries the Atlas
Block plus whatever the project has learned about itself - code posture, model
traps, house gotchas.

**CLAUDE.md**
The pointer, and nothing else: one line reading @AGENTS.md. Claude Code expands the
import, so it reads the same file every other agent reads and there is no second
copy to drift. Relative on purpose - an absolute pointer goes stale the day its
folder is renamed.

**Atlas Block**
The marker-wrapped region of AGENTS.md that Atlas owns, from atlas:agents-begin to
atlas:agents-end. House working style and an index built from the drive map.
Refreshed in place by conform; everything outside the markers is the project's own
and is never rewritten. Broken markers are a conflict, never a guess.

**Migration**
What conform does with a project whose CLAUDE.md still holds instructions: the
words move into AGENTS.md first, and CLAUDE.md becomes the Pointer only once every
non-blank line of it is provably present there, or it is stock generator output.
Anything else is left in place as a conflict for a person to merge.

## Atlas Project Templates

**Template File**
A file every project carries, copied by Atlas from the studio template folder in the
repo (tools/atlas/src/atlas/templates/project/). The drive map names where each one goes.
Created with a new project, backfilled by conform when absent, never overwritten. ADR 0012.

**Seeded Child**
A child folder created with its section when a project is started, and kept by clean.
Conform backfills it when its section exists. A child in the map is a name, or a name
marked seed.

**Task List**
00 Tasks/TASKS.md: the one live list of what is next on a project, in lanes TYLER,
AGENT, MODEL and WAIT. Facts go in PROJECT.md and reasons in decisions/; neither holds
tasks. ADR 0013.

**Scoped List**
A longer list for one scope - an audit, a revision round - in 00 Tasks/Lists/, copied from
the task list template and linked from the Task List. Archived when its parent task is done.

**AHJ Register**
13 AHJ/AHJ-REGISTER.md: one row per application to an authority having jurisdiction, with
its number, status and next action. The stage folders beside it hold the files. ADR 0013.

**Research Index**
06 Research & Existing Conditions/RESEARCH-INDEX.md: every source a person or agent may
rely on, who it came from, and its authority - official, record, professional, client,
derived or reference.

## Atlas Agent Workspace

**Run**
One agent session's work on one task. Its scratch lives in a Run Folder; its result, if a
person will read one, is filed in the numbered tree. ADR 0011.

**Run Folder**
.agent/runs/YYMMDD-slug/: everything a Run makes that no person will read, plus its RUN.md
log.

**Closed Run**
A Run Folder untouched for the map's runRetentionDays (14), named by no task list or
handoff, and fully readable. atlas runs --apply zips it into .agent/archive/ and removes the
folder once the zip has been read back and matches it file for file.
