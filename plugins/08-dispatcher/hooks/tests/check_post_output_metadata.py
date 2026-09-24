#!/usr/bin/env python3
"""Check the post-output-metadata hook against its marker-driven contract.

Pipes Write-tool JSON into the hook for files in temporary directories and
compares the bytes on disk afterwards. Stdlib only. Never touches tracked
files or a real project: every file it writes lives under a TemporaryDirectory.

Usage:
    python3 plugins/08-dispatcher/hooks/tests/check_post_output_metadata.py [HOOK]

HOOK defaults to the post-output-metadata.sh next to this directory. Pass an
older copy of the script to confirm the check fails against it.

Exit status: 0 when every case passes, 1 on any failure, 0 with a skip notice
when bash or jq is unavailable (the hook needs both; CI has both).
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_HOOK = HERE.parent / "post-output-metadata.sh"
MARKER = "<!-- architecture-studio:report -->"

FAILURES: list[str] = []
PASSES = 0


def find_bash() -> str | None:
    """Locate a POSIX bash. On Windows prefer Git Bash over the WSL launcher."""
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


def run_hook(bash: str, hook: pathlib.Path, payload: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [bash, hook.as_posix()],
        input=payload.encode("utf-8"),
        capture_output=True,
        timeout=30,
    )


def write_payload(path: pathlib.Path) -> str:
    return json.dumps({
        "tool_name": "Write",
        "tool_input": {"file_path": path.as_posix(), "content": ""},
    })


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASSES
    if ok:
        PASSES += 1
        print(f"  ok   {name}")
    else:
        FAILURES.append(name)
        print(f"  FAIL {name}" + (f"\n       {detail}" if detail else ""))


def expect_unchanged(bash: str, hook: pathlib.Path, name: str, path: pathlib.Path) -> None:
    before = path.read_bytes()
    proc = run_hook(bash, hook, write_payload(path))
    after = path.read_bytes()
    check(
        name,
        proc.returncode == 0 and after == before,
        f"exit={proc.returncode}; changed={after != before}; stderr={proc.stderr.decode(errors='replace').strip()!r}",
    )


def count_blocks(text: str) -> int:
    return len(re.findall(r"^generated_by: skills-for-architects$", text, re.MULTILINE))


def main() -> int:
    hook = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_HOOK
    bash = find_bash()
    if not bash:
        print("  ! bash not found; skipping post-output-metadata check")
        return 0
    jq_probe = subprocess.run([bash, "-c", "command -v jq"], capture_output=True)
    if jq_probe.returncode != 0:
        print("  ! jq not installed; skipping post-output-metadata check — CI will run it")
        return 0

    with tempfile.TemporaryDirectory(prefix="pom-check-") as tmp:
        root = pathlib.Path(tmp)

        # 1. Foreign Markdown in a plain git repo that is not a studio project.
        repo = root / "foreign-repo"
        repo.mkdir()
        if shutil.which("git"):
            subprocess.run(["git", "init", "-q", str(repo)], capture_output=True)
        plain = repo / "notes.md"
        plain.write_bytes(b"# Meeting notes\n\nSome paragraph.\n---\nMore text.\n")
        expect_unchanged(bash, hook, "plain markdown with a heading, no marker: byte-identical", plain)

        issue = repo / "issue-draft.md"
        issue.write_bytes(b"Body of an issue drafted in a file, no heading.\n")
        expect_unchanged(bash, hook, "plain markdown without a heading, no marker: byte-identical", issue)

        # 2. Unmarked Markdown inside a studio project is still left alone.
        studio = root / "studio-project"
        studio.mkdir()
        (studio / "PROJECT.md").write_bytes(b"---\nname: Test\n---\n# Test\n")
        loose = studio / "scratch.md"
        loose.write_bytes(b"# Scratch\n\nNot a report.\n")
        expect_unchanged(bash, hook, "unmarked markdown in a studio project: byte-identical", loose)

        # 3. A marked report without front matter gets exactly one block.
        body = f"{MARKER}\n# Zoning Analysis — 250 Hudson St\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        report = studio / "zoning-analysis-250-hudson-st.md"
        report.write_bytes(body.encode("utf-8"))
        proc = run_hook(bash, hook, write_payload(report))
        text = report.read_bytes().decode("utf-8")
        check("marked report: hook exits 0", proc.returncode == 0,
              f"exit={proc.returncode} stderr={proc.stderr!r}")
        check("marked report: starts with a front-matter block", text.startswith("---\n"), repr(text[:80]))
        check("marked report: exactly one block", count_blocks(text) == 1, f"blocks={count_blocks(text)}")
        check("marked report: title from first heading",
              'title: "Zoning Analysis — 250 Hudson St"\n' in text, repr(text[:160]))
        check("marked report: date line present", re.search(r"^date: \d{4}-\d{2}-\d{2}$", text, re.MULTILINE) is not None)
        check("marked report: original body preserved after the block", text.endswith(body), repr(text[-120:]))

        stamped = report.read_bytes()
        proc = run_hook(bash, hook, write_payload(report))
        check("marked report: second run adds no second block",
              proc.returncode == 0 and report.read_bytes() == stamped,
              f"blocks={count_blocks(report.read_bytes().decode('utf-8'))}")

        # 4. Marked report whose heading needs YAML escaping.
        quoted = studio / "quoted.md"
        quoted.write_bytes(f'{MARKER}\n# The "Annex" report\n'.encode("utf-8"))
        run_hook(bash, hook, write_payload(quoted))
        check("marked report: double quotes in the title are escaped",
              'title: "The \\"Annex\\" report"\n' in quoted.read_text(encoding="utf-8"),
              repr(quoted.read_text(encoding="utf-8")[:120]))

        # 5. Marked report with no heading falls back to the file name.
        headless = studio / "headless-report.md"
        headless.write_bytes(f"{MARKER}\nJust a table.\n".encode("utf-8"))
        run_hook(bash, hook, write_payload(headless))
        check("marked report without heading: title is the file name",
              'title: "headless-report.md"\n' in headless.read_text(encoding="utf-8"))

        # 6. Files that already start with front matter are unchanged.
        fm = studio / "has-front-matter.md"
        fm.write_bytes(f"---\ntitle: x\n---\n{MARKER}\n# X\n".encode("utf-8"))
        expect_unchanged(bash, hook, "marked report already starting with ---: unchanged", fm)

        fm_crlf = studio / "has-front-matter-crlf.md"
        fm_crlf.write_bytes(f"---\r\ntitle: x\r\n---\r\n{MARKER}\r\n# X\r\n".encode("utf-8"))
        expect_unchanged(bash, hook, "marked report starting with ---CRLF: unchanged", fm_crlf)

        # 7. Skip names are unchanged even when marked.
        for skip in ("README.md", "SKILL.md", "CLAUDE.md", "AGENTS.md"):
            d = root / f"skipname-{skip[:-3].lower()}"
            d.mkdir()
            f = d / skip
            f.write_bytes(f"{MARKER}\n# {skip}\n".encode("utf-8"))
            expect_unchanged(bash, hook, f"marked {skip}: unchanged", f)

        # 8. Skip directories are unchanged even when marked.
        for sub in ("rules", "hooks", ".claude-plugin"):
            d = root / "plugin" / sub
            d.mkdir(parents=True)
            f = d / "doc.md"
            f.write_bytes(f"{MARKER}\n# In {sub}\n".encode("utf-8"))
            expect_unchanged(bash, hook, f"marked file under {sub}/: unchanged", f)

        # 9. Non-Markdown files are unchanged even when marked.
        txt = studio / "report.txt"
        txt.write_bytes(f"{MARKER}\n# Not markdown\n".encode("utf-8"))
        expect_unchanged(bash, hook, "marked .txt file: unchanged", txt)

        # 10. The hook never blocks a Write: odd payloads still exit 0.
        for label, payload in (
            ("empty stdin", ""),
            ("malformed JSON", "{not json"),
            ("no file_path", json.dumps({"tool_input": {}})),
            ("missing file", write_payload(studio / "does-not-exist.md")),
        ):
            proc = run_hook(bash, hook, payload)
            check(f"never blocks: {label} exits 0", proc.returncode == 0, f"exit={proc.returncode}")

    total = PASSES + len(FAILURES)
    if FAILURES:
        print(f"  {len(FAILURES)} of {total} cases failed")
        return 1
    print(f"  {total} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
