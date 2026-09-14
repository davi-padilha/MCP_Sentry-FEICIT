#!/usr/bin/env python3
"""Runner fail-closed da campanha aditiva multimodelo M2.3.

Reutiliza, sem alterá-los, o construtor de envelope (`offline.build_request`) e
o transporte e os validadores da verificação real anterior à execução. A
classificação das tentativas segue o runner da campanha original
(`tools/m2_3_runner_v2/runner.py`): resposta recebida é terminal para a unidade,
válida ou não; falha de transporte recuperável repete até A3; e divergência de
identidade efetiva, depois de persistida, interrompe a campanha
(`_raise_if_identity_divergence`, linhas 136 a 142 do original).
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import subprocess
import time
import urllib.error
from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Mapping

from . import offline, verificacao_antes_da_execucao as preflight_runner


REPO = offline.REPO
CANDIDATE = offline.PACKAGE
READY = REPO / "baterias_finais/m2_3_extensao_multimodelo_v1_ready"
MANIFEST = READY / "manifesto_ready_v1.json"
SOURCE_SET = READY / "source_set_v1.json"
IDENTITIES = READY / "config/identidades_efetivas_v1.json"
ANALYSIS_CONTRACT = READY / "contrato_analitico_v1.json"
AUTHORIZATION_SCHEMA = READY / "schemas/autorizacao_campanha_extensao_v1.json"
RECORD_SCHEMAS = READY / "schemas/registros_campanha_extensao_v1.json"
CONFIG = CANDIDATE / "config/modelos_posicoes_extensao_v1.json"
AGENDA = CANDIDATE / "agenda/agenda_extensao_v1.json"

SNAPSHOT_ID = "m2_3_extensao_multimodelo_v1_ready"
READY_STATUS = "READY_OFFLINE_CAMPAIGN_NOT_AUTHORIZED"
AUTH_STATEMENT = (
    "Autorizo a campanha real da extensão multimodelo M2.3, em uma lane sequencial, "
    "com as três posições fixadas e sob o teto externo declarado de até US$ 14."
)
POSITIONS = [
    "remote-gpt-5-6-luna-high-openai",
    "remote-gpt-5-6-sol-medium-openai",
    "remote-claude-opus-5-medium-anthropic",
]
EXECUTABLE_SOURCES = frozenset(
    f"tools/m2_3_extensao_multimodelo_v1/{name}"
    for name in ("__init__.py", "offline.py", "verificacao_antes_da_execucao.py", "campaign.py", "verify_campaign.py", "campaign_visible.ps1")
)

FILES = {
    "intent": "intencoes.jsonl",
    "attempt": "tentativas.jsonl",
    "checkpoint": "checkpoints.jsonl",
    "result": "resultados.jsonl",
    "closure": "fechamento.jsonl",
}
EXECUTION_MANIFEST = "manifesto_execucao.json"
LOCK = "campaign.lock"

COMPLETE = "COMPLETE_PENDING_INDEPENDENT_REVIEW"
ABORTED = "ABORTED"
VALID = "valid_semantic_response"
SEMANTIC_FAILURE = "terminal_structural_or_semantic_failure"
RETRYABLE = "retryable_transport_failure"
TRANSPORT_FAILURE = "terminal_transport_failure"
COST_VIOLATION = "aborted_cost_violation"
TERMINAL = frozenset({VALID, SEMANTIC_FAILURE, TRANSPORT_FAILURE})

MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = {1: 10, 2: 30}
RETRYABLE_KINDS = frozenset({"connection", "timeout", "connection_interrupted"})
RETRYABLE_HTTP = frozenset({408, 429, *range(500, 600)})
# Credencial, crédito ou permissão recusados são falhas sistêmicas: a tentativa
# fica terminal, como no runner original, mas a campanha para em vez de repetir
# o mesmo erro nas unidades seguintes.
SYSTEMIC_HTTP = frozenset({401, 402, 403})
# Marca herdada do runner original: identidade efetiva divergente é persistida
# como falha terminal da unidade e, logo depois do checkpoint, interrompe a
# campanha. A retomada fica bloqueada até decisão humana.
IDENTITY_FAILURE_PREFIX = "identity_effective_failure:"


class GateError(RuntimeError):
    pass


def _reject_constant(value: str) -> Any:
    raise ValueError(f"constante JSON não permitida: {value}")


def loads(text: str) -> Any:
    return json.loads(text, parse_float=Decimal, parse_constant=_reject_constant)


def load(path: Path) -> Any:
    return loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def money(value: Decimal) -> str:
    return format(value, "f")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def request_sha256(payload: Mapping[str, Any]) -> str:
    """Mesma serialização do dry-run offline (`offline.dry_run`)."""
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def planned_ceiling(position: Mapping[str, Any], payload: Mapping[str, Any]) -> Decimal:
    """Reserva máxima por tentativa, com a mesma fórmula do preflight real."""
    prices = position["provider_max_price_usd_per_million"]
    params = position["requested_parameters"]
    maximum_tokens = params.get("max_output_tokens", params.get("max_tokens"))
    prompt_bound = Decimal(len(json.dumps(payload, ensure_ascii=False).encode("utf-8")))
    return (
        Decimal(str(prices["prompt"])) * preflight_runner._cache_write_multiplier(position) * prompt_bound / Decimal(1_000_000)
        + Decimal(str(prices["completion"])) * Decimal(maximum_tokens) / Decimal(1_000_000)
        + Decimal(str(prices.get("request", 0)))
    )


def read_jsonl(path: Path) -> list[Any]:
    if not path.exists():
        return []
    data = path.read_bytes()
    if not data:
        return []
    if not data.endswith(b"\n"):
        raise GateError(f"última linha truncada: {path.name}")
    return [loads(line) for line in data.decode("utf-8").split("\n")[:-1]]


def append(path: Path, value: Mapping[str, Any]) -> None:
    line = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    with path.open("ab") as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())


_TYPES = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool, "null": type(None)}


def _type_ok(kind: str, value: Any) -> bool:
    if kind == "number":
        return type(value) in (int, Decimal)
    return type(value) is _TYPES[kind]


def identical(left: Any, right: Any) -> bool:
    """Igualdade material com tipo exato: recusa lavagem `true↔1` e `25↔25.0`."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(identical(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(identical(a, b) for a, b in zip(left, right))
    return left == right


