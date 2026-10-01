"""Explicit client-review fixtures; no gateway-initiated model evaluation."""
import json
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / "codigo_gateway"))
from mcp_sentry_gateway.core import approve
from mcp_sentry_gateway.gateway import StdioGateway
from mcp_sentry_gateway.review import security_status
from mcp_sentry_gateway.core import APPROVED_VERSION_FILE

EXAMPLE = Path(__file__).parents[1] / "exemplo_mcp"


class ClientReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sentry-client-review-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.project = root / "project"
        shutil.copytree(EXAMPLE, self.project)
        self.manifest, self.store = self.project / "manifest.json", root / "store"
        approve(self.manifest, self.store)
        self.project.joinpath("server.py").write_text("# changed implementation\n", encoding="utf-8")
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["metadata"]["revision_note"] = "changed metadata"
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        self.gateway = StdioGateway(self.manifest, self.store)
        self.addCleanup(self.gateway.backend.close)

    def call(self, name="ping", arguments=None):
        return self.gateway.handle({"jsonrpc": "2.0", "id": 99, "method": "tools/call", "params": {"name": name, "arguments": arguments or {}}})["result"]

    def read_all_evidence(self, review_id):
        page = 1
        first = None
        while True:
            evidence = self.call("sentry_review_evidence", {"review_id": review_id, "page": page, "page_size": 1})["structuredContent"]
            first = first or evidence
            if not evidence["has_more"]:
                return first
            page = evidence["next_page"]

    def test_changed_donna_call_is_neutral_and_never_requests_an_automatic_review(self):
        result = self.call()["structuredContent"]
        self.assertEqual(result["status"], "security_review_required")
        self.assertTrue(result["review_required"])
        self.assertFalse(result["action_executed"])
        self.assertEqual(result["semantic_review_status"], "not_evaluated")
        self.assertEqual(result["review_interface"], "mcp_sentry_review")
        self.assertEqual(result["review_capability"], "read_only_evidence")
        self.assertNotIn("assessment", result)
        self.assertNotIn("next_action", result)
        self.assertIsNone(self.gateway.backend.process)
        self.assertEqual(self.gateway.backend.lifecycle.snapshot()["spawn_attempts"], 0)

    def test_client_cannot_record_an_assessment_before_all_evidence_pages_are_read(self):
        pending = self.call()["structuredContent"]
        incomplete = self.call("sentry_review_evidence", {"review_id": pending["review_id"], "page": 1, "page_size": 1})["structuredContent"]
        verdict = {"review_id": incomplete["review_id"], "reviewed_hash": incomplete["current_hash"], "dossier_hash": incomplete["dossier_hash"], "policy_version": incomplete["policy_version"], "decision": "block", "justification": "Parecer explícito do cliente.", "risks": []}
        result = self.call("sentry_record_assessment", {"verdict": verdict})
        self.assertTrue(result["isError"])
        self.assertIn("complete review evidence", result["structuredContent"]["reason"])
        self.assertEqual(security_status(self.manifest, self.store)["status"], "review_required")

    def test_explicit_client_assessment_records_provenance_but_cannot_authorize_or_start_donna(self):
        pending = self.call()["structuredContent"]
        evidence = self.read_all_evidence(pending["review_id"])
        verdict = {"review_id": evidence["review_id"], "reviewed_hash": evidence["current_hash"], "dossier_hash": evidence["dossier_hash"], "policy_version": evidence["policy_version"], "decision": "allow", "justification": "Parecer submetido pelo cliente após leitura das evidências.", "risks": ["requer aprovação externa"]}
        recorded = self.call("sentry_record_assessment", {"verdict": verdict})["structuredContent"]
        self.assertEqual(recorded["status"], "awaiting_human_approval")
        status = self.call("sentry_security_status")["structuredContent"]
        self.assertEqual(status["assessment"]["source"], "client_submitted")
        self.assertNotIn("model", status["assessment"])
        self.assertEqual(security_status(self.manifest, self.store)["status"], "awaiting_human_approval")
        attempted = self.call()["structuredContent"]
        self.assertEqual(attempted["status"], "security_blocked")
        self.assertFalse(attempted["action_executed"])
        self.assertIsNone(self.gateway.backend.process)
        self.assertEqual(self.gateway.backend.lifecycle.snapshot()["spawn_attempts"], 0)


    def test_review_interface_has_no_backend_and_reads_the_same_pending_diff(self):
        pending = self.call()["structuredContent"]
        baseline_before = (self.store / APPROVED_VERSION_FILE).read_bytes()
        with mock.patch("mcp_sentry_gateway.gateway.BackendSession", side_effect=AssertionError("review must not create a backend")):
            reviewer = StdioGateway(self.manifest, self.store, interface="review")
        self.assertIsNone(reviewer.backend)
        catalog = reviewer.handle({"id": 1, "method": "tools/list"})["result"]["tools"]
        self.assertEqual({tool["name"] for tool in catalog}, {"sentry_security_status", "sentry_review_current_block", "sentry_review_evidence", "sentry_record_assessment"})
        evidence = reviewer.handle({"id": 2, "method": "tools/call", "params": {"name": "sentry_review_evidence", "arguments": {"review_id": pending["review_id"]}}})["result"]["structuredContent"]
        self.assertEqual(evidence["current_hash"], pending["current_hash"])
        self.assertNotEqual(evidence["baseline_hash"], evidence["current_hash"])
        self.assertTrue(evidence["changes"])
        self.assertEqual((self.store / APPROVED_VERSION_FILE).read_bytes(), baseline_before)
        self.assertEqual(security_status(self.manifest, self.store)["status"], "review_required")
        self.assertEqual(self.gateway.backend.lifecycle.snapshot()["spawn_attempts"], 0)

    def test_one_call_review_reads_all_evidence_but_does_not_authorize_execution(self):
        pending = self.call()["structuredContent"]
        reviewer = StdioGateway(self.manifest, self.store, interface="review")
        response = reviewer.handle({"id": 1, "method": "tools/call", "params": {"name": "sentry_review_current_block", "arguments": {}}})["result"]
        evidence = response["structuredContent"]
        self.assertFalse(response.get("isError"), response)
        self.assertEqual(evidence["review_id"], pending["review_id"])
        self.assertEqual(len(evidence["changes"]), evidence["total_changes"])
        self.assertNotIn("page", evidence)
        self.assertNotIn("next_page", evidence)
        self.assertIsNone(reviewer.backend)
        self.assertEqual(security_status(self.manifest, self.store)["status"], "review_required")
        self.assertEqual(self.gateway.backend.lifecycle.snapshot()["spawn_attempts"], 0)

    def test_review_interface_never_dispatches_donna_even_with_an_unchanged_baseline(self):
        clean_store = self.store.parent / "clean-store"
        approve(self.manifest, clean_store)
        reviewer = StdioGateway(self.manifest, clean_store, interface="review")
        with mock.patch.object(reviewer.facade, "call_tool", side_effect=AssertionError("Donna dispatch is forbidden")):
            for name in ("ping", "enviar_email"):
                response = reviewer.handle({"id": 1, "method": "tools/call", "params": {"name": name, "arguments": {}}})
                self.assertEqual(response["error"]["code"], -32602)
        self.assertIsNone(reviewer.backend)

    def test_separate_review_assessment_does_not_release_execution_interface(self):
        executor = StdioGateway(self.manifest, self.store, interface="execution")
        self.addCleanup(executor.backend.close)
        reviewer = StdioGateway(self.manifest, self.store, interface="review")
        def call(gateway, name, arguments=None):
            return gateway.handle({"id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments or {}}})
        catalog = executor.handle({"id": 1, "method": "tools/list"})["result"]["tools"]
        self.assertTrue(catalog)
        self.assertFalse(any(tool["name"].startswith("sentry_") for tool in catalog))
        self.assertIn("error", call(executor, "sentry_record_assessment", {"verdict": {}}))
        self.assertTrue(call(reviewer, "sentry_submit_verdict", {"verdict": {}})["result"]["isError"])
        pending = call(executor, "ping")["result"]["structuredContent"]
        evidence = call(reviewer, "sentry_review_evidence", {"review_id": pending["review_id"]})["result"]["structuredContent"]
        verdict = {"review_id": evidence["review_id"], "reviewed_hash": evidence["current_hash"], "dossier_hash": evidence["dossier_hash"], "policy_version": evidence["policy_version"], "decision": "allow", "justification": "client analysis, not approval", "risks": []}
        recorded = call(reviewer, "sentry_record_assessment", {"verdict": verdict})["result"]["structuredContent"]
        self.assertEqual(recorded["status"], "awaiting_human_approval")
        blocked = call(executor, "ping")["result"]["structuredContent"]
        self.assertEqual(blocked["status"], "security_blocked")
        self.assertFalse(blocked["action_executed"])
        self.assertEqual(executor.backend.lifecycle.snapshot()["spawn_attempts"], 0)

    def test_review_stdio_initialize_and_shutdown_need_no_backend(self):
        reviewer = StdioGateway(self.manifest, self.store, interface="review")
        messages = [
            {"id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "fixture", "version": "1"}}},
            {"method": "notifications/initialized"},
            {"id": 2, "method": "tools/list"},
            {"method": "$/cancelRequest", "params": {"id": 2}},
        ]
        writer = io.StringIO()
        reviewer.serve(io.StringIO("\n".join(json.dumps(message) for message in messages)), writer)
        responses = {response["id"]: response for response in map(json.loads, writer.getvalue().splitlines())}
        self.assertEqual(responses[1]["result"]["serverInfo"]["name"], "mcp-sentry-review")
        self.assertEqual(len(responses[2]["result"]["tools"]), 4)
        self.assertIsNone(reviewer.backend)


if __name__ == "__main__":
    unittest.main()
