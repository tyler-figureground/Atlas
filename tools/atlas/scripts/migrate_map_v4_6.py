"""Write drive map v4.6 (ADR 0026) from a v4.5 map.

    python scripts/migrate_map_v4_6.py <v4.5 map.json> <out.json>

Reads the source, writes only the output path, and refuses to overwrite the
source - review the output with `atlas lint` before copying it into place. Map
v4.6 needs Atlas 0.28.0 or later on every machine that opens the drive: older
Atlas does not bundle CHECK-PRINTS-README.md and fails when it renders it.
"""

import json
import os
import sys


def refuse(why: str) -> None:
    sys.exit(f"refusing: {why}")


if len(sys.argv) != 3:
    sys.exit(__doc__)
src, out = sys.argv[1], sys.argv[2]
if os.path.exists(out) and os.path.samefile(src, out):
    refuse("would overwrite the source map; write to another path")
d = json.load(open(src, encoding="utf-8"))
if d.get("version") != "4.5":
    refuse(f"source map is v{d.get('version')}, not v4.5")

CHECK = "_Check Prints"
CP = f"02 Sheets/{CHECK}"
CHILD = {
    "name": CHECK,
    "seed": True,
    "description": "Sets printed for review, never issued: one YYMMDD_<Scope> folder per check "
                   "with its redline. Agent in-between prints stay in the run",
}

sheets = next((s for s in d["sections"] if s["id"] == "02 Sheets"), None)
if sheets is None or sheets.get("seed") is not True:
    refuse("02 Sheets must exist and be seeded for its child to seed")
names = [c if isinstance(c, str) else c["name"] for c in sheets["children"]]
if CHECK not in names:
    refuse(f"02 Sheets has no '{CHECK}' child: {names}")
sheets["children"][names.index(CHECK)] = CHILD

card = {
    "path": f"{CP}/README.md",
    "template": "CHECK-PRINTS-README.md",
    "index": "Check prints - where a set printed for review goes, and its redline",
}
if any(t["path"] == card["path"] for t in d["templates"]):
    refuse(f"a template already writes {card['path']}")
d["templates"].append(card)

# A hand-made check folder moves in whole, as one folder, so its prints never
# land loose beside the card (one folder per check, ADR 0026 decision 2).
for old in ("Check Set", "Check Sets", "Check Prints", "Tylers Review", "Test Prints"):
    d["relocations"][f"02 Sheets/{old}"] = f"{CP}/{old} (moved)"

d["version"] = "4.6"
d["versionNote"] = ("v4.6 (ADR 0026, Atlas 0.28.0+): 02 Sheets/_Check Prints seeded, with a "
                    "filing card (README.md); hand-made check-set folders relocate into it whole. "
                    "Previous: " + d.get("versionNote", ""))
with open(out, "w", encoding="utf-8", newline="\n") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("ok")
