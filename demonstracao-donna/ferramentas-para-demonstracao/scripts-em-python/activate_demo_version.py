"""Ativa um snapshot no caminho canonico usado pelo servidor de demonstracao."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSIONS = {
    "approved": PROJECT_ROOT / "versoes-para-demonstracao" / "simulacao-controlada" / "versao-aprovada" / "provider.py",
    "rug-pull": PROJECT_ROOT / "versoes-para-demonstracao" / "simulacao-controlada" / "alteracao-maliciosa-simulada" / "provider.py",
}
ACTIVE_FILE = PROJECT_ROOT / "versao-em-uso-do-mcp" / "simulacao-controlada" / "provider.py"
ACTIVE_METADATA = PROJECT_ROOT / "versao-em-uso-do-mcp" / "simulacao-controlada" / "version.json"
SESSION_FILES = [
    PROJECT_ROOT / "dados-gerados-pelo-mcp" / "estado-da-simulacao.json",
    PROJECT_ROOT / "dados-gerados-pelo-mcp" / "estado-das-acoes.json",
]
AUDIT_FILE = PROJECT_ROOT / "dados-gerados-pelo-mcp" / "historico-de-atividades.jsonl"


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            with source.open("rb") as source_stream:
                shutil.copyfileobj(source_stream, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _atomic_write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def activate(
    version: str,
    destination: Path = ACTIVE_FILE,
    *,
    reset_session: bool = False,
    clear_audit: bool = False,
) -> dict[str, object]:
    source = VERSIONS[version]
    _atomic_copy(source, destination)
    removed: list[str] = []
    if reset_session:
        for path in SESSION_FILES:
            if path.exists():
                path.unlink()
                removed.append(str(path.resolve()))
    if clear_audit and AUDIT_FILE.exists():
        AUDIT_FILE.unlink()
        removed.append(str(AUDIT_FILE.resolve()))
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    metadata = {
        "version": version,
        "active_path": str(destination.resolve()),
        "sha256": digest,
        "session_reset": reset_session,
        "audit_cleared": clear_audit,
    }
    metadata_path = destination.parent / ACTIVE_METADATA.name
    _atomic_write_json(metadata_path, metadata)
    return {**metadata, "removed_local_files": removed}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version", choices=sorted(VERSIONS))
    parser.add_argument("--destination", type=Path, default=ACTIVE_FILE)
    parser.add_argument("--reset-session", action="store_true")
    parser.add_argument("--clear-audit", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            activate(
                args.version,
                args.destination,
                reset_session=args.reset_session,
                clear_audit=args.clear_audit,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
