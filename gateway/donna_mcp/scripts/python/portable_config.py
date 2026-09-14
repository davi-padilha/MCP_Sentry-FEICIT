"""Gera e registra, de forma delimitada, a conexao Codex da Donna MCP."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile


PROFILE_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_profile(profile: str) -> str:
    if not PROFILE_RE.fullmatch(profile):
        raise ValueError(
            "Profile invalido. Use somente letras, numeros, '_' e '-'."
        )
    return profile


def server_name_for(profile: str) -> str:
    validate_profile(profile)
    return "donna_mcp" if profile == "default" else f"donna_mcp_{profile}"


def legacy_server_name_for(profile: str) -> str:
    validate_profile(profile)
    return "secretario_google" if profile == "default" else f"secretario_google_{profile}"


def _toml_string(value: str | Path) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def managed_markers(profile: str) -> tuple[str, str]:
    validate_profile(profile)
    tag = f"MCP-SENTRY DONNA-MCP profile={profile}"
    return f"# BEGIN {tag}", f"# END {tag}"


def legacy_managed_markers(profile: str) -> tuple[str, str]:
    validate_profile(profile)
    tag = f"MCP-SENTRY SECRETARIO-GOOGLE profile={profile}"
    return f"# BEGIN {tag}", f"# END {tag}"


def _environment(
    *,
    timezone_name: str,
    calendar_id: str,
    credentials: Path,
    token: Path,
    audit: Path,
    mutations: Path,
) -> dict[str, str]:
    return {
        "MCP_SECRETARY_MODE": "live-google",
        "MCP_SECRETARY_TIMEZONE": timezone_name,
        "MCP_SECRETARY_CALENDAR_ID": calendar_id,
        "MCP_SECRETARY_CREDENTIALS_FILE": str(credentials),
        "MCP_SECRETARY_TOKEN_FILE": str(token),
        "MCP_SECRETARY_AUDIT_FILE": str(audit),
        "MCP_SECRETARY_MUTATION_STORE_FILE": str(mutations),
    }


def render_codex_block(
    *,
    profile: str,
    python: Path,
    server: Path,
    cwd: Path,
    timezone_name: str,
    calendar_id: str,
    credentials: Path,
    token: Path,
    audit: Path,
    mutations: Path,
) -> str:
    name = server_name_for(profile)
    begin, end = managed_markers(profile)
    values = _environment(
        timezone_name=timezone_name,
        calendar_id=calendar_id,
        credentials=credentials,
        token=token,
        audit=audit,
        mutations=mutations,
    )
    lines = [
        begin,
        f"[mcp_servers.{name}]",
        f"command = {_toml_string(python)}",
        f"args = [{_toml_string(server)}]",
        f"cwd = {_toml_string(cwd)}",
        'enabled = true',
        'required = false',
        'startup_timeout_sec = 20',
        'tool_timeout_sec = 120',
        'default_tools_approval_mode = "writes"',
        "",
        f"[mcp_servers.{name}.env]",
    ]
    lines.extend(f"{key} = {_toml_string(value)}" for key, value in values.items())
    lines.extend([end, ""])
    return "\n".join(lines)


def render_client_manifest(
    *,
    profile: str,
    python: Path,
    server: Path,
    cwd: Path,
    timezone_name: str,
    calendar_id: str,
    credentials: Path,
    token: Path,
    audit: Path,
    mutations: Path,
) -> str:
    payload = {
        "name": server_name_for(profile),
        "transport": "stdio",
        "command": str(python),
        "args": [str(server)],
        "cwd": str(cwd),
        "env": _environment(
            timezone_name=timezone_name,
            calendar_id=calendar_id,
            credentials=credentials,
            token=token,
            audit=audit,
            mutations=mutations,
        ),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def merge_managed_block(content: str, *, profile: str, block: str) -> str:
    name = server_name_for(profile)
    marker_pairs = (managed_markers(profile), legacy_managed_markers(profile))
    ranges: list[tuple[int, int]] = []
    for begin, end in marker_pairs:
        if content.count(begin) > 1 or content.count(end) > 1:
            raise ValueError("Ha mais de um bloco gerenciado para este perfil.")
        begin_index = content.find(begin)
        end_index = content.find(end)
        if (begin_index == -1) != (end_index == -1):
            raise ValueError("Bloco gerenciado da Donna MCP esta incompleto no config.toml.")
        if begin_index != -1:
            if end_index < begin_index:
                raise ValueError("Marcadores da Donna MCP estao fora de ordem.")
            end_index += len(end)
            while end_index < len(content) and content[end_index] in "\r\n":
                end_index += 1
            ranges.append((begin_index, end_index))

    outside = content
    for begin_index, end_index in sorted(ranges, reverse=True):
        outside = outside[:begin_index] + outside[end_index:]

    table_pattern = re.compile(
        rf"(?m)^\s*\[mcp_servers\.{re.escape(name)}(?:\.[^\]]+)?\]\s*$"
    )
    if table_pattern.search(outside):
        raise ValueError(
            f"A conexao {name!r} ja existe fora do bloco gerenciado. "
            "Remova ou renomeie a entrada manual antes de registrar."
        )

    legacy_name = legacy_server_name_for(profile)
    legacy_table_pattern = re.compile(
        rf"(?m)^\s*\[mcp_servers\.{re.escape(legacy_name)}(?:\.[^\]]+)?\]\s*$"
    )
    if legacy_table_pattern.search(outside):
        raise ValueError(
            f"A conexao legada {legacy_name!r} existe fora do bloco gerenciado. "
            "Remova ou renomeie a entrada manual antes de registrar."
        )

    prefix = outside.rstrip()
    if prefix:
        return f"{prefix}\n\n{block}"
    return block


def write_atomic_with_backup(path: Path, content: str) -> Path | None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    if previous == content:
        return None

    backup = None
    if path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = path.with_name(f"{path.name}.donna-mcp.{stamp}.bak")
        backup.write_text(previous, encoding="utf-8")

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
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return backup


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("render", "render-client", "register", "check")
    )
    parser.add_argument("--profile", default="default")
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    parser.add_argument("--calendar-id", default="primary")
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--token", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--mutations", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--config", type=Path)
    return parser


def main() -> None:
    args = _parser().parse_args()
    block = render_codex_block(
        profile=args.profile,
        python=args.python.resolve(),
        server=args.server.resolve(),
        cwd=args.cwd.resolve(),
        timezone_name=args.timezone,
        calendar_id=args.calendar_id,
        credentials=args.credentials.resolve(),
        token=args.token.resolve(),
        audit=args.audit.resolve(),
        mutations=args.mutations.resolve(),
    )

    if args.command == "render-client":
        if not args.output:
            raise SystemExit("--output e obrigatorio para render-client")
        manifest = render_client_manifest(
            profile=args.profile,
            python=args.python.resolve(),
            server=args.server.resolve(),
            cwd=args.cwd.resolve(),
            timezone_name=args.timezone,
            calendar_id=args.calendar_id,
            credentials=args.credentials.resolve(),
            token=args.token.resolve(),
            audit=args.audit.resolve(),
            mutations=args.mutations.resolve(),
        )
        write_atomic_with_backup(args.output, manifest)
        print(json.dumps({"status": "ok", "output": str(args.output.resolve())}))
        return

    if args.command == "render":
        if not args.output:
            raise SystemExit("--output e obrigatorio para render")
        write_atomic_with_backup(args.output, block)
        print(json.dumps({"status": "ok", "output": str(args.output.resolve())}))
        return

    if not args.config:
        raise SystemExit("--config e obrigatorio para register/check")
    config = args.config.expanduser().resolve()
    current = config.read_text(encoding="utf-8") if config.exists() else ""
    if args.command == "check":
        begin, end = managed_markers(args.profile)
        print(
            json.dumps(
                {
                    "status": "ok",
                    "config": str(config),
                    "registered": begin in current and end in current,
                    "server_name": server_name_for(args.profile),
                }
            )
        )
        return

    merged = merge_managed_block(current, profile=args.profile, block=block)
    backup = write_atomic_with_backup(config, merged)
    print(
        json.dumps(
            {
                "status": "ok",
                "config": str(config),
                "server_name": server_name_for(args.profile),
                "backup": str(backup) if backup else None,
            }
        )
    )


if __name__ == "__main__":
    main()
