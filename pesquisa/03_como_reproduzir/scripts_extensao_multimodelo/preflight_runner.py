#!/usr/bin/env python3
"""Preflight da extensão: nove chamadas somente sob autorização externa explícita."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from . import offline


REPO = offline.REPO
PACKAGE = offline.PACKAGE


class GateError(RuntimeError):
    pass


class RemoteResponseError(GateError):
    def __init__(self, message: str, status: int | None = None, raw_response: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.raw_response = raw_response


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


def _json_line(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab", buffering=0) as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8") + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def _manifest_hash() -> str:
    return hashlib.sha256((PACKAGE / "manifesto_extensao_v1.json").read_bytes()).hexdigest()


def validate_authorization(value: Mapping[str, Any], authorization_path: Path, output_root: Path) -> None:
    required = {
        "schema_version", "run_id", "extension_manifest_sha256", "human_preflight_authorized",
        "cost_cap_usd", "authorized_positions", "authorized_conditions",
    }
    if set(value) != required or value.get("schema_version") != "m2_3_extension_preflight_authorization_v1":
        raise GateError("autorização de preflight inválida")
    if value.get("human_preflight_authorized") is not True:
        raise GateError("preflight sem autorização humana explícita")
    if value.get("extension_manifest_sha256") != _manifest_hash():
        raise GateError("autorização não fixa o manifesto atual")
    if not isinstance(value.get("run_id"), str) or not value["run_id"].startswith("m2_3_extension_preflight_"):
        raise GateError("run_id de preflight inválido")
    if Decimal(str(value["cost_cap_usd"])) <= 0 or Decimal(str(value["cost_cap_usd"])) > Decimal("0.25"):
        raise GateError("teto de preflight inválido ou superior a US$ 0,25")
    config = _load(PACKAGE / "config/modelos_posicoes_extensao_v1.json")
    position_ids = {item["position_id"] for item in config["positions"]}
    if set(value["authorized_positions"]) != position_ids or set(value["authorized_conditions"]) != {"C1", "C2", "D"}:
        raise GateError("autorização não cobre exatamente as nove chamadas")
    if authorization_path.resolve().is_relative_to(REPO.resolve()) or output_root.resolve().is_relative_to(REPO.resolve()):
        raise GateError("autorização e saída devem ficar fora do repositório")
    if output_root.exists():
        raise GateError("saída de preflight deve iniciar inexistente")


def _content_and_route(position: Mapping[str, Any], body: Mapping[str, Any]) -> tuple[str, Mapping[str, Any]]:
    metadata = body.get("openrouter_metadata")
    endpoints = metadata.get("endpoints") if isinstance(metadata, Mapping) else None
    available = endpoints.get("available") if isinstance(endpoints, Mapping) else None
    selected = [item for item in available or [] if isinstance(item, Mapping) and item.get("selected") is True]
    if len(selected) != 1:
        raise GateError("resposta não prova um provedor selecionado único")
    if str(selected[0].get("provider")).casefold() != str(position["requested_provider"]).casefold():
        raise GateError("provedor efetivo diverge ou houve fallback")
    requested = metadata.get("requested") if isinstance(metadata, Mapping) else None
    selected_model = selected[0].get("model")
    body_model = body.get("model")
    requested_model = str(position["requested_model"])
    allowed_models = {requested_model, f"{requested_model}-"}
    for observed in (requested, selected_model, body_model):
        if not isinstance(observed, str) or not any(observed == allowed or observed.startswith(allowed) for allowed in allowed_models):
            raise GateError("modelo solicitado, efetivo ou revisão diverge da posição")
    attempts = metadata.get("attempts") if isinstance(metadata, Mapping) else []
    if attempts is not None and (
        not isinstance(attempts, list)
        or any(not isinstance(item, Mapping) or str(item.get("provider")).casefold() != str(position["requested_provider"]).casefold() for item in attempts)
    ):
        raise GateError("metadados de rota indicam fallback ou tentativa não comprovada")
    if position["transport"] == "openrouter_responses":
        text = [part.get("text") for item in body.get("output", []) if item.get("type") == "message" for part in item.get("content", []) if isinstance(part, Mapping) and part.get("type") == "output_text"]
        if len(text) != 1 or not isinstance(text[0], str):
            raise GateError("Responses não devolveu um único output_text")
        return text[0], selected[0]
    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GateError("Chat Completions não devolveu conteúdo") from exc
    if not isinstance(text, str):
        raise GateError("conteúdo Chat Completions não é texto")
    return text, selected[0]


def _cache_write_multiplier(position: Mapping[str, Any]) -> Decimal:
    # OpenAI aplica cache de prompt automaticamente e publica gravação a 1,25x.
    # Anthropic só grava cache quando cache_control é enviado, o que este pacote omite.
    return Decimal("1.25") if position.get("provider_slug") == "openai" else Decimal("1")


def _observed_cost_within_ceiling(position: Mapping[str, Any], body: Mapping[str, Any]) -> Decimal:
    usage = body.get("usage")
    if not isinstance(usage, Mapping) or usage.get("cost") is None:
        raise GateError("resposta de preflight sem custo observável")
    def tokens(*names: str) -> Decimal:
        values = [usage[name] for name in names if name in usage]
        if len(values) != 1:
            raise GateError("resposta de preflight sem contagem de tokens inequívoca")
        value = Decimal(str(values[0]))
        if value < 0 or value != value.to_integral_value():
            raise GateError("contagem de tokens inválida")
        return value
    prompt = tokens("prompt_tokens", "input_tokens")
    completion = tokens("completion_tokens", "output_tokens")
    input_details = usage.get("prompt_tokens_details", usage.get("input_tokens_details", {}))
    if not isinstance(input_details, Mapping):
        raise GateError("detalhes de tokens de entrada inválidos")
    cache_write = Decimal(str(input_details.get("cache_write_tokens", 0)))
    if cache_write < 0 or cache_write != cache_write.to_integral_value() or cache_write > prompt:
        raise GateError("contagem de tokens gravados em cache inválida")
    observed = Decimal(str(usage["cost"]))
    if observed < 0:
        raise GateError("custo observado inválido")
    prices = position["provider_max_price_usd_per_million"]
    cache_write_multiplier = _cache_write_multiplier(position)
    ceiling = (
        Decimal(str(prices["prompt"]))
        * (prompt - cache_write + cache_write * cache_write_multiplier)
        / Decimal("1000000")
        + Decimal(str(prices["completion"])) * completion / Decimal("1000000")
        + Decimal(str(prices.get("request", 0)))
    )
    if observed > ceiling:
        raise GateError("custo observado excede o teto da tabela versionada")
    return observed


def _validate_semantic_schema(content: str) -> None:
    try:
        semantic = json.loads(content)
    except json.JSONDecodeError as exc:
        raise GateError("conteúdo não é JSON") from exc
    if (
        not isinstance(semantic, Mapping)
        or set(semantic) != {"acao", "justificativa"}
        or semantic["acao"] not in {"bloquear", "permitir", "inconclusiva"}
        or not isinstance(semantic["justificativa"], str)
        or not 1 <= len(semantic["justificativa"]) <= 800
    ):
        raise GateError("schema semântico inválido no preflight")


def _send(position: Mapping[str, Any], payload: Mapping[str, Any]) -> tuple[dict[str, Any], int, str]:
    # Esta função só é alcançada depois de validação da autorização externa.
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise GateError("OPENROUTER_API_KEY ausente após portão de autorização")
    request = urllib.request.Request(
        position["public_endpoint"], data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key, "X-OpenRouter-Metadata": "enabled"}, method="POST",
    )
    key = None
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8")
            try:
                return json.loads(raw, parse_float=Decimal), response.status, raw
            except json.JSONDecodeError as exc:
                raise RemoteResponseError("preflight HTTP 2xx com corpo não-JSON", response.status, raw) from exc
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RemoteResponseError(f"preflight HTTP {exc.code}", exc.code, raw) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise GateError("preflight sem conexão") from exc


def run(authorization_path: Path, output_root: Path) -> None:
    offline.validate()
    authorization = _load(authorization_path)
    validate_authorization(authorization, authorization_path, output_root)
    # O envelope HTTP precisa manter números JSON serializáveis. A carga exata
    # com Decimal fica restrita à autorização e à contabilidade monetária.
    config = offline.load(PACKAGE / "config/modelos_posicoes_extensao_v1.json")
    plan = _load(PACKAGE / "preflight/plano_preflight_9_chamadas_v1.json")
    positions = {item["position_id"]: item for item in config["positions"]}
    expected_pairs = {(position_id, condition) for position_id in positions for condition in ("C1", "C2", "D")}
    actual_pairs = {(call.get("position_id"), call.get("condition")) for call in plan.get("calls", [])}
    if len(plan.get("calls", [])) != 9 or actual_pairs != expected_pairs:
        raise GateError("plano de preflight não é exatamente 3 posições × C1/C2/D")
    system = offline.PROMPT.read_text(encoding="utf-8")
    planned_maximum = Decimal("0")
    rendered: list[tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], str]] = []
    for call in plan["calls"]:
        position = positions[call["position_id"]]
        evidence = (REPO / call["surface_path"]).read_text(encoding="utf-8")
        payload = offline.build_request(position, system, evidence)
        prices = position["provider_max_price_usd_per_million"]
        maximum_tokens = position["requested_parameters"].get("max_output_tokens", position["requested_parameters"].get("max_tokens"))
        planned_maximum += Decimal(str(prices["prompt"])) * _cache_write_multiplier(position) * Decimal(len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))) / Decimal("1000000")
        planned_maximum += Decimal(str(prices["completion"])) * Decimal(maximum_tokens) / Decimal("1000000")
        rendered.append((call, position, payload, evidence))
    if planned_maximum > Decimal(str(authorization["cost_cap_usd"])):
        raise GateError("teto não cobre o máximo das nove chamadas antes da rede")
    total = Decimal("0")
    for call, position, payload, _ in rendered:
        request_sha = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        _json_line(output_root / "intencoes_preflight.jsonl", {"ordinal": call["ordinal"], "request_sha256": request_sha, "position_id": call["position_id"], "condition": call["condition"]})
        status: int | None = None
        raw_response: str | None = None
        try:
            body, status, raw_response = _send(position, payload)
            content, selected = _content_and_route(position, body)
            _validate_semantic_schema(content)
            cost = _observed_cost_within_ceiling(position, body)
            total += cost
            if total > Decimal(str(authorization["cost_cap_usd"])):
                raise GateError("teto cumulativo do preflight excedido")
        except RemoteResponseError as exc:
            status, raw_response = exc.status, exc.raw_response
            _json_line(output_root / "registros_preflight.jsonl", {"ordinal": call["ordinal"], "http_status": status, "position_id": call["position_id"], "condition": call["condition"], "request_sha256": request_sha, "requested_parameters": position["requested_parameters"], "raw_response": raw_response, "verdict": "FAIL", "error": str(exc)})
            raise
        except Exception as exc:
            _json_line(output_root / "registros_preflight.jsonl", {"ordinal": call["ordinal"], "http_status": status, "position_id": call["position_id"], "condition": call["condition"], "request_sha256": request_sha, "requested_parameters": position["requested_parameters"], "raw_response": raw_response, "verdict": "FAIL", "error": str(exc)})
            raise
        _json_line(output_root / "registros_preflight.jsonl", {"ordinal": call["ordinal"], "http_status": status, "position_id": call["position_id"], "condition": call["condition"], "effective_provider": selected.get("provider"), "effective_revision": selected.get("model") or body.get("model"), "cost_usd": str(cost), "request_sha256": request_sha, "requested_parameters": position["requested_parameters"], "raw_response": raw_response, "verdict": "OK"})
    _json_line(output_root / "fechamento_preflight.jsonl", {"status": "GO_PENDING_INDEPENDENT_REVIEW", "calls": 9, "cost_usd": str(total), "planned_maximum_usd": str(planned_maximum), "campaign_authorized": False})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight_real",), required=True)
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    run(args.authorization.resolve(), args.output_root.resolve())


if __name__ == "__main__":
    main()
