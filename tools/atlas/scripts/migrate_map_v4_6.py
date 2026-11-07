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

if len(sys.argv) != 3:
    sys.exit(__doc__)
src, out = sys.argv[1], sys.argv[2]
if os.path.exists(out) and os.path.samefile(src, out):
    sys.exit("refusing to overwrite the source map; write to another path")
d = json.load(open(src, encoding="utf-8"))
assert d["version"] == "4.5", d["version"]

CHECK = "_Check Prints"
CHILD = {
    "name": CHECK,
    "seed": True,
    "description": "Sets printed for review, never issued: one YYMMDD_<Scope> folder per check "
                   "with its redline. Agent in-between prints stay in the run",
}

sheets = next(s for s in d["sections"] if s["id"] == "02 Sheets")
assert sheets.get("seed") is True, "02 Sheets must be seeded for its child to seed"
names = [c if isinstance(c, str) else c["name"] for c in sheets["children"]]
assert CHECK in names, names
sheets["children"][names.index(CHECK)] = CHILD

card = {
    "path": f"02 Sheets/{CHECK}/README.md",
    "template": "CHECK-PRINTS-README.md",
    "index": "Check prints - where a set printed for review goes, and its redline",
}
assert all(t["path"] != card["path"] for t in d["templates"])
d["templates"].append(card)

d["relocations"].update({
    "02 Sheets/Check Set": f"02 Sheets/{CHECK}",
    "02 Sheets/Check Sets": f"02 Sheets/{CHECK}",
    "02 Sheets/Check Prints": f"02 Sheets/{CHECK}",
    "02 Sheets/Tylers Review": f"02 Sheets/{CHECK}",
    "02 Sheets/Test Prints": f"02 Sheets/{CHECK}",
})

d["version"] = "4.6"
d["versionNote"] = ("v4.6 (ADR 0026, Atlas 0.28.0+): 02 Sheets/_Check Prints seeded, with a "
                    "filing card (README.md); hand-made check-set folders relocate into it. "
                    "Previous: " + d.get("versionNote", ""))
with open(out, "w", encoding="utf-8", newline="\n") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
    f.write("\n")
print("ok")