def _strict(schema: Mapping[str, Any], value: Any, label: str) -> None:
    if "const" in schema and not identical(value, schema["const"]):
        raise GateError(f"{label}: const divergente")
    if "enum" in schema and not any(identical(value, option) for option in schema["enum"]):
        raise GateError(f"{label}: enum divergente")
    kinds = schema.get("type")
    kinds = [kinds] if isinstance(kinds, str) else kinds
    if kinds and not any(_type_ok(kind, value) for kind in kinds):
        raise GateError(f"{label}: tipo divergente")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if not set(schema.get("required", [])) <= set(value):
            raise GateError(f"{label}: campo obrigatório ausente")
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            raise GateError(f"{label}: campo extra")
        for key, child in value.items():
            if key in properties:
                _strict(properties[key], child, f"{label}.{key}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise GateError(f"{label}: string curta demais")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            raise GateError(f"{label}: string fora do padrão")
    if type(value) in (int, Decimal):
        if (
            ("minimum" in schema and value < schema["minimum"])
            or ("exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"])
            or ("maximum" in schema and value > schema["maximum"])
        ):
            raise GateError(f"{label}: número fora do limite")


@lru_cache(maxsize=None)
def _record_schemas() -> Mapping[str, Any]:
    return load(RECORD_SCHEMAS)["$defs"]


def validate_role(role: str, value: Mapping[str, Any]) -> None:
    _strict(_record_schemas()[role], value, role)


