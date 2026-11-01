"""Write the PROJECT.md `billing:` block the JDP time ledger reads.

The block is Pyvoid PRD-209's billing identity: ``project`` (the Atlas
project number, the folder's YYMMDD), ``client`` and an optional ``rate``
(USD/hr). Pyvoid's ``jdp.billing_identity`` is its only reader; the CRM owns
the values (CRM ADR 0004) and writes them only through ``atlas project
billing``. Atlas owns the writer, so the shape stays one the reader parses.

Atlas has no YAML parser, so it rewrites only what it can see is safe: a
block-mapping ``billing:`` whose ``project``/``client``/``rate`` children are
flat one-line scalars. Every other line - other keys in the block, comments,
the rest of the front matter - is carried through byte-for-byte. Any shape it
cannot read (a flow mapping, a scalar ``billing:``, a nested child, tabs) is
refused, never guessed at (ADR 0001).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .intake import CONTROL_PATTERN
from .project_data import (
    ProjectDataError,
    _atomic_replace,
    _front_matter_bounds,
    _lines,
    _read_source,
    _yaml_scalar,
)
from .projectmd import yaml_quote

BILLING_KEY = "billing"
BILLING_FIELDS = ("project", "client", "rate")
CHILD_INDENT = "  "

_PROJECT_NUMBER = re.compile(r"[0-9]{6}")
# Plain decimal only: PyYAML (YAML 1.1) reads `1e-05` as a string, and a
# string rate degrades the whole billing rung in Pyvoid.
_RATE = re.compile(r"[0-9]{1,9}(?:\.[0-9]{1,4})?")
_ROOT_BILLING = re.compile(r"billing:(?=[ \t]|$)")
# Any spelling a YAML reader takes as the `billing` key: quoted, or with space
# before the colon. Only the plain form is rewritten; the others are refused,
# since appending a second plain key would hide the first (last one wins).
_ANY_BILLING = re.compile(r"""["']?billing["']?[ \t]*:(?=[ \t]|$)""")
_CHILD_KEY = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*):(?=[ \t]|$)")


@dataclass(frozen=True)
class BillingValues:
    """The values Atlas writes. ``rate`` is the YAML text, or None to keep
    whatever rate line is there."""

    project: str
    client: str
    rate: str | None = None


def check_billing(project: str, client: str, rate: str | None) -> BillingValues:
    """Validate CLI text into the values the block will hold."""

    project = project.strip()
    if _PROJECT_NUMBER.fullmatch(project) is None:
        raise ProjectDataError(
            f"billing project must be the six-digit project number (YYMMDD), got {project!r}"
        )
    client = client.strip()
    if not client:
        raise ProjectDataError("billing client is required")
    if CONTROL_PATTERN.search(client):
        raise ProjectDataError("billing client cannot contain control characters")
    try:
        client.encode("utf-8")
    except UnicodeEncodeError:
        raise ProjectDataError("billing client is not valid Unicode text") from None
    if rate is None:
        return BillingValues(project, client, None)
    text = rate.strip()
    if _RATE.fullmatch(text) is None:
        raise ProjectDataError(
            f"billing rate must be a non-negative number like 60 or 62.5, got {rate!r}"
        )
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ProjectDataError(f"billing rate is not a number: {rate!r}") from None
    # Canonical: no trailing zeros, no exponent. 60.00 -> 60, 62.50 -> 62.5.
    return BillingValues(project, client, format(value.normalize(), "f"))


def _child_line(key: str, value: str) -> str:
    # project and client are always quoted: a bare 260415 is a YAML int, and
    # Pyvoid refuses a non-string project. rate is a bare number.
    rendered = value if key == "rate" else yaml_quote(value)
    return f"{CHILD_INDENT}{key}: {rendered}"


@dataclass(frozen=True)
class _Block:
    start: int                 # the `billing:` line
    end: int                   # one past the block's last line
    child_at: dict[str, int]   # Atlas's child key -> line index
    values: dict[str, str]     # Atlas's child key -> parsed scalar
    raw: dict[str, str]        # Atlas's child key -> value text as written
    comment_at: dict[str, int]  # child key -> comment offset within its line
    last_child: int            # last indented content line, or start
    indent: str


def _indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" \t"))]


