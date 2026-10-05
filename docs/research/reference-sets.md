# Reference sets: show the agent (and the junior) a good one before they start

Date: 2026-10-04
Scope: how Figure Ground should give agents and junior designers a curated example of
every deliverable type before they make one, and the plan to build it.
> **Decided 2026-10-04** (ADR 0015). Q1: sets live in `LIBRARY - Reference\00 Office
> Standards and Administration\Reference Sets\`; juniors have the drive. Q2: the third-party
> folder is renamed `Precedent Sets` (done). Q3: pilot types stand, and every set's
> exemplars span **one California residential, one code-issue, one commercial** project.
> Q4: Tyler alone approves. Q5: drawing-type sets split by entity **only for Solid Void**.
> Library naming rules apply: Title Case folders, no leading `_`, and status lives in the
> card's front matter rather than in `_candidates` / `_retired` folders (N8, N11).
> `atlas refs` and `atlas refs check` were pulled forward from Phase 5; the drive map
> (v3.4) names the folder as `referenceSets`.

Method: four research passes - learning science, LLM prompting and agent practice, AEC
office practice, and a read-only inventory of `G:\Shared drives\ARCHITECTURE` and
`G:\Shared drives\LIBRARY - Reference`. Nothing on either drive was changed.

Confidence tiers: **Strong** = meta-analysis, replicated result or official vendor guidance.
**Medium** = single study or practitioner consensus. **Weak** = vendor claim or convention.
**Measured** = counted on the drive today. **Proposed** = this document's recommendation.

---

## 0. The answer in one screen

Tyler's observation - instruction alone is disastrous, for agents and for people - is one of
the best-supported findings in both literatures. The fix is not "add an example". It is a
**Reference Set** per deliverable type:

1. A **card** (`SET.md`): when to use it, what good looks like, what not to carry over,
   a review checklist. Short enough that an agent always reads it.
2. **2-3 exemplars** from different projects that share the quality but differ on the
   surface - frozen copies, each with a `NOTES.md` saying *why* it is good, page by page.
3. **One near-miss**, labelled, with what holds it back.
4. A **skeleton** (the Atlas template, where one exists) - structure, no content.
5. A **leak list** per exemplar - the project's name, address, BIN, permit numbers,
   code edition, client - which a check greps out of every new draft.

Agents are pointed at it by one rule in every AGENTS.md block, by a Reference step in every
deliverable-making skill, and by a post-write check. Juniors get the same card plus a short
crit with Tyler the first time they make each type. Tyler is the only one who promotes an
exemplar; every set carries a review date and is retired, not deleted, when it goes stale.

The two risks the evidence names - **copying the example's facts** and **examples going
stale** - are the two the design spends the most on.

---

## 1. Findings

### 1.1 Examples beat instructions for novices, at medium effect sizes (Strong)

- Worked-example effect, math: g = .43 across 55 randomized studies (Barbieri et al. 2023).
- Case comparison beats ordinary instruction: d = .50 across 57 experiments (Alfieri,
  Nokes-Malach and Schunn 2013).
- Self-explanation (learner says *why* each step) g = .55 across 64 reports (Bisra, Liu and
  Nesbit 2018).
- Anthropic: *"Examples are one of the most reliable ways to steer Claude's output format,
  tone, and structure."* Use 3-5, relevant, diverse, wrapped so they read as examples.
- Anthropic, context engineering: don't *"stuff a laundry list of edge cases into a
  prompt"*; *"curate a set of diverse, canonical examples ... examples are the 'pictures'
  worth a thousand words."*
- Gemini guidance: *"always include few-shot examples"*.

**Implication:** a reference is the default, not an extra, for any agent and any junior
making a deliverable type they have not made well before.

### 1.2 Criteria alone cannot carry a quality standard (Medium-Strong)

- Sadler (1987, 1989, 2009): quality in complex work is a whole-work judgment. Standards
  pass on through **verbal description plus exemplars together**; neither works alone.
  Preset criteria are indeterminate and make people look only for what is listed.
- Hendry et al.; To and Carless (2016); Carless and Chan (2016): the active ingredient is
  **explanation and dialogue about the exemplar**, which shows the learner the gap between
  it and their own work. One study handing exemplars out without discussion found no
  performance gain.

**Implication:** never a checklist without exemplars, never exemplars without the card that
says what is good about them. For juniors the crit is part of the set, not optional.

### 1.3 Two compared beat one studied (Strong)

- Gentner, Loewenstein and Thompson (2003): comparing 2 cases gave a marked transfer
  advantage over studying the same 2 separately. Studying them separately was no better
  than no training at all.
- Alfieri (2013): highlighting **similarities** helped more than similarities plus
  differences.
- Liu et al. (2022): examples picked close to the task beat random ones.

**Implication:** 2-3 exemplars that differ on the surface (NYC commercial vs Napa
residential; 2 sheets vs 23) so the shared quality is the only pattern left. The card
states that shared quality in one line *after* the exemplars, not instead of them. Tag
exemplars so the agent opens the 1-2 nearest, not all of them.

### 1.4 Examples get copied - by people and especially by agents (Strong)

- Design fixation: shown an example, designers repeat its features, *flaws included*
  (Jansson and Smith 1991). Warnings that name the specific feature reduce it (Chrysikou
  and Weisberg 2005).
- The nuance (Sio, Kotovsky and Cagan 2015, 43 studies): examples **reduce variety** but
  **raise quality**, and quality correlated with copying. For production documents,
  copying structure is the point; for concept design it is a real cost.
- LLMs: demonstrations transmit **format and distribution** more than correctness (Min et
  al. 2022). Documented "copy bias" - models copy lexical content from examples (Ali, Wolf
  and Titov). When examples and instructions disagree, examples tend to win; Claude Code's
  own docs say conflicting instructions are resolved *"arbitrarily"*.
- **On this drive (Observed):** `260203_262 Monte Vista Dr-Master Bed\AGENTS.md` line 139:
  *"Reference models are a contamination vector - the Monticello / McKean content traced to
  a reference model open alongside this one."* The failure has already happened here.
- NY seal rule: a sealed set is the licensee's responsibility *"as though the licensee had
  personally prepared all the documents"* (NYSED). A carried-over code edition or address
  is a liability error, not a style flaw.

**Implication:** every exemplar carries a **leak list**, and a deterministic check greps
drafts for it - the reliable kind of grader. The card says which traits are **required**
(section order, citation form, voice) and which are **incidental** (length, palette,
phrasing). Facts come only from the project's own `BRIEF.md` / `PROJECT.md`.

### 1.5 Examples go stale; libraries rot without an owner (Medium)

- Specifiers' core risk is working from *"the latest authored section from the last
  project rather than standardized vetted information"* (AIA / Deltek). Unmaintained
  masters were found still specifying lead paint and withdrawn standards (4specs).
- NBS: *"Who is going to keep your masters up to date? Who will communicate changes?"*
  Without that, *"any advantage ... will be lost."*
- AKF: *"the proliferation of unreviewed standards were leading to employee frustration."*
- Boulder Associates collected lessons for years *"and clung to the hope that doing so
  would keep us from repeating mistakes. Nope!"* What worked was delivery *"at the right
  time"* - tied to a task, not a browsable folder.
- The library's own `Third-Party Reference Policy.md` already sets a `reviewed:` date and an
  annual sweep, with a two-year purge trigger.

**Implication:** owner, `reviewed:`, `next_review:` and the code edition on every card;
review on triggers (code adoption, skill rule change, a Tyler correction), not only by
calendar; stale sets are flagged, never silently served. Sets are reached from the task,
by rule, not by browsing.

### 1.6 Support should taper as skill grows (Strong)

- Expertise reversal: high support helps novices (d = 0.51) and hurts experts
  (d = -0.43) (Tetzlaff et al. 2025, 60 studies).
- OpenAI and DeepSeek: reasoning models often do worse with few-shot on *reasoning*.
  Exemplars should show output **shape and citation form**, not the reasoning path.
- SkillsBench (2026): curated skills +16 points on average, but 16 of 84 tasks got worse,
  and **self-generated skills gave no benefit**. "Evaluating AGENTS.md" (2026): generic
  context files lowered task success and added 20% cost.

**Implication:** three tiers per set - full exemplars (juniors, agents on a new type),
skeleton plus principles, checklist only (seniors). Exemplars are **human-curated and
Tyler-approved**, never agent-generated. Measure each type with and without its set before
assuming it helps.

### 1.7 Loading: by path, on demand, never imported (Strong)

- Claude Code `@path` imports load at launch and cost context every session; quoted paths
  and unescaped spaces silently fail to import. Every studio path has spaces.
- Skills docs: bundled files cost nothing until read; keep references **one level deep**
  from SKILL.md, because nested chains get previewed with `head` instead of read.
- Vision: AECV-Bench (2026) - text and OCR questions on drawings up to 0.95, door and window
  counting 0.40-0.55. Higher resolution and crops help most on technical drawings. Claude
  Code reads at most 20 PDF pages per call.

**Implication:** AGENTS.md carries one plain backticked path to the index, never an import.
The card names exemplar files directly. Drawing exemplars ship as cropped, captioned PNGs
(about 1500-2500 px, one point per image) plus a text sidecar; the full PDF is opened only
when needed.

### 1.8 One set can serve prompting and grading - if split (Strong)

- Anthropic evals guidance: a *"reference solution"* per task; grade the output, not the
  path; *"20-50 simple tasks drawn from real failures is a great start."*
- Reference-guided LLM judges reach human-level agreement (Zheng et al. 2023), if
  calibrated against an expert.
- Husain: expert pass/fail plus written critique becomes the judge's examples. **Never put
  test cases in the prompt** - the eval then measures copying.

**Implication:** the card's checklist is the rubric; the leak list is an automatic grader;
Tyler's corrections become near-misses and known issues. Eval inputs are projects that are
**not** exemplar sources for that type.

### 1.9 What the studio already has (Measured)

- **`LIBRARY - Reference\04 Design Process by Phase\04 Construction Documents\Reference Sets\`**
  holds 12 drawing-set packages. Ten are third-party (`REF-` RAMSA, REIS, SO-IL, BMA,
  Harris, Northwell, REX), marked *"precedent only - do not copy into deliverables"*. The
  only house item, `Solid Void - Model Drawing Set`, is one sheet-list PDF with unconfirmed
  attribution. **The name "Reference Sets" is already taken by precedent material.**
- The library's `REF-` / `_SOURCE.md` convention (source, date, reuse, local changes,
  reviewed) is a sound provenance layer. It has no pedagogy: nothing says what is *good*.
- Only `00 Office Standards and Administration` is authoritative house standard.
- **No AGENTS.md points at an exemplar.** The only exemplar reference on the drive is one
  line in Monte Vista's AGENTS.md about cover-sheet anatomy.
- The closest thing to a card: `260924_295 West Ln-Beitz Fire Cleanup\06 Research &
  Existing Conditions\Reference Drawing Sets\READ-ME-visual-references.md` - *"Borrow
  graphic clarity only"* plus how this project must differ.
- `_tools\New+ Templates\` has empty Meeting, Presentation, Site Visit and Transmittal
  folders. Every `05 Specs\_Samples` and `04 Presentation\_Templates` is empty.

Candidate exemplars by type, from the inventory:

| Deliverable type | Candidates (best first) | State |
|---|---|---|
| Code analysis memo | Monte Vista CRC + Napa (`260730_Code Analysis - CRC + Napa Amendments.md`); 211 Centre NYC (`montez-press-radio-211-centre-code-analysis.md`); Silverado phase 2 (status flags, edition table) | Strong - 3 diverse |
| Zoning memo | 1350 Grove Ct summary; 7701 Bucktown (misfiled); 1757 Coleman land use (with `_sources\`) | Strong |
| Meeting minutes | 64th Lane 260916 contractor-owner; 211 Centre 260917 pre-bid / 260929 weekly; Silverado 260914 walkthrough | Strong; 3 filename conventions in use |
| Decision record | Monte Vista 0001; Bucktown 0002 (supersedes); Monticello 0004 (proposed); 64th Lane 0010 (procurement) | Strong |
| Decision register | 64th Lane `decisions\REGISTER.md` + xlsx + exporter | Good |
| BRIEF / PROJECT / TASKS | Monticello BRIEF + PROJECT; Pestoni BRIEF + TASKS; Beitz TASKS | Good |
| Client brief / email | 211 Centre TPA filing route brief; 64th Lane window-hold email; Bucktown critical-path email | Good |
| Agency letter / records request | Silverado PBES records request; Beitz county questions + response matrix | Good |
| Research report | Silverado research package; Beitz demolition permit research; Silverado 1998 as-built review | Good |
| AHJ register | Monticello; Pestoni | Good |
| CD set | 64th Lane construction set + permit; 1757 Coleman 23 sheets; Beitz 2-sheet permit set | Good, large PDFs |
| G-series cover / general notes / code sheet | 211 Centre G000; Dekalb G002 + G007 (2025); 64th Lane G001 notes text | Partial |
| Presentation deck | 1757 Coleman concept + DD; Dekalb SD V3; 211 Centre kitchen options | Partial, 9-84 MB |
| Comment-response letter | Monticello V2-V4 (by CODE360, not the studio) | Third-party only |
| Specs, RFI, transmittal, field report, punch list, submittal review | none | **Gap** |

---

## 2. Design

### 2.1 Vocabulary (lands in `CONTEXT.md`)

**Deliverable Type** - a kind of thing the studio issues or files, keyed by a slug:
`code-analysis`, `meeting-minutes`, `cd-set`, `client-email`. One type, one set.

**Reference Set** - the curated package for one Deliverable Type: card, exemplars,
near-miss, skeleton pointer, checklist. House standard, Tyler-approved.
_Avoid_: library, precedents, samples.

**Card** - the set's `SET.md`. The one file every agent and junior reads.

**Exemplar** - a frozen, approved copy of a real deliverable, with a `NOTES.md`. Read-only:
you learn from it, you never start from it.

**Near-miss** - a real deliverable of the type that falls short in one or two named ways,
annotated with what and why.

**Skeleton** - the structure with placeholders. The start file. Where Atlas already ships
a template (`TASKS.md`, `BRIEF.md`, `AHJ-REGISTER.md`), that is the skeleton.

**Leak List** - the facts an exemplar's project owns: name, address, BIN/APN, permit and
job numbers, client and contractor names, code edition, distinctive figures. Present in a
new draft = copied.

**Precedent** - other firms' material held for comparison (the existing `REF-` packages).
Never a Reference Set, never approved for reuse.

Masters/skeletons and exemplars stay separate, as specifiers keep masters and projects
separate: the skeleton is maintained and started from; the exemplar is looked at.

### 2.2 Where it lives (Proposed)

```
G:\Shared drives\LIBRARY - Reference\00 Office Standards and Administration\Reference Sets\
  README.md                      index: type, card path, status, trigger, skill, reviewed
  Code Analysis\
    SET.md                       the card; status: candidate | approved | retired
    E1 Monte Vista - CRC Napa\                California residential
      NOTES.md                   why chosen, callouts by section, leak list
      2026-07-30 - Code Analysis - CRC and Napa Amendments.md   frozen copy
    E2 Coleman - Habitability Audit\          code issue
    E3 211 Centre - NYC Commercial\           commercial
    N1 McKean - Debug Notes Up Front\
  Meeting Minutes\
  G-Series Sheets\               entity: Solid Void
    SET.md
    E1 Coleman - Construction Set\
      NOTES.md
      Pages\                     cropped PNGs, one point each, captioned
      <G-series pages only, as a PDF>
