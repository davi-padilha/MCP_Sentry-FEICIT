import json, shutil, sys, tempfile, unittest, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "gateway" / "src"))
sys.path.insert(0, str(Path(__file__).parent))
from support.agent_flow import FixtureError, FixtureReviewFlow
from mcp_sentry_gateway.core import approve
from mcp_sentry_gateway.mcp_facade import MinimumMcp

EXAMPLE = Path(__file__).parents[1] / "examples" / "mcp_minimo"


class T4Tests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.gettempdir()) / ("mcp-sentry-t4-test-" + uuid.uuid4().hex)
        self.project = self.temp / "project"; shutil.copytree(EXAMPLE, self.project)
        self.store = self.temp / "state"; self.manifest = self.project / "manifest.json"
        approve(self.manifest, self.store)
        self.mcp = MinimumMcp(self.manifest, self.store)
        self.flow = FixtureReviewFlow(self.mcp)

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def changed_state(self):
        (self.project / "server.py").write_text('MARKER = "must-not-execute"\ndef ping(): return "changed"\n', encoding="utf-8")
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest["metadata"]["tools"][0]["description"] = "untrusted changed metadata"
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")

    @staticmethod
    def allow_fixture():
        return {"decision": "allow", "justification": "controlled allow fixture", "risks": ["fixture-only"]}

    def test_b_attempt_reads_every_page_and_submits_fixture_without_replaying_tool(self):
        self.changed_state()
        result = self.flow.attempt_tool("ping", {}, self.allow_fixture(), page_size=1)
        self.assertEqual(result.path, "B")
        self.assertEqual(result.initial_response["structuredContent"]["status"], "security_review_required")
        self.assertEqual(result.pages_read, 2)  # changed server plus changed manifest metadata
        self.assertEqual(result.verdict_response["status"], "awaiting_human_approval")
        self.assertEqual(result.verdict_response["next_action"], "external_operator_approval_required")
        self.assertFalse((self.project / "executed.marker").exists())

    def test_b_without_fixture_keeps_pending_and_offers_explicit_fallback(self):
        self.changed_state()
        result = self.flow.attempt_tool("ping", {})
        content = result.initial_response["structuredContent"]
        self.assertEqual(content["status"], "security_review_required")
        self.assertEqual(content["fallback_action"], "request_explicit_pending_review")
        self.assertIsNone(result.verdict_response)
        self.assertEqual(self.mcp.call_tool("sentry_security_status")["structuredContent"]["status"], "review_required")

    def test_a_explicit_fallback_can_block(self):
        self.changed_state()
        self.flow.attempt_tool("ping", {})
        result = self.flow.review_pending_explicitly({"decision": "block", "justification": "marker is unsafe", "risks": ["marker"]})
        self.assertEqual(result.path, "A")
        self.assertEqual(result.verdict_response["status"], "blocked")
        self.assertEqual(self.mcp.call_tool("ping")["structuredContent"]["status"], "security_blocked")

    def test_invalid_fixture_fails_closed_without_submitting_a_verdict(self):
        self.changed_state()
        with self.assertRaises(FixtureError):
            self.flow.attempt_tool("ping", {}, {"decision": "allow"})
        self.assertEqual(self.mcp.call_tool("sentry_security_status")["structuredContent"]["status"], "review_required")
