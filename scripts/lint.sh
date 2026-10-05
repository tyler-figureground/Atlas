#!/usr/bin/env bash
# Architecture Studio repo lint.
# Runs the full set of structural checks. Exits non-zero if any fail.

set -uo pipefail

# Repo content is UTF-8. Force Python's UTF-8 mode so the embedded checks below
# read files consistently on platforms whose default locale encoding is not
# UTF-8 (notably Windows, where it is cp1252 and read_text() raises).
export PYTHONUTF8=1

cd "$(dirname "$0")/.."

FAIL=0
fail_check() { echo "  ✗ $1"; FAIL=1; }
pass_check() { echo "  ✓ $1"; }

# 1. No .DS_Store tracked
echo "→ no .DS_Store tracked"
DSSTORE=$(git ls-files | grep '\.DS_Store$' || true)
if [ -n "$DSSTORE" ]; then
  fail_check "tracked .DS_Store files:"
  echo "$DSSTORE" | sed 's/^/      /'
else
  pass_check "none"
fi

# 2. JSON validity
# A missing jq used to report every tracked file as invalid JSON, which reads as
# 18 broken files rather than one absent binary. python3 is already required by
# the frontmatter check below, so fall back to it and say which one ran.
echo "→ JSON validity"
JSON_FILES=$(git ls-files '*.json')
JSON_BAD=0
JSON_TOTAL=0
if command -v jq >/dev/null 2>&1; then
  json_valid() { jq empty "$1" >/dev/null 2>&1; }
