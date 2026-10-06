# /tasks

Works the project's two task lists: `00 Tasks/TASKS.md` (production - model, sheets,
research, drafting; lanes `AGENT`/`MODEL`/`DECISION`/`WAIT`) and `00 Tasks/TYLER.md`
(Tyler's personal errands - add-only for agents, never checked off by them).

## Usage

```
/tasks next        → claim the top unblocked AGENT/MODEL task and start it
/tasks add <item>  → file to the right list and lane
/tasks done T-NNN  → close with evidence
/tasks hold T-NNN  → move to Holds with what clears it
/tasks prune       → archive Done items older than 30 days
```

Claiming is first-class: an item being worked sits in **In progress** with
`claimed YYYY-MM-DD by <name>`, so a second agent - or a teammate in the office -
does not double-pick it. Tyler's errands are his alone; agents pre-draft artifacts
(`ready:` link) but never send and never check off.

Companion: [`/meeting-closeout`](../meeting-closeout) writes both lists from meeting
minutes. Facts in [`/project-dossier`](../project-dossier); reasoning in
[`/decision`](../decision). ADR 0016.
