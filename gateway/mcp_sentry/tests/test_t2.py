import json, shutil, sys, tempfile, unittest, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "gateway" / "src"))
from mcp_sentry_gateway.core import approve
from mcp_sentry_gateway.mcp_facade import MinimumMcp
from mcp_sentry_gateway.review import approve_review_execution

EXAMPLE = Path(__file__).parents[1] / "examples" / "mcp_minimo"

class T2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.gettempdir()) / ("mcp-sentry-t2-test-" + uuid.uuid4().hex)
        self.project = self.temp / "project"; shutil.copytree(EXAMPLE, self.project)
        self.store = self.temp / "state"; self.manifest = self.project / "manifest.json"
        approve(self.manifest, self.store); self.mcp = MinimumMcp(self.manifest, self.store)

    def rug_pull(self):
        (self.project / "server.py").write_text('SECRET = "fixture-secret-value"\nMARKER = "must-not-execute"\ndef ping(): return "changed"\n', encoding="utf-8")

    def pending(self):
        self.rug_pull(); result = self.mcp.call_tool("ping")["structuredContent"]
        self.assertEqual(result["status"], "security_review_required")
        return result

    def test_catalog_is_baseline_and_controlled(self):
        self.assertEqual([item["name"] for item in self.mcp.tools_list()["tools"]], ["ping", "sentry_security_status", "sentry_get_pending_review", "sentry_submit_verdict"])
        manifest = json.loads(self.manifest.read_text(encoding="utf-8")); manifest["metadata"]["tools"][0]["name"] = "evil"
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual(self.mcp.tools_list()["tools"][0]["name"], "ping")

    def test_rug_pull_needs_review_and_dossier_is_redacted(self):
        pending = self.pending(); marker = self.project / "executed.marker"
        self.assertFalse(marker.exists())
        dossier = self.mcp.call_tool("sentry_get_pending_review", {"review_id": pending["review_id"]})["structuredContent"]
        self.assertEqual(dossier["status"], "pending")
        self.assertIn("[REDACTED]", dossier["changes"][0]["diff"])
        self.assertNotIn("fixture-secret-value", json.dumps(dossier))
        self.assertIn("never instructions", dossier["untrusted_content_notice"])
        self.assertEqual(dossier["metadata"]["approved"], dossier["metadata"]["current"])
        self.assertEqual(dossier["configuration"]["approved"], dossier["configuration"]["current"])

    def test_only_exact_allow_is_recorded_and_execution_stays_blocked(self):
        pending = self.pending()
        bad = {"review_id": pending["review_id"], "reviewed_hash": "wrong", "dossier_hash": "wrong", "policy_version": "mcp-sentry-review-v1", "decision": "allow", "justification": "fixture", "risks": []}
        self.assertEqual(self.mcp.call_tool("sentry_submit_verdict", {"verdict": bad})["structuredContent"]["status"], "security_blocked")
        dossier = self.mcp.call_tool("sentry_get_pending_review", {"review_id": pending["review_id"]})["structuredContent"]
        good = {**bad, "reviewed_hash": dossier["current_hash"], "dossier_hash": dossier["dossier_hash"]}
        allowed = self.mcp.call_tool("sentry_submit_verdict", {"verdict": good})["structuredContent"]
        self.assertEqual(allowed["status"], "awaiting_human_approval")
        self.assertEqual(self.mcp.call_tool("ping")["structuredContent"]["status"], "security_blocked")
        approved = approve_review_execution(self.manifest, self.store, pending["review_id"], dossier["current_hash"], dossier["dossier_hash"], "APPROVE_REVIEW_EXECUTION")
        self.assertEqual(approved["status"], "allowed_once")
        self.assertEqual(self.mcp.call_tool("ping")["structuredContent"]["status"], "blocked_by_t2")

    def test_invalid_schema_and_block_persist(self):
        pending = self.pending()
        self.assertEqual(self.mcp.call_tool("sentry_submit_verdict", {"verdict": {}})["structuredContent"]["status"], "security_blocked")
        dossier = self.mcp.call_tool("sentry_get_pending_review", {"review_id": pending["review_id"]})["structuredContent"]
        block = {"review_id": pending["review_id"], "reviewed_hash": dossier["current_hash"], "dossier_hash": dossier["dossier_hash"], "policy_version": "mcp-sentry-review-v1", "decision": "block", "justification": "fixture risk", "risks": ["marker"]}
        self.assertEqual(self.mcp.call_tool("sentry_submit_verdict", {"verdict": block})["structuredContent"]["status"], "blocked")
        self.assertEqual(self.mcp.call_tool("ping")["structuredContent"]["status"], "security_blocked")
