"""In-memory-only host configuration for a single protected demonstration."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

from mcp_sentry_gateway.core import SentryError

# Codex MCP identifiers cannot contain spaces; this is displayed to people as
# “Donna via Sentry”, while the configuration key remains protocol-valid.
SENTRY_ENTRY_NAME = "Donna_via_Sentry"
DIRECT_BACKEND_ENTRY_NAME = "Donna"


def temporary_sentry_only_config(manifest_path, store_path):
    """Generate, but never write, the sole MCP entry permitted for a demo."""
    if not isinstance(manifest_path, (str, Path)) or not isinstance(store_path, (str, Path)):
        raise SentryError("configuração temporária inválida")
    return {"mcpServers": {SENTRY_ENTRY_NAME: {
        "command": str(Path(sys.executable).resolve()),
        "args": ["-m", "mcp_sentry_gateway.gateway", "--manifest", str(manifest_path), "--store", str(store_path)],
    }}}


def validate_sentry_only_config(config):
    """Fail closed if a direct Donna entry or any second MCP entry is present."""
    if not isinstance(config, dict) or set(config) != {"mcpServers"} or not isinstance(config["mcpServers"], dict):
        raise SentryError("configuração temporária inválida")
    entries = config["mcpServers"]
    if DIRECT_BACKEND_ENTRY_NAME in entries or set(entries) != {SENTRY_ENTRY_NAME}:
        raise SentryError("bypass detectado: somente Donna via Sentry pode ficar habilitada")
    entry = entries[SENTRY_ENTRY_NAME]
    if not isinstance(entry, dict) or set(entry) != {"command", "args"}:
        raise SentryError("entrada temporária do Sentry inválida")
    args = entry.get("args")
    if (entry.get("command") != str(Path(sys.executable).resolve()) or not isinstance(args, list) or len(args) != 6 or
            args[:2] != ["-m", "mcp_sentry_gateway.gateway"] or args[2] != "--manifest" or
            not isinstance(args[3], str) or not args[3] or args[4] != "--store" or not isinstance(args[5], str) or not args[5]):
        raise SentryError("entrada temporária do Sentry inválida")
    return deepcopy(config)


def cleanup_temporary_sentry_config(config):
    """Return an empty, verified replacement; caller remains responsible for any host write."""
    validate_sentry_only_config(config)
    return {"mcpServers": {}}
