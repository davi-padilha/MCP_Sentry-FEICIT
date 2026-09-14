#!/usr/bin/env python3
"""Materializa métricas descritivas estritas da campanha multimodelo M2.3."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO = Path(__file__).resolve().parents[2]
RUN_ID = "m2_3_extension_campaign_20260911_221516"
INPUT = REPO / "logs_resultados/evidencias" / RUN_ID
LEDGER = REPO / "logs_resultados/evidencias/2026-09-12_m2_3_extension_campaign_20260911_221516.sha256.tsv"
CONTRACT = REPO / "baterias_finais/m2_3_extensao_multimodelo_v1_ready/contrato_analitico_v1.json"
POSITIONS = (
    "remote-gpt-5-6-luna-high-openai",
    "remote-gpt-5-6-sol-medium-openai",
    "remote-claude-opus-5-medium-anthropic",
)
CONDITIONS = ("C1", "C2", "D")
ACTIONS = ("bloquear", "permitir", "inconclusiva", "terminal_failure")
FILES = ("authorization.json", "intencoes.jsonl", "tentativas.jsonl", "checkpoints.jsonl", "resultados.jsonl", "fechamento.jsonl", "manifesto_execucao.json")
EXPECTED_LEDGER_SHA256 = "c7a164fc3bfdfc36628a2cd9a3fb28767679226dc7754b1fc1eae483c3025998"
EXPECTED_CONTRACT_SHA256 = "64aab9b8251aa7fa871b90fd9899be65931ac90ad298846d86d53b0f046cc61c"
EXPECTED_INPUT_SHA256 = {
    "authorization.json": "3bdd6708b5babb868aa52342e8249df92e53efcd7a99bcae5c11cb52097a574b",
    "checkpoints.jsonl": "17860798d0ef7d03b8baf40b86e7b7c8441c2c3ede5d89e029a8fd7a2eff54b8",
    "fechamento.jsonl": "fc045ecacba1b243e6a3d757aa9a07f0d62ace8cc5cd9240225002e408cab45f",
    "intencoes.jsonl": "d7dfca78c9e14e13edde0db47a918c3d8883d61df13ee111af22f10b87fe4444",
    "manifesto_execucao.json": "3d1f9483c6b2b57b84b217de1a48738b321a107c50dc57044709f7ee3f63a1a7",
    "resultados.jsonl": "f8de05a0a1ce315a38cf6fdd1c3c84a94a14672f45c36a6ab7aa4deaea36bc36",
    "tentativas.jsonl": "7aaa42960aaa74b74d922f60281be5bfc2feab32da060a630708b7c55a96fb3f",
}
EXPECTED_CONTRACT = {
    "aborted_or_partial_is_complete_campaign": False,
    "cross_cohort_comparison": "descriptive_only_with_explicit_temporal_cohort",
    "denominators": {
        "per_position": {"by_condition_pairs": {"C1": 60, "C2": 60, "D": 30}, "pairs": 150, "primary_units": 300},
        "terminal_failures_remain_in_denominator": True,
        "total": {"pairs": 450, "primary_units": 900},
    },
    "estimand": "configuration_sensitivity_within_new_temporal_cohort",
    "historical_luna_low_equals_new_luna_high": False,
    "historical_metric_definitions_unchanged": True,
    "model_or_provider_superiority_is_causal": False,
    "outputs": ["action_distribution", "block_rate", "agreement_r1_r2", "r3_diagnostic_rate", "cost", "latency"],
    "r3_replaces_r1_r2": False,
    "r3_role": "diagnostic_only_under_valid_r1_r2_divergence",
    "schema_version": "m2_3_extension_analysis_contract_v1",
}


class AnalysisError(RuntimeError):
    pass


def reject_constant(value: str) -> Any:
    raise AnalysisError(f"constante JSON não permitida: {value}")


def loads(text: str) -> Any:
    return json.loads(text, parse_float=Decimal, parse_constant=reject_constant)


def load(path: Path) -> Any:
    return loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        raise AnalysisError(f"JSONL truncado: {path.name}")
    return [loads(line) for line in data.decode("utf-8").splitlines()]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dec(value: Any) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise AnalysisError("valor numérico não finito")
    return result


def exact_json_equal(actual: Any, expected: Any) -> bool:
    """Compara estrutura JSON sem as equivalências bool/int/Decimal do Python."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(exact_json_equal(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(exact_json_equal(left, right) for left, right in zip(actual, expected))
    return actual == expected


