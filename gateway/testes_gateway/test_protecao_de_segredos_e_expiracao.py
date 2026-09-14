import json
import io
import shutil
import sys
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from unittest import mock
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).parents[1] / "codigo_gateway"))

from mcp_sentry_gateway.core import SentryError, accept_current, approve, inspect
from mcp_sentry_gateway.gateway import StdioGateway
from mcp_sentry_gateway.mcp_facade import MinimumMcp
from mcp_sentry_gateway.review import approve_review_execution
from mcp_sentry_gateway import cli


EXAMPLE = Path(__file__).parents[1] / "exemplo_mcp"


class T6ADebtClosureTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.gettempdir()) / ("mcp-sentry-t6a-test-" + uuid.uuid4().hex)
        self.project = self.temp / "project"
        shutil.copytree(EXAMPLE, self.project)
        self.store = self.temp / "state"
        self.manifest = self.project / "manifest.json"

    def tearDown(self):
        shutil.rmtree(self.temp, ignore_errors=True)

    def approve(self):
        approve(self.manifest, self.store)

    def change_server(self, suffix="\n# reviewed fixture change\n"):
        server = self.project / "server.py"
        server.write_text(server.read_text(encoding="utf-8") + suffix, encoding="utf-8")

    def pending(self):
        mcp = MinimumMcp(self.manifest, self.store)
        response = mcp.call_tool("ping")["structuredContent"]
        self.assertEqual(response["status"], "security_review_required")
        dossier = mcp.call_tool("sentry_get_pending_review", {"review_id": response["review_id"]})["structuredContent"]
        return mcp, response, dossier

    def approve_recommendation(self, pending, dossier):
        return approve_review_execution(
            self.manifest, self.store, pending["review_id"], dossier["current_hash"],
            dossier["dossier_hash"], "APPROVE_REVIEW_EXECUTION",
        )

    @staticmethod
    def verdict(pending, dossier, decision="allow", justification="controlled fixture", risks=None):
        return {
            "review_id": pending["review_id"],
            "reviewed_hash": dossier["current_hash"],
            "dossier_hash": dossier["dossier_hash"],
            "policy_version": dossier["policy_version"],
            "decision": decision,
            "justification": justification,
            "risks": risks or [],
        }

    def test_gateway_without_baseline_fails_closed_before_spawn(self):
        gateway = StdioGateway(self.manifest, self.store)
        self.addCleanup(gateway.backend.close)
        result = gateway.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ping", "arguments": {}}})["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["status"], "security_blocked")
        self.assertIn("baseline", result["structuredContent"]["reason"])
        self.assertIsNone(gateway.backend.process)

    def test_new_file_omitted_by_current_manifest_is_detected_from_baseline_roots(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["inspect_roots"] = ["."]
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        self.approve()
        data["inspect_roots"] = ["server.py"]
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        (self.project / "omitted.py").write_text("MUST_BE_DETECTED = True\n", encoding="utf-8")
        paths = {change["path"] for change in inspect(self.manifest, self.store)["dossier"]["changes"]}
        self.assertIn("omitted.py", paths)

    def test_text_reports_reconstruct_inspection_and_decision_without_fixture_secret(self):
        secret = "fixture-secret-t6a"
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["inspect_roots"] = ["."]
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        (self.project / ".env").write_text(f"TOKEN={secret}\n", encoding="utf-8")
        (self.project / "config.json").write_text(json.dumps({"token": f'prefix"{secret}-suffix'}), encoding="utf-8")
        (self.project / "multiline.py").write_text(f'SECRET = """prefix\n{secret}\nsuffix"""\n', encoding="utf-8")
        self.change_server(f'\nAPI_KEY = "prefix\\\"{secret}-suffix"\n')
        self.approve()
        self.change_server(f'\nTOKEN = "{secret}"\n')
        mcp, pending, dossier = self.pending()
        submitted = mcp.call_tool("sentry_submit_verdict", {"verdict": self.verdict(
            pending, dossier, decision="block", justification=f'password = "{secret}"', risks=[f'token = "{secret}"']
        )})["structuredContent"]
        self.assertEqual(submitted["status"], "blocked")
        inspection = Path(inspect(self.manifest, self.store)["summary_report"]).read_text(encoding="utf-8")
        decision = (self.store / "reports" / f"review-{pending['review_id']}.txt").read_text(encoding="utf-8")
        self.assertIn("changes: 1", inspection)
        self.assertIn("decision: block", decision)
        self.assertIn("justification:", decision)
        for artifact in self.store.rglob("*"):
            if artifact.is_file():
                self.assertNotIn(secret, artifact.read_text(encoding="utf-8"), artifact)

    def test_oauth_and_pem_private_key_material_is_redacted_from_every_artifact(self):
        old_private = "fixture-old-private-key-t6r"
        new_private = "fixture-new-private-key-t6r"
        old_pem = "fixture-old-pem-body-t6r"
        new_pem = "fixture-new-pem-body-t6r"
        old_bearer = "fixture-old-bearer-t6r"
        new_basic = "fixture-new-basic-t6r"
        encrypted_pem = "fixture-encrypted-pem-body-t6r"
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["inspect_roots"] = ["."]
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        sensitive = self.project / "oauth_fixture.py"
        sensitive.write_text(
            f'private_key = "{old_private}"\n'
            f'clientSecret = "fixture-client-secret-t6r"\n'
            f'Authorization: Bearer {old_bearer}\n'
            f'PEM = """-----BEGIN PRIVATE KEY-----\n{old_pem}\n-----END PRIVATE KEY-----"""\n',
            encoding="utf-8",
        )
        self.approve()
        sensitive.write_text(
            f'private_key = "{new_private}"\n'
            f'refresh_token = "fixture-refresh-token-t6r"\n'
            f'Authorization: Basic {new_basic}\n'
            f'PEM = """-----BEGIN PRIVATE KEY-----\n{new_pem}\n-----END PRIVATE KEY-----"""\n'
            f'ENCRYPTED = """-----BEGIN ENCRYPTED PRIVATE KEY-----\n{encrypted_pem}\n-----END ENCRYPTED PRIVATE KEY-----"""\n',
            encoding="utf-8",
        )
        inspect(self.manifest, self.store)
        forbidden = {
            old_private, new_private, old_pem, new_pem, old_bearer, new_basic,
            encrypted_pem,
            "fixture-client-secret-t6r", "fixture-refresh-token-t6r",
        }
        for artifact in self.store.rglob("*"):
            if artifact.is_file():
                text = artifact.read_text(encoding="utf-8")
                for secret in forbidden:
                    self.assertNotIn(secret, text, artifact)
        baseline = (self.store / "baseline.json").read_text(encoding="utf-8")
        self.assertIn("[REDACTED]", baseline)

    def test_pending_review_expires_and_rejects_verdict(self):
        self.approve(); self.change_server()
        mcp, pending, dossier = self.pending()
        path = self.store / "reviews" / f"{pending['review_id']}.json"
        record = json.loads(path.read_text(encoding="utf-8")); record["created_at"] = "2000-01-01T00:00:00+00:00"
        path.write_text(json.dumps(record), encoding="utf-8")
        status = mcp.call_tool("sentry_security_status")["structuredContent"]
        self.assertEqual(status["status"], "review_required")
        self.assertNotEqual(status["review_id"], pending["review_id"])
        old = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(old["status"], "expired")
        rejected = mcp.call_tool("sentry_submit_verdict", {"verdict": self.verdict(pending, dossier)})["structuredContent"]
        self.assertEqual(rejected["status"], "security_blocked")

    def test_authorization_expires_before_spawn(self):
        self.approve(); self.change_server()
        mcp, pending, dossier = self.pending()
        self.assertEqual(mcp.call_tool("sentry_submit_verdict", {"verdict": self.verdict(pending, dossier)})["structuredContent"]["status"], "awaiting_human_approval")
        self.assertEqual(self.approve_recommendation(pending, dossier)["status"], "allowed_once")
        path = self.store / "reviews" / f"{pending['review_id']}.json"
        record = json.loads(path.read_text(encoding="utf-8")); record["decided_at"] = "2000-01-01T00:00:00+00:00"
        path.write_text(json.dumps(record), encoding="utf-8")
        gateway = StdioGateway(self.manifest, self.store); self.addCleanup(gateway.backend.close)
        result = gateway.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ping", "arguments": {}}})["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["status"], "security_review_required")
        self.assertIsNone(gateway.backend.process)

    def test_mutation_after_allow_invalidates_authorization_before_spawn(self):
        self.approve(); self.change_server()
        mcp, pending, dossier = self.pending()
        self.assertEqual(mcp.call_tool("sentry_submit_verdict", {"verdict": self.verdict(pending, dossier)})["structuredContent"]["status"], "awaiting_human_approval")
        self.assertEqual(self.approve_recommendation(pending, dossier)["status"], "allowed_once")
        self.change_server("\n# mutation after verdict\n")
        gateway = StdioGateway(self.manifest, self.store); self.addCleanup(gateway.backend.close)
        result = gateway.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ping", "arguments": {}}})["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["status"], "security_review_required")
        self.assertIsNone(gateway.backend.process)

    def test_operator_approval_requires_the_exact_recommendation_and_audit_artifact(self):
        self.approve(); self.change_server()
        mcp, pending, dossier = self.pending()
        self.assertEqual(mcp.call_tool("sentry_submit_verdict", {"verdict": self.verdict(pending, dossier)})["structuredContent"]["status"], "awaiting_human_approval")
        with self.assertRaisesRegex(SentryError, "atestação"):
            approve_review_execution(self.manifest, self.store, pending["review_id"], dossier["current_hash"], dossier["dossier_hash"], "no")
        with self.assertRaisesRegex(SentryError, "não corresponde"):
            approve_review_execution(self.manifest, self.store, pending["review_id"], "wrong", dossier["dossier_hash"], "APPROVE_REVIEW_EXECUTION")
        self.assertEqual(self.approve_recommendation(pending, dossier)["status"], "allowed_once")
        self.assertTrue((self.store / "reports" / f"operator-approval-{pending['review_id']}.txt").is_file())

    def test_operator_approval_cli_is_outside_the_mcp_surface(self):
        self.approve(); self.change_server()
        mcp, pending, dossier = self.pending()
        self.assertEqual(mcp.call_tool("sentry_submit_verdict", {"verdict": self.verdict(pending, dossier)})["structuredContent"]["status"], "awaiting_human_approval")
        output = io.StringIO()
        with mock.patch.object(sys, "argv", [
            "mcp-sentry", "approve-review-execution", "--manifest", str(self.manifest),
            "--store", str(self.store), "--review-id", pending["review_id"],
            "--reviewed-hash", dossier["current_hash"], "--dossier-hash", dossier["dossier_hash"],
            "--human-confirmation", "APPROVE_REVIEW_EXECUTION",
        ]), redirect_stdout(output):
            self.assertEqual(cli.main(), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "allowed_once")

    def test_accept_current_is_a_separate_explicit_promotion(self):
        self.approve(); original = json.loads((self.store / "baseline.json").read_text(encoding="utf-8"))["integrity_hash"]
        self.change_server()
        self.assertEqual(inspect(self.manifest, self.store)["status"], "review_required")
        promoted = accept_current(self.manifest, self.store)
        self.assertEqual(promoted["status"], "accepted_current")
        self.assertNotEqual(promoted["integrity_hash"], original)
        self.assertEqual(inspect(self.manifest, self.store)["status"], "unchanged")

    def test_report_write_failure_keeps_gateway_closed(self):
        self.approve()
        gateway = StdioGateway(self.manifest, self.store); self.addCleanup(gateway.backend.close)
        with mock.patch("mcp_sentry_gateway.core.write_text_report", side_effect=OSError("fixture report failure")):
            result = gateway.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ping", "arguments": {}}})["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["status"], "security_blocked")
        self.assertIsNone(gateway.backend.process)

    def test_review_store_failure_does_not_activate_authorization(self):
        self.approve(); self.change_server()
        mcp, pending, dossier = self.pending()
        with mock.patch("mcp_sentry_gateway.review.write", side_effect=OSError("fixture store failure")):
            result = mcp.call_tool("sentry_submit_verdict", {"verdict": self.verdict(pending, dossier)})["structuredContent"]
        self.assertEqual(result["status"], "security_blocked")
        record = json.loads((self.store / "reviews" / f"{pending['review_id']}.json").read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "pending")
        self.assertFalse((self.store / "reports" / f"review-{pending['review_id']}.txt").exists())

    def test_concurrent_verdicts_cannot_both_commit(self):
        self.approve(); self.change_server()
        mcp, pending, dossier = self.pending()
        entered, release = threading.Event(), threading.Event()
        from mcp_sentry_gateway import review
        original = review.write_text_report

        def pause_first(path, text):
            entered.set(); release.wait(timeout=2)
            return original(path, text)

        first_result = {}
        def submit_first():
            first_result.update(mcp.call_tool("sentry_submit_verdict", {"verdict": self.verdict(pending, dossier, "allow")}))

        with mock.patch("mcp_sentry_gateway.review.write_text_report", side_effect=pause_first):
            worker = threading.Thread(target=submit_first); worker.start()
            self.assertTrue(entered.wait(timeout=1))
            second = mcp.call_tool("sentry_submit_verdict", {"verdict": self.verdict(pending, dossier, "block")})["structuredContent"]
            release.set(); worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(second["status"], "security_blocked")
        self.assertEqual(first_result["structuredContent"]["status"], "awaiting_human_approval")
        record = json.loads((self.store / "reviews" / f"{pending['review_id']}.json").read_text(encoding="utf-8"))
        self.assertEqual(record["verdict"]["decision"], "allow")

    def test_missing_final_decision_report_never_authorizes_spawn(self):
        self.approve(); self.change_server()
        mcp, pending, dossier = self.pending()
        from mcp_sentry_gateway import review
        real_replace = review.os.replace
        def fail_only_final_report(source, target):
            if Path(source).name.startswith(f".review-{pending['review_id']}.") and Path(target).name == f"review-{pending['review_id']}.txt":
                raise OSError("fixture final report failure")
            return real_replace(source, target)
        with mock.patch("mcp_sentry_gateway.review.os.replace", side_effect=fail_only_final_report):
            result = mcp.call_tool("sentry_submit_verdict", {"verdict": self.verdict(pending, dossier)})["structuredContent"]
        self.assertEqual(result["status"], "security_blocked")
        gateway = StdioGateway(self.manifest, self.store); self.addCleanup(gateway.backend.close)
        call = gateway.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ping", "arguments": {}}})["result"]
        self.assertTrue(call["isError"])
        self.assertEqual(call["structuredContent"]["status"], "security_blocked")
        self.assertIsNone(gateway.backend.process)

    def test_backend_cannot_claim_reserved_sentry_namespace(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["metadata"]["tools"][0]["name"] = "sentry_shadow"
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(SentryError, "reservado"):
            self.approve()

    def test_legacy_baseline_with_reserved_namespace_fails_tools_list_closed(self):
        self.approve()
        baseline_path = self.store / "baseline.json"
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        baseline["capture"]["manifest"]["metadata"]["tools"][0]["name"] = "sentry_shadow"
        baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
        with self.assertRaisesRegex(SentryError, "reservado"):
            MinimumMcp(self.manifest, self.store).tools_list()
        gateway = StdioGateway(self.manifest, self.store); self.addCleanup(gateway.backend.close)
        response = gateway.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertIn("security blocked", response["error"]["message"])


if __name__ == "__main__":
    unittest.main()
