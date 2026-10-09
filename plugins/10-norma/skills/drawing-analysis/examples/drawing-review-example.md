<!-- architecture-studio:report -->
> **Fictional example.** Invented project, address, people and data - shows structure only. Never carry a fact from this file into real work.

# Drawing Review - A-101 Second Floor Plan, Fable Street Lofts

2022 NYC Building Code (nyc) · Group B · Sprinklered (NFPA 13) · Scale 1/8"=1'-0" (title block)

## Findings

| Check | Measured (source) | Code limit | Result | Section |
|---|---|---|---|---|
| Occupant load (Suite 200) | 3,000 sf (tagged) | 100 gross | 30 occ | NYC Table 1004.1.3 |
| Min exits | 30 occ | <= 49 single-exit | 1 OK | NYC § 1006.2.1 |
| Exit separation | 48 ft provided (scaled) | 50 ft (1/3 diag, spr) | FAIL (verify) | NYC § 1007.1.1 |
| Dead-end corridor | 34 ft (scaled) | 50 ft (spr, Grp B) | PASS | NYC § 1020.4 |
| Travel distance | ~180 ft (scaled) | 300 ft (spr) | PASS | NYC § 1016.2.1 |

## Detail (per finding)

- **Exit separation FAILS by 2 ft as scaled.** Measured 48 ft between the stair A and stair B doors; one-third of the 150 ft overall diagonal requires 50 ft (NYC § 1007.1.1). Scaled value, near margin - provisional until checked against a dimensioned drawing. Options: relocate the stair B door, or show the corridor path increases the measured separation.
- **Dead-end corridor PASS.** 34 ft scaled against the 50 ft sprinklered Group B limit (NYC § 1020.4). Controlling text quoted in the review file.

## Could not determine

- Door swings at Suite 210 (not drawn at this scale)
- Corridor wall rating (no partition schedule on sheet)

## Verify before relying

- Scale-derived dimensions: exit separation, dead-end, travel distance
- Confirm against the jurisdiction's adopted edition
