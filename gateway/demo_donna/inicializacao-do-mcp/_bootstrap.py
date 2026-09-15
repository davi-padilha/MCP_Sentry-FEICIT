"""Torna o código-fonte do MCP importável quando um iniciador é executado diretamente."""

from __future__ import annotations

import sys
from pathlib import Path


def configure_import_path() -> None:
    codigo_fonte = Path(__file__).resolve().parents[1] / "codigo-fonte-do-mcp"
    if str(codigo_fonte) not in sys.path:
        sys.path.insert(0, str(codigo_fonte))
