"""Prepare a local tool server for Codex without approving or installing it."""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tomllib
from pathlib import Path

from .core import APPROVED_VERSION_FILE, SentryError, capture, execution_envelope, external, load, load_execution_envelope

PROTOCOL_VERSION = "2025-06-18"
DISCOVERY_TIMEOUT_SECONDS = 15


def _command(parts: list[str], root: Path) -> list[str]:
    if parts and parts[0] == "--":
        parts = parts[1:]
    if not parts:
        raise SentryError("informe o comando do servidor após --")
    executable = sys.executable if parts[0] == "python" else parts[0]
    if Path(executable).is_absolute():
        resolved = Path(executable).resolve()
    elif any(separator in executable for separator in ("/", "\\")):
        resolved = (root / executable).resolve()
    else:
        found = shutil.which(executable)
        if not found:
            raise SentryError(f"executável não encontrado: {executable}")
        resolved = Path(found).resolve()
    if not resolved.is_file():
        raise SentryError(f"executável não encontrado: {resolved}")
    return [str(resolved), *parts[1:]]


def discover_tools(command: list[str], cwd: Path, env_names: list[str]) -> list[dict]:
    """Run the selected server once to read its real MCP tool catalog."""
    environment = {"PYTHONIOENCODING": "utf-8"}
    for name in ("SYSTEMROOT", "WINDIR", "COMSPEC", *env_names):
        if os.environ.get(name):
            environment[name] = os.environ[name]
    process = subprocess.Popen(
        command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
        env=environment,
    )
    output: queue.Queue[str | None] = queue.Queue()

    def read_stdout():
        try:
            for line in process.stdout:
                output.put(line)
        finally:
            output.put(None)

    threading.Thread(target=read_stdout, daemon=True).start()
    request_id = 0

    def exchange(method: str, params: dict | None = None) -> dict:
        nonlocal request_id
        request_id += 1
        message = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        process.stdin.flush()
        deadline = time.monotonic() + DISCOVERY_TIMEOUT_SECONDS
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SentryError(f"o servidor não respondeu a {method} em {DISCOVERY_TIMEOUT_SECONDS}s")
            try:
                line = output.get(timeout=remaining)
            except queue.Empty as exc:
                raise SentryError(f"o servidor não respondeu a {method} em {DISCOVERY_TIMEOUT_SECONDS}s") from exc
            if line is None:
                raise SentryError(f"o servidor terminou antes de responder a {method}")
            try:
                response = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SentryError("o servidor escreveu conteúdo não MCP em stdout") from exc
            if not isinstance(response, dict) or response.get("id") != request_id:
                continue
            if "error" in response or not isinstance(response.get("result"), dict):
                raise SentryError(f"o servidor rejeitou {method}")
            return response["result"]

    try:
        initialized = exchange("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "mcp-sentry-setup", "version": "0.4.0"},
        })
        if initialized.get("protocolVersion") not in {"2025-03-26", "2025-06-18"}:
            raise SentryError("versão MCP do servidor fora do escopo atual do Sentry")
        process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        process.stdin.flush()
        tools: list[dict] = []
        cursor = None
        seen_cursors = set()
        while True:
            result = exchange("tools/list", {"cursor": cursor} if cursor else {})
            page = result.get("tools")
            if not isinstance(page, list):
                raise SentryError("tools/list não retornou uma lista de ferramentas")
            tools.extend(page)
            cursor = result.get("nextCursor")
            if not cursor:
                break
            if not isinstance(cursor, str) or cursor in seen_cursors:
                raise SentryError("paginação inválida do catálogo MCP")
            seen_cursors.add(cursor)
            if len(seen_cursors) > 100:
                raise SentryError("catálogo MCP excedeu 100 páginas")
        names = [tool.get("name") for tool in tools if isinstance(tool, dict)]
        if (not tools or len(names) != len(tools) or
                any(not isinstance(name, str) or not name or name.startswith("sentry_") for name in names) or
                len(set(names)) != len(names) or
                any(not isinstance(tool.get("inputSchema"), dict) for tool in tools)):
            raise SentryError("catálogo de ferramentas inválido ou incompatível")
        return tools
    except (OSError, ValueError) as exc:
        if isinstance(exc, SentryError):
            raise
        raise SentryError(f"não foi possível consultar o servidor: {exc}") from exc
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        for stream in (process.stdin, process.stdout):
            if stream is not None:
                stream.close()


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def codex_fragment(name: str, manifest: Path, store: Path, env_names: list[str]) -> str:
    if (not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name) or
            name.startswith("mcp_sentry_review")):
        raise SentryError("nome do servidor Codex inválido ou reservado")
    review_name = f"mcp_sentry_review_{name}"
    command = str(Path(sys.executable).resolve())
    common = ["-m", "mcp_sentry_gateway.gateway"]
    execution = common + ["--interface", "execution", "--manifest", str(manifest), "--store", str(store)]
    review = common + ["--interface", "review", "--manifest", str(manifest), "--store", str(store)]
    lines = [
        f"[mcp_servers.{_toml_string(name)}]",
        f"command = {_toml_string(command)}",
        "args = " + json.dumps(execution, ensure_ascii=False),
    ]
    if env_names:
        lines.append("env_vars = " + json.dumps(env_names, ensure_ascii=False))
    lines.extend([
        "",
        f"[mcp_servers.{_toml_string(review_name)}]",
        f"command = {_toml_string(command)}",
        "args = " + json.dumps(review, ensure_ascii=False),
        "",
    ])
    fragment = "\n".join(lines)
    tomllib.loads(fragment)
    return fragment


