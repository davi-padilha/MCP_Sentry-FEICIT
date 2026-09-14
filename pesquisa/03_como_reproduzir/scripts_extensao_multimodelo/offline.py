#!/usr/bin/env python3
"""Validador/dry-run fail-closed, deliberadamente sem transporte de rede."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping


REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / "baterias_finais/m2_3_extensao_multimodelo_v1_candidate"
SOURCE = REPO / "baterias_finais/m2_3_campaign_g1_v2_ready"
PROMPT = REPO / "baterias_finais/m2_3_pre_congelamento_v1/instrumento/prompt_sistema_v1.txt"
RESPONSE_SCHEMA = REPO / "baterias_finais/m2_3_pre_congelamento_v1/instrumento/schema_resposta_v1.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def provider(position: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "only": [position["provider_slug"]],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "deny",
        "max_price": position["provider_max_price_usd_per_million"],
    }


def response_schema() -> dict[str, Any]:
    value = load(RESPONSE_SCHEMA)
    return {key: item for key, item in value.items() if key not in {"$schema", "$id", "title"}}


def build_request(position: Mapping[str, Any], system: str, evidence: str) -> dict[str, Any]:
    params = position["requested_parameters"]
    clean_schema = response_schema()
    if position["transport"] == "openrouter_responses":
        return {
            "model": position["requested_model"],
            "input": [
                {"type": "message", "role": "system", "content": [{"type": "input_text", "text": system}]},
                {"type": "message", "role": "user", "content": [{"type": "input_text", "text": evidence}]},
            ],
            "stream": False,
            "store": False,
            "max_output_tokens": params["max_output_tokens"],
            "text": {"format": {"type": "json_schema", "name": "m2_3_response", "strict": True, "schema": clean_schema}},
            "provider": provider(position),
            "reasoning": params["reasoning"],
        }
    if position["transport"] == "openrouter_chat_completions":
        return {
            "model": position["requested_model"],
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": evidence}],
            "stream": False,
            "max_tokens": params["max_tokens"],
            "response_format": {"type": "json_schema", "json_schema": {"name": "m2_3_response", "strict": True, "schema": clean_schema}},
            "provider": provider(position),
            "reasoning": params["reasoning"],
        }
    raise ValueError("transporte não autorizado na extensão")


def validate() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = load(PACKAGE / "manifesto_extensao_v1.json")
    config = load(PACKAGE / "config/modelos_posicoes_extensao_v1.json")
    agenda = load(PACKAGE / "agenda/agenda_extensao_v1.json")
    preflight = load(PACKAGE / "preflight/plano_preflight_9_chamadas_v1.json")
    if any(manifest["gates"].values()) or any((config["execution_authorized"], config["preflight_execution_authorized"], config["official_campaign_authorized"])):
        raise ValueError("candidata abriu portão de execução")
    if len(config["positions"]) != 3 or len(agenda["entries"]) != 900:
        raise ValueError("contagens divergentes")
    if preflight["call_count"] != 9 or len(preflight["calls"]) != 9:
        raise ValueError("preflight não contém exatamente nove chamadas")
    for reference in manifest["source_references"]:
        path = REPO / reference["path"]
        if digest(path) != reference["sha256"]:
            raise ValueError(f"fonte divergiu: {reference['path']}")
    for reference in manifest["generated_artifacts"]:
        path = PACKAGE / reference["path"]
        if digest(path) != reference["sha256"]:
            raise ValueError(f"artefato gerado divergiu: {reference['path']}")
    ids = {p["position_id"] for p in config["positions"]}
    if {e["position_id"] for e in agenda["entries"]} != ids:
        raise ValueError("agenda e configuração divergem")
    if len({e["unit_id"] for e in agenda["entries"]}) != 900:
        raise ValueError("unit_id duplicado")
    for entry in agenda["entries"]:
        surface = REPO / entry["surface_path"]
        if digest(surface) != entry["surface_sha256"]:
            raise ValueError(f"superfície divergiu: {entry['surface_path']}")
    return manifest, config, agenda


def dry_run() -> None:
    if "OPENROUTER_API_KEY" in os.environ:
        raise RuntimeError("dry-run exige OPENROUTER_API_KEY ausente")
    _, config, agenda = validate()
    by_id = {p["position_id"]: p for p in config["positions"]}
    request_hashes = set()
    system = PROMPT.read_text(encoding="utf-8")
    for entry in agenda["entries"]:
        evidence = (REPO / entry["surface_path"]).read_text(encoding="utf-8")
        payload = build_request(by_id[entry["position_id"]], system, evidence)
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        request_hashes.add(hashlib.sha256(serialized).hexdigest())
        if "temperature" in payload or "top_p" in payload or "tools" in payload:
            raise ValueError("parâmetro deliberadamente omitido apareceu no envelope")
        route = payload["provider"]
        if route["allow_fallbacks"] is not False or len(route["only"]) != 1:
            raise ValueError("rota permite fallback")
    print(json.dumps({
        "status": "DRY_RUN_OFFLINE_OK",
        "network_calls": 0,
        "credential_value_read": False,
        "primary_units": len(agenda["entries"]),
        "unique_request_envelopes": len(request_hashes),
        "positions": len(config["positions"]),
    }, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.validate == args.dry_run:
        parser.error("escolha exatamente --validate ou --dry-run")
    if args.validate:
        validate()
        print('{"status":"VALIDATE_OK"}')
    else:
        dry_run()


if __name__ == "__main__":
    main()
