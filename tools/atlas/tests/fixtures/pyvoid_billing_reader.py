"""Pyvoid's billing-block reader, vendored as a contract fixture.

Copied from tyler-figureground/Pyvoid at 9f4ed728 (the last commit touching
either file): ``split_front_matter`` and ``read_front_matter``'s parse from
``mcp_server/pyvoid_mcp/jdp/project_dossier.py``, ``billing_block`` from the
same file, and ``checked_rate`` / ``_billing_facts`` from
``mcp_server/pyvoid_mcp/jdp/billing_identity.py``. Logic is unchanged; only
I/O and the degraded-reason prose are trimmed. A copy, not an import: ADR
0002 shares contracts between repos through tests, never through code.

When Pyvoid changes how it reads ``billing:``, re-copy these functions and
re-run ``tests/test_billing_block.py``.
"""

from __future__ import annotations

import math
from datetime import datetime

import yaml

_MAX_BILLABLE_HOURS = (datetime.max - datetime.min).total_seconds() / 3600.0
_EXPLICIT_NULL_BILLING = object()


def split_front_matter(text: str) -> str | None:
    lines = text.removeprefix("﻿").replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            return "\n".join(lines[1:index])
    return None


def read_front_matter_bytes(source: bytes) -> dict:
    """read_front_matter, minus the file read: Pyvoid opens with utf-8."""
    block = split_front_matter(source.decode("utf-8"))
    if block is None:
        return {}
    loaded = yaml.safe_load(block)
    return loaded if isinstance(loaded, dict) else {}


def billing_block(front_matter: dict) -> object:
    if "billing" not in front_matter:
        return None
    value = front_matter["billing"]
    return _EXPLICIT_NULL_BILLING if value is None else value


def checked_rate(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"rate must be a number, got {value!r}")
    try:
        rate = float(value)
    except OverflowError as ex:
        raise ValueError(f"rate is out of range: {value!r}") from ex
    if not math.isfinite(rate) or not math.isfinite(rate * _MAX_BILLABLE_HOURS):
        raise ValueError(f"rate must be finite and billing-safe, got {value!r}")
    if rate < 0:
        raise ValueError(f"rate must not be negative, got {value!r}")
    return rate


def billing_facts(billing: object) -> tuple[dict | None, str | None]:
    """``_billing_facts``: ``({project, client, rate}, None)`` or ``(None, why)``."""
    if not isinstance(billing, dict):
        return None, "not a mapping"
    project_raw = billing.get("project")
    if project_raw is not None and not isinstance(project_raw, str):
        return None, "non-string 'project'"
    project = (project_raw or "").strip()
    if not project:
        return None, "missing required key 'project'"
    client_raw = billing.get("client")
    if client_raw is not None and not isinstance(client_raw, str):
        return None, "non-string 'client'"
    client = (client_raw or "").strip()
    rate_raw = billing.get("rate")
    rate: float | None = None
    if rate_raw is not None:
        try:
            rate = checked_rate(rate_raw)
        except ValueError as ex:
            return None, f"unusable 'rate' ({ex})"
    return {"project": project, "client": client, "rate": rate}, None


def read_billing(source: bytes) -> tuple[dict | None, str | None]:
    """What Pyvoid's dossier rung gets from these PROJECT.md bytes."""
    return billing_facts(billing_block(read_front_matter_bytes(source)))