elif command -v python3 >/dev/null 2>&1; then
  json_valid() { python3 -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8-sig'))" "$1" >/dev/null 2>&1; }
  echo "  ! jq not installed; validating with python3 instead"
else
  json_valid() { return 0; }
  echo "  ! neither jq nor python3 installed; skipping locally — CI will run it"
fi
while IFS= read -r f; do
  [ -z "$f" ] && continue
  JSON_TOTAL=$((JSON_TOTAL + 1))
  if ! json_valid "$f"; then
    fail_check "invalid JSON: $f"
    JSON_BAD=$((JSON_BAD + 1))
  fi
done <<< "$JSON_FILES"
[ "$JSON_BAD" -eq 0 ] && pass_check "$JSON_TOTAL files"

# 3. SKILL.md frontmatter
echo "→ SKILL.md frontmatter"
python3 - <<'PYEOF'
import sys, pathlib, subprocess
try:
    import yaml
except ImportError:
    print("  ! PyYAML not installed; skipping (install with: pip install pyyaml)")
    sys.exit(2)

files = subprocess.check_output(['git', 'ls-files', '*SKILL.md']).decode().strip().split('\n')
errors = 0
for f in files:
    text = pathlib.Path(f).read_text()
    if not text.startswith('---\n'):
        print(f"  ✗ {f}: missing frontmatter delimiter")
        errors += 1
        continue
    end = text.find('\n---\n', 4)
    if end < 0:
        print(f"  ✗ {f}: unterminated frontmatter")
        errors += 1
        continue
    try:
        meta = yaml.safe_load(text[4:end])
    except Exception as e:
        print(f"  ✗ {f}: YAML parse error: {e}")
        errors += 1
        continue
    if not isinstance(meta, dict):
        print(f"  ✗ {f}: frontmatter is not a mapping")
        errors += 1
        continue
    for key in ('name', 'description'):
        if key not in meta:
            print(f"  ✗ {f}: missing required key '{key}'")
            errors += 1
if errors:
    sys.exit(1)
print(f"  ✓ {len(files)} files")
PYEOF
RC=$?
[ "$RC" -eq 1 ] && FAIL=1

# 4. Count consistency
echo "→ count consistency"
python3 - <<'PYEOF'
import sys, re, json, pathlib

errors = []
plugins_dir = pathlib.Path('plugins')
plugin_dirs = sorted(p for p in plugins_dir.iterdir() if p.is_dir() and not p.name.startswith('.'))
plugin_count = len(plugin_dirs)
per_plugin = {}
for p in plugin_dirs:
    skills_dir = p / 'skills'
    if skills_dir.exists():
        per_plugin[p.name] = sum(1 for s in skills_dir.iterdir()
                                 if s.is_dir() and not s.name.startswith('.'))

total_skills = sum(per_plugin.values())
readme = pathlib.Path('README.md').read_text()

m = re.search(r'\*\*(\d+) plugins\*\*', readme)
if not m:
    errors.append("README headline missing '**N plugins**'")
elif int(m.group(1)) != plugin_count:
    errors.append(f"README headline claims {m.group(1)} plugins, actual {plugin_count}")

m = re.search(r'\*\*(\d+) skills\*\*', readme)
if not m:
    errors.append("README headline missing '**N skills**'")
elif int(m.group(1)) != total_skills:
    errors.append(f"README headline claims {m.group(1)} skills, actual {total_skills}")

m = re.search(r'<summary><strong>All (\d+) skills</strong></summary>', readme)
if not m:
    errors.append("README details block missing '<summary><strong>All N skills</strong></summary>'")
elif int(m.group(1)) != total_skills:
    errors.append(f"README details claims {m.group(1)} skills, actual {total_skills}")

# Catalog row count inside the details block
details_match = re.search(
    r'<summary><strong>All \d+ skills</strong></summary>(.*?)</details>',
    readme, re.DOTALL,
)
if details_match:
    catalog_rows = len(re.findall(r'^\|\s*\[`/[^`]+`\]', details_match.group(1), re.MULTILINE))
    if catalog_rows != total_skills:
        errors.append(f"README details catalog has {catalog_rows} skill rows, actual {total_skills}")

# Per-plugin counts in the README plugin table
for name, count in per_plugin.items():
    pat = re.compile(rf'\[[^\]]+\]\(\./plugins/{re.escape(name)}\)\s*\|\s*(\d+)\s*\|')
    m = pat.search(readme)
    if m and int(m.group(1)) != count:
        errors.append(f"README plugin table claims {name} has {m.group(1)} skills, actual {count}")

menu = pathlib.Path('plugins/08-dispatcher/skills/skills-menu/SKILL.md').read_text()
m = re.search(r'\*\*(\d+) skills', menu)
if m and int(m.group(1)) != total_skills:
    errors.append(f"skills-menu claims {m.group(1)} skills, actual {total_skills}")

mp = json.loads(pathlib.Path('.claude-plugin/marketplace.json').read_text())
if len(mp.get('plugins', [])) != plugin_count:
    errors.append(f"marketplace.json lists {len(mp.get('plugins', []))} plugins, actual {plugin_count}")

for entry in mp.get('plugins', []):
    src = entry.get('source', '')
    if not pathlib.Path(src).is_dir():
        errors.append(f"marketplace.json points to missing dir: {src}")

if errors:
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
print(f"  ✓ {plugin_count} plugins, {sum(per_plugin.values())} skills, counts consistent")
PYEOF
RC=$?
[ "$RC" -ne 0 ] && FAIL=1

# 5. Internal markdown links
echo "→ internal markdown links"
python3 - <<'PYEOF'
import sys, re, pathlib, subprocess
md_files = subprocess.check_output(['git', 'ls-files', '*.md']).decode().strip().split('\n')
link_re = re.compile(r'\]\((?!https?://|mailto:|#)([^)\s]+)(?:\s+"[^"]*")?\)')
# Example links inside fenced code or HTML comments are text, not links.
not_links_re = re.compile(r'^```.*?^```|<!--.*?-->', re.S | re.M)
errors = 0
for f in md_files:
    p = pathlib.Path(f)
    text = not_links_re.sub('', p.read_text())
    base = p.parent
    for m in link_re.finditer(text):
        target = m.group(1).split('#')[0]
        if not target:
            continue
        resolved = (base / target).resolve()
        if not resolved.exists():
            print(f"  ✗ {f}: broken link → {target}")
            errors += 1
if errors:
    sys.exit(1)
print(f"  ✓ {len(md_files)} markdown files scanned")
PYEOF
RC=$?
[ "$RC" -ne 0 ] && FAIL=1

# 6. Shellcheck on hooks
echo "→ shellcheck on plugins/08-dispatcher/hooks/"
if command -v shellcheck >/dev/null 2>&1; then
  if shellcheck plugins/08-dispatcher/hooks/*.sh; then
    pass_check "$(ls plugins/08-dispatcher/hooks/*.sh 2>/dev/null | wc -l | tr -d ' ') scripts"
  else
    fail_check "shellcheck issues"
  fi
else
  echo "  ! shellcheck not installed; skipping locally — CI will run it"
fi

# 7. Norma surface drift — 10-norma skills must shell out to the `norma` CLI,
#    never reach into the engine's tools/ adapters (`python tools/…`, the removed
#    `$NORMA_HOME/tools/norma_cli.py` fallback) or grep a raw corpus path
#    (`rg … <juris>/20NN/`). The surface is prose; the engine is editable.
echo "→ norma surface (10-norma shells out to the norma CLI)"
NORMA_FILES=$(ls plugins/10-norma/agents.md plugins/10-norma/skills/*/SKILL.md 2>/dev/null)
if [ -z "$NORMA_FILES" ]; then
  pass_check "no 10-norma skills to check"
