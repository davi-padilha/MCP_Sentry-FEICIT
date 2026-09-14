"""Instala uma versao Google de demonstracao no mesmo caminho ativo."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS = {
    "approved": PROJECT_ROOT / "examples" / "demo_versions" / "google_live" / "approved" / "provider.py",
    "rug-pull": PROJECT_ROOT / "examples" / "demo_versions" / "google_live" / "rug_pull" / "provider.py",
}
DEFAULT_ACTIVE_PROVIDER = PROJECT_ROOT / "runtime" / "active_google_version" / "provider.py"


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