```

Why here:
- `00 Office Standards and Administration` is the library's only authoritative section;
  exemplars are house standard.
- Shared across entities (Figure Ground, Solid Void, Space Place), like the library.
- Frozen copies, not pointers: projects keep changing after issue, and agents cannot follow
  `.lnk` or Drive shortcuts (ADR 0014).
- Paths stay near 130 characters, well under MAX_PATH.

Name clash: the existing third-party `04 ...\Reference Sets\` folder should be renamed
`Precedent Sets` so the term means one thing. See Open questions.

Public repo: the marketplace is public, so studio exemplars never go in it. Skills that
make a deliverable bundle **fictional, sanitized** examples in `examples/` for outside users,
and look for the studio set first.

### 2.3 The card (`SET.md`)

```markdown
---
type: code-analysis
title: Code analysis memo
status: approved            # candidate | approved | retired
owner: Tyler
approved_by: Tyler
approved: 2026-10-10
reviewed: 2026-10-10
next_review: 2027-04-10
skill: 10-norma:code-analysis
skeleton: none
code_editions: [2022 NYC BC, 2025 CRC + Napa amendments, 2025 CBC]
applies_to: {phase: [SD, DD, CD], use_case: [Renovation, Addition, Ground Up]}
triggers: [permit set, code cover sheet, DOB pre-filing, county pre-application]
---

