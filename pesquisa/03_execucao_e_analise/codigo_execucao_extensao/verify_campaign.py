#!/usr/bin/env python3
"""Consumidor independente dos registros da campanha da extensão.

Reconstrói o universo esperado — unidades, `request_sha256`, reservas, R3,
parâmetros, identidades, custos e ledger — a partir da agenda, da configuração,
das identidades e do prompt pinados no ready, nunca das contagens declaradas
pelo produtor. Campos derivados da resposta são reconstruídos do corpo bruto
preservado, e não aceitos como declarados. Não escreve em lugar algum.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from . import campaign, offline, verificacao_antes_da_execucao as preflight_runner


def _fail(message: str) -> None:
    raise campaign.GateError(message)


def _unique(rows: list[Mapping[str, Any]], key: str, label: str) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if row[key] in index:
            _fail(f"{label} duplicado: {row[key]}")
        index[row[key]] = row
    return index


def _action(checkpoint: Mapping[str, Any]) -> str | None:
    return checkpoint["semantic_action"] if checkpoint["state"] == "OK" else None


def _as_record_json(value: Any) -> Any:
    """Normaliza o lado pinado para a mesma forma que o JSONL devolve."""
    return campaign.loads(json.dumps(value, ensure_ascii=False, default=str))


def _reprocess(position: Mapping[str, Any], identity: Mapping[str, Any], attempt: Mapping[str, Any]) -> None:
    """Refaz, do corpo bruto, o que o produtor derivou da resposta."""
    raw = attempt["raw_response"]
    label = attempt["intent_id"]
    if attempt["transport_kind"] != "response":
        if attempt["cost_usd"] is not None or attempt["semantic_action"] is not None:
            _fail(f"custo ou ação sem resposta recebida: {label}")
        if attempt["effective_provider"] is not None or attempt["effective_revision"] is not None:
            _fail(f"identidade efetiva sem resposta recebida: {label}")
        return
    if attempt["classification"] == campaign.VALID:
        if not isinstance(raw, str):
            _fail(f"tentativa válida sem resposta bruta: {label}")
        body = campaign.loads(raw)
        classification, action, provider, revision, error = campaign.evaluate(position, identity, body)
        if classification != campaign.VALID:
            _fail(f"resposta bruta não sustenta a tentativa válida: {label}: {error}")
        cost = campaign._observed_cost(position, body)
        recorded = None if attempt["cost_usd"] is None else Decimal(attempt["cost_usd"])
        if action != attempt["semantic_action"] or provider != attempt["effective_provider"] or revision != attempt["effective_revision"]:
            _fail(f"ação ou identidade divergem do corpo bruto: {label}")
        if cost != recorded:
            _fail(f"custo divergente do corpo bruto: {label}")
        return
    # Falha terminal com resposta recebida: o corpo não pode sustentar sucesso.
    if raw is None:
        return
    try:
        body = campaign.loads(raw)
    except (ValueError, TypeError):
        return
    classification, _, _, _, _ = campaign.evaluate(position, identity, body)
    if classification == campaign.VALID and campaign._observed_cost(position, body) is not None:
        _fail(f"resposta bruta válida registrada como falha: {label}")


def check(output_root: Path, authorization_path: Path) -> dict[str, Any]:
    output = output_root.resolve()
    campaign.validate_ready()
    authorization, authorization_sha = campaign.validate_authorization(authorization_path.resolve(), output, False)
    common = {
        "run_id": authorization["run_id"], "authorization_sha256": authorization_sha,
        "snapshot_id": campaign.SNAPSHOT_ID, "snapshot_sha256": campaign.sha(campaign.MANIFEST),
    }
    rows = {role: campaign.read_jsonl(output / name) for role, name in campaign.FILES.items()}
    for role, items in rows.items():
        for item in items:
            campaign.validate_role(role, item)
            if any(item[key] != value for key, value in common.items()):
                _fail("junta de autoridade divergente")

    closures = rows["closure"]
    if (
        not closures
        or closures[-1]["status"] != campaign.COMPLETE
        or any(item["status"] != campaign.ABORTED for item in closures[:-1])
        or [item["session"] for item in closures] != list(range(1, len(closures) + 1))
    ):
        _fail("fechamento não termina em uma única conclusão")
    closure = closures[-1]

    # Universo esperado, só a partir dos artefatos pinados.
    positions = {item["position_id"]: item for item in offline.load(campaign.CONFIG)["positions"]}
    identities = {item["position_id"]: item for item in campaign.load(campaign.IDENTITIES)["positions"]}
    system = offline.PROMPT.read_text(encoding="utf-8")
    agenda = offline.load(campaign.AGENDA)["entries"]
    units = {entry["unit_id"]: entry for entry in agenda}
    pairs: dict[str, dict[str, Mapping[str, Any]]] = {}
    for entry in agenda:
        pairs.setdefault(entry["pair_id"], {})[entry["repetition"]] = entry
    if len(units) != 900 or len(pairs) != 450 or any(set(pair) != {"R1", "R2"} for pair in pairs.values()):
        _fail("agenda pinada fora da topologia 450 pares × R1/R2")

    def expect(entry: Mapping[str, Any]) -> tuple[str, Decimal]:
        position = positions[entry["position_id"]]
        payload = offline.build_request(position, system, (offline.REPO / entry["surface_path"]).read_text(encoding="utf-8"))
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest(), campaign.planned_ceiling(position, payload)

    expected = {unit_id: expect(entry) for unit_id, entry in units.items()}

    intents = _unique(rows["intent"], "intent_id", "intenção")
    attempts = _unique(rows["attempt"], "intent_id", "tentativa")
    if intents.keys() != attempts.keys():
        _fail("intenção e tentativa não são 1:1")
    by_unit: dict[str, list[Mapping[str, Any]]] = {}
    for intent_id, attempt in attempts.items():
        intent = intents[intent_id]
        if intent_id != f"{attempt['unit_id']}|A{attempt['attempt']}" or any(
            intent[key] != attempt[key] for key in ("unit_id", "attempt", "request_sha256", "reserved_usd")
        ):
            _fail(f"intenção e tentativa divergem: {intent_id}")
        if datetime.fromisoformat(attempt["started_at"]) > datetime.fromisoformat(attempt["completed_at"]):
            _fail(f"intervalo de tempo inválido: {intent_id}")
        by_unit.setdefault(attempt["unit_id"], []).append(attempt)

    checkpoints = _unique(rows["checkpoint"], "unit_id", "checkpoint")
    if checkpoints.keys() != by_unit.keys():
        _fail("unidades com tentativa e checkpoints divergem")
    r3_expected: dict[str, Mapping[str, Any]] = {}
    for pair_id, pair in pairs.items():
        first, second = checkpoints.get(pair["R1"]["unit_id"]), checkpoints.get(pair["R2"]["unit_id"])
        if first is None or second is None:
            _fail(f"unidade primária sem desfecho terminal: {pair_id}")
        a1, a2 = _action(first), _action(second)
        if a1 is not None and a2 is not None and a1 != a2:
            entry = dict(pair["R2"], repetition="R3", unit_id=f"{pair_id}|R3")
            r3_expected[entry["unit_id"]] = entry
            expected[entry["unit_id"]] = expect(entry)
    if set(checkpoints) != set(units) | set(r3_expected):
        _fail("universo de unidades terminais divergente da agenda e da regra R3")

    observed = accounted = Decimal(0)
    for unit_id, items in by_unit.items():
        items.sort(key=lambda item: item["attempt"])
        if [item["attempt"] for item in items] != list(range(1, len(items) + 1)) or len(items) > campaign.MAX_ATTEMPTS:
            _fail(f"sequência de tentativas inválida: {unit_id}")
        if any(item["classification"] != campaign.RETRYABLE for item in items[:-1]) or items[-1]["classification"] not in campaign.TERMINAL:
            _fail(f"cadeia de retry inválida: {unit_id}")
        digest, reserve = expected[unit_id]
        entry = units.get(unit_id) or r3_expected[unit_id]
        position = positions[entry["position_id"]]
        identity = identities[entry["position_id"]]
        expected_parameters = _as_record_json(position["requested_parameters"])
        for item in items:
            if item["request_sha256"] != digest or Decimal(item["reserved_usd"]) != reserve:
                _fail(f"request_sha256 ou reserva não reconstruíveis: {item['intent_id']}")
            if intents[item["intent_id"]]["position_id"] != entry["position_id"] or intents[item["intent_id"]]["repetition"] != entry["repetition"]:
                _fail(f"intenção fora da agenda: {item['intent_id']}")
            if not campaign.identical(item["requested_parameters"], expected_parameters):
                _fail(f"parâmetros solicitados divergem da configuração pinada: {item['intent_id']}")
            if not campaign.identical(item["accepted_by_contract"], identity["accepted_by_contract"]) or not campaign.identical(
                item["observed_or_echoed"], identity["observed_or_echoed"]
            ):
                _fail(f"aceite contratual ou eco divergem das identidades pinadas: {item['intent_id']}")
            if str(item["error"] or "").startswith(campaign.IDENTITY_FAILURE_PREFIX):
                _fail(f"campanha concluída contém divergência de identidade: {item['intent_id']}")
            cost = None if item["cost_usd"] is None else Decimal(item["cost_usd"])
            if Decimal(item["accounted_usd"]) != (reserve if cost is None else cost) or (cost is not None and cost > reserve):
                _fail(f"custo contabilizado divergente: {item['intent_id']}")
            valid = item["classification"] == campaign.VALID
            if valid != (item["semantic_action"] is not None):
                _fail(f"ação semântica incoerente com a classificação: {item['intent_id']}")
            if valid and (item["effective_provider"] != identity["effective_provider"] or item["effective_revision"] != identity["effective_revision"]):
                _fail(f"identidade efetiva divergente: {item['intent_id']}")
            _reprocess(position, identity, item)
            observed += cost or Decimal(0)
            accounted += Decimal(item["accounted_usd"])
        last, checkpoint = items[-1], checkpoints[unit_id]
        if (
            checkpoint["attempt"] != last["attempt"]
            or checkpoint["request_sha256"] != last["request_sha256"]
            or checkpoint["state"] != ("OK" if last["classification"] == campaign.VALID else "FAIL")
            or checkpoint["semantic_action"] != last["semantic_action"]
        ):
            _fail(f"checkpoint não reflete a tentativa terminal: {unit_id}")

    results = _unique(rows["result"], "pair_id", "resultado")
    if set(results) != set(pairs):
        _fail("resultados não cobrem exatamente os 450 pares")
    for pair_id, result in results.items():
        pair, base = pairs[pair_id], pairs[pair_id]["R1"]
        r3_unit = f"{pair_id}|R3"
        diagnostic = r3_unit in r3_expected
        if (
            (result["position_id"], result["case_id"], result["condition"]) != (base["position_id"], base["case_id"], base["condition"])
            or result["r1_action"] != _action(checkpoints[pair["R1"]["unit_id"]])
            or result["r2_action"] != _action(checkpoints[pair["R2"]["unit_id"]])
            or result["r3_diagnostic"] is not diagnostic
            or result["r3_action"] != (_action(checkpoints[r3_unit]) if diagnostic else None)
        ):
            _fail(f"resultado não reconstruível: {pair_id}")

    cap = Decimal(str(authorization["external_budget_cap_usd"]))
    if Decimal(closure["cost_observed_usd"]) != observed or Decimal(closure["cost_accounted_usd"]) != accounted or accounted > cap:
        _fail("custo do fechamento divergente ou acima do teto")
    if closure["primary_units_terminal"] != len(units) or closure["r3_units_terminal"] != len(r3_expected) or closure["attempts"] != len(attempts):
        _fail("contagens do fechamento divergem da reconstrução")

    ledger = campaign.load(output / campaign.EXECUTION_MANIFEST)
    campaign.validate_role("execution_manifest", ledger)
    counts = {"pairs": len(pairs), "primary_units": len(units), "r3_units": len(r3_expected), "attempts": len(attempts)}
    if (
        any(ledger[key] != value for key, value in common.items())
        or ledger["files"] != {name: campaign.sha(output / name) for name in campaign.FILES.values()}
        or ledger["counts"] != counts
        or Decimal(ledger["cost_observed_usd"]) != observed
        or Decimal(ledger["cost_accounted_usd"]) != accounted
    ):
        _fail("manifesto de execução divergente")
    return {
        "status": "CHECK_OK", **counts, "sessions": len(closures),
        "cost_observed_usd": campaign.money(observed), "cost_accounted_usd": campaign.money(accounted),
        "execution_manifest_sha256": campaign.sha(output / campaign.EXECUTION_MANIFEST),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.output_root, args.authorization), sort_keys=True))


if __name__ == "__main__":
    main()