def prepare_codex(args):
    root = args.project_root.resolve()
    manifest_path = args.manifest.resolve()
    store = args.store.resolve()
    fragment_path = args.fragment.resolve()
    if not root.is_dir():
        raise SentryError("project-root não existe")
    if not args.inspect_root:
        raise SentryError("declare pelo menos um --inspect-root")
    if not manifest_path.parent.is_dir() or not fragment_path.parent.is_dir():
        raise SentryError("as pastas do manifesto e do fragmento devem existir")
    if manifest_path == fragment_path:
        raise SentryError("manifesto e fragmento precisam de caminhos diferentes")
    for path in (manifest_path, fragment_path):
        if path.exists():
            raise SentryError(f"não sobrescrevo um arquivo existente: {path}")
        if path == root or root in path.parents:
            raise SentryError("manifesto e fragmento devem ficar fora do servidor protegido")
    external(store, root)
    command = _command(args.backend_command, root)
    names = args.passthrough_name or []
    if (len(set(names)) != len(names) or
            any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in names)):
        raise SentryError("nomes de variáveis de ambiente inválidos ou duplicados")
    manifest = {
        "manifest_version": 1,
        "project_root": os.path.relpath(root, manifest_path.parent).replace("\\", "/"),
        "inspect_roots": args.inspect_root,
        "metadata": {"tools": discover_tools(command, root, names)},
        "configuration": {
            "command": command,
            "cwd": ".",
            "runtime_paths": {},
            "passthrough_names": names,
        },
    }
    fragment = codex_fragment(args.name, manifest_path, store, names)
    created_manifest = False
    created_fragment = False
    try:
        with manifest_path.open("x", encoding="utf-8") as stream:
            created_manifest = True
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        capture(manifest_path)
        with fragment_path.open("x", encoding="utf-8") as stream:
            created_fragment = True
            stream.write(fragment)
    except Exception:
        if created_manifest:
            manifest_path.unlink(missing_ok=True)
        if created_fragment:
            fragment_path.unlink(missing_ok=True)
        raise
    return {
        "status": "prepared_for_review",
        "manifest": str(manifest_path),
        "codex_fragment": str(fragment_path),
        "tools_discovered": len(manifest["metadata"]["tools"]),
        "approved": False,
        "codex_configuration_changed": False,
    }


