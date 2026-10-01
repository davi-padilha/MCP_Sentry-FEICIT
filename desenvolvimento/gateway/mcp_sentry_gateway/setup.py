"""Interactive, conservative setup for one Codex stdio server."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
import uuid
from pathlib import Path
from types import SimpleNamespace

from .core import SentryError, approve, capture, canon, digest
from .onboarding import codex_fragment, doctor, prepare_codex

CLIENT_OPTIONS = {"default_tools_approval_mode", "startup_timeout_sec", "tool_timeout_sec"}
SUPPORTED_FIELDS = {"command", "args", "cwd", "env", "env_vars", "enabled", *CLIENT_OPTIONS}
SECTION_RE = re.compile(r"^\s*(\[\[?)([^\[\]]+)(\]\]?)\s*(?:#.*)?$")
NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*\Z")


def _ask(prompt, input_fn, output):
    output(prompt)
    try:
        return input_fn().strip()
    except (EOFError, KeyboardInterrupt) as exc:
        raise SentryError("preparação cancelada") from exc


def _configuration(path: Path):
    try:
        raw = path.read_bytes()
        data = tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise SentryError(f"não foi possível ler config.toml: {exc}") from exc
    servers = data.get("mcp_servers", {})
    if not isinstance(servers, dict):
        raise SentryError("mcp_servers do Codex é inválido")
    return raw, data, servers


def _eligible(name, entry):
    return (
        isinstance(name, str) and NAME_RE.fullmatch(name) is not None
        and not name.startswith("mcp_sentry_review")
        and isinstance(entry, dict) and entry.get("enabled", True) is True
        and isinstance(entry.get("command"), str) and bool(entry["command"])
        and "url" not in entry and "type" not in entry
    )


def _select_server(servers, requested_name, input_fn, output):
    choices = sorted(name for name, entry in servers.items() if _eligible(name, entry))
    if not choices:
        raise SentryError("nenhum servidor MCP local stdio compatível foi encontrado neste arquivo")
    if requested_name is not None:
        if requested_name not in choices:
            raise SentryError("servidor solicitado não está entre as entradas stdio compatíveis")
        return requested_name
    output("Servidores MCP locais encontrados:")
    for number, name in enumerate(choices, 1):
        output(f"  {number}. {name}")
    selected = _ask("Digite o número do servidor que deseja proteger:", input_fn, output)
    if not selected.isdigit() or not 1 <= int(selected) <= len(choices):
        raise SentryError("seleção inválida")
    return choices[int(selected) - 1]


def _server_details(name, entry):
    extra = set(entry) - SUPPORTED_FIELDS
    if extra:
        raise SentryError(f"{name} usa opções ainda não migradas pelo setup: {', '.join(sorted(extra))}")
    args = entry.get("args", [])
    env = entry.get("env", {})
    env_vars = entry.get("env_vars", [])
    if (not isinstance(args, list) or not all(isinstance(item, str) for item in args)
            or not isinstance(env, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in env.items())
            or not isinstance(env_vars, list) or not all(isinstance(item, str) for item in env_vars)):
        raise SentryError("args, env ou env_vars incompatíveis com esta versão do setup")
    if entry["command"].lower() in {"python", "python.exe", "py", "py.exe"}:
        raise SentryError("use um caminho absoluto para o interpretador Python antes de executar setup")
    original_cwd = entry.get("cwd")
    if original_cwd is not None:
        if not isinstance(original_cwd, str) or not Path(original_cwd).is_absolute():
            raise SentryError("cwd deve ser um caminho absoluto para migrá-lo com segurança")
        original_cwd = Path(original_cwd).resolve()
        if not original_cwd.is_dir():
            raise SentryError("cwd do servidor não existe")
    policy = entry.get("default_tools_approval_mode")
    if policy is not None and policy not in {"auto", "prompt", "writes", "approve"}:
        raise SentryError("default_tools_approval_mode inválido")
    for field in ("startup_timeout_sec", "tool_timeout_sec"):
        value = entry.get(field)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= 3600):
            raise SentryError(f"{field} deve ser um número entre 0 e 3600")
    command = [entry["command"], *args]
    options = {key: entry[key] for key in CLIENT_OPTIONS if key in entry}
    return command, original_cwd, env, list(dict.fromkeys([*env_vars, *env.keys()])), options


def _suggest_root(command, original_cwd=None):
    if original_cwd is not None:
        return original_cwd
    for item in command[1:]:
        candidate = Path(item)
        if candidate.suffix.lower() in {".py", ".js", ".mjs", ".cjs"} and candidate.is_absolute() and candidate.is_file():
            return candidate.parent.resolve()
    return None


def _suggest_inspection(command, root, original_cwd=None):
    suggested = []
    if "-m" in command[1:]:
        index = command.index("-m")
        if index + 1 < len(command):
            module = (original_cwd or root) / command[index + 1].replace(".", "/")
            if (module / "__main__.py").is_file() and (module / "__init__.py").is_file() and root in module.parents:
                suggested.append(module.relative_to(root).as_posix())
    for item in command[1:]:
        candidate = Path(item)
        if candidate.suffix not in {".py", ".js", ".mjs", ".cjs"}:
            continue
        resolved = candidate.resolve() if candidate.is_absolute() else ((original_cwd or root) / candidate).resolve()
        if resolved.is_file() and root in resolved.parents:
            suggested.append(resolved.relative_to(root).as_posix())
    for package in root.iterdir():
        if package.is_dir() and (package / "__init__.py").is_file():
            suggested.append(package.relative_to(root).as_posix())
    if Path(command[0]).name.lower() in {"node", "node.exe"}:
        for item in ("node_modules", "package.json", "package-lock.json"):
            if (root / item).exists():
                suggested.append(item)
    return list(dict.fromkeys(suggested))


def _package_launcher(command):
    launcher = Path(command[0]).stem.lower()
    return launcher in {"npx", "uvx"} or (
        launcher == "cmd" and len(command) >= 3
        and command[1].lower() == "/c" and Path(command[2]).stem.lower() == "npx"
    )


def _package_plan(command, original_cwd, state_root, name, input_fn, output):
    """Install a pinned launcher, then return the same plan as materialize."""
    from .materialize import launcher_spec, materialize
    from .onboarding import _command
    # A copied installation cannot reproduce an arbitrary launcher's cwd.
    if original_cwd is not None:
        raise SentryError("npx/uvx com cwd explícito exige preparação manual; use caminhos absolutos para dados e prepare-server")
    try:
        spec = launcher_spec(command)
    except SentryError as exc:
        # Ask only for a plain unpinned package, never reinterpret a tag/range.
        if "versão exata obrigatória" not in str(exc):
            raise
        launcher_spec(command, "0.0.0")
        version = _ask("Versão exata do pacote (sem latest ou intervalos):", input_fn, output)
        spec = launcher_spec(command, version)
    runtime_default = (shutil.which("node.exe") or shutil.which("node")) if spec["kind"] == "node" else sys.executable
    runtime_answer = _ask(
        f"Executável {'Node.js' if spec['kind'] == 'node' else 'Python'} [{runtime_default or 'não encontrado'}]:",
        input_fn, output,
    )
    runtime = _command([runtime_answer or runtime_default or "node"], Path.cwd())[0]
    expected = r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?" if spec["kind"] == "python" else r"node(?:\.exe)?"
    if not re.fullmatch(expected, Path(runtime).name.lower()):
        raise SentryError("informe o executável Python/Node correspondente ao pacote")
    default_root = state_root.parent / "MCP-Sentry-servidores" / f"{name}-{spec['version']}-{uuid.uuid4().hex[:8]}"
    answer = _ask(f"Pasta nova para instalar o servidor [{default_root}]:", input_fn, output)
    install_root = Path(answer).resolve() if answer else default_root
    if install_root.exists():
        raise SentryError("a pasta de instalação já existe; escolha uma pasta nova")
    if install_root == state_root or state_root in install_root.parents or install_root in state_root.parents:
        raise SentryError("a instalação do servidor deve ficar separada do estado do Sentry")
    output(f"Pacote: {spec['package']} — versão {spec['version']}.")
    output("Os argumentos do servidor serão mantidos. Caminhos de dados devem ser absolutos.")
    output("O download instala dependências; ainda não inicia nem aprova o servidor.")
    if _ask("Digite INSTALAR para baixar nesta pasta nova:", input_fn, output) != "INSTALAR":
        return None
    try:
        plan = materialize(spec, install_root, runtime)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise SentryError(f"não foi possível instalar o pacote; configuração do Codex preservada. Confira {install_root}: {exc}") from exc
    output(f"Instalação preparada em {install_root}; plano: {plan['plan']}.")
    output("Dependências externas confiadas: " + "; ".join(plan["external_dependencies"]))
    return plan


def _portable_backend_command(command, root, original_cwd=None):
    """Bind the Python entry script to the verified copy, not the original tree."""
    executable = Path(command[0])
    if executable.name.lower() in {"node", "node.exe"}:
        from .preparation import local_command
        return local_command(command, root, (original_cwd or root).relative_to(root).as_posix())
    if (not executable.is_absolute() or not executable.is_file()
            or not re.fullmatch(r"python(?:\d+(?:\.\d+)?)?(?:\.exe)?", executable.name.lower())):
        raise SentryError("setup inicial suporta apenas um interpretador Python com caminho absoluto")
    if len(command) >= 3 and command[1] == "-m":
        if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", command[2]):
            raise SentryError("nome de módulo inválido")
        module = (original_cwd or root) / command[2].replace(".", "/")
        if not (module / "__main__.py").is_file() or not (module / "__init__.py").is_file() or root not in module.parents:
            raise SentryError("módulo precisa existir na pasta protegida; use prepare-profile para pacotes instalados")
        return [str(executable.resolve()), "-B", *command[1:]]
    if len(command) < 2 or Path(command[1]).suffix.lower() != ".py":
        raise SentryError("setup inicial requer um script .py como primeiro argumento")
    script = Path(command[1])
    resolved = script.resolve() if script.is_absolute() else ((original_cwd or root) / script).resolve()
    if not resolved.is_file() or root not in resolved.parents:
        raise SentryError(f"script Python não existe dentro da pasta escolhida: {resolved}")
    working_directory = original_cwd or root
    return [str(executable.resolve()), os.path.relpath(resolved, working_directory), *command[2:]]


def _mastertool_batch_plan(command, root, original_cwd, inline_env):
    """Translate the known MasterTool launcher without executing its original tree."""
    launcher = Path(command[0]).resolve()
    if (len(command) != 1 or launcher.name.lower() != "run_server.cmd"
            or launcher.parent.name.lower() != "scripts"
            or launcher.parent.parent != root or original_cwd != root):
        raise SentryError("launcher .cmd não reconhecido; este setup só adapta scripts/run_server.cmd do MasterTool")
    try:
        source = launcher.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SentryError("não foi possível conferir o launcher do MasterTool") from exc
    markers = (
        r'set\s+"SCRIPT_DIR=%~dp0"',
        r'set\s+"PACKAGE_ROOT=%%~fI"',
        r'%PACKAGE_ROOT%\\\.venv\\Scripts\\python\.exe',
        r'%PACKAGE_ROOT%\\server\.py',
    )
    if any(re.search(marker, source, re.IGNORECASE) is None for marker in markers):
        raise SentryError("run_server.cmd não corresponde ao formato conhecido; nenhuma troca foi feita")
    interpreter = root / ".venv" / "Scripts" / "python.exe"
    entry = root / "server.py"
    package = root / "mastertool_mcp"
    if not interpreter.is_file() or not entry.is_file() or not package.is_dir():
        raise SentryError("MasterTool precisa de .venv/Scripts/python.exe, server.py e mastertool_mcp")
    package_files = sorted(package.rglob("*.py"))
    if not package_files:
        raise SentryError("nenhum arquivo Python foi encontrado em mastertool_mcp")
    defaults = {}
    for name in ("MASTERTOOL_MCP_WORKSPACE", "MASTERTOOL_EXECUTABLE"):
        match = re.search(rf'set\s+"{name}=([^"\r\n]+)"', source, re.IGNORECASE)
        if match is None:
            raise SentryError(f"launcher não declara {name}; confira-o antes da migração")
        value = match.group(1)
        if "%USERPROFILE%" in value.upper():
            value = re.sub(r"%USERPROFILE%", lambda _: str(Path.home()), value, flags=re.IGNORECASE)
        if "%" in value or not Path(value).is_absolute():
            raise SentryError(f"valor padrão de {name} não pôde ser resolvido")
        defaults[name] = os.environ.get(name) or value
    # Codex's explicit values take precedence over the launcher's defaults.
    defaults.update({key: inline_env[key] for key in defaults if inline_env.get(key)})
    inspect_files = ["server.py", *(item.relative_to(root).as_posix() for item in package_files)]
    return [str(interpreter.resolve()), "server.py"], inspect_files, defaults


def _covers_required_files(project_root, inspect_roots, required_files):
    selected = [(project_root / item).resolve() for item in inspect_roots]
    return all(
        any(file == chosen or chosen in file.parents for chosen in selected)
        for file in ((project_root / item).resolve() for item in required_files)
    )


def _validate_inspection(project_root, inspect_roots):
    for item in inspect_roots:
        selected = (project_root / item).resolve()
        if not (selected == project_root or project_root in selected.parents):
            raise SentryError(f"arquivo/pasta fora do projeto: {item}")
        files = [selected] if selected.is_file() else list(selected.rglob("*")) if selected.is_dir() else []
        files = [path for path in files if path.is_file()]
        if not files:
            raise SentryError(f"arquivo/pasta inexistente ou vazio: {item}")
        if any(not (path.resolve() == project_root or project_root in path.resolve().parents) for path in files):
            raise SentryError(f"arquivo/pasta inclui link para fora do projeto: {item}")


def _section_path(header):
    marker = "__mcp_sentry_section_marker__"
    try:
        parsed = tomllib.loads(f"[{header}]\n{marker} = true\n")
    except tomllib.TOMLDecodeError as exc:
        raise SentryError("cabeçalho TOML não suportado pelo instalador") from exc

    def find(value, path=()):
        if isinstance(value, dict):
            if marker in value:
                return path
            for key, child in value.items():
                result = find(child, path + (key,))
                if result is not None:
                    return result
        return None

    return find(parsed)


def _replace_server_table(original: bytes, name: str, replacement: str):
    text = original.decode("utf-8")
    lines = text.splitlines(keepends=True)
    headings = []
    for index, line in enumerate(lines):
        match = SECTION_RE.fullmatch(line.rstrip("\r\n"))
        if match and len(match.group(1)) == len(match.group(3)):
            headings.append((index, _section_path(match.group(2))))
    target = ("mcp_servers", name)
    if not any(path == target for _, path in headings):
        raise SentryError("a entrada selecionada precisa estar em uma tabela [mcp_servers.nome]")
    remove = set()
    for position, (start, path) in enumerate(headings):
        if path is not None and path[:2] == target:
            end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
            remove.update(range(start, end))
    retained = "".join(line for index, line in enumerate(lines) if index not in remove)
    if retained and not retained.endswith("\n"):
        retained += "\n"
    changed = retained + "\n" + replacement
    before = tomllib.loads(text)
    after = tomllib.loads(changed)
    expected = dict(before)
    expected_servers = dict(before["mcp_servers"])
    expected_servers.pop(name)
    expected_servers.update(tomllib.loads(replacement)["mcp_servers"])
    expected["mcp_servers"] = expected_servers
    if after != expected:
        raise SentryError("a edição proposta alteraria outras opções do Codex")
    return changed.encode("utf-8")


def _fragment_with_env(name, manifest, store, passthrough_names, inline_env, client_options):
    fragment = codex_fragment(name, manifest, store, passthrough_names)
    if not inline_env and not client_options:
        return fragment
    lines = fragment.splitlines()
    first_gap = lines.index("")
    additions = []
    if inline_env:
        encoded = ", ".join(
            f"{json.dumps(key, ensure_ascii=False)} = {json.dumps(value, ensure_ascii=False)}"
            for key, value in inline_env.items()
        )
        additions.append(f"env = {{ {encoded} }}")
    for key in sorted(client_options):
        additions.append(f"{key} = {json.dumps(client_options[key])}")
    lines[first_gap:first_gap] = additions
    result = "\n".join(lines) + "\n"
    tomllib.loads(result)
    return result


def _save_config(config_path, original, updated):
    backup = config_path.with_name(f"{config_path.name}.sentry-backup-{uuid.uuid4().hex}.bak")
    temporary = config_path.with_name(f".{config_path.name}.sentry-{uuid.uuid4().hex}.tmp")
    try:
        with backup.open("xb") as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
        with temporary.open("xb") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        if config_path.read_bytes() != original:
            raise SentryError("config.toml mudou durante a preparação; backup preservado")
        os.replace(temporary, config_path)
        return backup
    finally:
        temporary.unlink(missing_ok=True)


def _restore_config(config_path, original, updated):
    """Roll back only our own write; never replace a concurrent user edit."""
    if config_path.read_bytes() != updated:
        raise SentryError("config.toml mudou após a instalação; restaure o backup manualmente")
    temporary = config_path.with_name(f".{config_path.name}.sentry-rollback-{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, config_path)
    finally:
        temporary.unlink(missing_ok=True)


def run_setup(config_path: Path, state_root: Path, *, requested_name=None, input_fn=input, output=print):
    config_path = config_path.resolve()
    state_root = state_root.resolve()
    original, _, servers = _configuration(config_path)
    name = _select_server(servers, requested_name, input_fn, output)
    review_name = f"mcp_sentry_review_{name}"
    if review_name in servers:
        raise SentryError("já existe uma entrada de revisão com este nome")
    command, original_cwd, inline_env, passthrough_names, client_options = _server_details(name, servers[name])
    # Validate the destination table before downloads or discovery.
    _replace_server_table(original, name, f"[mcp_servers.{json.dumps(name)}]\ncommand = \"preflight\"\n")
    if _package_launcher(command):
        existing = state_root / name
        if existing.exists():
            raise SentryError(f"já existe um estado para {name}: {existing}")
        plan = _package_plan(command, original_cwd, state_root, name, input_fn, output)
        if plan is None:
            return {"status": "cancelled_before_installation"}
        root = Path(plan["project_root"]).resolve()
        backend_cwd = "."
        portable_command = plan["command"]
        suggested_files = plan["inspect_roots"]
    else:
        suggested_root = _suggest_root(command, original_cwd)
        suffix = f" [{suggested_root}]" if suggested_root else ""
        root_answer = _ask(f"Pasta do projeto do servidor{suffix}:", input_fn, output)
        root = Path(root_answer).resolve() if root_answer else suggested_root
        if root is None or not root.is_dir():
            raise SentryError("informe uma pasta de servidor existente")
        if original_cwd is not None and not (original_cwd == root or root in original_cwd.parents):
            raise SentryError("cwd precisa estar dentro da pasta do projeto escolhida")
        backend_cwd = original_cwd.relative_to(root).as_posix() if original_cwd else "."
        if Path(command[0]).suffix.lower() == ".cmd":
            portable_command, suggested_files, defaults = _mastertool_batch_plan(command, root, original_cwd, inline_env)
            inline_env = {**defaults, **{key: value for key, value in inline_env.items()
                                         if value or key not in defaults}}
            passthrough_names = list(dict.fromkeys([*passthrough_names, *defaults]))
            output("Launcher MasterTool reconhecido: a cópia verificada usará server.py e mastertool_mcp.")
            output("Python instalado, workspace de trabalho e executável MasterTool permanecem dependências externas.")
        else:
            portable_command = _portable_backend_command(command, root, original_cwd)
            suggested_files = _suggest_inspection(command, root, original_cwd)
    default = ", ".join(suggested_files)
    files_answer = _ask(
        f"Arquivos/pastas a proteger, separados por vírgula [{default}]:", input_fn, output,
    )
    inspect_roots = [part.strip() for part in (files_answer or default).split(",") if part.strip()]
    if not inspect_roots:
        raise SentryError("nenhum arquivo foi escolhido; inclua também módulos e configurações locais necessários")
    if not _covers_required_files(root, inspect_roots, suggested_files):
        raise SentryError("a seleção precisa incluir todos os arquivos de código sugeridos para esta entrada")
    _validate_inspection(root, inspect_roots)
    state_dir = state_root / name
    manifest_dir = state_dir / "config"
    manifest_path = manifest_dir / "manifest.json"
    fragment_path = manifest_dir / "codex-fragment.toml"
    store = state_dir / "state"
    if any(path == root or root in path.parents for path in (manifest_path, fragment_path, store)):
        raise SentryError("o estado do Sentry deve ficar fora da pasta do servidor protegido")
    # Verify the selected TOML table can be replaced before starting the backend.
    _replace_server_table(original, name, f"[mcp_servers.{json.dumps(name)}]\ncommand = \"preflight\"\n")
    output("A descoberta iniciará uma cópia verificada do servidor uma vez para consultar tools/list.")
    if _ask("Digite DESCOBRIR para continuar:", input_fn, output) != "DESCOBRIR":
        return {"status": "cancelled_before_discovery"}
    if state_dir.exists():
        # A failed preparation may leave only this empty config directory.
        # Reuse it without deleting or replacing any user data.
        reusable = (
            state_dir.is_dir() and not state_dir.is_symlink()
            and manifest_dir.is_dir() and not manifest_dir.is_symlink()
            and set(state_dir.iterdir()) == {manifest_dir}
            and not any(manifest_dir.iterdir())
        )
        if not reusable:
            raise SentryError(f"já existe um estado para {name}: {state_dir}")
        output("Preparação anterior deixou apenas uma pasta de configuração vazia; reutilizando-a.")
    else:
        manifest_dir.mkdir(parents=True)
    arguments = SimpleNamespace(
        name=name, project_root=root, inspect_root=inspect_roots,
        manifest=manifest_path, store=store, fragment=fragment_path,
        passthrough_name=passthrough_names, backend_command=portable_command, env_values=inline_env,
        backend_cwd=backend_cwd,
        backend_timeout_sec=max(10, client_options.get("startup_timeout_sec", 10), client_options.get("tool_timeout_sec", 10)),
    )
    prepare_codex(arguments)
    snapshot = capture(manifest_path)
    output(f"Manifesto para revisão: {manifest_path}")
    output(f"Arquivos inspecionados: {len(snapshot['files']) - 1}")
    shown_files = [item for item in snapshot["files"] if item["path"] != "@manifest"]
    for item in shown_files[:20]:
        output(f"  {item['path']}  sha256:{item['sha256'][:16]}…")
    if len(shown_files) > 20:
        output(f"  ... e mais {len(shown_files) - 20} arquivos; a referência completa será registrada no estado.")
    output("Ferramentas anunciadas:")
    for tool in snapshot["manifest"]["metadata"]["tools"]:
        output(f"  {tool['name']}: {tool.get('description', '')}")
    output("Confira o código e o manifesto antes de aprovar. Arquivos externos não são verificados.")
    if _ask("Digite APROVAR para registrar esta versão como referência:", input_fn, output) != "APROVAR":
        return {"status": "prepared_not_approved", "manifest": str(manifest_path)}
    approve(manifest_path, store, expected_hash=digest(canon(snapshot)))
    replacement = _fragment_with_env(name, manifest_path, store, passthrough_names, inline_env, client_options)
    updated = _replace_server_table(original, name, replacement)
    output(f"A entrada direta '{name}' será substituída por execução via Sentry e revisão separada.")
    output(f"Arquivo a alterar: {config_path}. Um backup integral será preservado.")
    if _ask("Digite SUBSTITUIR para aplicar a configuração:", input_fn, output) != "SUBSTITUIR":
        return {"status": "approved_not_connected", "manifest": str(manifest_path)}
    backup = _save_config(config_path, original, updated)
    diagnosis = doctor(manifest_path, store, config_path, name)
    if diagnosis["status"] != "ready":
        try:
            _restore_config(config_path, original, updated)
        except (OSError, SentryError) as exc:
            raise SentryError(f"doctor requer atenção e a restauração automática falhou; backup: {backup}; causa: {exc}") from exc
        raise SentryError(f"doctor requer atenção; configuração original restaurada; backup: {backup}; problemas: {diagnosis['issues']}")
    return {
        "status": "connected_restart_required", "server": name,
        "manifest": str(manifest_path), "backup": str(backup),
        "config": str(config_path), "tools": diagnosis["tools"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Instalação assistida do MCP Sentry no Codex")
    parser.add_argument("--codex-config", type=Path, default=Path.home() / ".codex" / "config.toml")
    parser.add_argument("--state-root", type=Path, default=Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MCP-Sentry")
    parser.add_argument("--name", help="selecionar servidor sem menu")
    args = parser.parse_args(argv)
    try:
        result = run_setup(args.codex_config, args.state_root, requested_name=args.name)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["status"] == "connected_restart_required":
            print("Reinicie o Codex e verifique as conexões em /mcp.")
        return 0
    except (OSError, ValueError, SentryError) as exc:
        print(f"mcp-sentry: setup interrompido: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
