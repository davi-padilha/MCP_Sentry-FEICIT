"""Utilitários de teste para carregar scripts pelos seus caminhos explícitos."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType


def load_script(path: Path, module_name: str) -> ModuleType:
    """Carrega um script de apoio sem exigir que sua pasta seja um pacote Python."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível carregar o script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