def validate_ready() -> dict[str, Any]:
    """Confere manifesto ready, pins e source-set antes de qualquer outra coisa."""
    manifest = load(MANIFEST)
    if (
        manifest.get("schema_version") != "m2_3_extension_ready_manifest_v1"
        or manifest.get("package_id") != SNAPSHOT_ID
        or manifest.get("status") != READY_STATUS
    ):
        raise GateError("manifesto ready inválido")
    if not identical(manifest.get("gates"), {"campaign_authorized": False, "credential_access_allowed": False, "network_allowed": False}):
        raise GateError("ready abriu portão")
    pins: dict[str, str] = {}
    for item in manifest["pinned_artifacts"]:
        if item["path"] in pins:
            raise GateError(f"pin duplicado: {item['path']}")
        pins[item["path"]] = item["sha256"]
    repo = REPO.resolve()
    for path, digest in pins.items():
        target = (REPO / path).resolve()
        if not target.is_relative_to(repo) or not target.is_file() or sha(target) != digest:
            raise GateError(f"pin divergente: {path}")
    source_set = load(SOURCE_SET)
    declared = {item["path"]: item["sha256"] for item in source_set["executable_sources"]}
    if (
        source_set.get("schema_version") != "m2_3_extension_source_set_v1"
        or len(declared) != len(source_set["executable_sources"])
        or set(declared) != EXECUTABLE_SOURCES
    ):
        raise GateError("source-set não cobre exatamente o código executado")
    required = {
        *declared, rel(SOURCE_SET), rel(IDENTITIES), rel(ANALYSIS_CONTRACT), rel(AUTHORIZATION_SCHEMA), rel(RECORD_SCHEMAS),
        rel(CANDIDATE / "manifesto_extensao_v1.json"), rel(CONFIG), rel(AGENDA), rel(offline.PROMPT), rel(offline.RESPONSE_SCHEMA),
    }
    if not required <= set(pins) or any(declared[path] != pins[path] for path in declared):
        raise GateError("pin obrigatório ausente ou divergente do source-set")
    offline.validate()
    return manifest


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False)


def _git_gate(authorization: Mapping[str, Any], pinned_paths: list[str]) -> None:
    head = _git("rev-parse", "HEAD").stdout.strip()
    upstream = _git("rev-parse", "origin/main").stdout.strip()
    if not head or head != upstream or head != authorization["approved_commit"]:
        raise GateError("HEAD, origin/main e approved_commit divergem")
    status = _git("status", "--porcelain=v1", "--untracked-files=all")
    if status.returncode != 0 or status.stdout.strip():
        raise GateError("árvore ou índice não estão limpos")
    if _git("ls-files", "--error-unmatch", "--", rel(MANIFEST), *pinned_paths).returncode != 0:
        raise GateError("manifesto ready ou pin não rastreado")


def validate_authorization(authorization_path: Path, output_root: Path, real: bool) -> tuple[dict[str, Any], str]:
    if not authorization_path.is_absolute() or not output_root.is_absolute():
        raise GateError("autorização e saída devem ser caminhos absolutos")
    repo = REPO.resolve()
    authorization_file = authorization_path.resolve()
    output = output_root.resolve()
    if authorization_file.is_relative_to(repo) or output.is_relative_to(repo):
        raise GateError("autorização e saída devem ficar fora do repositório")
    if authorization_file.is_relative_to(output):
        raise GateError("autorização não pode ficar dentro da saída")
    raw = authorization_file.read_bytes()
    authorization = loads(raw.decode("utf-8"))
    _strict(load(AUTHORIZATION_SCHEMA), authorization, "authorization")
    if authorization["snapshot_sha256"] != sha(MANIFEST):
        raise GateError("autorização não fixa o manifesto ready atual")
    if real:
        base = os.environ.get("LOCALAPPDATA")
        canonical = (Path(base) / "MCP-Sentry" / "m2_3_extension_campaign" / authorization["run_id"]).resolve() if base else None
        if output != canonical:
            raise GateError("saída real deve ser o diretório canônico derivado do run_id")
        _git_gate(authorization, [item["path"] for item in load(MANIFEST)["pinned_artifacts"]])
    return authorization, hashlib.sha256(raw).hexdigest()


