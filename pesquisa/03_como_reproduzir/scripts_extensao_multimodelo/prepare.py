#!/usr/bin/env python3
"""Materializa, de forma deterministica e sem rede, a candidata da extensao."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "baterias_finais/m2_3_campaign_g1_v2_ready"
TARGET = REPO / "baterias_finais/m2_3_extensao_multimodelo_v1_candidate"
SOURCE_AGENDA = SOURCE / "agenda/agenda_primaria_v6_i1.json"
SOURCE_MANIFEST = SOURCE / "manifesto_campaign_g1_ready_v1.json"
SOURCE_CONFIG = SOURCE / "config/modelos_posicoes_v6.json"
SOURCE_PROMPT = REPO / "baterias_finais/m2_3_pre_congelamento_v1/instrumento/prompt_sistema_v1.txt"
SOURCE_RESPONSE_SCHEMA = REPO / "baterias_finais/m2_3_pre_congelamento_v1/instrumento/schema_resposta_v1.json"

POSITIONS: list[dict[str, Any]] = [
    {
        "position_id": "remote-gpt-5-6-luna-high-openai",
        "lane": "cloud_extension",
        "machine": "PC-EXT",
        "transport": "openrouter_responses",
        "public_endpoint": "https://openrouter.ai/api/v1/responses",
        "requested_model": "openai/gpt-5.6-luna",
        "requested_provider": "OpenAI",
        "provider_slug": "openai",
        "response_format_mode": "json_schema",
        "requested_parameters": {
            "reasoning": {"effort": "high", "context": "current_turn"},
            "temperature": "intentionally_omitted",
            "top_p": "intentionally_omitted",
            "store": False,
            "previous_response_id": "absent",
            "max_output_tokens": 1024,
            "tools": "intentionally_omitted",
        },
        "provider_max_price_usd_per_million": {
            "prompt": 0.20, "completion": 1.20, "request": 0.0,
        },
        "approved_effective_identity": "pending_preflight",
        "observed_parameters": "pending_preflight",
    },
    {
        "position_id": "remote-gpt-5-6-sol-medium-openai",
        "lane": "cloud_extension",
        "machine": "PC-EXT",
        "transport": "openrouter_responses",
        "public_endpoint": "https://openrouter.ai/api/v1/responses",
        "requested_model": "openai/gpt-5.6-sol",
        "requested_provider": "OpenAI",
        "provider_slug": "openai",
        "response_format_mode": "json_schema",
        "requested_parameters": {
            "reasoning": {"effort": "medium", "context": "current_turn"},
            "temperature": "intentionally_omitted",
            "top_p": "intentionally_omitted",
            "store": False,
            "previous_response_id": "absent",
            "max_output_tokens": 1024,
            "tools": "intentionally_omitted",
        },
        "provider_max_price_usd_per_million": {
            "prompt": 2.0, "completion": 10.0, "request": 0.0,
        },
        "approved_effective_identity": "pending_preflight",
        "observed_parameters": "pending_preflight",
    },
    {
        "position_id": "remote-claude-opus-5-medium-anthropic",
        "lane": "cloud_extension",
        "machine": "PC-EXT",
        "transport": "openrouter_chat_completions",
        "public_endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "requested_model": "anthropic/claude-opus-5",
        "requested_provider": "Anthropic",
        "provider_slug": "anthropic",
        "response_format_mode": "json_schema",
        "requested_parameters": {
            "reasoning": {"effort": "medium"},
            "temperature": "intentionally_omitted",
            "top_p": "intentionally_omitted",
            "max_tokens": 1024,
            "tools": "intentionally_omitted",
        },
        "provider_max_price_usd_per_million": {
            "prompt": 5.0, "completion": 25.0, "request": 0.0,
        },
        "approved_effective_identity": "pending_preflight",
        "observed_parameters": "pending_preflight",
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )


def derive_agenda() -> dict[str, Any]:
    source = load(SOURCE_AGENDA)
    anchors: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in source["entries"]:
        key = (entry["semantic_id"], entry["repetition"])
        anchors.setdefault(key, entry)
    if len(anchors) != 300:
        raise RuntimeError(f"esperadas 300 unidades sem modelo; obtidas {len(anchors)}")

    entries: list[dict[str, Any]] = []
    ordinal = 0
    for anchor in anchors.values():
        for position in POSITIONS:
            ordinal += 1
            item = deepcopy(anchor)
            item["position_id"] = position["position_id"]
            item["lane"] = position["lane"]
            item["machine"] = position["machine"]
            item["pair_id"] = f'{anchor["semantic_id"]}|{position["position_id"]}'
            item["unit_id"] = f'{item["pair_id"]}|{anchor["repetition"]}'
            item["primary_ordinal"] = ordinal
            entries.append(item)
    return {
        "schema_version": "m2_3_extension_agenda_v1",
        "source_agenda": {
            "path": SOURCE_AGENDA.relative_to(REPO).as_posix(),
            "sha256": sha256(SOURCE_AGENDA),
        },
        "counts": {
            "semantic_units": 150,
            "model_independent_primary_units": 300,
            "positions": 3,
            "primary_units": 900,
            "r3_theoretical_max": 450,
        },
        "entries": entries,
    }


def derive_preflight(agenda: dict[str, Any]) -> dict[str, Any]:
    representatives: dict[str, dict[str, Any]] = {}
    for entry in agenda["entries"]:
        representatives.setdefault(entry["condition"], entry)
    if set(representatives) != {"C1", "C2", "D"}:
        raise RuntimeError("agenda não oferece as três superfícies C1/C2/D")
    calls = []
    ordinal = 0
    for position in POSITIONS:
        for condition in ("C1", "C2", "D"):
            ordinal += 1
            source = representatives[condition]
            calls.append({
                "ordinal": ordinal,
                "position_id": position["position_id"],
                "condition": condition,
                "case_id": source["case_id"],
                "surface_path": source["surface_path"],
                "surface_sha256": source["surface_sha256"],
                "status": "not_authorized_not_executed",
            })
    return {
        "schema_version": "m2_3_extension_preflight_plan_v1",
        "execution_authorized": False,
        "campaign_authorized": False,
        "call_count": 9,
        "acceptance": [
            "http_success",
            "strict_json_schema_valid",
            "requested_model_matches",
            "effective_provider_matches_without_fallback",
            "effective_revision_recorded",
            "accepted_parameters_match",
            "effective_cost_within_versioned_ceiling",
        ],
        "calls": calls,
    }


def main() -> None:
    for required in (SOURCE_AGENDA, SOURCE_MANIFEST, SOURCE_CONFIG, SOURCE_PROMPT, SOURCE_RESPONSE_SCHEMA):
        if not required.is_file():
            raise SystemExit(f"fonte ausente: {required}")
    agenda = derive_agenda()
    config = {
        "schema_version": "m2_3_extension_model_positions_v1",
        "status": "candidate_offline_not_authorized",
        "credential_environment_variable": "OPENROUTER_API_KEY",
        "execution_authorized": False,
        "preflight_execution_authorized": False,
        "official_campaign_authorized": False,
        "positions": POSITIONS,
    }
    preflight = derive_preflight(agenda)
    write(TARGET / "config/modelos_posicoes_extensao_v1.json", config)
    write(TARGET / "agenda/agenda_extensao_v1.json", agenda)
    write(TARGET / "preflight/plano_preflight_9_chamadas_v1.json", preflight)

    referenced = [SOURCE_MANIFEST, SOURCE_AGENDA, SOURCE_CONFIG, SOURCE_PROMPT, SOURCE_RESPONSE_SCHEMA]
    generated = [
        TARGET / "config/modelos_posicoes_extensao_v1.json",
        TARGET / "agenda/agenda_extensao_v1.json",
        TARGET / "preflight/plano_preflight_9_chamadas_v1.json",
    ]
    manifest = {
        "schema_version": "m2_3_extension_candidate_manifest_v1",
        "status": "candidate_offline_not_authorized",
        "extension_id": "m2_3_extension_three_models_v1",
        "original_campaign_run_id": "m2_3_campaign_20260907_01",
        "temporal_cohort": "new_distinct_cohort_pending",
        "comparison_scope": {
            "direct_within_new_cohort": True,
            "joint_with_original_requires_temporal_cohort_label": True,
            "luna_low_and_luna_high_are_distinct_configurations": True,
        },
        "gates": {
            "preflight_authorized": False,
            "campaign_authorized": False,
            "network_allowed": False,
            "credential_access_allowed": False,
        },
        "proposed_budget": {
            "estimated_equal_token_usd": 3.35,
            "operational_reserve_usd": 7.0,
            "hard_cap_usd": 14.0,
            "status": "proposal_pending_human_approval",
        },
        "source_references": [
            {"path": path.relative_to(REPO).as_posix(), "sha256": sha256(path)}
            for path in referenced
        ],
        "generated_artifacts": [
            {
                "path": path.relative_to(TARGET).as_posix(),
                "sha256": sha256(path),
            }
            for path in generated
        ],
        "counts": agenda["counts"],
    }
    write(TARGET / "manifesto_extensao_v1.json", manifest)
    print(json.dumps({"status": "PREPARE_OK", "primary_units": 900, "preflight_calls": 9}, sort_keys=True))


if __name__ == "__main__":
    main()
