"""Ponto de entrada da integracao funcional com Google."""

from __future__ import annotations

import os

try:
    from ._bootstrap import configure_import_path
except ImportError:
    from _bootstrap import configure_import_path

os.environ["MCP_SECRETARY_MODE"] = "live-google"
configure_import_path()

from donna_mcp.server import main  # noqa: E402


if __name__ == "__main__":
    main()
