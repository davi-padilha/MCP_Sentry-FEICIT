"""Executa somente o fluxo OAuth e grava o token local."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "codigo-fonte-do-mcp"))

from donna_mcp.config import SecretaryConfig  # noqa: E402
from donna_mcp.providers.google import load_google_credentials  # noqa: E402


def main() -> None:
    config = SecretaryConfig.from_env()
    load_google_credentials(
        config.credentials_file,
        config.token_file,
        allow_interactive=True,
    )
    print(f"Autorizacao concluida. Token salvo em: {config.token_file}")


if __name__ == "__main__":
    main()