# Code analysis memo

## When to use / when not
## What good looks like            5-8 qualities, each with "see E1 section 3, E2 table 2"
## The exemplars                   table: id, project, what it shows, how it differs
## Near-miss                       N1: what holds it back, in two lines
## Required vs incidental          required: section order, citation form ...; incidental: length ...
## Do not carry over               facts belong to the exemplar's project; source yours from BRIEF/PROJECT
## Known issues                    Tyler corrections that are not yet in an exemplar
## Principles only                 the 5-line version for seniors and repeat agents
## Review checklist                pass/fail lines; also the eval rubric
## Ask                             who to ask, and what is already settled here
```

Rules for the card, drawn from section 1:
- Under 150 lines, no line over 1,000 characters (ADR 0014 limits).
- "What good looks like" names the **shared** quality across exemplars and points at where
  each one shows it. Says why, with conditions: "guard noted because parapet < 30 in;
  would differ if ...".
- "Do not carry over" names specific features. Not "don't copy" in general: specific
  wording reduces fixation, generic wording does not.

### 2.4 The exemplar (`NOTES.md`)

```markdown
---
id: E1
set: code-analysis
source_path: G:\Shared drives\ARCHITECTURE\260203_262 Monte Vista Dr-Master Bed\06 Research & Existing Conditions\Code\260730_Code Analysis - CRC + Napa Amendments.md
source_date: 2026-07-30
frozen: 2026-10-10
project_use_case: Addition
jurisdiction: Napa County, CA
code_edition: 2025 CRC + Napa County amendments
tier: full
leak_list: ["262 Monte Vista", "Monte Vista", "<APN>", "<client surname>", "<permit no>"]
---

