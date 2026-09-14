"""Torna o pacote src importável quando um entrypoint é executado diretamente."""

from __future__ import annotations

import sys
from pathlib import Path


def configure_import_path() -> None:
    src = Path(__file__).resolve().parents[1] / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