def _find_block(lines: list[str], end: int, dossier: Path) -> _Block | None:
    starts = [i for i in range(1, end) if _ANY_BILLING.match(lines[i])]
    if not starts:
        return None
    if len(starts) > 1:
        raise ProjectDataError(f"{dossier} has duplicate YAML key 'billing'")
    start = starts[0]
    if not _ROOT_BILLING.match(lines[start]):
        raise ProjectDataError(
            f"{dossier} spells the 'billing' key in a form Atlas does not rewrite "
            "(write it as plain `billing:`); file not changed"
        )
    rest = lines[start][len("billing:"):].strip(" \t")
    if rest and not rest.startswith("#"):
        raise ProjectDataError(
            f"{dossier} uses unsupported YAML for 'billing' (write it as a block "
            "mapping, one key per line); file not changed"
        )
    first = next(
        (i for i in range(start + 1, end)
         if lines[i].strip() and not lines[i].lstrip().startswith("#")),
        None,
    )
    if first is not None and lines[first][:1] == "-":
        raise ProjectDataError(
            f"{dossier} uses unsupported YAML for 'billing' (a list, not a mapping); "
            "file not changed"
        )
    stop = start + 1
    while stop < end:
        line = lines[stop]
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and line[:1] not in (" ", "\t"):
            break   # the next root key
        stop += 1
    # Trailing blank and comment lines at column 0 belong after the block.
    while stop - 1 > start and (
        not lines[stop - 1].strip() or lines[stop - 1].startswith("#")
    ):
        stop -= 1

    indent: str | None = None
    child_at: dict[str, int] = {}
    values: dict[str, str] = {}
    raw: dict[str, str] = {}
    comment_at: dict[str, int] = {}
    # New children go after the last line the block owns - indented comments
    # too, which may be the tail of another child's literal value.
    last_child = start
    for index in range(start + 1, stop):
        if lines[index].strip() and not lines[index].startswith("#"):
            last_child = index
    owner: str | None = None   # the child key the current line sits under
    for index in range(start + 1, stop):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lead = _indent(line)
        if "\t" in lead:
            raise ProjectDataError(f"{dossier} indents 'billing' with a tab; file not changed")
        if indent is None:
            indent = lead
        if len(lead) > len(indent):
            if owner in BILLING_FIELDS:
                raise ProjectDataError(
                    f"{dossier} uses unsupported YAML for 'billing.{owner}' "
                    "(one-line value only); file not changed"
                )
            continue   # a nested line under someone else's key: theirs
        if lead != indent:
            raise ProjectDataError(
                f"{dossier} has inconsistent indentation in 'billing'; file not changed"
            )
        match = _CHILD_KEY.match(line[len(indent):])
        if match is None:
            raise ProjectDataError(f"{dossier} uses unsupported YAML in 'billing'; file not changed")
        owner = match.group(1)
        if owner not in BILLING_FIELDS:
            continue
        if owner in child_at:
            raise ProjectDataError(f"{dossier} has duplicate YAML key 'billing.{owner}'")
        offset = len(indent) + match.end()
        value, comment = _yaml_scalar(line[offset:], key=f"billing.{owner}", dossier=dossier)
        child_at[owner] = index
        values[owner] = value
        head = line if comment is None else line[: offset + comment]
        raw[owner] = head[offset:].strip(" \t")
        if comment is not None:
            comment_at[owner] = offset + comment
    return _Block(start, stop, child_at, values, raw, comment_at, last_child,
                  indent or CHILD_INDENT)


@dataclass(frozen=True)
class BillingPlan:
    path: Path
    values: BillingValues
    previous: dict[str, str] | None   # parsed old values; None when no block
    changed: bool
    source_digest: str
    _source: bytes = field(repr=False, compare=False)
    _rendered: bytes = field(repr=False, compare=False, default=b"")
    project_file: str = "PROJECT.md"

    @property
    def written(self) -> dict[str, str | None]:
        """The block's values after the write, as text."""
        rate = self.values.rate
        if rate is None and self.previous is not None:
            rate = self.previous.get("rate")
        return {"project": self.values.project, "client": self.values.client, "rate": rate}


def plan_billing(
    project_path: Path, values: BillingValues, *, project_file: str = "PROJECT.md"
) -> BillingPlan:
    """Plan writing the block. Never writes; ``changed`` is False when the
    block already reads exactly this way (a retry is a no-op)."""

    project, dossier, source = _read_source(project_path, project_file)
    lines = _lines(source)
    end = _front_matter_bounds(lines, dossier)
    if any(lines[i].strip() in ("---", "...") for i in range(1, end)):
        # Pyvoid ends the front matter at the first of these, Atlas at an
        # unindented `---`: a block placed between them would not be read.
        raise ProjectDataError(
            f"{dossier} has a YAML document marker inside its front matter; "
            "file not changed"
        )
    block = _find_block(lines, end, dossier)
    if block is not None and values.rate is None and "rate" in block.raw:
        kept = block.raw["rate"]
        if kept and _RATE.fullmatch(kept) is None:
            raise ProjectDataError(
                f"{dossier} has billing.rate {kept!r}, which Pyvoid cannot read as a "
                "rate; pass --rate to replace it. File not changed"
            )
    output = list(lines)
    wanted = {"project": values.project, "client": values.client}
    if values.rate is not None:
        wanted["rate"] = values.rate
    if block is None:
        output[end:end] = ["billing:", *(_child_line(k, v) for k, v in wanted.items())]
        previous = None
    else:
        previous = dict(block.values)
        appended: list[str] = []
        for key, value in wanted.items():
            rendered = _child_line(key, value)
            if block.indent != CHILD_INDENT:
                rendered = block.indent + rendered[len(CHILD_INDENT):]
            index = block.child_at.get(key)
            if index is None:
                appended.append(rendered)
                continue
            line = lines[index]
            comment_at = block.comment_at.get(key)
            head = line if comment_at is None else line[:comment_at]
            if head.rstrip(" \t") == rendered:
                continue   # already written this way: keep the line as is
            if comment_at is not None:
                rendered += " " * max(1, comment_at - len(rendered)) + line[comment_at:]
            output[index] = rendered
        insert_at = block.last_child + 1
        output[insert_at:insert_at] = appended
    rendered_bytes = ("\r\n".join(output) + "\r\n").encode("utf-8")
    return BillingPlan(
        path=project,
        values=values,
        previous=previous,
        changed=output != lines,
        source_digest=hashlib.sha256(source).hexdigest(),
        _source=source,
        _rendered=rendered_bytes,
        project_file=project_file,
    )


def apply_billing(plan: BillingPlan) -> bool:
    """Write a planned block; a no-op plan writes nothing. The dossier is
    rechecked at the swap, so an edit made since the plan is kept."""

    if not plan.changed:
        return False
    _atomic_replace(plan.path / plan.project_file, plan._rendered, plan._source)
    return True
