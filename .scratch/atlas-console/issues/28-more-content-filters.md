# More content filters: DXF title blocks, and files whose extension lies

Type: task
Status: open
Blocked by: -
Parent: ../map.md

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
