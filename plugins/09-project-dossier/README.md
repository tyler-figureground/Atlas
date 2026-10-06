# 09 — Project Dossier

Persistent per-project state for architecture work, as plain files in the project folder. Two layers:

| Layer | File(s) | Holds | Skill |
|-------|---------|-------|-------|
| **Facts** | `PROJECT.md` | What is — project identity, use case, billing/client contacts, address, zoning, program, and code. | [`/project-dossier`](./skills/project-dossier) |
| **Reasoning** | `decisions/NNNN-*.md` | Why it is — ADR-style records: context, options, the call, consequences, status. | [`/decision`](./skills/decision) |

## Why

A building project spans months and a team. Without a dossier, every session re-derives the BBL, the district, the code edition — and the *reasoning* behind choices ("why scheme B?") gets lost in email threads and meetings. Software solved the second problem with ADRs; AEC never adopted an equivalent. These are Architecture Decision Records for actual architecture.

Atlas project intake pre-populates project identity, full address, Project Use Case, and creation-time Billing/Client Contact snapshots. Analysis skills check `PROJECT.md` before fetching, append their key findings after completing, and propose `/decision` when an analysis forces a choice.

## What this is not

- **Not agent instructions.** User preferences and firm conventions belong in the project's `AGENTS.md` (`CLAUDE.md` is only a pointer at it) or Claude Code's auto memory. The dossier holds project facts only.
- **Not a collaboration platform.** No sync, statuses dashboard, or approvals — the files live in the project folder and are shared however the project already is (git, Drive, Dropbox). That's deliberate: files outlive tools.

## Quick start

```
/project-dossier init        ← create PROJECT.md, answer a couple of questions
/zoning-analysis-nyc ...     ← analysis lands in the dossier automatically
/decision we're going with the UAP bonus scheme
```

## Skills

| Skill | What it does |
|-------|-------------|
| [`/project-dossier`](./skills/project-dossier) | Create or update `PROJECT.md` — init interview, in-place fact updates, source + date on every entry |
| [`/decision`](./skills/decision) | Record a decision in `decisions/` — numbered, statused (proposed / decided / superseded), indexed in the dossier |
| [`/tasks`](./skills/tasks) | Work the two task lists — production `TASKS.md` (claim, work, close with evidence) and Tyler's `TYLER.md` (add-only) |
| [`/meeting-closeout`](./skills/meeting-closeout) | Transcript to full closeout — minutes, decision records, facts, tasks in both lists, rebuilt brief |