def doctor(manifest_path: Path, store: Path, codex_config: Path | None = None, name: str | None = None):
    issues = []
    try:
        manifest, root = load(manifest_path)
        external(store, root)
        snapshot = capture(manifest_path)
        if not snapshot["manifest"]["metadata"].get("tools"):
            issues.append("o catálogo de ferramentas está vazio")
        command = manifest["configuration"]["command"]
        if not Path(command[0]).is_file():
            issues.append("o executável do servidor protegido não existe")
        cwd = (root / manifest["configuration"].get("cwd", ".")).resolve()
        if not cwd.is_dir() or not (cwd == root or root in cwd.parents):
            issues.append("cwd não existe ou está fora do projeto")
        baseline = store / APPROVED_VERSION_FILE
        if not baseline.is_file():
            issues.append("versão inicial ainda não aprovada")
        else:
            approved = json.loads(baseline.read_text(encoding="utf-8"))
            if approved.get("capture") != snapshot:
                issues.append("a versão atual difere da aprovada")
            if execution_envelope(snapshot) != load_execution_envelope(store):
                issues.append("a configuração de execução difere da aprovada")
        if codex_config is not None:
            if not codex_config.is_file():
                issues.append("configuração do Codex não encontrada")
            else:
                configured = tomllib.loads(codex_config.read_text(encoding="utf-8")).get("mcp_servers", {})
                expected = tomllib.loads(codex_fragment(
                    name, manifest_path.resolve(), store.resolve(),
                    manifest["configuration"].get("passthrough_names", []),
                ))["mcp_servers"]
                for entry_name, desired in expected.items():
                    actual = configured.get(entry_name) if isinstance(configured, dict) else None
                    if not isinstance(actual, dict):
                        issues.append(f"entrada {entry_name} não encontrada no Codex")
                        continue
                    if actual.get("enabled", True) is False:
                        issues.append(f"entrada {entry_name} está desativada no Codex")
                    for field, value in desired.items():
                        if actual.get(field, [] if field == "env_vars" else None) != value:
                            issues.append(f"{entry_name}.{field} difere do trecho gerado")
                for env_name in manifest["configuration"].get("passthrough_names", []):
                    if env_name not in os.environ:
                        issues.append(f"variável {env_name} não está presente no ambiente local")
        return {"status": "ready" if not issues else "needs_attention", "issues": issues,
                "protected_files": len(snapshot["files"]) - 1,
                "tools": len(manifest["metadata"].get("tools", []))}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"status": "needs_attention", "issues": [str(exc)]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare MCP Sentry for Codex desktop")
    subcommands = parser.add_subparsers(dest="command", required=True)
    prepare = subcommands.add_parser("prepare-codex", help="discover tools and generate reviewable files")
    prepare.add_argument("--name", required=True)
    prepare.add_argument("--project-root", required=True, type=Path)
    prepare.add_argument("--inspect-root", action="append", required=True)
    prepare.add_argument("--manifest", required=True, type=Path)
    prepare.add_argument("--store", required=True, type=Path)
    prepare.add_argument("--fragment", required=True, type=Path)
    prepare.add_argument("--passthrough-name", action="append")
    prepare.add_argument("backend_command", nargs=argparse.REMAINDER)
    check = subcommands.add_parser("doctor", help="check local files without starting the protected server")
    check.add_argument("--manifest", required=True, type=Path)
    check.add_argument("--store", required=True, type=Path)
    check.add_argument("--codex-config", type=Path)
    check.add_argument("--name")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            if args.codex_config and not args.name:
                raise SentryError("--name é necessário com --codex-config")
            result = doctor(args.manifest, args.store, args.codex_config, args.name)
        else:
            result = prepare_codex(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] != "needs_attention" else 2
    except (OSError, ValueError, SentryError) as exc:
        print(f"mcp-sentry: preparação interrompida: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