def _transport(sender: Callable, position: Mapping[str, Any], payload: Mapping[str, Any]) -> tuple[str, int | None, Any, str | None, str | None]:
    """Envia e classifica o tipo de desfecho, sem decidir retry."""
    try:
        body, status, raw = sender(position, payload)
        return "response", status, body, raw, None
    except preflight_runner.RemoteResponseError as exc:
        if exc.status is not None and 200 <= exc.status < 300:
            return "response", exc.status, None, exc.raw_response, str(exc)
        return "http", exc.status, None, exc.raw_response, str(exc)
    except preflight_runner.GateError as exc:
        cause = exc.__cause__
        reason = getattr(cause, "reason", None)
        if isinstance(cause, TimeoutError) or isinstance(reason, TimeoutError):
            return "timeout", None, None, None, str(exc)
        if isinstance(cause, urllib.error.URLError):
            return "connection", None, None, None, str(exc)
        raise
    except TimeoutError as exc:
        return "timeout", None, None, None, f"{type(exc).__name__}: {exc}"
    except (ConnectionError, http.client.HTTPException) as exc:
        return "connection_interrupted", None, None, None, f"{type(exc).__name__}: {exc}"


def _observed_cost(position: Mapping[str, Any], body: Any) -> Decimal | None:
    usage = body.get("usage") if isinstance(body, Mapping) else None
    if not isinstance(usage, Mapping) or usage.get("cost") is None:
        return None
    return preflight_runner._observed_cost_within_ceiling(position, body)


def _route_identity(body: Any) -> tuple[str | None, str | None]:
    """Provedor e revisão da rota efetiva, quando a resposta os prova sem ambiguidade."""
    metadata = body.get("openrouter_metadata") if isinstance(body, Mapping) else None
    endpoints = metadata.get("endpoints") if isinstance(metadata, Mapping) else None
    available = endpoints.get("available") if isinstance(endpoints, Mapping) else None
    selected = [item for item in available or [] if isinstance(item, Mapping) and item.get("selected") is True]
    if len(selected) != 1:
        return None, None
    return selected[0].get("provider"), selected[0].get("model") or body.get("model")


