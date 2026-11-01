# PROJECT.md YAML front-matter is the shared machine contract every architect skill reads

## Status

accepted

## Context

The facts that actually govern a code answer - jurisdiction, occupancy group, construction
type, sprinklered, the existing C-of-O occupant cap, the Place-of-Assembly strategy, the
tenancy - had nowhere consistent to live. They were scattered across spreadsheets, Google
Docs, and ad-hoc `Context.md` files the tools can't read (Norma BL-013), and nothing checked
that the scope Norma adopted actually matched the drawing under review (Norma BL-014). The 211
Centre review made this concrete: Norma's `project.py active` returned a *different* job (FiDi
Office), and the controlling facts (existing C-of-O cap = 74 floor-wide, PA strategy, existing
2 exits, multi-tenant floor) only existed in an external `Context.md` that didn't fit the thin
`projects/*.yaml` schema.

Two separate tools needed the same facts from the same place: this repo's `09-project-dossier`
skill (which *writes* a project's facts as it interviews the architect) and the Norma engine
(which *reads* them to auto-scope a calculation). A human-readable dossier table alone is not
machine-parseable; a separate Norma-only profile file would re-introduce the re-keying the
dossier exists to remove.

This record concerns a contract that spans two repos - the `skills-for-architects` dossier
that writes it and the Norma engine that reads it. It is recorded here, in
`skills-for-architects`, because this repo *authors* the contract: the `09-project-dossier`
skill defines, populates, and maintains the `PROJECT.md` front-matter, so the schema's source
of truth and its decision record live together. (This ADR establishes the repo's `docs/adr/`
convention; the Norma engine - the contract's consumer - references this decision from its own
`docs/adr/`.)

## Decision

Reuse the dossier's `PROJECT.md` as the **one** project file, and put a compact YAML
**front-matter block** at its head that is the shared machine contract for every architect
skill. The human dossier tables stay below it; `Context.md` remains optional narrative;
`decisions/` holds rationale.

- **The contract is the front-matter keys.** Twelve governing keys -
  `jurisdiction (nyc|california|other)`, `edition`, `occupancy_group`, `construction_type`,
  `sprinklered`, `stories`, `building_area_sf`, `frontage_ft`, `existing_co_occupant_load`,
  `existing_exits`, `place_of_assembly_strategy`, `tenancy` - plus optional `project`/`name`
  and `address`. The last four close Norma BL-013 directly: they are exactly the facts that
  decide an egress answer and had no schema slot before.
- **The dossier writes it; the engine reads it.** `/project-dossier init`/`update` populates
  and maintains the front-matter and mirrors the key rows into human tables (the table stays
  the source of truth for provenance; front-matter and tables are kept in sync). Norma's
  `project.py` resolves the active profile by reading the workspace `PROJECT.md`
  front-matter, falling back to the engine's `projects/*.yaml` examples when no real
  front-matter is present.
- **Blank means unknown.** Only a `PROJECT.md` whose front-matter carries a real
  `jurisdiction`/`occupancy_group`/`edition` is adopted as scope; an all-blank stub (what
  `New-Project.ps1` scaffolds) correctly falls through to the engine examples rather than
  hijacking scope with empty values.
- **Scope is guarded, not assumed (Norma BL-014).** Norma's `project.py scope-check
  <address-or-name>` compares the active project's name/address against a supplied string
  (e.g. the drawing's title-block address) by ≥3-char token overlap and warns - non-zero
  exit - before the wrong jurisdiction/occupancy/sprinkler scope is silently adopted.

## Consequences

One file now carries both the human dossier and the machine scope, so the architect keys a
fact once and every skill - studio and Norma alike - reads the same value; closes Norma BL-013
(the governing facts have a representable home) and BL-014 (the scope-check guard). The
round-trip is proven: a dossier-produced `PROJECT.md` (CA / A-2 / II-A / NFPA 13) resolves
through `norma project active` to the right jurisdiction/occupancy/construction/sprinklered
plus the four extended fields.

The contract is now a coupling surface: the front-matter key names and value vocabularies
(`nyc|california|other`, the occupancy/construction strings) are an interface shared across
two repos, so renaming a key or changing a value's spelling is a breaking change on both
sides and must move together. Front-matter and the mirrored human tables can also drift; the
dossier's hard rule keeps them in sync with the table as the provenance source of truth, but
a hand-edited `PROJECT.md` can desync until the next `/project-dossier update`. The
front-matter is trusted as authoritative when present - a wrong value there silently
mis-scopes every downstream calculation, which is why `scope-check` exists as the backstop.

Atlas 0.2 extends this same additive contract with project intake and flat Billing/Client Contact snapshot keys. Existing Norma keys and semantics remain unchanged. Shared contact IDs plus historical project snapshots are governed by [ADR 0003](./0003-shared-contact-directory-with-project-snapshots.md).

Atlas 0.3 adds `address_street`, `address_unit`, `address_city`, `address_state`, and `address_postal_code` beside the formatted `address`. These additive keys let Atlas safely pre-populate and edit site-address components without guessing how commas divide a legacy formatted address. Atlas retains the formatted key and mirrored Identity row for existing consumers. Project Address remains a physical numbered street; PO-box support applies only to Contact Mailing Address.

Two writers share the file - `/project-dossier` and Atlas - so the shapes Atlas can rewrite are part of the contract, stated in the skill's "Atlas-owned keys and rows" section. Atlas parses only its own keys, as flat one-line scalars (plain, single- or double-quoted, optional trailing comment), and carries every other front-matter line through byte-for-byte, so Norma keys keep whatever YAML shape the dossier gives them. It rewrites only the Identity rows whose value changed, keeping the provenance after the value, and refuses rather than guesses when `address`, the `address_*` components, and the Address / BBL row disagree. It reads LF, CRLF, and a BOM alike, and writes UTF-8 CRLF without a BOM. A parity test in `tools/atlas/tests` loads a dossier written from the skill's template and round-trips an edit.

## Addendum - the `revit:` block is Pyvoid-owned (2026-10-24)

Pyvoid PRD-220 (Project Seat, REQ-014 and REQ-022..REQ-024; Pyvoid issue #1545) adds a third domain to the contract: a nested `revit:` block naming the job's Revit model, with exactly six keys - `model`, `local`, `version`, `worksets`, `sheet_collection`, `library_containers`. The owning repo is **Pyvoid** (`tyler-figureground/Pyvoid`): Pyvoid defines the keys and their vocabularies (PRD-220 section 7.5) and is the only reader (`mcp_server/pyvoid_mcp/jdp/project_dossier.py`, `revit_block()`), which whitelists the six keys and drops any other. Atlas only scaffolds the block, blank, in every `PROJECT.md` it generates - at intake and in conform's stub - with bare keys and no inline comments, inside the existing UTF-8 / no-BOM / CRLF byte contract. Atlas never rewrites it: `project_data` parses Atlas's own keys only and carries the block through byte-for-byte. The `/project-dossier` key table lists the six keys as Pyvoid-owned. Blank means unknown, as for every other key. Renaming a key or changing a value's spelling is a breaking change in both repos and moves together.

The same change gives the drive map `controlPlane.mcpFile` (`.mcp.json`): Atlas writes an unpinned dossier-pointer entry there - `env` holds only `PYVOID_PROJECT_DOSSIER`, never `PYVOID_FLEET_PROJECT` - when the machine names its Pyvoid `mcp_server` folder in `ATLAS_PYVOID_MCP_SERVER`, and reports a skip otherwise (Tyler, 2026-10-07).

## Amendment - `crm_id` links a project to its CRM Project (2026-10-31)

Tyler's CRM (`tyler-figureground/CRM`, ADR 0004 there) keeps its own record of each Project and finds the matching folder by a flat front-matter key, `crm_id`: the CRM's stable Project id, an opaque token of 1-128 letters, digits, `_` or `-`, starting with a letter or digit. Atlas owns the key's shape and is its only writer; the CRM writes it only through the CLI (`atlas project link FOLDER --crm-id ID --json --yes`, or `atlas new ... --crm-id ID` for a project the CRM created). It is a flat one-line scalar like every other Atlas key, read through the same parser and carried through every other Atlas write byte-for-byte. Blank or absent means unlinked. Linking is idempotent for the same id and refuses a different existing id (exit 2): moving a folder to another CRM Project is a person's edit, not a retry. Only a CRM-created project carries the line at intake; Atlas never scaffolds a blank one. `atlas dossier --json` reports it, and `atlas search --json` reports each hit's project `crm_id` (read only for projects with hits). Renaming the key is a breaking change in both repos and moves together.

## Amendment - Atlas writes the `billing:` block for the CRM (2026-10-31)

Pyvoid PRD-209 reads a nested `billing:` block - `project` (string, required), `client` (string), `rate` (number, USD/hr, optional) - to attribute JDP time (`jdp/billing_identity.py`). Tyler's CRM owns the values (CRM ADR 0004: `project` is the Atlas project number, the folder's YYMMDD; `client` the Billing Contact's company or name; `rate` the Production Automation rate) and writes them only through `atlas project billing FOLDER --project YYMMDD --client TEXT [--rate N] --json --yes`. Atlas owns the writer, so the written shape is one Pyvoid parses: a block mapping, two-space children, `project` and `client` double-quoted (a bare `260415` is a YAML int, which Pyvoid refuses), `rate` a plain decimal (never an exponent, which YAML 1.1 reads as a string). Atlas rewrites only those three child lines and only when their text differs, keeping a trailing comment; other child keys, comments and every other front-matter line are carried through byte-for-byte. It refuses (exit 2) a flow-mapping or scalar `billing:`, a nested value under one of its three keys, tab indentation, or a duplicate key. A contract test in `tools/atlas/tests` runs a vendored copy of Pyvoid's front-matter split and billing validation, under PyYAML, over every shape the writer emits.
