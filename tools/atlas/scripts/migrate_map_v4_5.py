"""Write drive map v4.5 (ADR 0025) from a v4.4 map.

    python scripts/migrate_map_v4_5.py <v4.4 map.json> <out.json>

Reads the source, writes only the output path, and refuses to overwrite the
source - review the output with `atlas lint` before copying it into place. Map
v4.5 needs Atlas 0.27.0 or later on every machine that opens the drive: older
Atlas refuses the new keys (description, filingCard, when).
"""

import json
import os
import sys

if len(sys.argv) != 3:
    sys.exit(__doc__)
src, out = sys.argv[1], sys.argv[2]
if os.path.exists(out) and os.path.samefile(src, out):
    sys.exit("refusing to overwrite the source map; write to another path")
d = json.load(open(src, encoding="utf-8"))
assert d["version"] == "4.4", d["version"]

R = "06 Research & Existing Conditions"

DESCRIPTIONS = {
    R: {
        "Project Information": "Project basics as received: client info sheet, prior reports, program summaries from others",
        "Client Program": "What the client needs: who uses the place, rooms, sizes, must-haves (PROGRAM.md). Their own emails stay in 07 Client/In",
        "Client Program/Client Items": "Photos and sizes of what the client owns that must fit: appliances, coffee setup, collections (CLIENT-ITEMS.md)",
        "Site Review/Photos": "Our own site photos, by visit date",
        "Site Review/Ex CADs & PDF": "Existing-conditions CAD and PDF drawings received from others",
        "Site Review/Scans & Tours": "3D scans and virtual tours (iGUIDE, Matterport), one dated folder per capture",
        "Site Review/Field Measurements": "Tape and laser measurements taken on site, and as-built dimensions from the contractor",
        "As-Builts & Record Drawings": "Drawings of what was built before: as-builts, record sets, prior permits' plans",
        "Public Records": "County and city records: assessor maps, permit history, parcel reports",
        "Deed": "Title reports, deeds, CC&Rs and easements",
        "Survey": "Licensed surveys only. GIS and aerial maps go in GIS & Maps",
        "GIS & Maps": "GIS exports, vicinity maps, aerials, Google Maps captures",
        "Zoning": "Zoning code, overlays, setbacks and zoning research reports",
        "Code": "Building code research and code analyses",
        "Utilities & Services": "Water, sewer or septic, well, power, gas, will-serve letters and service capacity",
        "Environmental & Hazards": "Geotech, hazmat, flood, fire and other hazard reports",
        "Climate": "Climate, sun and wind data",
        "Products & Materials": "Products and materials we are researching. Chosen ones go in 05 Specs/00 Selections",
        "Costs & Bids": "Cost estimates, budget research, contractor licence checks and prequalification",
        "Inspiration": "Precedent and inspiration images",
    },
}

NEW_CHILDREN = {
    R: [("Client Program", True, "Project Information"),
        ("Client Program/Client Items", False, "Client Program"),
        ("Site Review/Field Measurements", False, "Site Review/Scans & Tours"),
        ("Utilities & Services", False, "GIS & Maps")],
    "05 Specs": [("00 Selections", False, None),
                 ("10 Specialties", False, "09 Finishes"),
                 ("11 Equipment", False, "10 Specialties"),
                 ("12 Furnishings", False, "11 Equipment")],
    "01 Model": [("_Archive", False, None)],
    "02 Sheets": [("_Check Prints", False, None)],
    "03 Renderings": [("Material Studies", False, None)],
    "10 Legal": [("Receipts", False, None)],
    "12 Construction Administration": [("Pay Applications", False, None), ("Closeout", False, None)],
}
NEW_DESCRIPTIONS = {
    "00 Tasks": {"Archive": "Done tasks older than 30 days, one file per month (YYMM-done.md)"},
    "07 Correspondence": {
        "_Outbox": "Drafts not sent yet. Move to the party's Out the day it is sent",
        "Client": "Everything exchanged with the client",
        "Client/In": "From the client, as received, one YYMMDD_<Description> folder per exchange",
        "Client/Out": "To the client, as sent, one YYMMDD_<Description> folder per exchange",
        "AHJ": "Agencies, design review boards and HOAs, by stage; one register row per application",
        "AHJ/01 Requirements & Pre-Application": "Agency requirements, checklists, pre-application notes",
        "AHJ/02 Applications & Forms": "Application forms, owner authorisations, fee receipts",
        "AHJ/03 Submissions": "What we filed, one R<n>_YYMMDD folder per round",
        "AHJ/04 Comments & Responses": "Plan-check comments and our responses, same R<n>_YYMMDD as the round",
        "AHJ/05 Letters & Emails": "Other letters and emails with an agency",
        "AHJ/06 Permits & Inspections": "Issued permits, stamped sets, inspection records, finals",
        "Consultants": "Engineers, surveyors and other consultants, by discipline, In and Out",
    },
    "05 Specs": {"00 Selections": "What was chosen, who furnishes and installs it, and its status (SELECTIONS.md)"},
}


