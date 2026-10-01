"""Small installed-package profiles; package managers never run in the gateway."""
import argparse
import json
import re
from pathlib import Path

from .core import SentryError
from .onboarding import prepare_codex

EXCLUDED = {"__pycache__", ".git", ".venv", "venv", ".pytest_cache", ".cache"}


def files_under(root, folder):
    selected = []
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(root)
        if any(part in EXCLUDED for part in relative.parts):
            continue
        if path.is_symlink():
            raise SentryError(f"perfil não aceita links: {relative}")
        if path.is_file():
            if path.name.startswith(".env") or re.search(r"credential|token|secret", path.name, re.I):
                # Package source can legitimately contain these words; only
                # reject common secret/config file formats.
                if path.suffix.lower() in {".json", ".pem", ".key"} or path.name.startswith(".env"):
                    raise SentryError(f"retire credenciais da instalação: {relative}")
            if path.suffix.lower() not in {".pyc", ".pyo"}:
                selected.append(relative.as_posix())
    return selected


def installed_plan(profile, root, runtime, version, data):
    root, runtime, data = root.resolve(), runtime.resolve(), data.resolve()
    if not runtime.is_file() or not data.is_dir() or not root.is_dir():
        raise SentryError("runtime, instalação e pasta de dados precisam existir")
    if data == root or root in data.parents or data in root.parents:
        raise SentryError("dados de trabalho precisam ficar separados do código instalado")
    if profile == "filesystem":
        package = root / "node_modules/@modelcontextprotocol/server-filesystem"
        metadata = json.loads((package / "package.json").read_text(encoding="utf-8"))
        if metadata.get("name") != "@modelcontextprotocol/server-filesystem" or metadata.get("version") != version:
            raise SentryError("Filesystem instalado não corresponde à versão exata solicitada")
        entry = package / "dist/index.js"
        if not entry.is_file() or not (root / "package-lock.json").is_file():
            raise SentryError("instale localmente por npm com package-lock e dist/index.js")
        files_under(root, root / "node_modules")  # reject links and credential files
        roots = ["node_modules", "package-lock.json"]
        if (root / "package.json").is_file():
            roots.append("package.json")
        command = [str(runtime), entry.relative_to(root).as_posix(), str(data)]
    else:
        # root is the selected environment's site-packages, not the whole venv.
        package = root / "mcp_server_git"
        distributions = list(root.glob("mcp_server_git-*.dist-info"))
        if len(distributions) != 1 or not (package / "__main__.py").is_file() or not (package / "__init__.py").is_file():
            raise SentryError("informe site-packages da instalação de mcp-server-git")
        metadata = (distributions[0] / "METADATA").read_text(encoding="utf-8")
        if f"Version: {version}" not in metadata.splitlines():
            raise SentryError("Git instalado não corresponde à versão exata solicitada")
        files_under(root, package)
        files_under(root, distributions[0])
        roots = ["mcp_server_git", distributions[0].name]
        command = [str(runtime), "-B", "-m", "mcp_server_git", "--repository", str(data)]
    return roots, command


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preparar instalação local fixada de Filesystem ou Git")
    parser.add_argument("--profile", choices=("filesystem", "git"), required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--fragment", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        args.inspect_root, args.backend_command = installed_plan(
            args.profile, args.project_root, args.runtime, args.version, args.data_root)
        args.passthrough_name = ["PATH", "GIT_PYTHON_GIT_EXECUTABLE"] if args.profile == "git" else []
        print(f"Perfil {args.profile} {args.version}: {len(args.inspect_root)} arquivos locais. Confira o código antes da descoberta.")
        print("Digite DESCOBRIR para autorizar uma inicialização e consultar tools/list:")
        if input() != "DESCOBRIR":
            return 0
        print(json.dumps(prepare_codex(args), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, EOFError) as exc:
        print(f"mcp-sentry: blocked: {exc}")
        return 2
