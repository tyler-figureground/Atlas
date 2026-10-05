#!/usr/bin/env python3
"""Check the post-write-reference-check hook against its marker-driven contract.

Runs the hook with a stub `atlas` first on PATH, so no drive and no Atlas
install are needed. The stub records each call and answers with the exit code
named in STUB_EXIT. Stdlib only; every file lives under a TemporaryDirectory.

Usage:
    python3 plugins/08-dispatcher/hooks/tests/check_post_write_reference.py [HOOK]

Exit status: 0 when every case passes, 1 on any failure, 0 with a skip notice
when bash or jq is unavailable (CI has both).
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_HOOK = HERE.parent / "post-write-reference-check.sh"
MARKER = "<!-- architecture-studio:reference: code-analysis E1,E3 -->"

FAILURES: list[str] = []
PASSES = 0

STUB = """#!/bin/bash
echo "$@" >> "$STUB_LOG"
if [ "$STUB_EXIT" = "1" ]; then
  echo "draft.md:4: code-analysis E3 owns '211 Centre' - Project: 211 Centre"
  echo "1 leak(s); checked code-analysis E3"
fi
exit "${STUB_EXIT:-0}"
"""


def find_bash() -> str | None:
    override = os.environ.get("HOOK_BASH")
    if override:
        return override
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            root = pathlib.Path(git).resolve().parent.parent
            for cand in (root / "bin" / "bash.exe", root / "usr" / "bin" / "bash.exe",
                         root.parent / "bin" / "bash.exe"):
                if cand.is_file():
                    return str(cand)
    return shutil.which("bash")


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASSES
    if ok:
        PASSES += 1
        print(f"  ok   {name}")
    else:
        FAILURES.append(name)
        print(f"  FAIL {name}" + (f"\n       {detail}" if detail else ""))


def payload(path: pathlib.Path) -> str:
    return json.dumps({"tool_name": "Write", "tool_input": {"file_path": path.as_posix()}})


def main() -> int:
    hook = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_HOOK
    bash = find_bash()
    if not bash:
        print("  ! bash not found; skipping post-write-reference-check")
        return 0
    if subprocess.run([bash, "-c", "command -v jq"], capture_output=True).returncode != 0:
        print("  ! jq not installed; skipping post-write-reference-check - CI will run it")
        return 0

    with tempfile.TemporaryDirectory(prefix="prc-check-") as tmp:
        root = pathlib.Path(tmp)
        stub_dir = root / "bin"
        stub_dir.mkdir()
        stub = stub_dir / "atlas"
        stub.write_text(STUB, encoding="utf-8", newline="\n")
        stub.chmod(0o755)
        log = root / "calls.log"

        def run(path: pathlib.Path, stub_exit: str = "0", with_atlas: bool = True):
            if log.exists():
                log.unlink()
            # Inside the hook's bash: put the stub first, or drop every PATH entry
            # that resolves an atlas, so `command -v atlas` fails.
            if with_atlas:
                # cygpath turns C:/x into /c/x on Git Bash; a drive colon would split PATH.
                prefix = (f'd="{stub_dir.as_posix()}"; command -v cygpath >/dev/null && d="$(cygpath -u "$d")"; '
                          'export PATH="$d:$PATH"; ')
            else:
                prefix = ('export PATH="$(printf %s "$PATH" | tr : "\\n" | '
                          'while read -r d; do [ -x "$d/atlas" ] || printf "%s:" "$d"; done)"; ')
            env = dict(os.environ, STUB_LOG=log.as_posix(), STUB_EXIT=stub_exit)
            cmd = prefix + f'bash "{hook.as_posix()}"'
            proc = subprocess.run([bash, "-c", cmd], input=payload(path).encode(),
                                  capture_output=True, env=env, timeout=30)
            called = log.exists() and log.read_text().strip() != ""
            return proc, called

        draft = root / "project" / "06 Code" / "draft.md"
        draft.parent.mkdir(parents=True)

        draft.write_text("# Code analysis\nNo marker here.\n", encoding="utf-8")
        proc, called = run(draft, "1")
        check("no marker: exit 0, atlas not called", proc.returncode == 0 and not called,
              f"exit={proc.returncode} called={called}")

        draft.write_text(f"<!-- architecture-studio:report -->\n{MARKER}\n# Memo\n", encoding="utf-8")
        proc, called = run(draft, "0")
        check("marker, clean draft: exit 0, atlas called", proc.returncode == 0 and called,
              f"exit={proc.returncode} called={called} err={proc.stderr!r}")

        proc, called = run(draft, "1")
        err = proc.stderr.decode(errors="replace")
        check("marker, leaks: exit 2 with the report on stderr",
              proc.returncode == 2 and "211 Centre" in err and "atlas refs check" in err,
              f"exit={proc.returncode} err={err!r}")
        check("marker, leaks: atlas called with refs check <file>",
              called and log.read_text().startswith("refs check "), log.read_text() if log.exists() else "")

        proc, called = run(draft, "2")
        check("atlas error (no sets configured): silent exit 0",
              proc.returncode == 0 and proc.stderr == b"", f"exit={proc.returncode} err={proc.stderr!r}")

        proc, called = run(draft, "1", with_atlas=False)
        check("no atlas on PATH: silent exit 0", proc.returncode == 0 and not called,
              f"exit={proc.returncode} err={proc.stderr!r}")

        for name in ("README.md", "SKILL.md", "AGENTS.md", "NOTES.md", "SET.md"):
            f = root / "skip" / name
            f.parent.mkdir(exist_ok=True)
            f.write_text(f"{MARKER}\n", encoding="utf-8")
            proc, called = run(f, "1")
            check(f"marked {name}: skipped", proc.returncode == 0 and not called)

        for sub in ("rules", "hooks", "Reference Sets"):
            f = root / sub / "doc.md"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(f"{MARKER}\n", encoding="utf-8")
            proc, called = run(f, "1")
            check(f"marked file under {sub}/: skipped", proc.returncode == 0 and not called)

        txt = root / "project" / "draft.txt"
        txt.write_text(f"{MARKER}\n", encoding="utf-8")
        proc, called = run(txt, "1")
        check("marked .txt: skipped", proc.returncode == 0 and not called)

        for label, raw in (("empty stdin", ""), ("malformed JSON", "{not json"),
                           ("missing file", payload(root / "nope.md"))):
            proc = subprocess.run([bash, hook.as_posix()], input=raw.encode(),
                                  capture_output=True, timeout=30)
            check(f"{label}: exit 0", proc.returncode == 0, f"exit={proc.returncode}")

    total = PASSES + len(FAILURES)
    if FAILURES:
        print(f"  {len(FAILURES)} of {total} cases failed")
        return 1
    print(f"  {PASSES} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
