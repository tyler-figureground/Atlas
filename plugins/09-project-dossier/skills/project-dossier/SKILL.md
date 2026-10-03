---
name: project-dossier
description: Create or update the project dossier — a PROJECT.md file in the working directory holding persistent project facts (identity, site, zoning, program, code edition) plus an index of decisions. Use when starting a project, when the user says "set up the project" or "remember this for the project", or when an analysis skill needs somewhere to record findings. Facts only — to record a decision with its rationale, use /decision.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
---

# /project-dossier — Project Facts File

You maintain `PROJECT.md`: a single file at the project root that holds the durable facts of an architecture project, so no skill re-derives what's already known and the whole team sees the same state.

The dossier is the **facts layer**. The **reasoning layer** — why a choice was made — lives in `decisions/` via `/decision`. Don't mix them: PROJECT.md says *what is*; a decision record says *why it is*.

`PROJECT.md` has two parts that must agree: a **YAML front-matter machine contract** at the very top (tools read this) and **human-readable tables** below (people read these). The front-matter is the shared header every architect skill keys off — most importantly Norma, which scopes code answers from `jurisdiction`, `occupancy_group`, `construction_type`, and `sprinklered`. Your job includes keeping the two in sync.

## Usage

```
/project-dossier            → show current dossier status (or offer to init)
/project-dossier init       → create PROJECT.md, interview for the basics
/project-dossier update     → reconcile the dossier with new facts from the conversation
```

## Hard rules

1. **Every entry carries a source and a date.** `FAR 6.02 (PLUTO, 2026-06-10)` — never an orphan number. If the user states a fact verbally, the source is `client, YYYY-MM-DD`.
2. **Update in place, never duplicate.** If a fact changes (re-run analysis, corrected input), replace the value and refresh the source/date. The dossier holds current state, not history — history is git's job.
3. **Facts only.** "Zoning district: R7A" belongs here. "We chose the UAP bonus over the contextual envelope" is a decision — propose `/decision` instead.
4. **Project facts only.** User preferences, workflow habits, and firm conventions do NOT belong in the dossier — the project's `AGENTS.md` (which `CLAUDE.md` only points at) and Claude Code's auto memory handle those.
5. **Front-matter and tables stay in sync.** Every code/identity fact you write to a human table also updates the matching front-matter key, and vice-versa — they are one fact in two places. The front-matter holds the bare current value (no source/date — YAML keys can't); the table row carries that value plus its Source + Date. If they ever disagree, the table (with its provenance) is the source of truth — reconcile the front-matter to it.
6. **Contact snapshots are project history.** Atlas records Billing Contact and Client Contact directory IDs plus creation-time details. Preserve those snapshots during unrelated updates. A later shared-directory edit does not silently rewrite an existing project; change a project contact only from an explicit user correction.
7. **Project Use Case is not occupancy.** Renovation, Addition, Feasibility, and related intake labels describe the engagement. Never copy them into `occupancy_group` or infer an IBC use group from them.
8. **No tasks, no session logs.** Open items, action lists and next steps go in `00 Tasks/TASKS.md` - the project's one live task list, which Atlas creates from the studio template. What an agent session did goes in its run folder's `RUN.md` under `.agent/runs/`. Neither belongs in the dossier: both grow without bound and bury the facts other skills read. Before editing `PROJECT.md`, copy it to `.agent/backups/`, never beside it at the project root.

## The machine contract (front-matter)

The YAML block at the top of `PROJECT.md` is the contract every architect skill reads. Use exactly these keys — tools look them up by name:

| Key | Type / values | Mirrors (human table) | Notes |
|-----|---------------|-----------------------|-------|
| `project` | free text | Identity → Project | display name; `name` is an accepted alias |
| `address` | free text | Identity → Address / BBL | formatted full project/site address; not a contact mailing address |
| `address_street`, `address_unit`, `address_city`, `address_state`, `address_postal_code` | strings | Identity → Address / BBL | Atlas structured site-address components; street is physical, never a PO box |
| `description` | free text | Identity → Descriptor | optional folder qualifier |
| `project_use_case` | canonical label or custom Other label | Identity → Project Use Case | engagement classification; not IBC occupancy |
| `project_use_case_category` | canonical label | Identity → Project Use Case | preserves `Other` when the display value is custom |
| `billing_contact_*` | flat contact snapshot fields | Identity → Billing rows | suffixes: `id`, `name`, `email`, `phone`, `company`, `address` |
| `client_contact_*` | flat contact snapshot fields | Identity → Client rows | same suffixes; client may differ from billing |
| `jurisdiction` | `nyc` \| `california` \| `other` | Identity → Jurisdiction | **drives Norma's corpus + edition** |
| `edition` | string | Code → Building code edition | blank → derived from `jurisdiction` |
| `occupancy_group` | `B`, `"A-2"`, or list `[B, "S-1"]` | Code → Occupancy group | IBC use group(s) |
| `construction_type` | `I-A`, `II-B`, `V-B`, … | Code → Construction type | IBC Ch.6 |
| `sprinklered` | `true` \| `false` \| `"NFPA 13"` … | Code → Sprinklered | bool or system string |
| `stories` | integer | Code → Stories | above grade plane |
| `building_area_sf` | number | Code → Building area (SF) | whole-building vs fit-out → note in table |
| `frontage_ft` | number | Code → Frontage (ft) | Ch.5 area-increase input |
| `existing_co_occupant_load` | number | Code → Existing C-of-O occupant load | from the existing Certificate of Occupancy |
| `existing_exits` | integer | Code → Existing exits | exits serving the space today |
| `place_of_assembly_strategy` | free text | Code → Place-of-assembly strategy | e.g. "stay under 75 occ" |
| `tenancy` | `single` \| `multi` | Code → Tenancy | tenant configuration |

Rules for the block:
- **Blank means unknown, not a default.** Norma ignores blank fields and falls back to its own examples; it never assumes a value you didn't write. (So don't pre-fill `jurisdiction: other` on a project you haven't scoped — leave it blank.)
- `jurisdiction` is canonical — write `nyc`, `california`, or `other`. Free-form forms ("New York City", "ca") are tolerated but normalize to those three.
- This block carries **values only** — no source/date. Provenance lives in the matching table row.
- **Quote ZIP codes:** `address_postal_code: "02134"`. Unquoted, a YAML reader turns `02134` into the number 1116 and drops the leading zero.

### Atlas-owned keys and rows

Atlas (the studio drive tool) creates the dossier at project intake and edits the intake facts later, so it shares this file with you. It parses only its own keys and rows, carries every other line through untouched, and refuses — naming the problem — any shape below it cannot rewrite safely. Keep these shapes:

- **Front-matter keys Atlas owns:** `project` (or its alias `name`), `address`, `address_street`, `address_unit`, `address_city`, `address_state`, `address_postal_code`, `description`, `project_use_case`, `project_use_case_category`, `billing_contact_*`, `client_contact_*`. Each is a **flat scalar on one line**: plain, `'single'`- or `"double"`-quoted, optionally followed by ` # comment`. Never a list, a block, or a value continued on the next line. Every other key (`occupancy_group: [B, "S-1"]`, block lists, anchors) is yours to shape freely.
- **One address, three places.** `address`, the `address_*` components, and the Identity → Address / BBL row must agree. When you correct the site address, update all three in the same pass; Atlas refuses to edit a dossier whose `address` or Address / BBL row disagrees with the components rather than guess which is right.
- **Contact names** (`*_contact_name`) are `First Last`. `*_contact_id` is the shared-directory UUID; never invent one.
- **Identity rows Atlas owns:** Project, Address / BBL, Project Use Case, Client, Billing Contact / Email / Phone / Company / Address, Client Contact / Email / Phone / Company / Address, Descriptor, Created. Keep the shape `| Field | value (source, date) |`: **the value first**, provenance after it. When Atlas changes a value it replaces only that leading value and keeps the provenance; rows whose value did not change are left byte-for-byte. One row per field. Table padding is fine.
- **Created** starts with the date, `YYYY-MM-DD`; provenance may follow. Atlas never rewrites it.
- **Client** is a human fact. Atlas seeds it with the client contact's name and keeps it in step only while it still holds that name; once you write something else there, Atlas leaves it alone.
- **Top heading.** Atlas's heading is the folder name, and follows a folder rename. Any other heading (the template's `# Project Dossier — …`) is left alone.
- **Encoding.** Atlas writes UTF-8, CRLF line endings, a trailing newline, no BOM. It reads LF and a missing final newline too, and writes its own form back on the next edit.

