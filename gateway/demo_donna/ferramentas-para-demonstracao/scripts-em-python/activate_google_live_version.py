"""Instala uma versao Google de demonstracao no mesmo caminho ativo."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS = {
    "approved": PROJECT_ROOT / "versoes-para-demonstracao" / "integracao-google" / "versao-aprovada" / "provider.py",
    "rug-pull": PROJECT_ROOT / "versoes-para-demonstracao" / "integracao-google" / "alteracao-maliciosa-simulada" / "provider.py",
}
DEFAULT_ACTIVE_PROVIDER = PROJECT_ROOT / "versao-em-uso-do-mcp" / "integracao-google" / "provider.py"


def activate(version: str, destination: Path = DEFAULT_ACTIVE_PROVIDER) -> str:
    """Substitui o mesmo artefato ativo por um snapshot versionado."""

    source = SNAPSHOTS[version]
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version", choices=sorted(SNAPSHOTS))
    args = parser.parse_args()
    digest = activate(args.version)
    print(f"Google active provider: {args.version} sha256={digest}")


if __name__ == "__main__":
    main()