def evaluate(position: Mapping[str, Any], identity: Mapping[str, Any], body: Any) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Resposta recebida: devolve classificação, ação, provedor, revisão e erro.

    Serve também ao consumidor, que reprocessa a resposta bruta preservada. A
    identidade é conferida antes da extração de conteúdo: fallback de provedor e
    revisão inesperada são divergência de identidade, não falha estrutural.
    """
    provider, revision = _route_identity(body)
    if provider is not None and (provider != identity["effective_provider"] or revision != identity["effective_revision"]):
        return SEMANTIC_FAILURE, None, provider, revision, IDENTITY_FAILURE_PREFIX + " identidade efetiva diverge da aprovada no preflight"
    try:
        content, selected = preflight_runner._content_and_route(position, body)
    except preflight_runner.GateError as exc:
        return SEMANTIC_FAILURE, None, provider, revision, f"rota/identidade: {exc}"
    provider = selected.get("provider")
    revision = selected.get("model") or body.get("model")
    if provider != identity["effective_provider"] or revision != identity["effective_revision"]:
        return SEMANTIC_FAILURE, None, provider, revision, IDENTITY_FAILURE_PREFIX + " identidade efetiva diverge da aprovada no preflight"
    try:
        preflight_runner._validate_semantic_schema(content)
    except preflight_runner.GateError as exc:
        return SEMANTIC_FAILURE, None, provider, revision, str(exc)
    return VALID, json.loads(content)["acao"], provider, revision, None


class Campaign:
    def __init__(self, authorization: Mapping[str, Any], authorization_sha: str, output: Path, sender: Callable, sleeper: Callable[[float], None]) -> None:
        self.authorization = authorization
        self.authorization_sha = authorization_sha
        self.output = output
        self.sender = sender
        self.sleeper = sleeper
        self.snapshot_sha = sha(MANIFEST)
        self.cap = Decimal(str(authorization["external_budget_cap_usd"]))
        # O envelope HTTP precisa de números JSON serializáveis; Decimal fica só
        # na contabilidade (mesma separação corrigida no preflight em 3a38579).
        self.positions = {item["position_id"]: item for item in offline.load(CONFIG)["positions"]}
        self.identities = {item["position_id"]: item for item in load(IDENTITIES)["positions"]}
        if list(self.positions) != POSITIONS or set(self.identities) != set(POSITIONS):
            raise GateError("posições da configuração ou das identidades divergem")
        self.system = offline.PROMPT.read_text(encoding="utf-8")
        self.pairs: dict[str, dict[str, dict[str, Any]]] = {}
        for entry in offline.load(AGENDA)["entries"]:
            self.pairs.setdefault(entry["pair_id"], {})[entry["repetition"]] = entry
        self._load_state()

    def common(self) -> dict[str, Any]:
        return {
            "run_id": self.authorization["run_id"],
            "authorization_sha256": self.authorization_sha,
            "snapshot_id": SNAPSHOT_ID,
            "snapshot_sha256": self.snapshot_sha,
        }

    def _load_state(self) -> None:
        """Retomada: só sob a mesma autorização, sem intenção órfã nem conclusão."""
        rows = {role: read_jsonl(self.output / name) for role, name in FILES.items()}
        common = self.common()
        for role, items in rows.items():
            for item in items:
                validate_role(role, item)
                if any(item[key] != value for key, value in common.items()):
                    raise GateError("registro existente pertence a outra autorização ou snapshot")
        if any(item["status"] == COMPLETE for item in rows["closure"]) or (self.output / EXECUTION_MANIFEST).exists():
            raise GateError("campanha já concluída")
        if any(item["classification"] == COST_VIOLATION for item in rows["attempt"]):
            raise GateError("violação de custo anterior; retomada exige decisão humana")
        if any(str(item["error"] or "").startswith(IDENTITY_FAILURE_PREFIX) for item in rows["attempt"]):
            raise GateError("divergência de identidade anterior; retomada exige decisão humana")
        intent_ids = [item["intent_id"] for item in rows["intent"]]
        attempt_ids = [item["intent_id"] for item in rows["attempt"]]
        if len(set(intent_ids)) != len(intent_ids) or len(set(attempt_ids)) != len(attempt_ids):
            raise GateError("intenção ou tentativa duplicada")
        if set(intent_ids) - set(attempt_ids):
            raise GateError("intenção órfã; retomada bloqueada")
        if set(attempt_ids) - set(intent_ids):
            raise GateError("tentativa sem intenção")
        self.attempts: dict[str, list[dict[str, Any]]] = {}
        for item in rows["attempt"]:
            self.attempts.setdefault(item["unit_id"], []).append(item)
        self.checkpoints = {item["unit_id"]: item for item in rows["checkpoint"]}
        self.results = {item["pair_id"]: item for item in rows["result"]}
        if len(self.checkpoints) != len(rows["checkpoint"]) or len(self.results) != len(rows["result"]):
            raise GateError("checkpoint ou resultado duplicado")
        self.session = len(rows["closure"]) + 1
        self.attempt_count = len(rows["attempt"])
        self.observed = sum((Decimal(item["cost_usd"]) for item in rows["attempt"] if item["cost_usd"] is not None), Decimal(0))
        self.accounted = sum((Decimal(item["accounted_usd"]) for item in rows["attempt"]), Decimal(0))

    def _emit(self, role: str, value: dict[str, Any]) -> dict[str, Any]:
        record = {**value, **self.common()}
        validate_role(role, record)
        append(self.output / FILES[role], record)
        return record

    def _checkpoint(self, attempt: Mapping[str, Any]) -> dict[str, Any]:
        ok = attempt["classification"] == VALID
        record = self._emit("checkpoint", {
            "unit_id": attempt["unit_id"], "attempt": attempt["attempt"], "request_sha256": attempt["request_sha256"],
            "state": "OK" if ok else "FAIL", "semantic_action": attempt["semantic_action"] if ok else None,
        })
        self.checkpoints[record["unit_id"]] = record
        return record

    def unit(self, entry: Mapping[str, Any]) -> dict[str, Any]:
        unit_id = entry["unit_id"]
        if unit_id in self.checkpoints:
            return self.checkpoints[unit_id]
        position = self.positions[entry["position_id"]]
        payload = offline.build_request(position, self.system, (REPO / entry["surface_path"]).read_text(encoding="utf-8"))
        digest = request_sha256(payload)
        reserve = planned_ceiling(position, payload)
        previous = self.attempts.get(unit_id, [])
        if [item["attempt"] for item in previous] != list(range(1, len(previous) + 1)):
            raise GateError(f"numeração de tentativas divergente: {unit_id}")
        if any(item["request_sha256"] != digest for item in previous):
            raise GateError(f"request_sha256 da retomada diverge: {unit_id}")
        if previous and previous[-1]["classification"] in TERMINAL:
            # Tentativa terminal gravada sem checkpoint: recupera sem nova chamada.
            return self._checkpoint(previous[-1])
        number = len(previous) + 1
        while True:
            if number > MAX_ATTEMPTS:
                raise GateError(f"tentativas esgotadas sem desfecho terminal: {unit_id}")
            if self.accounted + reserve > self.cap:
                raise GateError("teto impede a próxima chamada")
            self._emit("intent", {
                "intent_id": f"{unit_id}|A{number}", "unit_id": unit_id, "pair_id": entry["pair_id"],
                "position_id": entry["position_id"], "case_id": entry["case_id"], "condition": entry["condition"],
                "repetition": entry["repetition"], "attempt": number, "request_sha256": digest,
                "reserved_usd": money(reserve), "recorded_at": now(),
            })
            started_at, started = now(), time.monotonic_ns()
            kind, status, body, raw, error = _transport(self.sender, position, payload)
            latency_ms = (time.monotonic_ns() - started) // 1_000_000
            completed_at = now()
            cost: Decimal | None = None
            action = provider = revision = None
            identity = self.identities[entry["position_id"]]
            if kind == "response":
                violation = None
                if body is not None:
                    try:
                        cost = _observed_cost(position, body)
                    except preflight_runner.GateError as exc:
                        violation = str(exc)
                    if cost is not None and cost > reserve:
                        violation = "custo observado acima da reserva da tentativa"
                if violation is not None:
                    classification, error = COST_VIOLATION, violation
                elif body is None:
                    classification = SEMANTIC_FAILURE
                else:
                    classification, action, provider, revision, error = evaluate(position, identity, body)
            else:
                retry = kind in RETRYABLE_KINDS or (kind == "http" and status in RETRYABLE_HTTP)
                classification = RETRYABLE if retry and number < MAX_ATTEMPTS else TRANSPORT_FAILURE
            accounted = reserve if cost is None else cost
            record = self._emit("attempt", {
                "intent_id": f"{unit_id}|A{number}", "unit_id": unit_id, "attempt": number, "request_sha256": digest,
                "classification": classification, "transport_kind": kind, "http_status": status,
                "started_at": started_at, "completed_at": completed_at, "latency_ms": latency_ms,
                "reserved_usd": money(reserve), "cost_usd": None if cost is None else money(cost), "accounted_usd": money(accounted),
                "semantic_action": action, "effective_provider": provider, "effective_revision": revision,
                "requested_parameters": position["requested_parameters"],
                "accepted_by_contract": identity["accepted_by_contract"], "observed_or_echoed": identity["observed_or_echoed"],
                "raw_response": raw, "error": error,
            })
            self.attempts.setdefault(unit_id, []).append(record)
            self.attempt_count += 1
            self.accounted += accounted
            if cost is not None:
                self.observed += cost
            if classification == COST_VIOLATION:
                raise GateError(f"violação de custo: {error}")
            if classification in TERMINAL:
                checkpoint = self._checkpoint(record)
                # Persistido primeiro, interrompido depois: mesma ordem do original.
                if str(error or "").startswith(IDENTITY_FAILURE_PREFIX):
                    raise GateError(f"identidade efetiva divergente; campanha interrompida para decisão humana: {unit_id}")
                if kind == "http" and status in SYSTEMIC_HTTP:
                    raise GateError(f"falha sistêmica HTTP {status}; campanha interrompida para conferência humana")
                return checkpoint
            self.sleeper(RETRY_DELAY_SECONDS[number])
            number += 1

    @staticmethod
    def action(checkpoint: Mapping[str, Any]) -> str | None:
        return checkpoint["semantic_action"] if checkpoint["state"] == "OK" else None

    def execute(self) -> str:
        status, error = ABORTED, None
        try:
            order = sorted(self.pairs, key=lambda pair_id: min(item["primary_ordinal"] for item in self.pairs[pair_id].values()))
            for pair_id in order:
                if pair_id in self.results:
                    continue
                pair = self.pairs[pair_id]
                first = self.action(self.unit(pair["R1"]))
                second = self.action(self.unit(pair["R2"]))
                diagnostic = first is not None and second is not None and first != second
                third = None
                if diagnostic:
                    entry = dict(pair["R2"], repetition="R3", unit_id=f"{pair_id}|R3")
                    third = self.action(self.unit(entry))
                base = pair["R1"]
                self.results[pair_id] = self._emit("result", {
                    "pair_id": pair_id, "position_id": base["position_id"], "case_id": base["case_id"],
                    "condition": base["condition"], "r1_action": first, "r2_action": second,
                    "r3_action": third, "r3_diagnostic": diagnostic,
                })
            status = COMPLETE
            return status
        except BaseException as exc:
            error = f"{type(exc).__name__}: {exc}"[:500]
            raise
        finally:
            self._close(status, error)

    def _close(self, status: str, error: str | None) -> None:
        r3_units = sum(1 for unit_id in self.checkpoints if unit_id.endswith("|R3"))
        self._emit("closure", {
            "status": status, "session": self.session,
            "primary_units_terminal": len(self.checkpoints) - r3_units, "r3_units_terminal": r3_units,
            "attempts": self.attempt_count, "cost_observed_usd": money(self.observed),
            "cost_accounted_usd": money(self.accounted), "analysis_authorized": False, "error": error,
        })
        if status != COMPLETE:
            return
        ledger = {
            "schema_version": "m2_3_extension_execution_manifest_v1",
            "files": {name: sha(self.output / name) for name in FILES.values()},
            "counts": {"pairs": len(self.results), "primary_units": len(self.checkpoints) - r3_units, "r3_units": r3_units, "attempts": self.attempt_count},
            "cost_observed_usd": money(self.observed), "cost_accounted_usd": money(self.accounted),
            **self.common(),
        }
        validate_role("execution_manifest", ledger)
        with (self.output / EXECUTION_MANIFEST).open("xb") as stream:
            stream.write(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
            stream.flush()
            os.fsync(stream.fileno())


def run(authorization_path: Path, output_root: Path, sender: Callable, real: bool = True, sleeper: Callable[[float], None] = time.sleep) -> str:
    if not real and os.environ.get("OPENROUTER_API_KEY"):
        raise GateError("simulação exige OPENROUTER_API_KEY ausente")
    validate_ready()
    authorization, authorization_sha = validate_authorization(authorization_path, output_root, real)
    output_root.mkdir(parents=True, exist_ok=True)
    lock = output_root / LOCK
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise GateError("lock existente; conferir os registros antes de removê-lo") from exc
    try:
        os.write(descriptor, authorization_sha.encode("ascii"))
        os.close(descriptor)
        return Campaign(authorization, authorization_sha, output_root, sender, sleeper).execute()
    finally:
        lock.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("campaign_real",), required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise GateError("OPENROUTER_API_KEY ausente")
    status = run(args.authorization.resolve(), args.output_root.resolve(), preflight_runner._send, real=True)
    print(json.dumps({"status": status}, sort_keys=True))


if __name__ == "__main__":
    main()
