"""Carrega a versao Google ativa, instalada como uma atualizacao do mesmo MCP."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import ModuleType
from typing import Any

from .base import SecretaryProvider


def load_active_live_google_provider(
    provider_file: Path,
    **kwargs: Any,
) -> SecretaryProvider:
    """Importa o provedor que a atualizacao deixou no caminho ativo."""

    try:
        source = provider_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise FileNotFoundError(
            "Versao Google ativa ausente. Execute "
            "ferramentas-para-demonstracao/scripts-em-python/"
            "activate_google_live_version.py approved antes de iniciar."
        ) from exc
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    module = ModuleType(f"secretary_active_google_provider_{source_hash}")
    module.__file__ = str(provider_file)
    exec(compile(source, str(provider_file), "exec", dont_inherit=True), module.__dict__)
    provider_class = getattr(module, "ActiveGoogleProvider", None)
    if provider_class is None:
        raise RuntimeError("Provedor Google ativo nao define ActiveGoogleProvider.")
    return provider_class(**kwargs)
