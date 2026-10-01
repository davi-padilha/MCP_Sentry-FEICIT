"""Local-only building blocks for the T7 preparation preflight.

This module never authenticates, starts an MCP server, or contacts Google.  It
only renders a private Sentry-only Codex block and validates the declared OAuth
scope names without exposing a token value.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import Path
import sys
import tomllib

from .core import SentryError

SENTRY_ENTRY_NAME = "Donna_via_Sentry"
CODEX_PLATFORM_MCP_ENTRY_NAME = "node_repl"
GOOGLE_SCOPES = frozenset((
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
))
CAPABILITIES_REQUIRED_BLOCKED = (
    "shell", "terminal", "automated_browser", "external_file_write",
    "direct_network", "other_mcp",
)
PREFLIGHT_PROFILES = ("interoperability", "isolation")


def _absolute(value: str | Path, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise SentryError(f"{label} deve ser absoluto")
    return path


def _toml(value: str | Path) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def render_sentry_only_codex_block(*, python: str | Path, manifest: str | Path,
                                   store: str | Path, credentials: str | Path,
                                   token: str | Path, audit: str | Path,
                                   mutations: str | Path,
                                   timezone: str = "America/Sao_Paulo",
                                   calendar_id: str = "primary") -> str:
    """Render a private, single-entry Codex fragment for preparation only."""
    values = {
        "python": _absolute(python, "python"),
        "manifest": _absolute(manifest, "manifest"),
        "store": _absolute(store, "store"),
        "credentials": _absolute(credentials, "credentials"),
        "token": _absolute(token, "token"),
        "audit": _absolute(audit, "audit"),
        "mutations": _absolute(mutations, "mutations"),
    }
    if not isinstance(timezone, str) or not timezone or not isinstance(calendar_id, str) or not calendar_id:
        raise SentryError("timezone e calendar_id devem ser textos não vazios")
    lines = [
        "# PRIVATE T7 preparation fragment; do not commit or publish paths.",
        f"[mcp_servers.{SENTRY_ENTRY_NAME}]",
        f"command = {_toml(values['python'])}",
        'args = ["-m", "mcp_sentry_gateway.gateway", "--manifest", '
        f"{_toml(values['manifest'])}, \"--store\", {_toml(values['store'])}]",
        "enabled = true",
        "required = false",
        "startup_timeout_sec = 20",
        "tool_timeout_sec = 120",
        'default_tools_approval_mode = "writes"',
        "",
        f"[mcp_servers.{SENTRY_ENTRY_NAME}.env]",
        'MCP_SECRETARY_MODE = "live-google"',
        f"MCP_SECRETARY_TIMEZONE = {_toml(timezone)}",
        f"MCP_SECRETARY_CALENDAR_ID = {_toml(calendar_id)}",
        f"MCP_SECRETARY_CREDENTIALS_FILE = {_toml(values['credentials'])}",
        f"MCP_SECRETARY_TOKEN_FILE = {_toml(values['token'])}",
        f"MCP_SECRETARY_AUDIT_FILE = {_toml(values['audit'])}",
        f"MCP_SECRETARY_MUTATION_STORE_FILE = {_toml(values['mutations'])}",
        "",
    ]
    return "\n".join(lines)


def codex_platform_mcp_fingerprint(entry: object) -> str:
    """Return a stable digest for an externally captured platform entry."""
    try:
        serialized = json.dumps(entry, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise SentryError("entrada MCP de plataforma não serializável") from exc
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def read_codex_platform_mcp_contract(contract_path: str | Path) -> str:
    """Read the private, value-free fingerprint captured outside config.toml."""
    path = _absolute(contract_path, "contrato MCP de plataforma")
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SentryError("contrato MCP de plataforma inválido") from exc
    if not isinstance(contract, dict) or set(contract) != {"schema_version", "entry_sha256"} \
            or contract["schema_version"] != 1:
        raise SentryError("schema do contrato MCP de plataforma inválido")
    digest = contract["entry_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 \
            or any(character not in "0123456789abcdef" for character in digest):
        raise SentryError("fingerprint MCP de plataforma inválido")
    return digest


def validate_applied_sentry_only_config(config_path: str | Path, *,
                                        allow_codex_platform_mcp: bool = False,
                                        codex_platform_mcp_sha256: str | None = None,
                                        **expected) -> None:
    """Fail closed unless the Sentry route is the only backend route.

    The caller supplies the same private values used to render the fragment.
    They are compared only in memory and never returned or persisted.  The
    interoperability profile can additionally inventory the platform-injected
    ``node_repl`` entry only when it exactly matches a separately captured,
    private fingerprint. Every other parallel MCP remains a bypass.
    """
    path = _absolute(config_path, "configuração")
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise SentryError("configuração Codex efetiva inválida") from exc
    expected_config = tomllib.loads(render_sentry_only_codex_block(**expected))
    actual_servers = config.get("mcp_servers") if isinstance(config, dict) else None
    expected_servers = expected_config["mcp_servers"]
    allowed_entries = {SENTRY_ENTRY_NAME}
    if allow_codex_platform_mcp:
        allowed_entries.add(CODEX_PLATFORM_MCP_ENTRY_NAME)
    if not isinstance(actual_servers, dict) or not {SENTRY_ENTRY_NAME}.issubset(actual_servers) \
            or not set(actual_servers).issubset(allowed_entries):
        raise SentryError("bypass detectado: a configuração efetiva expõe MCP não aprovado")
    if actual_servers[SENTRY_ENTRY_NAME] != expected_servers[SENTRY_ENTRY_NAME]:
        raise SentryError("configuração efetiva diverge da entrada Sentry aprovada")
    if CODEX_PLATFORM_MCP_ENTRY_NAME in actual_servers and (
            not allow_codex_platform_mcp or
            not isinstance(codex_platform_mcp_sha256, str) or
            not hmac.compare_digest(
                codex_platform_mcp_fingerprint(actual_servers[CODEX_PLATFORM_MCP_ENTRY_NAME]),
                codex_platform_mcp_sha256,
            )):
        raise SentryError("entrada MCP de plataforma inválida ou não autorizada")


def validate_capability_report(report_path: str | Path, *, require_isolation: bool = False) -> dict[str, object]:
    """Validate a complete capability record; isolation is an explicit profile."""
    path = _absolute(report_path, "relatório de capacidades")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SentryError("relatório de capacidades inválido") from exc
    required = {"schema_version", "capabilities", "negative_probes"}
    if not isinstance(report, dict) or set(report) != required or report["schema_version"] != 1:
        raise SentryError("schema do relatório de capacidades inválido")
    capabilities, probes = report["capabilities"], report["negative_probes"]
    names = set(CAPABILITIES_REQUIRED_BLOCKED)
    if not isinstance(capabilities, dict) or not isinstance(probes, dict) or set(capabilities) != names or set(probes) != names:
        raise SentryError("relatório de capacidades incompleto")
    if any(type(capabilities[name]) is not bool for name in names):
        raise SentryError("relatório de capacidades inválido")
    if any(probes[name] not in {"blocked", "available", "not_probed"} for name in names):
        raise SentryError("sonda negativa inválida")
    if any(not capabilities[name] and probes[name] != "blocked" for name in names):
        raise SentryError("capacidade ausente exige sonda bloqueada")
    if any(capabilities[name] and probes[name] == "blocked" for name in names):
        raise SentryError("capacidade disponível não pode ter sonda bloqueada")
    isolated = all(capabilities[name] is False and probes[name] == "blocked" for name in names)
    if require_isolation and not isolated:
        raise SentryError("capacidade paralela disponível ou sonda negativa não bloqueada")
    return {"isolated": isolated, "capabilities": capabilities, "negative_probes": probes}


def validate_exact_google_scopes(token_path: str | Path) -> list[str]:
    """Validate only scope names in a local token file; never return token data."""
    path = _absolute(token_path, "token")
    try:
        token = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SentryError("token local inválido para validação de escopos") from exc
    scopes = token.get("scopes") if isinstance(token, dict) else None
    if isinstance(scopes, str):
        scopes = scopes.split()
    if not isinstance(scopes, list) or not all(isinstance(scope, str) for scope in scopes):
        raise SentryError("token não declara uma lista válida de escopos")
    observed = frozenset(scopes)
    if observed != GOOGLE_SCOPES or len(scopes) != len(observed):
        raise SentryError("escopos OAuth não correspondem exatamente à allowlist T7")
    return sorted(observed)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validador local e sanitizado do preflight T7")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--credentials", required=True, type=Path)
    parser.add_argument("--token", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--mutations", required=True, type=Path)
    parser.add_argument("--capability-report", required=True, type=Path)
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    parser.add_argument("--calendar-id", default="primary")
    parser.add_argument("--codex-platform-mcp-contract", type=Path)
    parser.add_argument("--profile", choices=PREFLIGHT_PROFILES, default="interoperability")
    args = parser.parse_args()
    expected = {
        "python": args.python, "manifest": args.manifest, "store": args.store,
        "credentials": args.credentials, "token": args.token, "audit": args.audit,
        "mutations": args.mutations, "timezone": args.timezone, "calendar_id": args.calendar_id,
    }
    try:
        platform_contract = (
            read_codex_platform_mcp_contract(args.codex_platform_mcp_contract)
            if args.codex_platform_mcp_contract is not None else None
        )
        validate_applied_sentry_only_config(
            args.config, allow_codex_platform_mcp=args.profile == "interoperability",
            codex_platform_mcp_sha256=platform_contract, **expected,
        )
        capability_record = validate_capability_report(
            args.capability_report, require_isolation=args.profile == "isolation"
        )
        scopes = validate_exact_google_scopes(args.token)
    except SentryError as exc:
        print(f"t7-preflight: blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "local_preflight_checks_ok", "profile": args.profile,
        "oauth_scopes": scopes,
        "capability_isolation": "verified" if capability_record["isolated"] else "not_verified",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
