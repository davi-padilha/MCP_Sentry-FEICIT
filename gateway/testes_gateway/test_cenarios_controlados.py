import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "codigo_gateway"))
sys.path.insert(0, str(Path(__file__).parent))

from mcp_sentry_gateway.core import SentryError
from mcp_sentry_gateway.mcp_facade import MinimumMcp
from support.cenarios_controlados import CASES, prepare
from mcp_sentry_gateway.gateway import StdioGateway
from mcp_sentry_gateway.review import approve_review_execution


class T6DFixtureTests(unittest.TestCase):
    def setUp(self): self.root = Path(tempfile.gettempdir()) / ("mcp-sentry-t6d-" + uuid.uuid4().hex)
    def tearDown(self): shutil.rmtree(self.root, ignore_errors=True)

    def test_each_case_has_fresh_baseline_then_two_page_review_without_external_capability(self):
        for case in CASES:
            prepared = prepare(case, self.root)
            self.assertFalse(prepared["network"]); self.assertFalse(prepared["credentials"]); self.assertFalse(prepared["external_effect"])
            facade = MinimumMcp(Path(prepared["manifest"]), Path(prepared["store"]))
            pending = facade.call_tool("ping")["structuredContent"]
            self.assertEqual(pending["status"], "security_review_required")
            page = facade.call_tool("sentry_get_pending_review", {"review_id": pending["review_id"], "page": 1, "page_size": 1})["structuredContent"]
            self.assertGreaterEqual(page["total_pages"], prepared["expected_min_pages"])
            self.assertTrue(page["has_more"])

    def test_preparer_never_reuses_a_destination(self):
        prepare("D-BENIGN-01", self.root)
        with self.assertRaisesRegex(SentryError, "já existe"):
            prepare("D-BENIGN-01", self.root)

    def test_benign_fixture_completes_the_minimum_mcp_lifecycle_after_allow(self):
        prepared = prepare("D-BENIGN-01", self.root)
        manifest, store = Path(prepared["manifest"]), Path(prepared["store"])
        facade = MinimumMcp(manifest, store)
        pending = facade.call_tool("ping")["structuredContent"]
        dossier = facade.call_tool("sentry_get_pending_review", {"review_id": pending["review_id"], "page": 1, "page_size": 1})["structuredContent"]
        pages = [dossier]
        while pages[-1]["has_more"]:
            pages.append(facade.call_tool("sentry_get_pending_review", {"review_id": pending["review_id"], "page": pages[-1]["next_page"], "page_size": 1})["structuredContent"])
        self.assertGreaterEqual(len(pages), 2)
        self.assertFalse(pages[-1]["has_more"])
        verdict = {"review_id": pending["review_id"], "reviewed_hash": dossier["current_hash"], "dossier_hash": dossier["dossier_hash"], "policy_version": dossier["policy_version"], "decision": "allow", "justification": "benign fixture protocol test", "risks": []}
        self.assertEqual(facade.call_tool("sentry_submit_verdict", {"verdict": verdict})["structuredContent"]["status"], "awaiting_human_approval")
        self.assertEqual(approve_review_execution(manifest, store, pending["review_id"], dossier["current_hash"], dossier["dossier_hash"], "APPROVE_REVIEW_EXECUTION")["status"], "allowed_once")
        gateway = StdioGateway(manifest, store)
        try:
            response = gateway.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ping", "arguments": {}}})["result"]
            self.assertEqual(response["content"][0]["text"], "benign local upgrade")
        finally:
            gateway.backend.close()


if __name__ == "__main__": unittest.main()
