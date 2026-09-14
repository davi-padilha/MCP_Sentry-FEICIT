from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import urllib.error
from decimal import Decimal
from pathlib import Path
from unittest import mock

from . import campaign, preflight_runner, verify_campaign


IDENTITIES = {item["position_id"]: item for item in campaign.load(campaign.IDENTITIES)["positions"]}


def response(position, content, provider=None, revision=None, cost="0.0001"):
    """Corpo no formato real do OpenRouter observado no preflight."""
    identity = IDENTITIES[position["position_id"]]
    model = revision or identity["effective_revision"]
    metadata = {
        "requested": position["requested_model"], "strategy": "direct", "attempt": 1,
        "endpoints": {"available": [{"provider": provider or identity["effective_provider"], "model": model, "selected": True}]},
    }
    if position["transport"] == "openrouter_responses":
        usage = {"input_tokens": 900, "output_tokens": 100, "input_tokens_details": {"cached_tokens": 0}, "cost": Decimal(cost)}
        body = {"model": model, "output": [{"type": "message", "content": [{"type": "output_text", "text": content}]}]}
    else:
        usage = {"prompt_tokens": 900, "completion_tokens": 100, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0}, "cost": Decimal(cost)}
        body = {"model": model, "choices": [{"message": {"content": content}}]}
    body.update(openrouter_metadata=metadata, usage=usage)
    return body, 200, json.dumps(body, default=str)


def semantic(action):
    return json.dumps({"acao": action, "justificativa": "simulação offline"})


class FakeSender:
    """Transporte simulado; `overrides` mapeia o número da chamada a um comportamento."""

    def __init__(self, overrides=None):
        self.calls = 0
        self.overrides = overrides or {}

    def __call__(self, position, payload):
        json.dumps(payload, ensure_ascii=False)  # o envelope real tem de ser serializável
        self.calls += 1
        behavior = self.overrides.get(self.calls, "bloquear")
        if callable(behavior):
            return behavior(position)
        return response(position, semantic(behavior))


def http_error(status):
    def behavior(position):
        raise preflight_runner.RemoteResponseError(f"preflight HTTP {status}", status, "{}")
    return behavior


def timeout(position):
    raise preflight_runner.GateError("preflight sem conexão") from urllib.error.URLError(TimeoutError("timed out"))


def non_json(position):
    raise preflight_runner.RemoteResponseError("preflight HTTP 2xx com corpo não-JSON", 200, "not-json")


def write_authorization(path: Path, cap="14", run_id="m2_3_extension_campaign_simulation", **changes):
    value = {
        "schema_version": "m2_3_extension_campaign_authorization_v1", "recorded": True, "run_id": run_id,
        "approved_at": "2026-09-11T00:00:00Z", "approved_by": "test-only", "approved_commit": "0" * 40,
        "snapshot_id": campaign.SNAPSHOT_ID, "snapshot_sha256": campaign.sha(campaign.MANIFEST),
        "positions": campaign.POSITIONS, "external_budget_cap_usd": float(cap) if "." in cap else int(cap),
        "execution_capability": "real_transport", "execution_authorized": True,
        "preflight_execution_authorized": False, "official_campaign_authorized": True,
        "authorization_statement": campaign.AUTH_STATEMENT,
    }
    value.update(changes)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def git_status() -> str:
    return subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=campaign.REPO, capture_output=True, text=True, check=True).stdout


class CampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment = mock.patch.dict(os.environ, {}, clear=False)
        cls.environment.start()
        os.environ.pop("OPENROUTER_API_KEY", None)
        cls.shared = tempfile.TemporaryDirectory()
        root = Path(cls.shared.name)
        cls.authorization = root / "authorization.json"
        write_authorization(cls.authorization)
        cls.status_before = git_status()
        cls.complete = root / "complete"
        cls.sender = FakeSender()
        cls.run_status = campaign.run(cls.authorization, cls.complete, cls.sender, False, lambda _: None)

    @classmethod
    def tearDownClass(cls):
        cls.shared.cleanup()
        cls.environment.stop()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def run_campaign(self, sender, output=None, authorization=None):
        sleeps = []
        output = output or self.root / "output"
        campaign.run(authorization or self.authorization, output, sender, False, sleeps.append)
        return output, sleeps

    def copy_complete(self) -> Path:
        target = self.root / "copy"
        shutil.copytree(self.complete, target)
        return target

    def rewrite(self, output: Path, name: str, change):
        """Adultera um arquivo e re-hasheia o manifesto de execução (ataque coerente)."""
        path = output / name
        rows = campaign.read_jsonl(path)
        change(rows)
        path.write_bytes(b"".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8") + b"\n" for row in rows))
        ledger_path = output / campaign.EXECUTION_MANIFEST
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        ledger["files"][name] = campaign.sha(path)
        ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def truncated(self, attempts: int, checkpoints: int, intents: int | None = None) -> Path:
        target = self.root / "partial"
        target.mkdir()
        keep = {"intencoes.jsonl": intents if intents is not None else attempts, "tentativas.jsonl": attempts, "checkpoints.jsonl": checkpoints}
        kept_units = {row["unit_id"] for row in campaign.read_jsonl(self.complete / "checkpoints.jsonl")[:checkpoints]}
        for name, count in keep.items():
            lines = (self.complete / name).read_bytes().split(b"\n")[:count]
            (target / name).write_bytes(b"".join(line + b"\n" for line in lines))
        results = [row for row in campaign.read_jsonl(self.complete / "resultados.jsonl") if f"{row['pair_id']}|R1" in kept_units and f"{row['pair_id']}|R2" in kept_units]
        (target / "resultados.jsonl").write_bytes(b"".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n" for row in results))
        return target

    # Pacote ready e pins.

    def test_ready_pins_source_set_and_counts(self):
        manifest = campaign.validate_ready()
        self.assertEqual(campaign.READY_STATUS, manifest["status"])
        self.assertFalse(any(manifest["gates"].values()))
        pinned = {item["path"] for item in manifest["pinned_artifacts"]}
        self.assertTrue(campaign.EXECUTABLE_SOURCES <= pinned)

    def test_ready_rejects_tampered_pin_and_incomplete_source_set(self):
        manifest = json.loads(campaign.MANIFEST.read_text(encoding="utf-8"))
        manifest["pinned_artifacts"][0]["sha256"] = "0" * 64
        tampered = self.root / "manifesto.json"
        tampered.write_text(json.dumps(manifest), encoding="utf-8")
        with mock.patch.object(campaign, "MANIFEST", tampered):
            with self.assertRaisesRegex(campaign.GateError, "pin divergente"):
                campaign.validate_ready()
        source_set = json.loads(campaign.SOURCE_SET.read_text(encoding="utf-8"))
        source_set["executable_sources"] = [item for item in source_set["executable_sources"] if not item["path"].endswith("offline.py")]
        partial = self.root / "source_set.json"
        partial.write_text(json.dumps(source_set), encoding="utf-8")
        with mock.patch.object(campaign, "SOURCE_SET", partial):
            with self.assertRaisesRegex(campaign.GateError, "source-set"):
                campaign.validate_ready()

    # Simulação integral e consumidor.

    def test_full_simulation_check_ok_without_repository_writes(self):
        self.assertEqual(campaign.COMPLETE, self.run_status)
        self.assertEqual(900, self.sender.calls)
        checked = verify_campaign.check(self.complete, self.authorization)
        self.assertEqual("CHECK_OK", checked["status"])
        self.assertEqual((450, 900, 0, 900, 1), (checked["pairs"], checked["primary_units"], checked["r3_units"], checked["attempts"], checked["sessions"]))
        self.assertEqual(self.status_before, git_status())
        self.assertFalse((self.complete / campaign.LOCK).exists())
        conditions = {(row["position_id"], row["condition"]) for row in campaign.read_jsonl(self.complete / "resultados.jsonl")}
        self.assertEqual({(position, condition) for position in campaign.POSITIONS for condition in ("C1", "C2", "D")}, conditions)
        for name in (*campaign.FILES.values(), campaign.EXECUTION_MANIFEST):
            self.assertNotIn(b"Bearer ", (self.complete / name).read_bytes())

    def test_completed_campaign_refuses_rerun(self):
        output = self.copy_complete()
        with self.assertRaisesRegex(campaign.GateError, "já concluída"):
            campaign.run(self.authorization, output, FakeSender(), False, lambda _: None)

    def test_r3_only_under_valid_divergence(self):
        # Chamadas 1-3: par 1 diverge e ganha R3. Chamadas 4-5: par 2 com R1 inválido não ganha R3.
        sender = FakeSender({1: "bloquear", 2: "permitir", 3: "inconclusiva", 4: lambda p: response(p, semantic("talvez")), 5: "permitir"})
        output, _ = self.run_campaign(sender)
        self.assertEqual(901, sender.calls)
        checked = verify_campaign.check(output, self.authorization)
        self.assertEqual(1, checked["r3_units"])
        first, second = campaign.read_jsonl(output / "resultados.jsonl")[:2]
        self.assertEqual(("bloquear", "permitir", "inconclusiva", True), (first["r1_action"], first["r2_action"], first["r3_action"], first["r3_diagnostic"]))
        self.assertEqual((None, "permitir", None, False), (second["r1_action"], second["r2_action"], second["r3_action"], second["r3_diagnostic"]))

    def test_recoverable_transport_retries_with_pessimistic_accounting(self):
        sender = FakeSender({1: http_error(503), 2: timeout})
        output, sleeps = self.run_campaign(sender)
        self.assertEqual([10, 30], sleeps)
        attempts = [row for row in campaign.read_jsonl(output / "tentativas.jsonl") if row["attempt"] > 1 or row["classification"] != campaign.VALID]
        self.assertEqual([campaign.RETRYABLE, campaign.RETRYABLE, campaign.VALID], [row["classification"] for row in attempts])
        self.assertEqual([None, None], [row["cost_usd"] for row in attempts[:2]])
        self.assertEqual(attempts[0]["reserved_usd"], attempts[0]["accounted_usd"])
        self.assertEqual("CHECK_OK", verify_campaign.check(output, self.authorization)["status"])

    def test_third_transport_failure_is_terminal(self):
        sender = FakeSender({1: http_error(500), 2: http_error(502), 3: http_error(503)})
        output, _ = self.run_campaign(sender)
        checkpoint = campaign.read_jsonl(output / "checkpoints.jsonl")[0]
        self.assertEqual(("FAIL", 3), (checkpoint["state"], checkpoint["attempt"]))
        self.assertEqual("CHECK_OK", verify_campaign.check(output, self.authorization)["status"])

    def test_response_failures_are_terminal_and_campaign_continues(self):
        sender = FakeSender({1: non_json, 3: lambda p: response(p, "Não posso ajudar com isso.")})
        output, _ = self.run_campaign(sender)
        self.assertEqual(900, sender.calls)
        failures = [row for row in campaign.read_jsonl(output / "tentativas.jsonl") if row["classification"] == campaign.SEMANTIC_FAILURE]
        self.assertEqual(2, len(failures))
        self.assertTrue(all(row["semantic_action"] is None for row in failures))
        self.assertEqual(0, verify_campaign.check(output, self.authorization)["r3_units"])

    def test_identity_divergence_stops_campaign_and_blocks_resume(self):
        # Herdado do runner original: persiste, faz checkpoint e interrompe.
        for label, behavior in (
            ("provedor", lambda p: response(p, semantic("bloquear"), provider="Azure")),
            ("revisão", lambda p: response(p, semantic("bloquear"), revision=p["requested_model"] + "-20990101")),
        ):
            with self.subTest(label):
                output = self.root / f"identity-{label}"
                sender = FakeSender({1: behavior})
                with self.assertRaisesRegex(campaign.GateError, "identidade efetiva divergente"):
                    self.run_campaign(sender, output)
                self.assertEqual(1, sender.calls)
                attempt = campaign.read_jsonl(output / "tentativas.jsonl")[0]
                self.assertEqual(campaign.SEMANTIC_FAILURE, attempt["classification"])
                self.assertTrue(attempt["error"].startswith(campaign.IDENTITY_FAILURE_PREFIX))
                self.assertEqual("FAIL", campaign.read_jsonl(output / "checkpoints.jsonl")[0]["state"])
                self.assertEqual(campaign.ABORTED, campaign.read_jsonl(output / "fechamento.jsonl")[-1]["status"])
                with self.assertRaisesRegex(campaign.GateError, "decisão humana"):
                    self.run_campaign(FakeSender(), output)

    def test_systemic_http_stops_and_resume_completes(self):
        output = self.root / "output"
        with self.assertRaisesRegex(campaign.GateError, "sistêmica HTTP 401"):
            self.run_campaign(FakeSender({1: http_error(401)}), output)
        self.assertEqual(campaign.ABORTED, campaign.read_jsonl(output / "fechamento.jsonl")[-1]["status"])
        resumed = FakeSender()
        self.run_campaign(resumed, output)
        self.assertEqual(899, resumed.calls)
        checked = verify_campaign.check(output, self.authorization)
        self.assertEqual(2, checked["sessions"])

    def test_resume_recovers_terminal_attempt_without_new_call(self):
        output = self.truncated(attempts=10, checkpoints=9)
        resumed = FakeSender()
        self.run_campaign(resumed, output)
        self.assertEqual(890, resumed.calls)
        self.assertEqual("CHECK_OK", verify_campaign.check(output, self.authorization)["status"])

    def test_orphan_intent_blocks_resume(self):
        output = self.truncated(attempts=9, checkpoints=9, intents=10)
        with self.assertRaisesRegex(campaign.GateError, "intenção órfã"):
            self.run_campaign(FakeSender(), output)

    def test_resume_requires_same_authorization(self):
        output = self.truncated(attempts=10, checkpoints=10)
        other = self.root / "other.json"
        write_authorization(other, run_id="m2_3_extension_campaign_other")
        with self.assertRaisesRegex(campaign.GateError, "outra autorização"):
            self.run_campaign(FakeSender(), output, other)

    def test_existing_lock_blocks(self):
        output = self.root / "output"
        output.mkdir()
        (output / campaign.LOCK).write_text("x", encoding="ascii")
        with self.assertRaisesRegex(campaign.GateError, "lock existente"):
            self.run_campaign(FakeSender(), output)

    # Dinheiro.

    def test_cumulative_cap_blocks_before_first_call(self):
        capped = self.root / "capped.json"
        write_authorization(capped, cap="0.0001")
        sender = FakeSender()
        with self.assertRaisesRegex(campaign.GateError, "teto impede"):
            self.run_campaign(sender, authorization=capped)
        self.assertEqual(0, sender.calls)
        self.assertEqual([], campaign.read_jsonl(self.root / "output" / "intencoes.jsonl"))

    def test_cost_above_ceiling_aborts_and_blocks_resume(self):
        output = self.root / "output"
        with self.assertRaisesRegex(campaign.GateError, "violação de custo"):
            self.run_campaign(FakeSender({1: lambda p: response(p, semantic("bloquear"), cost="1.00")}), output)
        self.assertEqual(campaign.COST_VIOLATION, campaign.read_jsonl(output / "tentativas.jsonl")[0]["classification"])
        with self.assertRaisesRegex(campaign.GateError, "decisão humana"):
            self.run_campaign(FakeSender(), output)

    # Autorização.

    def test_authorization_rejections(self):
        output = self.root / "output"
        cases = {
            "cap_above": {"cap": "14.01"}, "cap_zero": {"cap": "0"},
            "not_authorized": {"execution_authorized": False}, "bool_laundering": {"execution_authorized": 1},
            "preflight_open": {"preflight_execution_authorized": True}, "other_snapshot": {"snapshot_sha256": "0" * 64},
            "statement": {"authorization_statement": "ok"}, "extra": {"extra": True},
        }
        for label, changes in cases.items():
            with self.subTest(label):
                path = self.root / f"{label}.json"
                write_authorization(path, **changes)
                with self.assertRaises(campaign.GateError):
                    campaign.validate_authorization(path, output, False)
        with self.assertRaisesRegex(campaign.GateError, "fora do repositório"):
            campaign.validate_authorization(self.authorization, campaign.REPO / "saida", False)
        with self.assertRaisesRegex(campaign.GateError, "absolutos"):
            campaign.validate_authorization(Path("authorization.json"), output, False)
        with self.assertRaisesRegex(campaign.GateError, "dentro da saída"):
            campaign.validate_authorization(self.authorization, self.authorization.parent, False)

    def test_real_mode_requires_canonical_output_and_approved_commit(self):
        with self.assertRaisesRegex(campaign.GateError, "diretório canônico"):
            campaign.validate_authorization(self.authorization, self.root / "output", True)
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)}):
            canonical = self.root / "MCP-Sentry" / "m2_3_extension_campaign" / "m2_3_extension_campaign_simulation"
            with self.assertRaisesRegex(campaign.GateError, "approved_commit"):
                campaign.validate_authorization(self.authorization, canonical, True)

    def test_simulation_refuses_present_credential(self):
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-only"}):
            with self.assertRaisesRegex(campaign.GateError, "credencial|OPENROUTER_API_KEY"):
                self.run_campaign(FakeSender())

    # Consumidor contra adulterações coerentemente re-hasheadas.

    def forge_raw_response(self, rows):
        """Troca ação, custo e provedor dentro do corpo bruto da primeira tentativa."""
        row = rows[0]
        body = json.loads(row["raw_response"])
        body["output"][0]["content"][0]["text"] = json.dumps({"acao": "permitir", "justificativa": "corpo forjado"})
        body["usage"]["cost"] = "9.99"
        body["openrouter_metadata"]["endpoints"]["available"][0]["provider"] = "Azure"
        row["raw_response"] = json.dumps(body)

    def test_verifier_rejects_coherent_tampering(self):
        attacks = {
            "result_action": ("resultados.jsonl", lambda rows: rows[0].update(r1_action="permitir")),
            "dropped_checkpoint": ("checkpoints.jsonl", lambda rows: rows.pop()),
            "closure_cost": ("fechamento.jsonl", lambda rows: rows[-1].update(cost_accounted_usd="0")),
            "attempt_request": ("tentativas.jsonl", lambda rows: rows[0].update(request_sha256="0" * 64)),
            "attempt_revision": ("tentativas.jsonl", lambda rows: rows[0].update(effective_revision="openai/gpt-5.6-luna-20990101")),
            "duplicated_result": ("resultados.jsonl", lambda rows: rows.append(dict(rows[0]))),
            # Os quatro achados P0 da verificação independente de 2026-09-11.
            "requested_parameters": ("tentativas.jsonl", lambda rows: rows[0].update(requested_parameters={"max_output_tokens": 1, "reasoning": {"effort": "low"}})),
            "accepted_by_contract": ("tentativas.jsonl", lambda rows: rows[0].update(accepted_by_contract={"max_output_tokens": 99})),
            "observed_or_echoed": ("tentativas.jsonl", lambda rows: rows[0].update(observed_or_echoed={"effective_provider": False, "effective_revision": False, "reasoning_effort": True})),
            "raw_response": ("tentativas.jsonl", lambda rows: None),
        }
        for label, (name, change) in attacks.items():
            with self.subTest(label):
                output = self.copy_complete()
                self.rewrite(output, name, self.forge_raw_response if label == "raw_response" else change)
                with self.assertRaises(campaign.GateError):
                    verify_campaign.check(output, self.authorization)
                shutil.rmtree(output)

    def rewrite_first_attempt(self, output: Path, change):
        self.rewrite(output, "tentativas.jsonl", lambda rows: change(rows[0]))

    def test_verifier_rejects_failure_registered_over_valid_body(self):
        output = self.copy_complete()

        def downgrade(row):
            row["classification"] = campaign.SEMANTIC_FAILURE
            row["semantic_action"] = None
            row["error"] = "schema semântico inválido no preflight"

        self.rewrite_first_attempt(output, downgrade)
        with self.assertRaises(campaign.GateError):
            verify_campaign.check(output, self.authorization)

    def test_verifier_rejects_identity_failure_inside_complete_campaign(self):
        output = self.copy_complete()
        self.rewrite_first_attempt(output, lambda row: row.update(error=campaign.IDENTITY_FAILURE_PREFIX + " forjado"))
        with self.assertRaisesRegex(campaign.GateError, "divergência de identidade"):
            verify_campaign.check(output, self.authorization)

    def test_verifier_rejects_truncated_campaign_even_if_closed_complete(self):
        output = self.truncated(attempts=10, checkpoints=10)
        closure = campaign.read_jsonl(self.complete / "fechamento.jsonl")[0]
        (output / "fechamento.jsonl").write_bytes(json.dumps(closure, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
        shutil.copy(self.complete / campaign.EXECUTION_MANIFEST, output / campaign.EXECUTION_MANIFEST)
        with self.assertRaises(campaign.GateError):
            verify_campaign.check(output, self.authorization)

    # Launcher.

    def test_launcher_keeps_credential_out_of_parent_environment(self):
        text = (campaign.REPO / "tools/m2_3_extensao_multimodelo_v1/campaign_visible.ps1").read_text(encoding="utf-8")
        self.assertIn("-AsSecureString", text)
        self.assertIn("ZeroFreeBSTR", text)
        self.assertIn("$startInfo.Environment['OPENROUTER_API_KEY']", text)
        self.assertNotIn("$env:OPENROUTER_API_KEY =", text)
        self.assertIn("Remove-Item Env:\\OPENROUTER_API_KEY", text.split("finally", 1)[1])


if __name__ == "__main__":
    unittest.main()