**Round-trip check:** from a folder holding a filled `PROJECT.md`, `norma project active` returns that project's jurisdiction / occupancy / construction / sprinklered. That is the contract working.

## On `init`

1. If `PROJECT.md` already exists, say so and switch to `update` mode.
2. Ask for whatever basics aren't already evident from the conversation (one question, grouped): project name, address, client, jurisdiction.
3. Write `PROJECT.md` from the template below, filling what you know, leaving the rest blank. **Write the front-matter and the human tables together** — every fact you fill goes in both the machine contract (top) and its mirror row, with source + date on the table side.
4. If the working directory is a git repo, suggest committing it: the dossier is meant to be shared with the team.

## On `update`

1. Read `PROJECT.md` — both the front-matter and the tables.
2. Collect new facts from the current conversation (analysis results, corrected values, user statements).
3. Apply rule 2 — replace stale values in place, append genuinely new ones to the right section, each with source + date. When a fact maps to a front-matter key, **update the key and its mirror row in the same pass** (rule 5). If the file has no front-matter yet (an older dossier), add the block from the template while you're there.
4. Show a short diff-style summary of what changed.

## Template

```markdown
---
# ── Machine contract ──────────────────────────────────────────────────────
# Tool-authoritative project facts. Norma and other architect skills read THIS
# YAML block, not the prose below. Keep it in sync with the Identity + Code
# tables (the human mirror). Provenance — source + date — lives in those tables;
# this block carries only the current value each tool reads. Leave a field blank
# when unknown (a blank field is ignored, not assumed).
project:                     # display name (free text)
address:                     # formatted full project/site address
address_street:              # physical numbered street; never a PO box
address_unit:                # optional
address_city:
address_state:               # two-letter US state
address_postal_code:         # ZIP or ZIP+4, quoted: "02134"
description:                 # optional folder qualifier
project_use_case:            # display label; custom value when category is Other
project_use_case_category:   # Renovation | Addition | Renovation + Addition | Ground Up | Feasibility | Existing Conditions | Code Compliance | Other
billing_contact_id:          # shared Atlas contact UUID
billing_contact_name:
billing_contact_email:
billing_contact_phone:
billing_contact_company:
billing_contact_address:
client_contact_id:           # shared Atlas contact UUID
client_contact_name:
client_contact_email:
client_contact_phone:
client_contact_company:
client_contact_address:
jurisdiction:                # nyc | california | other  → drives the governing corpus + edition
edition:                     # blank → derived from jurisdiction; pin a string only to override
occupancy_group:             # IBC use group(s): B, "A-2", or a list [B, "S-1"]
construction_type:           # IBC Ch.6 type: I-A, II-B, III-A, IV, V-B …
sprinklered:                 # true | false | system string ("NFPA 13", "NFPA 13R", "none")
stories:                     # stories above grade plane (integer)
building_area_sf:            # area in SF (note whole-building vs fit-out in the Code table)
frontage_ft:                 # public-way / open-space frontage in feet (Ch.5 area increase)
existing_co_occupant_load:   # occupant load on the existing Certificate of Occupancy, if any
existing_exits:              # number of existing exits serving the space, if known
place_of_assembly_strategy:  # PA approach, e.g. "stay under 75 occ" or "file PA permit"
tenancy:                     # single | multi  (tenant configuration)
---

# Project Dossier — {project name}

> Maintained by Architecture Studio skills and the project team.
> Every entry carries a source and a date. Facts only — rationale lives in the decisions/ directory.
> The YAML front-matter above is the machine mirror of the Identity + Code tables — keep them in agreement.

## Identity

| Field | Value |
|-------|-------|
| Project | |
| Address / BBL | |
| Project Use Case | |
| Client | |
| Billing Contact | |
| Billing Email | |
| Billing Phone | |
| Billing Company | |
| Billing Address | |
| Client Contact | |
| Client Email | |
| Client Phone | |
| Client Company | |
| Client Address | |
| Descriptor | |
| Created | |
| Jurisdiction | |
| Virtual tour | |

<!-- Virtual tour: Matterport / iGuide / video walkthrough links. Several → one per line or " · "-separated. Blank until a scan exists. -->

## Site

<!-- site-planner skills append here: climate, flood, transit, demographics, context -->

## Zoning

<!-- zoning skills append here: district, FAR, envelope results, overlays, landmark status -->

## Program

<!-- programming skills append here: headcount, space program, occupant loads -->

## Code

<!-- Mirrors the machine contract in the front-matter. Change a value here → change it there too. -->

| Item | Value | Source | Date |
|------|-------|--------|------|
| Building code edition | | | |
| Occupancy group | | | |
| Construction type | | | |
| Sprinklered | | | |
| Stories | | | |
| Building area (SF) | | | |
| Frontage (ft) | | | |
| Existing C-of-O occupant load | | | |
| Existing exits | | | |
| Place-of-assembly strategy | | | |
| Tenancy | | | |

## Decisions

<!-- maintained by /decision — do not edit by hand -->

| # | Decision | Status | Date |
|---|----------|--------|------|
```

