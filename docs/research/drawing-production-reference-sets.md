# Drawing production: reference sets that agents can check against

Date: 2026-10-05
Scope: how agents producing Revit construction documents through Pyvoid should be given -
and held to - a reference for each sheet type. Extends `reference-sets.md` (ADR 0015), which
covered text deliverables, to drawings, which Tyler names as the real problem area.
Method: three passes - drive evidence across 64th Lane (64L), Montez (MPR), Monte Vista (MV),
Beitz / 315 West Ln (BZ) and Silverado (SV); a survey of Pyvoid's standards and model-reading
tools; outside practice and 2026 evidence on drawing QA and AI vision. Nothing was changed.

> **Decided 2026-10-05 (Tyler).** **Pyvoid owns the drawing standards and every check.** This
> repo and its agents do not draft standards or build sheet checks; they hand Pyvoid evidence
> and requirements, and follow through until Pyvoid delivers. Reference sets on the library
> drive carry exemplar sheets and redline pairs and **cite S+V rule ids; they never define
> rules** - so `RULES.yaml` below becomes a list of the Pyvoid rule ids each set relies on.
> Tyler is fixing the internal standards himself. Sheet-type priority: **plans** (always first),
> **schedules**, **RCPs and details**, **elevations**, **G-series** (Q1 answered). Handed to
> Pyvoid the same day: evidence on #2888 (sheet critic, CD-set extension), Tyler's composition
> rulings on #769 (PRD-199 / VS-006), new issue #3095 (model-side compliance check).

Confidence: **Measured** = counted in project records or the Pyvoid defect corpus.
**Observed** = seen in specific files. **Strong / Medium / Weak** for outside sources.
**Proposed** = this document's recommendation.

---

## 0. The answer in one screen

The text-deliverable fix was "show a good one". For drawings that is necessary and not
enough: agents already work from written standards (S+V-AS-001 annotation, DS-002 dimensioning,
TS-003 tagging, GN-004 notes, RS-005 symbols), and sheets still fail - because **nothing checks
the printed sheet against them**. About 34 of 218 standard rules are coded, none geometric, and
the typography numbers are data no code applies.

So a drawing reference set is four things, per sheet type:

1. **A sheet standard in rules** (`RULES.yaml`): every rule tagged `print` (checkable on the
   exported PDF), `model` (checkable through Pyvoid's API) or `tyler` (judgment only).
2. **An approved exemplar sheet**: PDF + per-block crops, callouts keyed to rule IDs.
3. **A redline pair**: a real failed sheet beside Tyler's markup - for juniors, and as a test
   that the checks catch what Tyler caught.
4. **A sheet check** an agent must pass before Tyler sees a sheet, **print first**: export the
   PDF, then check the PDF. The drive's worst failures (agent text printed on issued sheets,
   content off the sheet, blank schedules) were invisible to model checks and obvious on paper.

Build order follows the evidence: the print check first (cheap, catches the costliest class,
a labelled test fixture already exists), then one consolidated drawing standard from Tyler's
scattered rulings, then sheet-type sets in rework order - dimensioned plans and interior
elevations, G-series, schedules and legends, details, RCPs, exterior elevations and sections.

---

## 1. What goes wrong (Measured / Observed)

| Class | Projects | Example | Cost |
|---|---|---|---|
| A. Internal text printed on sheets - hold codes, agent notes, hedges, placeholders | 4 of 5 | BZ: 212 of 228 blockers were hold codes or agent meta-text, on 43 of 50 PDFs for 5 days, including the PDF sent to the County | BZ full text rewrite; "a regex lint at export would have caught every one" |
| B. Annotation collisions, text on linework, stacked tags | 5 of 5 | 64L: 43 pairs, then 109 detector findings; A222 x28. BZ: 167 text-on-text, 214 linework-through-text | 64L: 4 annotation rounds, a 12-round fix campaign, 2 readability rounds, 3 layout rounds |
| C. Content off the sheet or in the title-block strip | 4 of 5 | 64L wall schedule 10.7 in off the bottom; MPR viewport outline wrong by 2.57 in, overhang found by Tyler by hand | Re-layouts on every project |
| D. Dimension logic - datum, targets, overrides, unprinted dims | 4 of 5 | 64L baseline: 198 strings off the datum, 156 wrong datum, 64 of 258 dims not printing; Revit auto-deleted three | ~22 documents, 7 phases in 3 days |
| E. Wrong things in views - templates, phases, visibility | 3 of 5 | AC clearance lines on RCPs; elevations misnamed by 90 degrees | Per-sheet fixes |
| F. Broken schedules and legends | 4 of 5 | MV finish schedule shipped header-only after every data check passed; MPR schedule filter prints empty | Found only by looking at the print |
| G. Cross-references, numbering, identity out of sync | 4 of 5 | BZ 295 / 317 address conflict on the issued set; dead A502 references | Reissue |
| H. Content from another project or template | 2 of 5 | MV: 21 wrong-project notes from a reference model | 20-term sweep now mandatory on MV |
| I. Wrong source or settled scope re-asked | 2 of 5 | Full catalog electrical legends on plans; settled scope re-asked on MPR | Tyler's time |