# Why this one
# Callouts                     section by section (or page by page): what to notice, why
# What it gets wrong           if anything; the flaw stays visible
```

Drawing exemplars add `pages\` - one PNG crop per point, with a caption line in
`NOTES.md`: `pages/03-code-block.png - code block order: edition, occupancy, construction
type, sprinklers; reads top-down`. A deck exemplar adds a contact sheet of every page plus
2-3 full-size key pages.

### 2.5 How an agent uses a set

One new section in `tools/atlas/src/atlas/templates/project/agents-rules.md`, so it lands
in every project's AGENTS.md on the next conform:

> **Look before you make**
> - Before you draft any deliverable, find its type in
>   `G:\Shared drives\LIBRARY - Reference\00 Office Standards and Administration\Reference Sets\README.md`.
>   Read its `SET.md`, then the 1-2 exemplars nearest this project by jurisdiction, use case
>   and size. Start from the skeleton if the set names one, never from an exemplar.
> - Facts come from this project only: `BRIEF.md`, `PROJECT.md`, `decisions/`. Form comes
>   from the exemplar. Process comes from the skill. A skill's hard rule beats an exemplar.
> - Before you hand back, check the draft against the set's Review checklist and grep it for
>   every opened exemplar's leak list. A hit is a defect: fix it, don't explain it.
> - The run receipt names the set and exemplars used: `Reference: code-analysis E1, E2`.
> - No set for this type: say so in the receipt's asks, name the nearest set you used, and
>   ask Tyler for one example. This question is always allowed.
> - Never copy from a `REF-` precedent into a deliverable.

Skills get a short `## Reference` step that names their type key and the fallback to
bundled examples. First skills, because they already make Tyler-facing files:
`10-norma:code-analysis`, `09-project-dossier:decision`, `09-project-dossier:project-dossier`,
`07-presentations:slide-deck-generator`, `04-specifications:spec-writer`,
`02-zoning-analysis:zoning-analysis-nyc`.

