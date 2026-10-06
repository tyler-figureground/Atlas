#!/bin/bash
# post-output-metadata.sh
# Fires after Write tool. Stamps YAML front matter onto markdown reports that
# this marketplace's skills produce, if the report does not already carry it.
#
# Contract:
#   - Marker-driven. A report is identified by the HTML-comment marker
#     `<!-- architecture-studio:report -->`, which report-writing skills emit
#     (see rules/output-formatting.md). A markdown file without the marker is
#     never touched, in any repo — the hook used to stamp every *.md it saw,
#     which splices front matter into foreign notes, issue drafts and
#     machine-read files.
#   - A file whose first line is `---` already has front matter: unchanged.
#     This also makes the stamp idempotent — a second run adds nothing.
#   - README.md, SKILL.md, CLAUDE.md, AGENTS.md and anything under rules/,
#     hooks/ or .claude-plugin/ are skipped even when they mention the marker.
#   - Warn-only in spirit: this hook never blocks a Write. Every path exits 0.

INPUT=$(cat)
FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0
[[ "$FILE_PATH" != *.md ]] && exit 0
[ -f "$FILE_PATH" ] || exit 0

MARKER='<!-- architecture-studio:report -->'

# Only identifiable reports. Everything else stays byte-identical.
grep -qF -- "$MARKER" "$FILE_PATH" 2>/dev/null || exit 0

# Skip files that already have YAML front matter (tolerate CRLF line endings).
FIRST_LINE=$(head -n 1 "$FILE_PATH" 2>/dev/null | tr -d '\r')
[ "$FIRST_LINE" = "---" ] && exit 0

# Skip README, skill, and agent-instruction files.
BASENAME=$(basename "$FILE_PATH")
case "$BASENAME" in
  README.md|SKILL.md|CLAUDE.md|AGENTS.md) exit 0 ;;
esac

# Skip files inside rules/, hooks/, .claude-plugin/ directories. Normalize
# Windows separators first so the check holds for C:\...\rules\x.md too.
NORM_PATH=${FILE_PATH//\\//}
if printf '%s\n' "$NORM_PATH" | grep -qE '/(rules|hooks|\.claude-plugin)/'; then
  exit 0
fi

# Title from the first level-1 heading, else the file name. Escape it for a
# double-quoted YAML scalar.
TITLE=$(grep -m1 -E '^#[[:space:]]' "$FILE_PATH" 2>/dev/null | tr -d '\r' | sed -E 's/^#[[:space:]]+//')
[ -z "$TITLE" ] && TITLE="$BASENAME"
TITLE=${TITLE//\\/\\\\}
TITLE=${TITLE//\"/\\\"}

DATE=$(date '+%Y-%m-%d')

TMPFILE=$(mktemp 2>/dev/null) || exit 0
{
  printf -- '---\n'
  printf 'title: "%s"\n' "$TITLE"
  printf 'date: %s\n' "$DATE"
  printf 'generated_by: atlas\n'
  printf -- '---\n\n'
  cat "$FILE_PATH"
} > "$TMPFILE" 2>/dev/null || { rm -f "$TMPFILE"; exit 0; }

# Overwrite in place (cat >) rather than mv, so the file keeps its own
# permissions and any hard links.
cat "$TMPFILE" > "$FILE_PATH" 2>/dev/null
rm -f "$TMPFILE"

exit 0