## How other skills use the dossier

Identity rows with no front-matter key (Virtual tour, …) are human-only facts; tools that need them parse the table. Atlas intake rows for Project Use Case and Billing/Client Contact snapshots have matching flat front-matter keys.

Analysis skills in this marketplace check for `PROJECT.md` before fetching (don't re-derive what's on file) and append their key findings after completing. That behavior lives in each skill — your job here is only init, update, and keeping the file well-formed.

**Norma reads the front-matter, not the tables.** The `10-norma` code skills (`/ibc`, `/egress`, `/code-analysis`, …) call `norma project active`, which parses the YAML front-matter into the active project profile and auto-scopes every code answer to it. That is the whole reason the machine contract exists and the whole reason it must stay in sync — a stale front-matter key silently scopes a code analysis to the wrong jurisdiction or occupancy. When a Norma analysis hands back a corrected fact (e.g. it determined the construction type), fold it back in via `update` so the contract and the cited sheet agree.

## Edge cases

| Situation | Handling |
|-----------|----------|
| `PROJECT.md` exists but malformed / hand-edited | Preserve all content; reorganize into template sections; say what moved |
| `PROJECT.md` predates the front-matter (no YAML block) | Add the machine-contract block from the template, populated from the existing tables; don't disturb the prose |
| Front-matter and a table disagree | The table (sourced + dated) wins — reconcile the front-matter to it; note the fix |
| Facts conflict (dossier says X, user says Y) | Ask once; the answer wins; update with new source + date |
| No project context at all, user just ran `/project-dossier` | Show usage and ask if they want `init` |
| Multiple projects in one directory | One dossier per directory — suggest separate working directories |