Enforcement follows the existing marker pattern (`rules/README.md`): the skill writes
`<!-- architecture-studio:reference: code-analysis E1,E2 -->` into the output; a Dispatcher
post-write hook reads the marker, loads those exemplars' leak lists, and fails on a hit.
No marker on a file from a deliverable skill = a warning.

### 2.6 How a junior uses a set

- **Same card.** No second document for people; one source does not drift.
- **First time on a type:** a 15-minute crit. Tyler walks the exemplars against the card
  (the dialogue step the evidence says carries the effect). After that, the card alone.
- **On submission:** three lines, "where mine differs from the exemplar and why". This is
  the self-explanation and gap-awareness step, and a cheap check against blind copying.
- **Review** uses the card's checklist, so the junior knows the test in advance.
- **Redline pairs as exemplars.** A Tyler redline plus the corrected sheet is the highest-
  value exemplar for people: it shows judgment, not just the result. Add a `redlines\`
  folder per drawing set.
- **Tiers taper:** full exemplars until a junior has made the type twice cleanly; then the
  skeleton plus Principles only; then the checklist.
- **Browsing:** the index `README.md` plus each card is the gallery. Drive's preview shows
  the PNG crops and PDFs. A web gallery is deferred until the folder proves too slow.

### 2.7 Curation and governance

| Event | What happens | Who |
|---|---|---|
| Tyler says "this one's good", or a set is issued, or a project closes out | Agent copies it into the set as a new exemplar folder, NOTES marked `status: candidate`, leak list from `PROJECT.md` | Agent |
| Promotion | Tyler reads the stub, edits "Why this one", sets `status: approved`, bumps `reviewed:` | Tyler only |
| Tyler corrects a draft | The correction becomes a line under Known issues, or the draft becomes a near-miss | Agent, same run |
| Code edition adopted (NYC cycle, CA triennial), or a skill's rules change | Every set with that edition or skill gets `next_review: now` | Agent flags, Tyler reviews |
| `next_review` passed | Index shows the set as **stale**; agents still use it but say so in the receipt | Doctor |
| Better exemplar arrives | Old one gets `status: retired` and `superseded_by:`; never deleted (claims need lineage) | Tyler |
| Annual sweep (with the library's) | Unreviewed for two years -> retire | Tyler |

Caps that keep it usable: max 3 exemplars and 1 near-miss per set; card under 150 lines.
More is not better (Sio: fewer and less typical examples did best; SkillsBench: focused
beat comprehensive).

### 2.8 Concept and design work is different

For production documents, copying structure is the goal. For design concepts, fixation is
a real cost. Design-concept sets (massing, layout options, material palettes) therefore:
- show precedents described by **principle or category** ("cantilevered entry canopies"),
  not a gallery of typical solutions;
- include one **unusual** example rather than three typical ones;
- carry no skeleton.
These come last (Phase 6).

---

## 3. Implementation plan

Each phase ends with a done-test. Phases 1-3 are the pilot; nothing scales until Phase 3
says the sets help.

### Phase 0 - Decide (half a day)

| # | Work | Done when |
|---|---|---|
| 0.1 | Tyler answers the Open questions (section 5) | Answers recorded |
| 0.2 | ADR 0015 "Every deliverable type has a reference set; agents look before they make" | `docs/adr/0015-*.md` accepted |
| 0.3 | Vocabulary from 2.1 into `CONTEXT.md` | Terms present |
| 0.4 | Rename the third-party `Reference Sets` folder to `Precedent Sets` (library Plan, previewed) | Folder renamed, `library-map.json` updated |

### Phase 1 - Build three pilot sets by hand (2-3 days agent, ~2 h Tyler)

Pilot types, chosen to cover text, control file and drawing:

1. **`meeting-minutes`** - the most frequent agent deliverable; 3 filename conventions in
   use; strong candidates (64th Lane 260916, 211 Centre 260917, Silverado 260914).
2. **`code-analysis`** - highest liability; three diverse candidates (Monte Vista CRC,
   211 Centre NYC, Silverado); near-miss: McKean (debug notes on page one).
3. **`g-series`** (cover, general notes, code summary sheet), Solid Void entity (Q5) -
   tests drawing exemplars; 1757 Coleman (CA residential), 295 West Ln Beitz (code issue),
   211 Centre (commercial), all Solid Void title blocks.

Every set's exemplars span one California residential, one code-issue and one commercial
project (Q3). Meeting minutes has no code-issue candidate yet; E2 is a stand-in until one is
held.

| # | Work | Done when |
|---|---|---|
| 1.1 | Card and NOTES templates in `tools/atlas/src/atlas/templates/reference-set/` (`SET.md`, `NOTES.md`) | Done 2026-10-04 |
| 1.2 | Index `README.md` at the Reference Sets root, with front matter like the library's section READMEs | Index lists 3 types |
| 1.3 | Freeze candidates into the three sets; draft NOTES callouts, leak lists, near-misses | Files on drive, every NOTES has a leak list |
| 1.4 | Drawing pages: crop 6-10 PNGs per drawing exemplar with captions | `pages\` populated |
| 1.5 | Strip recurring flaws before freezing: duplicate PDFs, `(1)` names, personal emails in names, long lines | None present |
| 1.6 | Tyler review: edit "What good looks like" and "Why this one", approve | `status: approved` on 3 cards |

### Phase 2 - Wire agents (1-2 days)

| # | Work | Done when |
|---|---|---|
| 2.1 | "Look before you make" section into `agents-rules.md` | Done 2026-10-04 |
| 2.2 | Atlas release; conform refreshes every AGENTS.md block | Done 2026-10-04: Atlas 0.9.0, block in all 14 projects (`_tools\logs\atlas-0.9.0-deploy-20261004-192532`) |
| 2.3 | Reference step in deliverable skills; bundled fictional `examples/` for outside users | Partial: `code-analysis` has its step and marker; `rules/reference-sets.md` covers every skill. Other skills get a step when their type gets a set; fictional examples open |
| 2.4 | Leak check: `atlas refs check <draft>` - scope from the draft's marker or `--type` / `--exemplar`, else every set; skips exemplars from the draft's own project; exit 1 on a hit | Done 2026-10-04, `tools/atlas/tests/test_refsets.py` |
| 2.5 | Dispatcher post-write hook calling 2.4 on files with the reference marker | Done 2026-10-04: `post-write-reference-check`, 18 cases; exit 2 hands leaks to the agent |
| 2.6 | Run template gains a `Reference:` line | Done for new projects; existing projects keep their copy (conform never overwrites a template) - the AGENTS.md rule asks for the line anyway |

### Phase 3 - Measure the pilot (1 day agent, 1 h Tyler)

| # | Work | Done when |
|---|---|---|
| 3.1 | Per pilot type, 3 holdout inputs from projects that are **not** exemplar sources (e.g. minutes from a Pestoni recording; a code memo for 1673 St. Helena) | Done 2026-10-04: code analysis 3 (Grove, Bucktown, Pestoni); minutes 2 (no non-source project has a transcript - other meetings on source projects, own exemplar withheld); G-series not run (agents cannot draw sheets) |
| 3.2 | Run each twice: with the set, without it (same skill, same model) | Done: 10 drafts |
| 3.3 | Grade blind: card checklist (Tyler for a sample, an LLM judge calibrated on it for the rest) + leak check | LLM judges done; Tyler calibration sample open |
| 3.4 | Decide per type: keep, fix, or drop the set | Keep both; misses folded into Known issues |

Go signal: with-set drafts pass more checklist lines and need fewer Tyler edits, zero leak
hits. A type where the set does not help gets a skeleton and checklist only (section 1.6).

**Result (Measured, 2026-10-04, n = 5 pairs, LLM judges):** with-set preferred 5 of 5.
Edits before the draft could go to Tyler 26 vs 42 (-38%); checklist 92% vs 58%; accuracy
7.6 vs 6.6, completeness 7.0 vs 6.6, usefulness 8.3 vs 6.2 (of 10). Gains were in structure,
usefulness and avoiding the worst errors; facts were not better by default (Bucktown's
no-set memo was slightly more accurate) and minutes coverage fell (the tighter drafts
dropped scope items). No draft copied an exemplar fact; the first checker raised false hits
on dates, timestamps, IDs and studio vendors, and two agents bent true facts to clear them -
fixed in Atlas 0.9.1. Full table:
`G:\Shared drives\LIBRARY - Reference\00 Office Standards and Administration\Library Administration\Evals\2026-10-04 Reference Sets Pilot\RESULTS.md`.

### Phase 4 - Expand and bring in juniors (1-2 weeks, spread out)

Next types, in order of candidate strength and frequency:
`decision-record`, `zoning-memo`, `client-email`, `client-brief`, `research-report`,
`agency-letter`, `brief-md` / `project-md` / `tasks-md` (the control files), `ahj-register`,
`cd-set` (cartoon set first, then full sets), `presentation-deck`.

| # | Work | Done when |
|---|---|---|
| 4.1 | Build each set as in Phase 1, Tyler approves in batches of 3 | Approved cards |
| 4.2 | One-page onboarding note for juniors: where sets live, the crit, the "where mine differs" lines, the tiers | Note in `00 Office Standards and Administration` |
| 4.3 | Crit on first use of each type; collect the "where mine differs" notes | First 3 crits done |
| 4.4 | Start `redlines\` pairs from live drawing reviews | First pair filed |

### Phase 5 - Tooling (after the format has survived Phase 4)

Atlas owns writes to the drives, so set tooling goes there, with `--json` per the CLI
Obligation:

| Command | What it does |
|---|---|
| `atlas refs` | List sets: type, status, reviewed, stale flag |
| `atlas refs doctor` | Every set: card front matter valid; exemplars exist; every NOTES has a leak list; card under 150 lines; no long lines; no `.lnk`; `next_review` passed -> stale |
| `atlas refs nominate <file> --type <t>` | Plan: copy into the set as a candidate exemplar folder, stub NOTES with leak list from `PROJECT.md`. Preview, confirm |
| `atlas refs promote` / `retire` | Plan-previewed front-matter edits; retire writes `superseded_by:` |
| `atlas refs`, `atlas refs check <draft>` | Built early, 2026-10-04: list with problems and stale flags; the leak check |
| Index generation | `README.md` contents block rebuilt from card front matter, between markers, like the library's `atlas:contents` blocks |

Plus: lint fails a deliverable skill with no `## Reference` step.