def ratio(numerator: int, denominator: int) -> str:
    return format(Decimal(numerator) / Decimal(denominator), ".8f") if denominator else "NA"


def nearest_rank(values: list[int], quantile: Decimal) -> int | str:
    if not values:
        return "NA"
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * float(quantile)) - 1)]


def exact_median(values: list[int]) -> str:
    if not values:
        return "NA"
    ordered = sorted(values)
    middle = len(ordered) // 2
    value = Decimal(ordered[middle]) if len(ordered) % 2 else (Decimal(ordered[middle - 1]) + Decimal(ordered[middle])) / Decimal(2)
    return format(value, "f")


def validate_inputs() -> dict[str, str]:
    if sha(LEDGER) != EXPECTED_LEDGER_SHA256:
        raise AnalysisError("hash do ledger de entrada divergente")
    if sha(CONTRACT) != EXPECTED_CONTRACT_SHA256:
        raise AnalysisError("hash do contrato analítico divergente")
    entries: dict[str, str] = {}
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) != 2 or parts[1] in entries:
            raise AnalysisError("ledger de entrada inválido")
        entries[parts[1]] = parts[0]
    if set(entries) != set(FILES):
        raise AnalysisError("ledger não cobre os sete arquivos oficiais")
    if entries != EXPECTED_INPUT_SHA256:
        raise AnalysisError("ledger não corresponde aos hashes oficiais fixados")
    for name, digest in entries.items():
        if sha(INPUT / name) != digest:
            raise AnalysisError(f"hash de entrada divergente: {name}")
    contract = load(CONTRACT)
    if not exact_json_equal(contract, EXPECTED_CONTRACT):
        raise AnalysisError("contrato analítico inválido")
    return entries


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def analyze() -> dict[str, Any]:
    input_hashes = validate_inputs()
    intents = read_jsonl(INPUT / "intencoes.jsonl")
    attempts = read_jsonl(INPUT / "tentativas.jsonl")
    checkpoints = read_jsonl(INPUT / "checkpoints.jsonl")
    results = read_jsonl(INPUT / "resultados.jsonl")
    closures = read_jsonl(INPUT / "fechamento.jsonl")
    if (len(intents), len(attempts), len(checkpoints), len(results), len(closures)) != (905, 905, 905, 450, 1):
        raise AnalysisError("cardinalidades oficiais divergentes")
    if closures[0]["analysis_authorized"] is not False or closures[0]["status"] != "COMPLETE_PENDING_INDEPENDENT_REVIEW":
        raise AnalysisError("fechamento incompatível")
    intent_by_id = {row["intent_id"]: row for row in intents}
    if len(intent_by_id) != len(intents):
        raise AnalysisError("intenção duplicada")
    result_by_pair = {row["pair_id"]: row for row in results}
    if len(result_by_pair) != 450:
        raise AnalysisError("par duplicado")

    action_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    cost_rows: list[dict[str, Any]] = []
    groups = [("ALL", "ALL")]
    groups += [(p, "ALL") for p in POSITIONS]
    groups += [("ALL", c) for c in CONDITIONS]
    groups += [(p, c) for p in POSITIONS for c in CONDITIONS]

    for position, condition in groups:
        selected = [r for r in results if (position == "ALL" or r["position_id"] == position) and (condition == "ALL" or r["condition"] == condition)]
        pair_count = len(selected)
        primary = [r[key] for r in selected for key in ("r1_action", "r2_action")]
        counts = Counter(action if action is not None else "terminal_failure" for action in primary)
        valid_pairs = [r for r in selected if r["r1_action"] is not None and r["r2_action"] is not None]
        agreements = sum(r["r1_action"] == r["r2_action"] for r in valid_pairs)
        diagnostics = sum(bool(r["r3_diagnostic"]) for r in selected)
        for action in ACTIONS:
            action_rows.append({"position_id": position, "condition": condition, "action": action, "count": counts[action], "denominator_primary_units": len(primary), "proportion": ratio(counts[action], len(primary))})
        metric_rows.append({
            "position_id": position, "condition": condition, "pairs": pair_count, "primary_units": len(primary),
            "valid_primary_units": len(primary) - counts["terminal_failure"], "terminal_failures": counts["terminal_failure"],
            "block_count": counts["bloquear"], "block_rate_all_primary": ratio(counts["bloquear"], len(primary)),
            "valid_pairs": len(valid_pairs), "r1_r2_agreements": agreements,
            "agreement_rate_all_pairs": ratio(agreements, pair_count), "agreement_rate_valid_pairs": ratio(agreements, len(valid_pairs)),
            "r3_diagnostics": diagnostics, "r3_diagnostic_rate_all_pairs": ratio(diagnostics, pair_count),
        })

        attempt_selected = []
        for attempt in attempts:
            intent = intent_by_id.get(attempt["intent_id"])
            if intent is None:
                raise AnalysisError("tentativa sem intenção")
            if (position == "ALL" or intent["position_id"] == position) and (condition == "ALL" or intent["condition"] == condition):
                attempt_selected.append(attempt)
        latencies = [int(a["latency_ms"]) for a in attempt_selected]
        observed = sum((dec(a["cost_usd"]) for a in attempt_selected if a["cost_usd"] is not None), Decimal(0))
        accounted = sum((dec(a["accounted_usd"]) for a in attempt_selected), Decimal(0))
        cost_rows.append({
            "position_id": position, "condition": condition, "attempts": len(attempt_selected),
            "cost_observed_usd": format(observed, "f"), "cost_accounted_usd": format(accounted, "f"),
            "latency_min_ms": min(latencies) if latencies else "NA", "latency_median_ms": exact_median(latencies),
            "latency_p95_ms": nearest_rank(latencies, Decimal("0.95")), "latency_max_ms": max(latencies) if latencies else "NA",
        })

    overall = metric_rows[0]
    overall_cost = cost_rows[0]
    if (overall["pairs"], overall["primary_units"], overall["r3_diagnostics"], overall_cost["attempts"]) != (450, 900, 5, 905):
        raise AnalysisError("reconstrução global divergente")
    if overall_cost["cost_observed_usd"] != "5.14043240" or overall_cost["cost_accounted_usd"] != "5.80164740":
        raise AnalysisError("custos globais divergentes")
    return {"input_hashes": input_hashes, "action_rows": action_rows, "metric_rows": metric_rows, "cost_rows": cost_rows}


