"""Convert a pinned npx/uvx launch to a local installation, never a runtime fetch."""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .core import SentryError, safe_text, write
from .onboarding import _command
from .preparation import local_command


def launcher_spec(parts, version=None):
    parts = list(parts)
    if parts[:1] == ["--"]: parts.pop(0)
    if not parts: raise SentryError("informe npx ou uvx após --")
    launcher = Path(parts.pop(0)).stem.lower()
    if launcher == "cmd" and parts and parts[0].lower() == "/c" and len(parts) >= 2 and Path(parts[1]).stem.lower() == "npx":
        parts.pop(0); parts.pop(0); launcher = "npx"
    if launcher == "npx":
        while parts and parts[0] in {"-y", "--yes"}: parts.pop(0)
        binary = None
        if parts and parts[0] in {"--package", "-p"}:
            parts.pop(0)
            if len(parts) < 2: raise SentryError("--package requer pacote e nome do binário")
            package, binary = parts.pop(0), parts.pop(0)
        elif parts and parts[0].startswith("--package="):
            package = parts.pop(0).split("=", 1)[1]
            if not parts: raise SentryError("informe o binário após --package")
            binary = parts.pop(0)
        elif parts: package = parts.pop(0)
        else: raise SentryError("informe pacote npm com versão exata")
        if version and re.fullmatch(r"(?:@[a-z0-9._-]+/)?[a-z0-9._-]+", package): package += "@" + version
        match = re.fullmatch(r"((?:@[a-z0-9._-]+/)?[a-z0-9._-]+)@(\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?(?:\+[A-Za-z0-9.-]+)?)", package)
        kind = "node"
    elif launcher == "uvx":
        if parts[:1] == ["--from"]:
            if len(parts) < 3: raise SentryError("--from requer pacote==versão e comando")
            parts.pop(0); package, binary = parts.pop(0), parts.pop(0)
        elif parts and parts[0].startswith("--from="):
            package = parts.pop(0).split("=", 1)[1]
            if not parts: raise SentryError("informe o comando após --from")
            binary = parts.pop(0)
        elif parts:
            package = parts.pop(0); binary = re.split(r"==|@", package, 1)[0]
        else: raise SentryError("informe pacote Python com versão exata")
        if version and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", package): package += "==" + version
        match = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9._-]*)(?:==|@)(\d+(?:\.\d+)*(?:(?:a|b|rc)\d+|\.post\d+|\.dev\d+)?)", package)
        kind = "python"
    else:
        raise SentryError("conversão automática disponível para npx e uvx; use prepare-server para código local")
    if not match:
        raise SentryError("versão exata obrigatória; tags, ranges, URLs, extras e opções avançadas exigem preparação manual")
    if version and match[2] != version:
        raise SentryError("--version diverge da versão fixada no launcher")
    if binary is not None and not re.fullmatch(r"[A-Za-z0-9._-]+", binary):
        raise SentryError("nome de comando inválido")
    return {"kind": kind, "package": match[1], "version": match[2], "binary": binary, "args": parts}


def run_checked(command):
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if result.returncode:
        raise SentryError("instalação/consulta falhou: " + safe_text(result.stderr[-4000:].encode("utf-8")))
    return result.stdout


PYTHON_DISTRIBUTION_INFO = '''import importlib.metadata as m, json, sys
d=m.distribution(sys.argv[1])
files=list(d.files or [])
roots=sorted({str(f).replace(chr(92),'/').split('/')[0] for f in files if '..' not in f.parts})
ep=[{'name':e.name,'value':e.value} for e in d.entry_points if e.group=='console_scripts']
print(json.dumps({'name':d.metadata['Name'],'version':d.version,'root':str(d.locate_file('')),'roots':roots,'entry_points':ep}))
'''


