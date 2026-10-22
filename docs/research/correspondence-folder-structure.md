# Correspondence folder structure: party-first vs direction-first

Date: 2026-10-22. Basis for ADR 0021.

Question: should project exchange be filed by direction (`07 IN`, `08 OUT`) with a
separate `13 AHJ`, or by party under one section, with In / Out inside each party?

Confidence tiers: **Measured** = counted on the ARCHITECTURE drive on 2026-10-22.
**Sourced** = published source, URL given, with the researcher's confidence (high / med /
low). **Inferred** = this document's reading of the two.

---

## 1. What the drive shows (Measured, 10 live projects)

### 1.1 AHJ material still lands in IN / OUT after `13 AHJ` exists

| Project | Where the AHJ material is |
|---|---|
| 2267 Monticello | 95 files in `07 IN\Napa County PBES` (V1 Review, V2 Review, 91 saved portal files); `13 AHJ` empty |
| 1673 Pestoni | `07 IN\County`, `08 OUT\Resubmittal\Working`, and `13 AHJ\03`, `04`, `06` |
| 80-23 64th Lane | DOB route through `07 IN\Expediter`; `13 AHJ` empty |
| 1221 Hayes | `13 AHJ\05 Correspondence` (moved by the `07 IN/AHJ` relocation) |

The `07 IN/AHJ` relocation only catches a folder literally named `AHJ`. Staff name the
agency instead (`County`, `Napa County PBES`), so the rule misses it.

### 1.2 The current tree sorts three different ways

- `07 IN` - by party (Client, Architect, Fabricator, General Contractor).
- `08 OUT` - by instrument (Transmittals, RFI, Submittals, Change Orders, Sketches).
- `13 AHJ` - by party, then by stage.

A person filing a document has to know which axis applies before they can find the folder.

### 1.3 People already think by party (Measured)

Thirteen party folders were invented under `07 IN` / `08 OUT` that the map does not bless:
`Solar Vendor` (2 projects), `Kitchen` (in and out), `Speaker Consul`, `Bids`,
`Expediter`, `Civil`, `Electrical`, `MEP Engineer`, `Structural Engineer`, `Consultants`,
`County`, `Napa County PBES`, `Architect\From Scott`.

Most are firm or agency names, not roles.

### 1.4 The transmittal log is not kept (Measured)

`08 OUT\Transmittals\TRANSMITTAL-LOG.md` exists in all 10 projects. Rows logged: 1 in
total (64th Lane), against six dated packages in that same folder. Folders have to be
findable on their own; a log cannot be the only index.

### 1.5 Vocabulary collision persists (Measured)

`08 OUT\Submittals` means contractor shop-drawing submittals; Pestoni used `Submittal` and
`Resubmittal` for a county filing. ADR 0013 already fixed AHJ to "Submissions".

---

## 2. What published practice says (Sourced)

### 2.1 Party-first is the AIA precedent

- AIA "Keys to classifying project files": section 5.0 Correspondence has one folder per
  party (5.2 Architect, 5.3 Owner, 5.4 CM/Contractor, 5.5 Subs, 5.8 Civil, 5.10
  Structural, 5.12 Electrical, 5.16 Tenant), each reverse-chronological. 5.1 General
  Correspondence is "used only for smaller projects". **high**
  https://www.aia.org/resource-center/keys-classifying-project-files
- Same scheme: 4.0 Code/Approvals is its own section (State, Township/City Approvals, Code
  Research), keeping submittals, approvals, correspondence and transmittals for an agency
  together. Supports a stage-structured AHJ area. **high** (same URL)
- Same scheme: folders are chosen per project from a checklist at project start. **high**

### 2.2 Direction-first appears only below a party

- No source endorses a top-level IN / OUT split. Practitioners put Sent / Received inside
  each consultant folder, at most three levels deep. **low**
  https://archinect.com/forum/thread/100829/office-standards
- A structural engineer's template uses one Communication folder with Incoming / Outgoing,
  for attachments that are not submittals. **low**
  https://www.linkedin.com/pulse/folder-structure-design-construction-professionals-amy
- Received files kept untouched in dated folders; issued sets in dated folders. **med**
  https://blog.nobledesktop.com/learn/autocad/effective-file-storage-and-organization-methodology-for-architectural-projects

### 2.3 Formal exchanges are processes with logs

- Newforma Project Center: incoming and outgoing transmittals are records in a log; files
  sit in a configurable default location. **high**
  https://projectcenter.help.newforma.com/learning/how-tos/file_an_incoming_transmittal/
- Procore does not recommend folders for files that live in a Procore tool (RFIs,
  submittals, correspondence) and recommends a standard tree from a project template.
  **high**
  https://support.procore.com/products/online/user-guide/project-level/documents/tutorials/create-a-standard-project-folder-structure-for-the-documents-tool
- ISO 19650 CDE states (WIP / Shared / Published / Archive) carry meaning in metadata, not
  in direction folders. **med** https://www.cdbb.cam.ac.uk/files/national_annex_guidance.pdf

### 2.4 Records-management principles

- File plans built on people or organisations go stale as teams change; name by role or
  function. **med** (search snippet only; PDF returned 403)
  https://herts.ac.uk/__data/assets/pdf_file/0007/361654/Records-Management-and-the-Archiving-and-Retention-of-Prime-Documents-and-Business-Records-IM11-Apx-3.pdf
- Keep hierarchies about 4-5 levels. **med** (snippet only)
  https://www.usnh.edu/it/departments/cybersecurity/cybersecurity-policies-standards/shared-file-management-standard
- Windows MAX_PATH is 260 characters including drive, folders and file name. **high**
  https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation
- Shared drives: 500,000 items, 100 nesting levels; depth is a usability limit, not a
  platform one. **high** https://support.google.com/a/answer/7338880

### 2.5 US plan check

- Every resubmittal needs a written response letter saying where each comment was
  addressed; packages without one are rejected. **high**
  https://www.alamedaca.gov/Departments/Planning-Building-and-Transportation/Permit-Center/How-to-Respond-to-Plan-Check-Comments
  https://www.danville.ca.gov/DocumentCenter/View/4683/Resubmit-in-Response-to-Plan-Review-Comments-PDF
- Resubmittals are full sets, revisions clouded and deltaed. **high**
  https://www.novato.gov/home/showpublisheddocument/37399/639144464576230000
- No national standard numbers resubmittal rounds; each city sets its own. **thin**

---

## 3. Reading (Inferred)

1. File by **party** at the top, because recall starts with "what did we send the city /
   the structural engineer". This is the AIA 5.0 shape and how staff already behave (1.3).
2. Name parties by **role**, from a closed list in the map. Firm and agency names go in the
   folder below (`YYMMDD_<Firm>_<what>`) and in the registers.
3. Parties with a formal process (AHJ, Contractor) get **process folders**; the rest get
   **In / Out**. RFIs, submittals and change orders stay process folders, tied to a log,
   now under the party that drives them.
4. Rounds pair across stages: `R1_YYMMDD` in Submissions matches `R1_YYMMDD` in Comments &
   Responses, so a resubmittal and the comments it answers sort side by side.
5. Depth check: `<drive>\<project>\07 Correspondence\Consultants\Structural\In\
   YYMMDD_<pkg>\` is six levels below the project and about 150 characters before the
   file name. Inside both limits.