def materialize(output: Path) -> None:
    if output.exists():
        raise AnalysisError("saída já existe; materialização recusada")
    data = analyze()
    output.mkdir(parents=True)
    write_csv(output / "DISTRIBUICAO_DAS_DECISOES.csv", ["position_id", "condition", "action", "count", "denominator_primary_units", "proportion"], data["action_rows"])
    write_csv(output / "RESUMO_POR_MODELO_E_CONDICAO.csv", list(data["metric_rows"][0]), data["metric_rows"])
    write_csv(output / "CUSTOS_E_TEMPOS_DE_RESPOSTA.csv", list(data["cost_rows"][0]), data["cost_rows"])
    overall = data["metric_rows"][0]
    summary = {
        "schema_version": "m2_3_extension_descriptive_analysis_v1", "run_id": RUN_ID,
        "estimand": "configuration_sensitivity_within_new_temporal_cohort", "causal_superiority_claimed": False,
        "pairs": overall["pairs"], "primary_units": overall["primary_units"], "terminal_failures": overall["terminal_failures"],
        "r3_diagnostics": overall["r3_diagnostics"], "block_rate_all_primary": overall["block_rate_all_primary"],
        "agreement_rate_all_pairs": overall["agreement_rate_all_pairs"], "agreement_rate_valid_pairs": overall["agreement_rate_valid_pairs"],
        **{key: data["cost_rows"][0][key] for key in ("attempts", "cost_observed_usd", "cost_accounted_usd", "latency_min_ms", "latency_median_ms", "latency_p95_ms", "latency_max_ms")},
    }
    (output / "RESUMO_DA_ANALISE.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = f"""# Relatório descritivo — extensão multimodelo M2.3

Esta análise cobre exclusivamente a coorte temporal de `{RUN_ID}`. Ela descreve sensibilidade à configuração e **não demonstra superioridade causal de modelo ou provedor**.

## Universo

- 450 pares e 900 unidades primárias; falhas terminais permanecem nos denominadores.
- {overall['terminal_failures']} falhas terminais primárias e {overall['r3_diagnostics']} R3 diagnósticos.
- {data['cost_rows'][0]['attempts']} tentativas; custo observado US$ {data['cost_rows'][0]['cost_observed_usd']} e contabilizado US$ {data['cost_rows'][0]['cost_accounted_usd']}.

## Métricas globais

- taxa de bloqueio sobre todas as unidades primárias: {overall['block_rate_all_primary']};
- concordância R1/R2 sobre todos os pares: {overall['agreement_rate_all_pairs']};
- concordância entre pares com duas respostas válidas: {overall['agreement_rate_valid_pairs']};
- taxa diagnóstica R3 sobre todos os pares: {overall['r3_diagnostic_rate_all_pairs']}.

Os detalhamentos por posição e condição estão nos CSVs. R3 é diagnóstico e não substitui R1/R2. Comparações com coortes históricas não foram realizadas.
"""
    (output / "LEIA_PRIMEIRO_RESULTADOS_DA_EXTENSAO.md").write_text(report, encoding="utf-8")
    generated = ["DISTRIBUICAO_DAS_DECISOES.csv", "RESUMO_POR_MODELO_E_CONDICAO.csv", "CUSTOS_E_TEMPOS_DE_RESPOSTA.csv", "RESUMO_DA_ANALISE.json", "LEIA_PRIMEIRO_RESULTADOS_DA_EXTENSAO.md"]
    manifest = {
        "schema_version": "m2_3_extension_analysis_manifest_v1", "status": "CANDIDATE_PENDING_INDEPENDENT_REVIEW",
        "run_id": RUN_ID, "analysis_contract_sha256": sha(CONTRACT), "input_ledger_sha256": sha(LEDGER),
        "analyzer_sources_sha256": {
            "tools/m2_3_extensao_multimodelo_analysis_v1/__init__.py": sha(Path(__file__).with_name("__init__.py")),
            "tools/m2_3_extensao_multimodelo_analysis_v1/analyze.py": sha(Path(__file__)),
            "tools/m2_3_extensao_multimodelo_analysis_v1/test_analysis.py": sha(Path(__file__).with_name("test_analysis.py")),
        },
        "input_sha256": data["input_hashes"], "outputs_sha256": {name: sha(output / name) for name in generated},
        "gates": {"analysis_preservation_authorized": False, "model_calls_authorized": False, "new_campaign_authorized": False},
    }
    (output / "REGISTRO_TECNICO_DA_ANALISE.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ledger_names = [*generated, "REGISTRO_TECNICO_DA_ANALISE.json"]
    (output / "HASHES_DA_ANALISE.tsv").write_text("".join(f"{sha(output / name)}\t{name}\n" for name in ledger_names), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    materialize(args.output_root.resolve())
    print(json.dumps({"status": "ANALYSIS_CANDIDATE_OK", "output_root": str(args.output_root.resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
