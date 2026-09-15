"""Selecao explicita do provedor."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import ModuleType

from ..audit import AuditLog
from ..config import SecretaryConfig
from .base import SecretaryProvider
from .simulated import SimulatedProvider


def build_provider(config: SecretaryConfig, audit: AuditLog) -> SecretaryProvider:
    if config.mode == "simulated-safe":
        return SimulatedProvider(config.simulated_state_file, audit)
    if config.mode == "simulated-rug-pull":
        from .rug_pull import RugPullSimulatedProvider

        return RugPullSimulatedProvider(config.simulated_state_file, audit)
    if config.mode == "simulated-active":
        return _load_active_simulated_provider(
            config.active_provider_file, config.simulated_state_file, audit
        )
    if config.mode == "live-google":
        from .live_google import load_active_live_google_provider

        return load_active_live_google_provider(
            config.live_google_provider_file,
            credentials_file=config.credentials_file,
            token_file=config.token_file,
            calendar_id=config.calendar_id,
            timezone_name=config.timezone,
            audit=audit,
        )
    raise ValueError(f"Modo sem provedor: {config.mode}")


def _load_active_simulated_provider(
    provider_file: Path, state_file: Path, audit: AuditLog
) -> SecretaryProvider:
    """Carrega a versão ativa da demonstração sem o guard científico legado."""

    try:
        source = provider_file.read_text(encoding="utf-8")
    except OSError as exc:
        raise FileNotFoundError(
            "Versão ativa ausente. Execute activate_demo_version.py approved."
        ) from exc
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    module = ModuleType(f"donna_active_demo_provider_{source_hash}")
    module.__file__ = str(provider_file)
    exec(compile(source, str(provider_file), "exec", dont_inherit=True), module.__dict__)
    provider_class = getattr(module, "ActiveDemoProvider", None)
    if provider_class is None:
        raise RuntimeError("Provedor ativo não define ActiveDemoProvider.")
    return provider_class(state_file, audit)
