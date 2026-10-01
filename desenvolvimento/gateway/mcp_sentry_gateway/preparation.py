"""Generic, local Python/Node preparation. No server-specific identity required."""
import argparse
import os
import re
from pathlib import Path

from .core import SentryError


def module_files(workdir, name):
    parts = name.split(".")
    if not parts or not all(p.isidentifier() for p in parts):
        raise SentryError("nome de módulo Python inválido")
    target = workdir.joinpath(*parts)
    required = [workdir.joinpath(*parts[:n]) / "__init__.py" for n in range(1, len(parts))]
    if target.is_dir():
        required += [target / "__init__.py", target / "__main__.py"]
    else:
        required.append(target.with_suffix(".py"))
    if not all(p.is_file() for p in required):
        raise SentryError("módulo de entrada incompleto na cópia verificada ou pasta protegida; busca no pacote externo recusada")
    return required


def local_command(command, root, cwd=".", inspect_roots=None):
    """Normalize the entry to a local path and reject external launch code."""
    root = root.resolve()
    workdir = (root / cwd).resolve()
    if not (workdir == root or root in workdir.parents):
        raise SentryError("cwd escapa da pasta protegida")
    executable = Path(command[0])
    python = bool(re.fullmatch(r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?", executable.name.lower()))
    node = executable.name.lower() in {"node", "node.exe"}
    if not executable.is_absolute() or not executable.is_file() or not (python or node):
        raise SentryError("preparação genérica requer executável Python ou Node.js resolvido; use procedimento manual para outro runtime")
    args = list(command[1:])
    flags = []
    while python and args and args[0] in {"-B", "-u"}:
        flags.append(args.pop(0))
    if python and args[:1] == ["-m"] and len(args) >= 2:
        required = module_files(workdir, args[1])
        result = [str(executable), "-B", *[f for f in flags if f != "-B"], *args]
    else:
        if not args or Path(args[0]).suffix.lower() not in ({".py"} if python else {".js", ".mjs", ".cjs"}):
            raise SentryError("declare script .py, -m módulo ou entrada Node .js/.mjs/.cjs; opções de launcher exigem adaptação manual")
        entry = (workdir / args[0]).resolve()
        if not entry.is_file() or root not in entry.parents:
            raise SentryError("arquivo de entrada precisa existir dentro do código protegido")
        required = [entry]
        try:
            relative = entry.relative_to(workdir).as_posix()
        except ValueError:
            relative = os.path.relpath(entry, workdir)
        result = [str(executable), *flags, relative, *args[1:]]
    if inspect_roots is not None:
        selected = [(root / r).resolve() for r in inspect_roots]
        if any(not any(p == r or r in p.parents for r in selected) for p in required):
            raise SentryError("inspect_roots precisa cobrir o ponto de entrada e os arquivos do módulo")
    return result


def separated(root, store, data_roots):
    root, store = root.resolve(), store.resolve()
    for data in data_roots:
        data = data.resolve()
        if not data.is_dir():
            raise SentryError("pasta de dados declarada não existe")
        for other in (root, store):
            if data == other or other in data.parents or data in other.parents:
                raise SentryError("código, dados mutáveis e estado precisam de áreas separadas")


def main(argv=None):
    from .onboarding import prepare_codex
    parser = argparse.ArgumentParser(description="Preparar Python/Node local sem perfil de servidor")
    parser.add_argument("--name", required=True)
    parser.add_argument("--plan", type=Path, help="launch.json produzido por materialize")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--inspect-root", action="append", default=[])
    parser.add_argument("--cwd", dest="backend_cwd", default=".")
    parser.add_argument("--data-root", type=Path, action="append", default=[])
    parser.add_argument("--runtime-path", action="append", default=[], metavar="NAME=RELATIVE_PATH")
    parser.add_argument("--passthrough-name", action="append")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--fragment", type=Path, required=True)
    parser.add_argument("backend_command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        import json
        if args.plan:
            if args.project_root or args.backend_command:
                raise SentryError("use --plan ou projeto/comando explícitos, sem misturá-los")
            plan = json.loads(args.plan.read_text(encoding="utf-8"))
            args.project_root = Path(plan["project_root"])
            args.inspect_root = list(dict.fromkeys([*plan["inspect_roots"], *args.inspect_root]))
            args.backend_command = plan["command"]
            print(json.dumps({k: plan.get(k) for k in ("package", "version", "external_dependencies")}, ensure_ascii=False, indent=2))
        if not args.project_root or not args.inspect_root or not args.backend_command:
            raise SentryError("declare project-root, inspect-root e comando, ou use --plan")
        args.runtime_paths = dict(item.split("=", 1) for item in args.runtime_path)
        if len(args.runtime_paths) != len(args.runtime_path):
            raise SentryError("runtime-path duplicado")
        separated(args.project_root, args.store, args.data_root)
        print("Confira arquivos e configuração. DESCOBRIR autoriza uma inicialização para consultar tools/list:")
        if input() != "DESCOBRIR":
            return 0
        print(json.dumps(prepare_codex(args), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, EOFError) as exc:
        print(f"mcp-sentry: blocked: {exc}")
        return 2
