"""Regression tests for pilot profiles, transport and operator decisions."""
import json
import sys
import unittest
from pathlib import Path

import test_gateway_universal as fixtures
from mcp_sentry_gateway.core import SentryError, approve, capture, canon, digest, inspect
from mcp_sentry_gateway.gateway import StdioGateway
from mcp_sentry_gateway.operator import decide
from mcp_sentry_gateway.profiles import installed_plan
from mcp_sentry_gateway.review import ensure_pending, submit_verdict
from mcp_sentry_gateway.setup import _portable_backend_command, _suggest_inspection


SERVER_SOURCE = fixtures.SERVER_SOURCE


class UpdateTests(unittest.TestCase):
    setUp = fixtures.UniversalGatewayTests.setUp
    save_manifest = fixtures.UniversalGatewayTests.save_manifest
    request = staticmethod(fixtures.UniversalGatewayTests.request)
    def allow(self):
        record, _ = ensure_pending(self.manifest, self.state)
        dossier = record["dossier"]
        submit_verdict(self.manifest, self.state, {
            "review_id": record["review_id"], "reviewed_hash": dossier["current_hash"],
            "dossier_hash": dossier["dossier_hash"], "policy_version": record["policy_version"],
            "decision": "allow", "justification": "fixture: expected local update", "risks": [],
        })

    def change(self, source=None):
        (self.project / "server.py").write_text(source or SERVER_SOURCE + "\n# update\n", encoding="utf-8")

    def call(self):
        gateway = StdioGateway(self.manifest, self.state, interface="execution")
        self.addCleanup(gateway.backend.close)
        return gateway, gateway.handle(self.request(3, "tools/call", {"name": "echo", "arguments": {"value": "ok"}}))

    def test_notifications_interleaved_in_every_exchange(self):
        self.change(SERVER_SOURCE.replace('    if "id" in request:',
            '    if "id" in request:\n        print(json.dumps({"jsonrpc":"2.0", "method":"notifications/message", "params":{"level":"info", "data":"notice"}}), flush=True)'))
        approve(self.manifest, self.state)
        gateway, response = self.call()
        self.assertEqual(response["result"]["content"][0]["text"], "ok")
        self.assertEqual(gateway.backend.backend_protocol_version, "2025-06-18")

    def test_wrong_response_id_closes_backend(self):
        self.change(SERVER_SOURCE.replace('"id": request["id"]', '"id": "wrong"'))
        approve(self.manifest, self.state)
        gateway, response = self.call()
        self.assertIn("identificador inesperado", json.dumps(response))
        self.assertIsNone(gateway.backend.process)

    def test_supported_protocol_negotiation_and_rejection(self):
        for protocol in ("2025-03-26", "2099-01-01"):
            with self.subTest(protocol=protocol):
                self.change(SERVER_SOURCE.replace('"protocolVersion": "2025-06-18"', f'"protocolVersion": "{protocol}"'))
                # Each subcase has independent trusted state.
                self.state = self.temp / protocol
                approve(self.manifest, self.state)
                gateway, response = self.call()
                if protocol == "2025-03-26":
                    self.assertEqual(gateway.backend.backend_protocol_version, protocol)
                    self.assertEqual(response["result"]["content"][0]["text"], "ok")
                else:
                    self.assertIn("versão MCP suportada", json.dumps(response, ensure_ascii=False))
                    self.assertIsNone(gateway.backend.process)
                gateway.backend.close()

    def test_generated_review_interface_name_is_returned(self):
        self.manifest_data["metadata"]["review_interface"] = "mcp_sentry_review_example"
        self.save_manifest()
        approve(self.manifest, self.state)
        self.change()
        _, response = self.call()
        self.assertEqual(response["result"]["structuredContent"]["review_interface"], "mcp_sentry_review_example")

    def test_operator_accept_is_bound_to_displayed_version(self):
        approve(self.manifest, self.state)
        self.change()
        self.allow()
        def changed_during_prompt():
            self.change(SERVER_SOURCE + "\n# second update\n")
            return "ACEITAR"
        with self.assertRaisesRegex(SentryError, "mudou"):
            decide(self.manifest, self.state, "accept", input_fn=changed_during_prompt, output=lambda _: None)
        self.assertEqual(inspect(self.manifest, self.state)["status"], "review_required")

    def test_operator_once_does_not_promote_baseline(self):
        approve(self.manifest, self.state)
        self.change()
        self.allow()
        result = decide(self.manifest, self.state, "once", input_fn=lambda: "AUTORIZAR", output=lambda _: None)
        self.assertEqual(result["status"], "allowed_once")
        gateway, response = self.call()
        self.assertEqual(response["result"]["content"][0]["text"], "ok")
        gateway.backend.close()
        second, blocked = self.call()
        self.assertEqual(second.backend.lifecycle.snapshot()["spawn_attempts"], 0)
        self.assertIn("blocked", json.dumps(blocked))

    def test_catalog_requires_code_review_then_new_combined_review(self):
        approve(self.manifest, self.state)
        self.change(SERVER_SOURCE.replace("Echo a value", "New description"))
        self.allow()
        replies = iter(["DESCOBRIR", "APLICAR_CATALOGO"])
        result = decide(self.manifest, self.state, "catalog", input_fn=lambda: next(replies), output=lambda _: None)
        self.assertEqual(result["status"], "catalog_applied_review_required")
        self.assertEqual(inspect(self.manifest, self.state)["status"], "review_required")
        with self.assertRaisesRegex(SentryError, "parecer"):
            decide(self.manifest, self.state, "accept", input_fn=lambda: "ACEITAR", output=lambda _: None)
        self.allow()
        decide(self.manifest, self.state, "accept", input_fn=lambda: "ACEITAR", output=lambda _: None)
        gateway, response = self.call()
        self.assertEqual(response["result"]["content"][0]["text"], "ok")
        gateway.backend.close()
        self.assertFalse(any((self.state / "copias-verificadas").iterdir()))

    def test_catalog_cancel_does_not_spawn(self):
        approve(self.manifest, self.state)
        self.change()
        self.allow()
        before = digest(canon(capture(self.manifest)))
        result = decide(self.manifest, self.state, "catalog", input_fn=lambda: "", output=lambda _: None)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(digest(canon(capture(self.manifest))), before)
        self.assertFalse((self.state / "copias-verificadas").exists())

    def test_unchanged_catalog_preserves_existing_review(self):
        approve(self.manifest, self.state)
        self.change()
        self.allow()
        before = digest(canon(capture(self.manifest)))
        result = decide(self.manifest, self.state, "catalog", input_fn=lambda: "DESCOBRIR", output=lambda _: None)
        self.assertEqual(result["status"], "catalog_unchanged")
        self.assertEqual(digest(canon(capture(self.manifest))), before)
        decide(self.manifest, self.state, "accept", input_fn=lambda: "ACEITAR", output=lambda _: None)
        self.assertEqual(inspect(self.manifest, self.state)["status"], "unchanged")

    def test_module_profile_copies_package_and_ignores_cache(self):
        package = self.project / "mcp_server_git"
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "__main__.py").write_text(SERVER_SOURCE, encoding="utf-8")
        (package / "__pycache__").mkdir()
        (package / "__pycache__/ignored.pyc").write_bytes(b"mutable")
        dist = self.project / "mcp_server_git-1.2.3.dist-info"
        dist.mkdir()
        (dist / "METADATA").write_text("Name: mcp-server-git\nVersion: 1.2.3\n", encoding="utf-8")
        data = self.temp / "data"
        data.mkdir()
        roots, command = installed_plan("git", self.project, Path(sys.executable), "1.2.3", data)
        self.manifest_data["inspect_roots"] = roots
        self.manifest_data["configuration"]["command"] = command
        self.save_manifest()
        approve(self.manifest, self.state)
        gateway, response = self.call()
        self.assertEqual(response["result"]["content"][0]["text"], "ok")
        self.assertTrue((gateway.backend.copy_root / "mcp_server_git/__main__.py").is_file())
        self.assertFalse((gateway.backend.copy_root / "mcp_server_git/__pycache__").exists())
        (package / "added.py").write_text("# added", encoding="utf-8")
        self.assertEqual(inspect(self.manifest, self.state)["status"], "review_required")
        with self.assertRaisesRegex(SentryError, "versão exata"):
            installed_plan("git", self.project, Path(sys.executable), "9.9.9", data)

    def test_setup_local_python_module(self):
        module = self.project / "example"
        module.mkdir()
        (module / "__init__.py").write_text("", encoding="utf-8")
        (module / "__main__.py").write_text(SERVER_SOURCE, encoding="utf-8")
        command = [sys.executable, "-m", "example"]
        self.assertIn("example", _suggest_inspection(command, self.project))
        self.assertIn("-B", _portable_backend_command(command, self.project))

    def test_module_cannot_fall_back_to_installed_code(self):
        self.manifest_data["configuration"]["command"] = [sys.executable, "-m", "mcp_sentry_gateway.cli"]
        self.save_manifest()
        approve(self.manifest, self.state)
        gateway, response = self.call()
        self.assertIn("cópia verificada", json.dumps(response, ensure_ascii=False))
        self.assertEqual(gateway.backend.lifecycle.snapshot()["spawn_attempts"], 0)

    def test_package_manager_is_rejected_before_approval(self):
        self.manifest_data["configuration"]["command"] = ["npx", "@modelcontextprotocol/server-filesystem"]
        self.save_manifest()
        with self.assertRaisesRegex(SentryError, "gerenciador"):
            approve(self.manifest, self.state)
