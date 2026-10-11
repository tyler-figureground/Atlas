"""Deciding which File Rule, if any, files a Loose root file (ADR 0009).

Pure over a name, except for content filters, which read the file through
``content`` - and only once every name filter on the same rule has passed. The
order is the whole cost model: a name test is free, and a content test on the
Drive mount is a download.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from . import content
from .mapfile import FileRule


def _extension(name: str) -> str:
    return name.rpartition(".")[2].lower() if "." in name else ""


def names_match(rule, name: str) -> bool:
    """The name filters, for FileRule and ReceiptRule alike. Public so the
    deep pass (core/receipts.py) runs the identical tests."""
    if rule.extensions and _extension(name) not in rule.extensions:
        return False
    folded = name.casefold()
    if rule.names and not any(fnmatch.fnmatchcase(folded, g.casefold()) for g in rule.names):
        return False
    if rule.name_regex and not re.search(rule.name_regex, name, re.IGNORECASE):
        return False
    return True


def _content_matches(rule: FileRule, name: str, path: Path) -> bool:
    if not rule.pdf_text:
        return True
    # Only a file named as a PDF is ever opened for PDF text. Without this gate a
    # rule with nothing but a phrase would download every file at every root.
    if _extension(name) != "pdf":
        return False
    text = content.pdf_text(path)
    if text is None:
        return False
    return any(content.normalise(phrase) in text for phrase in rule.pdf_text)


def matches(rule: FileRule, name: str, path: Path) -> bool:
    return names_match(rule, name) and _content_matches(rule, name, path)


def first_match(rules: tuple[FileRule, ...], name: str, path: Path) -> FileRule | None:
    """The first rule, in map order, that files ``name``; None if none does.

    First match wins, the way every other map rule is resolved: a Filing State is
    decided by the first rule that applies, not by the most specific one.
    """
    return next((rule for rule in rules if matches(rule, name, path)), None)