**Review loops (Measured):** MPR Phase 2 A100, one sheet, review PDFs r4 to r38. BZ G-001/G-002,
47 drafts, then finished by Tyler by hand. 64L full-size QA reached v10.

**The pattern:** model-side checks passed while the print failed (F, C). The print is the
deliverable; the check has to run on it.

**Rework by sheet type (Measured, ranked):** 1 dimensioned plans and interior elevations;
2 G-series; 3 interior casework elevations (collision density); 4 single-sheet bid compositions;
5 schedules and legends; 6 details; 7 RCPs; 8 exterior elevations and sections.

## 2. What already exists

- **A written standard** in `C:\Users\YOLOTRON\Documents\GitHub\Pyvoid\docs\standards\`: S+V-00
  framework, AS-001 annotation, DS-002 dimensioning, TS-003 tagging, GN-004 general notes,
  RS-005 reference symbols. VS-006 sheet composition is planned (PRD-199), not written.
- **Typography as data**, unapplied: `annotation_standard.json` (notes 3/32", titles 1/4",
  Arial Narrow, leader terminators, 0.25 in viewport-edge clearance), `dimensioning_standard.json`,
  `tagging_standard.json`.
- **Model reads an agent can call** (Pyvoid MCP): sheets and viewports, view scale and
  template, `diff_view_templates`, type parameters, tags, dimensions with override flags via
  `get_text_inventory`, annotation crop, schedule data, `capture_view`; a sheet-level overlap
  sweep; an issue-readiness check; visual regression against a baseline image.
- **Gaps:** no check compares a sheet to a declared standard; most needed reads are on the
  full server only; no title-block region map, printable area or scale-fit table (PRD-199);
  no in-view collision engine (PRD-235 SheetInk); `print_to_pdf` unreliable (#2343); open
  sheet-critic PDF-pass issues #2888, #2913, #2917, #2918.
- **A labelled test fixture:** `C:\Users\YOLOTRON\Documents\GitHub\Pyvoid\docs\research\beitz\2889-defect-corpus.md`
  (1,031 deduplicated defects across 50 BZ PDFs) with `2889-acceptance-fixture.json`
  (must-flag and must-not-flag lists) against
  `G:\Shared drives\ARCHITECTURE\260924_315 West Ln-Beitz Fire Cleanup\295West-G001-G002-FOR-AGENCY-REVIEW.pdf`.
- **Tyler's rulings, scattered:** 64L `PROJECT.md` "Documentation conventions and Tyler rulings";
  MPR `PROJECT.md` `composition:`; MV `PROJECT.md` "Drafting standards" and `AGENTS.md` G000
  conventions; BZ `AGENTS.md` sheet-text rule. Each project re-learns them.

## 3. Outside evidence

- **Check in the model and on the print, not by eye** (Strong). 2026 benchmarks: frontier
  models read drawing text at about 0.95, count doors at 0.16-0.39 (AECV-Bench), place line
  endpoints at 22% at best (CrossProjection). Vision is for teaching and a gestalt glance
  against the exemplar crop, never for counts, dimension chains or references.
- **Firms codify text sizes, dimension styles, view templates and sheet format, then lock them
  in the template** (Strong: AEC UK BIM Protocol §9 - fixed text sizes, no dimension overrides,
  dims never cross, text never on lines; NCS UDS sheet organization). **Per-sheet-type content
  rules are not published anywhere** - the studio's own rulings are the source.
- **Commercial QA tools agree on the check menu** (Strong: Autodesk Model Checker, Ideate
  Annotate / Explorer / StyleManager): non-approved text and dimension types, dimension value
  overrides, views without the right template, annotation clashes, blank or hidden tags,
  untagged doors / windows / rooms, zero-length dimensions, views not on sheets, sheet naming,
  revision consistency.
- **Revit text bounding boxes are oversized** (Medium), so model-side overlap checks give false
  positives. **PDF text extents are exact** - a further reason to check the print.
- **Redlines carry the judgment** (Strong: WSDOT colour code - red add/correct, green delete,
  yellow checked). Design error is 57% of A/E claims (Victor) - the "tyler" rules stay human.

## 4. Design (Proposed)

### 4.1 One drawing standard, then sets per sheet type

- **S+V-VS-006 Sheet Composition** (already planned in PRD-199) becomes the home for Tyler's
  scattered rulings that hold studio-wide: view-title band and alignment, plan/RCP pairing on
  one datum, reading-order numbering, revision clouds on sheets, horizontal leader shoulders,
  key plan, standard scales, north arrows on overall plans, "contract-document language only",
  text floor 3/32", dimension type and anchors. Project files keep only project facts and
  deliberate deviations.
- Each sheet-type reference set points at the standard and adds what is specific to its type.

### 4.2 The sheet-type set

```
Reference Sets\
  Floor Plans\            (and Interior Elevations, G-Series Sheets, Schedules and Legends,
    SET.md                 Details, RCPs, Exterior Elevations and Sections)
    RULES.yaml            rule id, text, kind (print | model | tyler), check, source ruling
    E1 ...\  NOTES.md, <sheet>.pdf, Pages\NN-*.png   callouts cite rule ids
    R1 ...\  NOTES.md, before.pdf, redline.pdf       a real failed sheet and Tyler's markup
