#!/bin/bash
# post-write-reference-check.sh
# Fires after Write. Checks a drafted deliverable for facts copied out of the
# reference-set exemplars it was modelled on (rules/reference-sets.md, ADR 0015).
#
# Contract:
#   - Marker-driven. Only a .md file carrying
#     `<!-- architecture-studio:reference: <type> <E1,E2> -->` is checked. Every
#     other file is ignored, in any repo.
#   - The check is `atlas refs check <file>`: it greps the draft for the leak
#     list of each exemplar the marker names. No `atlas` on PATH, or Atlas cannot
#     find the reference sets: silent, exit 0. Outside the studio this hook does
#     nothing.
#   - Leaks found: the report goes to stderr and the hook exits 2, which hands it
#     back to the agent to fix. The Write has already happened; nothing is undone.
#     This is the one Dispatcher hook that answers with 2, because a copied
#     address or code edition is a defect, not a style note.
#   - README.md, SKILL.md, CLAUDE.md, AGENTS.md, NOTES.md, SET.md, and anything
#     under rules/, hooks/, .claude-plugin/ or a Reference Sets folder are skipped:
#     they describe the marker, they are not drafts.

INPUT=$(cat)
FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0
[[ "$FILE_PATH" != *.md ]] && exit 0
[ -f "$FILE_PATH" ] || exit 0

grep -qF -- '<!-- architecture-studio:reference:' "$FILE_PATH" 2>/dev/null || exit 0

case "$(basename "$FILE_PATH")" in
  README.md|SKILL.md|CLAUDE.md|AGENTS.md|NOTES.md|SET.md) exit 0 ;;
esac
NORM_PATH=${FILE_PATH//\\//}
if printf '%s\n' "$NORM_PATH" | grep -qE '/(rules|hooks|\.claude-plugin|Reference Sets)/'; then
  exit 0
fi

command -v atlas >/dev/null 2>&1 || exit 0

REPORT=$(atlas refs check "$FILE_PATH" 2>/dev/null)
STATUS=$?

if [ "$STATUS" -eq 1 ]; then
  {
    echo "Reference-set leak check: $FILE_PATH contains facts that belong to the exemplar projects."
    printf '%s\n' "$REPORT"
    echo "Replace each with this project's own fact from BRIEF.md / PROJECT.md / decisions/, or remove it. Re-run: atlas refs check \"$FILE_PATH\""
  } >&2
  exit 2
fi

# 0 = clean; 2 = Atlas could not run the check (no sets configured, drive offline).
exit 0
