# More content filters: DXF title blocks, and files whose extension lies

Type: task
Status: parked (2026-10-07)
Blocked by: -
Parent: ../map.md

Parked: valid but conditional. The ticket's own bar is a real example from the
drive, not a hypothetical - `pdfText` was justified by the permit set, and no
equivalent case has surfaced for DXF title blocks or lying extensions. Unpark
trigger: a misfiled DXF or a rule that silently failed on a mislabelled file,
from the real drive. `core/content.py` stays the seam; nothing here bit-rots.

## Question

ADR 0009 built one content filter, `pdfText`, and a module to hold the rest.
`core/content.py` is the seam; this ticket fills it out if the studio wants it.

- **`dxfText` or `dxfAttribute`** via ezdxf (MIT). Reads layers, blocks, and title
  block ATTRIBs from a DXF. **DXF only** - a DWG needs the ODA File Converter add-on,
  a separate free-but-proprietary install, which is a decision in itself and probably
  a no.
- **`contentType`** via puremagic (MIT, pure Python). Matches on magic bytes rather
  than the extension, for the file someone saved as `.pdf` that is really a `.dwg`.
  Also the honest answer to "why did my rule not match this" - today the answer is
  silence.
- Decide whether either earns its dependency. `pdfText` was justified by the permit
  set; these two need a real example from the drive, not a hypothetical.

## Constraints

- Same rules as ADR 0009: name filters first, format gate before opening, a read limit,
  cached by path + size + mtime, unreadable never matches, and nothing on stderr.
- Every new filter key is a fail-closed key in `load_map`, and a line in the README
  table and `/CONTEXT.md`.
- Fixture drives only.