```

- `RULES.yaml` is the contract. A rule without a check is labelled `tyler`, honestly.
- Callouts in an exemplar cite rule ids, so the junior's explanation and the agent's check say
  the same thing.
- Redline pairs come from the drive's own history: 64L A220-A222 (stacked tags on casework
  hatching), MV finish schedule (header only), BZ G-001/G-002 (internal text), MPR A100 r4.
  Each redline mark is tagged with the rule it violates; the pair is also a regression test.

### 4.3 The sheet check - print first

| Stage | What | Catches | Where it runs |
|---|---|---|---|
| 1. Export | Sheet to PDF (workaround in #2343 until fixed) | - | Pyvoid |
| 2. Print text lint | Hold codes, agent meta-text, hedge words, `?` and `XX.XX` placeholders, bid language, contamination terms, leak lists, address and project identity | A, G, H | PDF text, no Revit needed |
| 3. Print geometry | Text and linework outside the border or in the title-block strip; text below the size floor; text-on-text overlaps from exact PDF extents; empty or header-only schedule regions | B (text), C, F | PDF geometry |
| 4. Model compliance | Title block and type allowlist; view template and scale per viewport; text and dimension types vs the standard's typography; dimension value overrides; untagged required categories; annotation crop | D, E, typography | Pyvoid MCP reads |
| 5. Exemplar glance | Rendered block crops beside the exemplar crops: crowded, empty, missing title - questions only | gestalt | vision, advisory |

Stages 2-3 run on the PDF alone, so they can ship before any new Revit API work and they
check what Tyler actually reads. Every finding cites a rule id. A sheet goes to Tyler only
with stages 2-4 clean or each remaining finding named.

### 4.4 How agents and juniors use it

- `agents-rules.md` "Look before you make" already applies; a drawing run adds: export, run
  the sheet check, attach its report to the run receipt.
- Juniors: the same card and exemplar; the redline pair first; Tyler's 15-minute walk-through
  on first use of a sheet type.

## 5. Implementation plan

| Phase | Work | Done when |
|---|---|---|
| **A. Print gate** | Stages 2-3 as one command (Pyvoid, under the existing sheet-critic PDF-pass issues #2888 / #2917 / #2918), rules read from a `RULES.yaml`. Test on the BZ acceptance fixture | Fixture: every must-flag caught, no must-not-flag; then re-run on MPR A100 r4 and MV finish schedule |
| **B. One drawing standard** | Consolidate Tyler's rulings from 64L, MPR, MV, BZ into S+V-VS-006; mark each as studio-wide or project deviation; Tyler reviews | VS-006 written; project `PROJECT.md` tables trimmed to deviations |
| **C. First two sheet-type sets** | Floor Plans (exemplars 64L A123 re-exported after the layout pass, MV A101/A102; redline 64L A220-series) and Interior Elevations (MV A622/A623; redline 64L A220-A222). `RULES.yaml` per set | Tyler approves both cards |
| **D. Model compliance** | Stage 4: a "reference card check" composing existing Pyvoid reads; typography applied to real types; move needed reads onto the designer server | Passes on the exemplars, flags the redline sheets |
| **E. Remaining sets** | G-series (exists - add `RULES.yaml`), Schedules and Legends (64L A800 / P205; near-miss MV finish schedule), Details (MPR Phase 2 A100), RCPs, Exterior Elevations and Sections (SV A200, 64L A300) | Cards approved |
| **F. Measure** | Rounds to acceptance per sheet (baseline: r4-r38, 47 drafts), defects reaching Tyler per sheet, issued-set defects | Tracked per sheet; reported monthly |

Phase A is days, not weeks: PDF text and geometry need no new Revit access, the failure class
it targets is the one that reached the County, and the test fixture is already labelled.

## 6. Open questions (answered 2026-10-05)

- **Q1** Sheet-type order: plans, schedules, RCPs and details, elevations, G-series (Tyler).
- **Q2** Checks live in Pyvoid - print and model alike.
- **Q3** Pyvoid writes VS-006 and every standard; this side supplies inputs only.

## 7. Who does what, and the follow-through

| Work | Owner | Tracked at | This side's part |
|---|---|---|---|
| Print critic extended to CD sheets, plans first | Pyvoid | #2888 | Evidence and fixtures posted 2026-10-05; check progress, add fixtures as sets are built |
| VS-006 sheet composition standard | Pyvoid | #769, #770 | Tyler's rulings posted 2026-10-05 |
| Model-side compliance check | Pyvoid | #3095 | Filed 2026-10-05 |
| Internal standards corrections | Tyler | - | - |
| Plan reference set: exemplars + redline pairs, citing rule ids | This side | Library drive | Next: from 64L A123 (re-export after the layout pass) and MV A101 / A102; redline 64L A220-series |
| Then schedules, RCPs and details, elevations, G-series sets | This side | Library drive | In Tyler's order |

Follow-through: before each new set, re-read #2888, #770 and #3095; a set ships once the rule
ids it cites exist in Pyvoid. Phases A, B and D in section 5 are Pyvoid's; C, E and F stay here.

## 8. Sources

Drive: the project files cited in section 1, chiefly
`G:\Shared drives\ARCHITECTURE\260301_80-23 64th Lane-Refactored Design\12 Construction Administration\`,
`G:\Shared drives\ARCHITECTURE\260527_211 centre street ny-Montez Radio (MPR)\PROJECT.md`,
`G:\Shared drives\ARCHITECTURE\260203_262 Monte Vista Dr-Master Bed\PROJECT.md`,
`G:\Shared drives\ARCHITECTURE\260924_315 West Ln-Beitz Fire Cleanup\AGENTS.md`.
Pyvoid: `docs\standards\`, `STANDARDS-AUDIT.md`, `mcp_server\pyvoid_mcp\jdp\data\`,
`docs\research\beitz\2889-defect-corpus.md`; issues #2343, #2368-#2371, #2888, #2913-#2918,
PRD-199, PRD-235.
Outside: AEC (UK) BIM Technology Protocol v2.1.1
https://aecuk.wordpress.com/wp-content/uploads/2015/06/aecukbimtechnologyprotocol-v2-1-1-201506022.pdf ;
NCS https://www.csiresources.org/standards/ncs ; Autodesk Model Checker
https://interoperability.autodesk.com/modelchecker.php ; Ideate Annotate
https://ideatesoftware.com/15-15-2d-annotation-excellence-using-ideate-annotate-review ;
Revit API text extents https://blog.autodesk.io/detailed-2d-text-and-other-element-geometry/ ;
WSDOT QC colour code https://wsdot.wa.gov/publications/manuals/fulltext/M3082/AppendixE.pdf ;
Victor A/E risk charts https://www.victorinsurance.com/content/dam/victor/victor2/documents/victor-canada/english/risk-analysis-charts/AE-Risk-Analysis-Charts_E.pdf ;
AECV-Bench https://arxiv.org/abs/2601.04819 ; DrawingVQA https://www.alphaxiv.org/abs/2607.15418 ;
CrossProjection https://arxiv.org/abs/2608.00473 .
