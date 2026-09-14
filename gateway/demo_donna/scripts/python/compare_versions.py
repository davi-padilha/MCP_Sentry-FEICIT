"""Compara as impressoes digitais das duas versoes da demonstracao."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMMON_FILES = [
    "entrypoints/server_demonstracao.py",
    "src/donna_mcp/server.py",
    "src/donna_mcp/audit.py",
    "src/donna_mcp/config.py",
    "src/donna_mcp/mutations.py",
    "src/donna_mcp/service.py",
    "src/donna_mcp/providers/base.py",
    "src/donna_mcp/providers/factory.py",
    "src/donna_mcp/providers/simulated.py",
]
VERSION_PROVIDER = {
    "approved": "examples/demo_versions/approved/provider.py",
    "rug_pull": "examples/demo_versions/rug_pull/provider.py",
}
CANONICAL_PROVIDER_PATH = "runtime/active_version/provider.py"


def _fingerprint(provider_source: str) -> tuple[str, dict[str, str]]:
    aggregate = hashlib.sha256()
    per_file: dict[str, str] = {}
    canonical_sources = {
        relative_path: relative_path for relative_path in COMMON_FILES
    }
    canonical_sources[CANONICAL_PROVIDER_PATH] = provider_source
    for canonical_path in sorted(canonical_sources):
        source_path = canonical_sources[canonical_path]
        content = (PROJECT_ROOT / source_path).read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        per_file[canonical_path] = digest
        aggregate.update(canonical_path.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(content)
        aggregate.update(b"\0")
    return aggregate.hexdigest(), per_file


def main() -> None:
    result = {}
    for version, provider_source in VERSION_PROVIDER.items():
        digest, per_file = _fingerprint(provider_source)
        result[version] = {"sha256": digest, "files": per_file}
    changed_files = [
        path
        for path in result["approved"]["files"]
        if result["approved"]["files"][path]
        != result["rug_pull"]["files"][path]
    ]
    result["changed"] = result["approved"]["sha256"] != result["rug_pull"]["sha256"]
    result["changed_files"] = changed_files
    result["only_canonical_provider_changed"] = changed_files == [
        CANONICAL_PROVIDER_PATH
    ]
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if not result["changed"] or not result["only_canonical_provider_changed"]:
        raise SystemExit(
            "Comparacao invalida: as versoes devem diferir somente no provedor canonico."
        )


if __name__ == "__main__":
    main()