def name_of(c):
    return c if isinstance(c, str) else c["name"]


for s in d["sections"]:
    kids = s.setdefault("children", [])
    for name, seed, after in NEW_CHILDREN.get(s["id"], []):
        assert name not in [name_of(c) for c in kids], (s["id"], name)
        entry = {"name": name, "seed": True} if seed else name
        names = [name_of(c) for c in kids]
        at = names.index(after) + 1 if after else (0 if name.startswith(("0", "_")) else len(kids))
        kids.insert(at, entry)
    about = {**DESCRIPTIONS.get(s["id"], {}), **NEW_DESCRIPTIONS.get(s["id"], {})}
    for i, c in enumerate(kids):
        n = name_of(c)
        if n in about:
            obj = {"name": n} if isinstance(c, str) else dict(c)
            obj["description"] = about.pop(n)
            kids[i] = obj
    assert not about, (s["id"], about)
    if s["id"] == R:
        s["filingCard"] = True

d["templates"] += [
    {"path": f"{R}/Client Program/PROGRAM.md", "template": "PROGRAM.md",
     "index": "Client program - who uses the place, rooms, sizes, must-haves"},
    {"path": f"{R}/Client Program/Client Items/CLIENT-ITEMS.md", "template": "CLIENT-ITEMS.md",
     "index": "Client items - what the client owns that must fit, with sizes and services",
     "when": "on-create"},
    {"path": "05 Specs/00 Selections/SELECTIONS.md", "template": "SELECTIONS.md",
     "index": "Selections register - what is chosen, who furnishes and installs it, status",
     "when": "on-create"},
]

d["relocations"].update({
    "01 Model/Archive": "01 Model/_Archive",
    "01 Model/archive": "01 Model/_Archive",
    "01 Model/aRCHIVE": "01 Model/_Archive",
    "02 Sheets/Test Prints": "02 Sheets/_Check Prints",
    f"{R}/Photos": f"{R}/Site Review/Photos",
    f"{R}/Vicinity Map": f"{R}/GIS & Maps",
    f"{R}/Google Maps": f"{R}/GIS & Maps",
    f"{R}/County Records - Site Review": f"{R}/Public Records",
    f"{R}/Site Review/Virtual Tour": f"{R}/Site Review/Scans & Tours",
    f"{R}/Program and client Reqs": f"{R}/Client Program",
})

d["version"] = "4.5"
d["versionNote"] = ("v4.5 (ADR 0025, Atlas 0.27.0+): 06 Client Program (seeded, PROGRAM.md) with "
                    "Client Items on demand; 05 Specs/00 Selections and 10-12 divisions; utilities, "
                    "field measurements, _Archive, _Check Prints, Material Studies, Receipts, Pay "
                    "Applications, Closeout; child descriptions and a generated 06 filing card. "
                    "Previous: " + d.get("versionNote", ""))
with open(out, "w", encoding="utf-8", newline="\n") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("ok")