else
  NORMA_DRIFT=0
  # shellcheck disable=SC2086
  DIRECT=$(grep -nE 'python tools/|\$NORMA_HOME/tools/|tools/norma_cli\.py' $NORMA_FILES 2>/dev/null || true)
  if [ -n "$DIRECT" ]; then
    fail_check "10-norma reaches into the engine's tools/ (removed in v0.3) — use 'norma <verb>' or 'python -m norma.cli <verb>':"
    echo "$DIRECT" | sed 's/^/      /'
    NORMA_DRIFT=1
  fi
  # shellcheck disable=SC2086
  RAWRG=$(grep -nE 'rg .*/20[0-9][0-9]/' $NORMA_FILES 2>/dev/null || true)
  if [ -n "$RAWRG" ]; then
    fail_check "10-norma greps a raw corpus path — use 'norma grep \"…\" -j <j>':"
    echo "$RAWRG" | sed 's/^/      /'
    NORMA_DRIFT=1
  fi
  [ "$NORMA_DRIFT" -eq 0 ] && pass_check "clean (norma CLI only)"
fi

# 8. post-output-metadata hook behavior — marker-driven, never stamps foreign
#    Markdown. Pipes Write-tool JSON into the hook against temp files only.
echo "→ post-output-metadata hook (marker-driven stamping)"
if POM_OUT=$(python3 plugins/08-dispatcher/hooks/tests/check_post_output_metadata.py 2>&1); then
  POM_LAST=$(printf '%s\n' "$POM_OUT" | tail -n 1)
  case "$POM_LAST" in
    *"!"*) echo "$POM_LAST" ;;
    *) pass_check "${POM_LAST#"${POM_LAST%%[![:space:]]*}"}" ;;
  esac
else
  printf '%s\n' "$POM_OUT"
  fail_check "post-output-metadata hook check failed"
fi

# 9. post-write-reference-check hook behavior - marker-driven leak check. Stub
#    atlas on PATH; temp files only.
echo "→ post-write-reference-check hook (marker-driven leak check)"
if PRC_OUT=$(python3 plugins/08-dispatcher/hooks/tests/check_post_write_reference.py 2>&1); then
  PRC_LAST=$(printf '%s\n' "$PRC_OUT" | tail -n 1)
  case "$PRC_LAST" in
    *"!"*) echo "$PRC_LAST" ;;
    *) pass_check "${PRC_LAST#"${PRC_LAST%%[![:space:]]*}"}" ;;
  esac
else
  printf '%s\n' "$PRC_OUT"
  fail_check "post-write-reference-check hook check failed"
fi

echo
if [ "$FAIL" -ne 0 ]; then
  echo "lint failed"
  exit 1
fi
echo "all checks passed"
