"""Configuracao da Donna MCP."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALID_MODES = {
    "live-google",
    "simulated-active",
    "simulated-safe",
    "simulated-rug-pull",
}


def _resolve_local_path(raw_value: str, default_relative: str) -> Path:
    value = raw_value.strip() if raw_value else default_relative
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


@dataclass(frozen=True)
class SecretaryConfig:
    """Configuracao imutavel carregada a partir do ambiente."""

    mode: str
    timezone: str
    calendar_id: str
    credentials_file: Path
    token_file: Path
    audit_file: Path
    simulated_state_file: Path
    mutation_store_file: Path
    active_provider_file: Path
    approved_provider_file: Path
    live_google_provider_file: Path

    @classmethod
    def from_env(cls) -> "SecretaryConfig":
        mode = os.getenv("MCP_SECRETARY_MODE", "simulated-safe").strip()
        if mode not in VALID_MODES:
            valid = ", ".join(sorted(VALID_MODES))
            raise ValueError(f"MCP_SECRETARY_MODE invalido: {mode!r}. Use: {valid}.")

        return cls(
            mode=mode,
            timezone=os.getenv(
                "MCP_SECRETARY_TIMEZONE", "America/Sao_Paulo"
            ).strip(),
            calendar_id=os.getenv("MCP_SECRETARY_CALENDAR_ID", "primary").strip(),
            credentials_file=_resolve_local_path(
                os.getenv("MCP_SECRETARY_CREDENTIALS_FILE", ""),
                "local_data/credentials.json",
            ),
            token_file=_resolve_local_path(
                os.getenv("MCP_SECRETARY_TOKEN_FILE", ""),
                "local_data/token.json",
            ),
            audit_file=_resolve_local_path(
                os.getenv("MCP_SECRETARY_AUDIT_FILE", ""),
                "runtime/audit.jsonl",
            ),
            simulated_state_file=_resolve_local_path(
                os.getenv("MCP_SECRETARY_SIMULATED_STATE_FILE", ""),
                "runtime/simulated_state.json",
            ),
            mutation_store_file=_resolve_local_path(
                os.getenv("MCP_SECRETARY_MUTATION_STORE_FILE", ""),
                "runtime/mutations.json",
            ),
            active_provider_file=_resolve_local_path(
                os.getenv("MCP_SECRETARY_ACTIVE_PROVIDER_FILE", ""),
                "runtime/active_version/provider.py",
            ),
            approved_provider_file=_resolve_local_path(
                os.getenv("MCP_SECRETARY_APPROVED_PROVIDER_FILE", ""),
                "examples/demo_versions/approved/provider.py",
            ),
            live_google_provider_file=_resolve_local_path(
                os.getenv("MCP_SECRETARY_LIVE_GOOGLE_PROVIDER_FILE", ""),
                "runtime/active_google_version/provider.py",
            ),
        )

    def with_mode(self, mode: str) -> "SecretaryConfig":
        if mode not in VALID_MODES:
            raise ValueError(f"Modo invalido: {mode}")
        return replace(self, mode=mode)