def materialize(spec, install_root, runtime):
    install_root = install_root.resolve()
    runtime = _command([str(runtime)], install_root)[0]
    if install_root.exists():
        raise SentryError("install-root já existe; use uma pasta nova, sem substituir o código ou estado aprovado")
    install_root.mkdir(parents=True)
    if spec["kind"] == "node":
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm: raise SentryError("npm não encontrado; instale manualmente e use prepare-server")
        run_checked([npm, "install", "--prefix", str(install_root), "--save-exact", "--ignore-scripts", "--no-audit", "--no-fund",
                     "--fetch-timeout=20000", "--fetch-retries=0", "--cache", str(install_root/".cache"),
                     f"{spec['package']}@{spec['version']}"])
        package = install_root / "node_modules" / spec["package"]
        metadata = json.loads((package/"package.json").read_text(encoding="utf-8"))
        if metadata.get("name") != spec["package"] or metadata.get("version") != spec["version"]:
            raise SentryError("identidade/versão instalada difere da solicitada")
        bins = metadata.get("bin", {})
        if isinstance(bins, str): bins = {spec["package"].split("/")[-1]: bins}
        if not isinstance(bins, dict) or not bins: raise SentryError("pacote sem bin Node; declare entrada manualmente")
        binary = spec["binary"]
        if binary is None:
            if len(set(bins.values())) == 1: binary = next(iter(bins))
            elif spec["package"].split("/")[-1] in bins: binary = spec["package"].split("/")[-1]
            else: raise SentryError("pacote com múltiplos bins; use npx --package pacote@versão binário")
        if binary not in bins: raise SentryError("binário não declarado pelo pacote")
        entry = (package / bins[binary]).resolve()
        if package not in entry.parents: raise SentryError("bin escapa do pacote instalado")
        root = install_root
        roots = ["node_modules", "package.json", "package-lock.json"]
        command = local_command([runtime, str(entry), *spec["args"]], root, inspect_roots=roots)
        external_dependencies = ["Node.js", "sistema operacional"]
    else:
        environment = install_root / "env"
        run_checked([runtime, "-m", "venv", str(environment)])
        python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        run_checked([str(python), "-m", "pip", "install", "--only-binary=:all:", "--disable-pip-version-check",
                     "--retries", "0", "--timeout", "20", "--cache-dir", str(install_root/".cache"),
                     f"{spec['package']}=={spec['version']}"])
        info = json.loads(run_checked([str(python), "-I", "-c", PYTHON_DISTRIBUTION_INFO, spec["package"]]))
        normalized = lambda value: re.sub(r"[-_.]+", "-", value).lower()
        if normalized(info["name"]) != normalized(spec["package"]) or info["version"] != spec["version"]:
            raise SentryError("identidade/versão Python instalada difere da solicitada")
        entries = [ep for ep in info["entry_points"] if ep["name"] == spec["binary"]]
        if len(entries) != 1: raise SentryError("console_script não encontrado; use --from com o comando correto ou prepare-server")
        value = entries[0]["value"]
        if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", value):
            raise SentryError("entry point Python fora do formato módulo:função; adapte manualmente")
        module, function = value.split(":")
        root = Path(info["root"])
        roots = [r for r in info["roots"] if (root/r).exists() and r not in {"__pycache__", ".git"}]
        wrapper = root / "_sentry_entry.py"
        wrapper.write_text(
            "import importlib, pathlib, sys\n"
            "root = pathlib.Path(__file__).resolve().parent\n"
            f"parts = {module.split('.')!r}\n"
            "target = root.joinpath(*parts)\n"
            "parents = [root.joinpath(*parts[:i]) for i in range(1, len(parts))]\n"
            "entry = target.with_suffix('.py')\n"
            "if target.is_dir():\n    parents.append(target)\n    entry = target / '__init__.py'\n"
            "if not entry.is_file() or any(not (p/'__init__.py').is_file() for p in parents):\n"
            "    raise SystemExit('entry point absent from verified copy')\n"
            f"function = importlib.import_module({module!r})\n"
            f"for name in {function.split('.')!r}: function = getattr(function, name)\n"
            "sys.exit(function())\n", encoding="utf-8")
        roots.append(wrapper.name)
        command = local_command([str(python), "-B", wrapper.name, *spec["args"]], root, inspect_roots=roots)
        freeze = run_checked([str(python), "-m", "pip", "freeze"])
        (install_root/"dependencies.txt").write_text(freeze, encoding="utf-8")
        external_dependencies = ["Python", "demais distribuições do ambiente: dependencies.txt", "sistema operacional e subprocessos declarados pelo operador"]
    plan = {"project_root": str(root), "inspect_roots": roots, "command": command,
            "package": spec["package"], "version": spec["version"], "external_dependencies": external_dependencies}
    write(install_root/"launch.json", plan)
    return {"status": "installed_not_approved", "plan": str(install_root/"launch.json"), **plan}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Materializar npx/uvx fixado sem executar o servidor")
    parser.add_argument("--install-root", type=Path, required=True)
    parser.add_argument("--runtime", required=True, help="Node para npx; Python para uvx")
    parser.add_argument("--version", help="versão exata para um launcher sem versão")
    parser.add_argument("launcher", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        spec = launcher_spec(args.launcher, args.version)
        print(json.dumps(spec, ensure_ascii=False, indent=2))
        print("INSTALAR autoriza obter o pacote e dependências nesta pasta nova. O servidor não será iniciado:")
        if input() != "INSTALAR": return 0
        print(json.dumps(materialize(spec, args.install_root, args.runtime), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, EOFError, subprocess.SubprocessError) as exc:
        print(f"mcp-sentry: blocked: {exc}")
        return 2