### Phase 6 - Fill the gaps

Types with no studio-authored candidate: **specs, RFI, transmittal, field report, punch
list, submittal review, comment-response letter**. For each, in order of upcoming need:

1. Use the third-party precedent as a temporary near-reference, marked as precedent.
2. The next real one the studio issues gets made carefully, Tyler-reviewed, and frozen as E1.
3. The set ships with one exemplar plus a skeleton; E2 and E3 follow as they are issued.

The empty `_tools\New+ Templates\` Transmittal, Meeting and Site Visit folders get skeletons
at the same time. Design-concept sets (2.8) come last.

### Ongoing

- Every Tyler correction lands in a card the same run (Known issues or a near-miss).
- Code adoption and skill rule changes trigger reviews.
- Quarterly glance at `atlas refs doctor`; annual sweep with the library.
- Holdout evals re-run when a model or a skill changes.

---

## 4. Risks

| Risk | Mitigation |
|---|---|
| Agents copy exemplar facts | Leak lists + post-write check; facts sourced from project files by rule; 2-3 diverse exemplars |
| Sets go stale | Owner, `next_review`, trigger-based review, stale flag in index, retire not delete |
| Card grows into a manual | 150-line cap; one level deep; Principles-only section for repeat users |
| Tyler becomes the bottleneck | Agents draft NOTES and cards; Tyler only edits "why" and approves; batches of 3 |
| Exemplars hurt on some types | Phase 3 measurement per type; drop to skeleton plus checklist where they don't help |
| Juniors copy instead of learn | Crit, "where mine differs" lines, redline pairs, tiers |
| Confidential client material spreads | Internal library drive only; never in the public repo; bundled skill examples are fictional |
| Large PDFs blow agent context | PNG crops + text sidecar; full PDF only by page range |

---

## 5. Open questions (answered 2026-10-04 - see the note at the top)

- **Q1 Location.** `LIBRARY - Reference\00 Office Standards and Administration\Reference Sets\`
  (recommended) vs a folder on the ARCHITECTURE drive. Do juniors have the library drive?
- **Q2 Name clash.** Rename the existing third-party `04 ...\Reference Sets\` to
  `Precedent Sets`? Recommended.
- **Q3 Pilot types.** `meeting-minutes`, `code-analysis`, `g-series` - or swap one for the
  deliverable that has hurt most lately.
- **Q4 Approver.** Tyler only, or can a named senior approve a type?
- **Q5 Entity marks.** Exemplars carry Figure Ground, Solid Void and Space Place title blocks.
  One shared set, or per entity for drawing types?

---

## 6. Sources

Learning science
- Barbieri et al. 2023, worked examples meta-analysis: https://oaks.kent.edu/hcri/meta-analysis-worked-examples-effect-mathematics-performance
- Kalyuga, Ayres, Chandler and Sweller 2003, expertise reversal: https://ro.uow.edu.au/edupapers/136
- Tetzlaff et al. 2025: https://doi.org/10.1016/j.learninstruc.2025.102142
- Sadler 1989: https://link.springer.com/doi/10.1007/BF00118558
- Sadler 2009, preset criteria: https://www.ualberta.ca/centre-for-teaching-and-learning/media-library/symposium/less-teaching-more-learning-2009/royce-sadler/articles/symposiumltmlroyce-sadlerindeterminacy-in-the-use-of-preset-criteria-for-assessment-and-grading.pdf
- To and Carless 2016: https://web.edu.hku.hk/f/staff/412/2015_Making-productive-use-of-exemplars.pdf
- Carless and Chan 2016: https://repository.hku.hk/handle/10722/234115
- Alfieri, Nokes-Malach and Schunn 2013: https://www.lrdc.pitt.edu/Schunn/papers/ContrastingCasesMeta-AlfieriEtAl2013.pdf
- Gentner, Loewenstein and Thompson 2003: https://business.illinois.edu/loewenstein/papers/Loewensteinetal%20AMLE03.pdf
- Schwartz and Bransford 1998: https://www.wright.edu/sites/www.wright.edu/files/uploads/2017/Feb/event/Schwartz_Bransford_1998_TimeForTelling.pdf
- Chrysikou and Weisberg 2005: https://researchdiscovery.drexel.edu/esploro/outputs/journalArticle/Following-the-wrong-footsteps-fixation-effects/991020531858804721
- Sio, Kotovsky and Cagan 2015 (abstract only): https://www.sciencedirect.com/science/article/abs/pii/S0142694X15000290
- Vasconcelos and Crilly 2016: https://www.repository.cam.ac.uk/handle/1810/252511
- Ezzat et al. 2018: https://metatoc.com/papers/111861-specificity-and-abstraction-of-examples-opposite-effects-on-fixation-for-creative-ideation
- Chi et al. 1989: https://pcl.sitehost.iu.edu/rgoldsto/courses/cogscilearning/chiselfexplanation.pdf
- Bisra, Liu and Nesbit 2018: https://www.gwern.net/doc/psychology/spaced-repetition/2018-bisra.pdf
- Renkl and Atkinson, fading: https://faculty.engineering.asu.edu/mre/wp-content/uploads/sites/31/2020/02/Exp_Rev_LI06.pdf
- Collins, Brown and Newman 1989: https://en.wikipedia.org/wiki/Cognitive_apprenticeship
- Lave and Wenger 1991: https://doi.org/10.1017/CBO9780511815355

LLM and agent practice
- Claude prompting best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- Skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Claude Code memory and imports: https://code.claude.com/docs/en/memory
- Effective context engineering for AI agents: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Demystifying evals for AI agents: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Vision: https://platform.claude.com/docs/en/build-with-claude/vision
- OpenAI reasoning best practices: https://developers.openai.com/api/docs/guides/reasoning-best-practices
- Gemini prompting strategies: https://ai.google.dev/gemini-api/docs/prompting-strategies
- Min et al. 2022: https://aclanthology.org/2022.emnlp-main.759
- Liu et al. 2022: https://aclanthology.org/2022.deelio-1.10
- Lu et al. 2022, order effects: https://aclanthology.org/2022.acl-long.556
- Agarwal et al. 2024, many-shot ICL: https://arxiv.org/abs/2404.11018
- Ali, Wolf and Titov, copy bias: https://arxiv.org/abs/2410.01288
- Evaluating AGENTS.md: https://arxiv.org/abs/2602.11988
- SkillsBench (figures from summary, confirm before citing in an ADR): https://arxiv.org/abs/2602.12670
- Zheng et al. 2023, LLM-as-judge: https://arxiv.org/abs/2306.05685
- Husain, LLM judge guide: https://hamel.dev/blog/posts/llm-judge/
- AECV-Bench: https://arxiv.org/abs/2601.04819

AEC practice
- AIA, specification strategies: https://www.aia.org/resource-center/proven-specification-strategies-better-built-projects
- 4specs, office masters: https://forum.4specs.com/t/master-specifications/3361
- NBS, making better use of masters: https://www.thenbs.com/knowledge/making-better-use-of-masters-
- AIA Best Practices, lessons learned: https://www.aia.org/sites/default/files/2026-02/AIA_BestPractices_Lessonslearnedapotentknowledgebuildingtool.pdf
- KA Connect, Boulder Associates lessons learned: https://knowledge-architecture.com/ka-connect-talks/operationalizing-lessons-learned-at-boulder-associates
- KA Connect, AKF content maintenance: https://www.knowledge-architecture.com/ka-connect-talks/a-sustainable-approach-to-technical-content-maintenance
- KA, Turner Fleischer: https://www.knowledge-architecture.com/blog/km-30-case-study-driving-technology-adoption-at-scale-turner-fleischer
- Autodesk, cartoon sets: https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-7FB0A890-6B81-47C5-9E27-999DB7C587F4.htm
- Architizer, redlines: https://architizer.com/blog/practice/details/young-architect-guide-architectural-redlines/
- NYSED, sealing and signing: https://www.op.nysed.gov/professions/architecture/professional-practice/sealing-and-signing
- GOV.UK Design System content pattern: https://github.com/alphagov/govuk-design-system-backlog/blob/master/docs/DESIGN_SYSTEM_CONTENT_PATTERN.md
- Alexander, A Pattern Language: https://en.wikipedia.org/wiki/A_Pattern_Language

Negative evidence
- No published insurer guidance on reusing typical details was found.
- No SOM, Gensler, HOK or Perkins&Will "golden project" program is documented publicly.
- No controlled study of how junior architects use past examples; evidence is ethnography
  (Cuff 1991) and practitioner writing.
- "Three exemplars across a quality range" is a teaching convention, not a tested number.
- Order effects and few-shot penalties on reasoning are measured on other models; untested
  on Claude for these deliverables - hence Phase 3.
