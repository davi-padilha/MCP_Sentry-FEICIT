from __future__ import annotations

import json
import unittest
import tempfile
from decimal import Decimal
from pathlib import Path
from unittest import mock

from . import offline, prepare, verificacao_antes_da_execucao as preflight_runner


class ExtensionOfflineTests(unittest.TestCase):
    def test_counts_and_closed_gates(self) -> None:
        manifest, config, agenda = offline.validate()
        self.assertEqual(900, len(agenda["entries"]))
        self.assertEqual(3, len(config["positions"]))
        self.assertFalse(any(manifest["gates"].values()))

    def test_all_conditions_and_repetitions(self) -> None:
        _, _, agenda = offline.validate()
        self.assertEqual({"C1", "C2", "D"}, {x["condition"] for x in agenda["entries"]})
        self.assertEqual({"R1", "R2"}, {x["repetition"] for x in agenda["entries"]})

    def test_envelopes_omit_sampling_and_tools(self) -> None:
        for position in prepare.POSITIONS:
            payload = offline.build_request(position, "system", "evidence")
            self.assertNotIn("temperature", payload)
            self.assertNotIn("top_p", payload)
            self.assertNotIn("tools", payload)
            self.assertFalse(payload["provider"]["allow_fallbacks"])
            self.assertEqual([position["provider_slug"]], payload["provider"]["only"])

    def test_reasoning_levels(self) -> None:
        levels = {
            position["position_id"]: position["requested_parameters"]["reasoning"]["effort"]
            for position in prepare.POSITIONS
        }
        self.assertEqual("high", levels["remote-gpt-5-6-luna-high-openai"])
        self.assertEqual("medium", levels["remote-gpt-5-6-sol-medium-openai"])
        self.assertEqual("medium", levels["remote-claude-opus-5-medium-anthropic"])

    def test_real_package_reaches_transport_with_serializable_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authorization_path = root / "authorization.json"
            output_root = root / "output"
            authorization_path.write_text(json.dumps({
                "schema_version": "m2_3_extension_preflight_authorization_v1",
                "run_id": "m2_3_extension_preflight_serialization_test",
                "extension_manifest_sha256": preflight_runner._manifest_hash(),
                "human_preflight_authorized": True,
                "cost_cap_usd": "0.25",
                "authorized_positions": [item["position_id"] for item in prepare.POSITIONS],
                "authorized_conditions": ["C1", "C2", "D"],
            }), encoding="utf-8")
            with mock.patch.object(
                preflight_runner, "_send", side_effect=preflight_runner.GateError("transport sentinel")
            ) as send:
                with self.assertRaisesRegex(preflight_runner.GateError, "transport sentinel"):
                    preflight_runner.run(authorization_path, output_root)
            self.assertEqual(1, send.call_count)
            self.assertTrue((output_root / "intencoes_preflight.jsonl").is_file())

    def test_preflight_rejects_authorization_without_human_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authorization = {
                "schema_version": "m2_3_extension_preflight_authorization_v1",
                "run_id": "m2_3_extension_preflight_test",
                "extension_manifest_sha256": preflight_runner._manifest_hash(),
                "human_preflight_authorized": False,
                "cost_cap_usd": "0.25",
                "authorized_positions": [item["position_id"] for item in prepare.POSITIONS],
                "authorized_conditions": ["C1", "C2", "D"],
            }
            with self.assertRaises(preflight_runner.GateError):
                preflight_runner.validate_authorization(authorization, root / "authorization.json", root / "output")

    def test_preflight_accepts_single_pinned_provider_and_schema_content(self) -> None:
        position = prepare.POSITIONS[0]
        body = {
            "output": [{"type": "message", "content": [{
                "type": "output_text", "text": '{"acao":"bloquear","justificativa":"teste"}'
            }]}],
            "openrouter_metadata": {
                "requested": position["requested_model"],
                "endpoints": {"available": [{
                    "provider": "OpenAI", "model": position["requested_model"], "selected": True
                }]},
                "attempts": [{"provider": "OpenAI", "model": position["requested_model"], "status": 200}],
            },
            "model": position["requested_model"],
        }
        content, selected = preflight_runner._content_and_route(position, body)
        self.assertEqual('{"acao":"bloquear","justificativa":"teste"}', content)
        self.assertEqual("OpenAI", selected["provider"])

    def test_preflight_rejects_provider_fallback_metadata(self) -> None:
        position = prepare.POSITIONS[2]
        body = {
            "choices": [{"message": {"content": '{"acao":"permitir","justificativa":"teste"}'}}],
            "model": position["requested_model"],
            "openrouter_metadata": {
                "requested": position["requested_model"],
                "endpoints": {"available": [{"provider": "Anthropic", "model": position["requested_model"], "selected": True}]},
                "attempts": [
                    {"provider": "OpenAI", "status": 500},
                    {"provider": "Anthropic", "status": 200},
                ],
            },
        }
        with self.assertRaises(preflight_runner.GateError):
            preflight_runner._content_and_route(position, body)

    def test_preflight_rejects_effective_model_mismatch(self) -> None:
        position = prepare.POSITIONS[1]
        body = {
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "{}"}]}],
            "model": "openai/gpt-5.6-luna",
            "openrouter_metadata": {
                "requested": position["requested_model"],
                "endpoints": {"available": [{"provider": "OpenAI", "model": "openai/gpt-5.6-luna", "selected": True}]},
                "attempts": [{"provider": "OpenAI", "model": "openai/gpt-5.6-luna", "status": 200}],
            },
        }
        with self.assertRaises(preflight_runner.GateError):
            preflight_runner._content_and_route(position, body)

    def test_preflight_cost_rejects_observed_price_above_ceiling(self) -> None:
        position = prepare.POSITIONS[0]
        body = {"usage": {"prompt_tokens": 100, "completion_tokens": 10, "cost": "1.00"}}
        with self.assertRaises(preflight_runner.GateError):
            preflight_runner._observed_cost_within_ceiling(position, body)

    def test_preflight_accepts_observed_openai_cache_write_price(self) -> None:
        position = prepare.POSITIONS[0]
        body = {"usage": {
            "input_tokens": 1094,
            "output_tokens": 122,
            "cost": "0.00041975",
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 1091},
        }}
        self.assertEqual(
            Decimal("0.00041975"),
            preflight_runner._observed_cost_within_ceiling(position, body),
        )

    def test_preflight_schema_enforces_justification_length(self) -> None:
        with self.assertRaises(preflight_runner.GateError):
            preflight_runner._validate_semantic_schema('{"acao":"bloquear","justificativa":""}')
        with self.assertRaises(preflight_runner.GateError):
            preflight_runner._validate_semantic_schema('{"acao":"bloquear","justificativa":"' + "x" * 801 + '"}')

    def test_preflight_preserves_2xx_non_json_body_for_failure_ledger(self) -> None:
        response = mock.MagicMock()
        response.status = 200
        response.read.return_value = b"not-json-response"
        response.__enter__.return_value = response
        with mock.patch.object(preflight_runner.os, "environ", {"OPENROUTER_API_KEY": "test-only"}):
            with mock.patch("urllib.request.urlopen", return_value=response):
                with self.assertRaises(preflight_runner.RemoteResponseError) as captured:
                    preflight_runner._send(prepare.POSITIONS[0], {"model": "test"})
        self.assertEqual(200, captured.exception.status)
        self.assertEqual("not-json-response", captured.exception.raw_response)


if __name__ == "__main__":
    unittest.main()
