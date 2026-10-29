"""The project-root `.mcp.json`: Pyvoid's unpinned dossier-pointer block.

Pyvoid #1545, PRD-220 section 7.6 and REQ-024. Atlas writes one MCP server
entry, ``pyvoid-revit``, whose ``env`` holds exactly ``PYVOID_PROJECT_DOSSIER``
= the job folder. ``PYVOID_FLEET_PROJECT`` is never written - not even as
``""``, which Pyvoid refuses (REQ-020). Pinning is ``pyvoid-fleet ensure``'s
job, so an existing ``pyvoid-revit`` entry, pinned or not, is never touched.

Where the server code lives is per machine (Tyler, 2026-10-07): the
``ATLAS_PYVOID_MCP_SERVER`` environment variable names this machine's Pyvoid
``mcp_server`` folder. Unset, or not a folder, Atlas writes nothing and says it
skipped. No map key and no hard-coded checkout path: job folders live on a
shared drive that several machines open.

Writes are constructive. A new file is created exclusively. An existing file
gains the entry only when it has none; every other server and top-level key
survives with its parsed content unchanged (the document is re-serialized, so
whitespace and key order may change - the PRD's semantic preservation). A file
that is not a JSON object with an object ``mcpServers`` is a conflict and is
left alone.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

MCP_SERVER_ENV = "ATLAS_PYVOID_MCP_SERVER"
SERVER_NAME = "pyvoid-revit"
DOSSIER_ENV = "PYVOID_PROJECT_DOSSIER"

# Outcome statuses; the conform statuses spelled the same, so an Action can
# carry one directly.
DONE = "done"
SKIPPED = "skipped"
CONFLICT = "conflict"


@dataclass(frozen=True)
class McpOutcome:
    status: str
    note: str


def machine_mcp_server(environ: Mapping[str, str] | None = None) -> tuple[str | None, str]:
    """This machine's Pyvoid ``mcp_server`` folder as a forward-slash path, or
    None plus the reason it cannot be used."""

    env = os.environ if environ is None else environ
    value = env.get(MCP_SERVER_ENV, "").strip()
    if not value:
        return None, f"{MCP_SERVER_ENV} is not set on this machine; .mcp.json skipped"
    path = Path(value)
    if not path.is_absolute() or not path.is_dir():
        return None, f"{MCP_SERVER_ENV}={value} is not a folder on this machine; .mcp.json skipped"
    return path.as_posix(), ""


def server_block(mcp_server: str, project: Path) -> dict:
    """The unpinned block: PRD-220 section 7.6's shape, one env key."""

    return {
        "command": "uv",
        "args": ["run", "--directory", mcp_server, "python", "-m", "pyvoid_mcp"],
        "cwd": mcp_server,
        "env": {DOSSIER_ENV: project.as_posix()},
    }


def has_pyvoid_server(text: str) -> bool:
    """Whether a `.mcp.json`'s text already names the Pyvoid server. Unparseable
    or oddly shaped text does not: doctor reports it, and conform's apply then
    finds the conflict and leaves the file alone."""

    try:
        document = json.loads(text)
    except ValueError:
        return False
    servers = document.get("mcpServers") if isinstance(document, dict) else None
    return isinstance(servers, dict) and SERVER_NAME in servers


def _serialize(document: dict) -> bytes:
    # json.dumps escapes "\n" inside strings, so every raw "\n" is structural.
    # Never splitlines(): it also splits on U+2028/U+2029/U+0085, which
    # ensure_ascii=False leaves raw inside string values.
    text = json.dumps(document, indent=2, ensure_ascii=False)
    return (text.replace("\n", "\r\n") + "\r\n").encode("utf-8")


def write_mcp_json(project: Path, mcp_file: str,
                   environ: Mapping[str, str] | None = None) -> McpOutcome:
    """Give ``project``'s ``mcp_file`` the unpinned Pyvoid entry, or say why not."""

    mcp_server, why = machine_mcp_server(environ)
    if mcp_server is None:
        return McpOutcome(SKIPPED, why)
    path = project / mcp_file
    block = server_block(mcp_server, project)
    try:
        with path.open("xb") as stream:
            stream.write(_serialize({"mcpServers": {SERVER_NAME: block}}))
        return McpOutcome(DONE, f"{mcp_file} written (unpinned dossier pointer)")
    except FileExistsError:
        pass

    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        return McpOutcome(CONFLICT, f"{mcp_file} is not valid UTF-8 JSON; left unchanged")
    if not isinstance(document, dict):
        return McpOutcome(CONFLICT, f"{mcp_file} top level is not an object; left unchanged")
    servers = document.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        return McpOutcome(CONFLICT, f"{mcp_file} mcpServers is not an object; left unchanged")
    if SERVER_NAME in servers:
        return McpOutcome(SKIPPED, f"{mcp_file} already names {SERVER_NAME}; left unchanged")
    servers[SERVER_NAME] = block
    return _replace(path, _serialize(document), raw, mcp_file)


def _replace(path: Path, contents: bytes, expected: bytes, name: str) -> McpOutcome:
    """Atomic replace, refused if the file changed since it was read.

    The compare and the replace are two steps, so a writer landing between
    them is overwritten. Known, accepted window: Pyvoid's own REQ-088 lock is a
    machine-local sentinel, and a Google Drive shared folder offers no
    cross-machine compare-and-swap, so Atlas has no lock it could share. The
    window is the few microseconds after the re-read; losing it leaves the
    unpinned block, the scaffold's normal state, which a rerun of
    `pyvoid-fleet ensure` treats like any unpinned folder."""

    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=f".{path.name}.",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
        if path.read_bytes() != expected:
            return McpOutcome(SKIPPED, f"{name} changed during apply; rerun")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return McpOutcome(DONE, f"{SERVER_NAME} added to {name} (unpinned dossier pointer)")
