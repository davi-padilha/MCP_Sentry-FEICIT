import json, shutil, sys, tempfile, threading, unittest, uuid
from io import StringIO
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / "codigo_gateway"))
from mcp_sentry_gateway.core import SentryError, approve
from mcp_sentry_gateway.gateway import StdioGateway, configure_stdio_utf8
from mcp_sentry_gateway.lifecycle import read_backend_lifecycle
from mcp_sentry_gateway.mcp_facade import MinimumMcp
from mcp_sentry_gateway.review import approve_review_execution

EXAMPLE = Path(__file__).parents[1] / "exemplo_mcp"

class T3Tests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.gettempdir()) / ("mcp-sentry-t3-test-" + uuid.uuid4().hex)
        self.project = self.temp / "project"; shutil.copytree(EXAMPLE, self.project)
        self.store = self.temp / "state"; self.manifest = self.project / "manifest.json"
        approve(self.manifest, self.store); self.gateway = StdioGateway(self.manifest, self.store)

    def tearDown(self):
        self.gateway.backend.close(); shutil.rmtree(self.temp, ignore_errors=True)

    def call(self, number, name, arguments=None):
        return self.gateway.handle({"jsonrpc": "2.0", "id": number, "method": "tools/call", "params": {"name": name, "arguments": arguments or {}}})["result"]

    def test_unchanged_backend_runs_from_verified_copy(self):
        before = self.call(0, "sentry_security_status")["structuredContent"]["backend_lifecycle"]
        self.assertEqual(before["spawn_attempts"], 0)
        self.assertEqual(before["last_event"], "gateway_started")
        session_report = self.store / "relatorios-de-seguranca" / f"backend-lifecycle-{before['gateway_session_id']}.json"
        self.assertTrue(session_report.is_file())
        response = self.call(1, "ping")
        self.assertIn("content", response, response)
        self.assertEqual(response["content"][0]["text"], "pong")
        self.assertTrue(self.gateway.backend.copy_root.is_dir())
        after = self.call(0, "sentry_security_status")["structuredContent"]["backend_lifecycle"]
        self.assertEqual(after["spawn_attempts"], 1)
        self.assertEqual(after["last_event"], "backend_started")
        self.assertEqual(read_backend_lifecycle(self.store), after)
        (self.project / "server.py").write_text("raise RuntimeError('original changed after spawn')\n", encoding="utf-8")
        blocked_after_change = self.call(2, "ping")
        self.assertTrue(blocked_after_change["isError"])
        self.assertEqual(blocked_after_change["structuredContent"]["status"], "security_review_required")

    def test_copy_rejects_a_byte_changed_after_recapture(self):
        original = self.gateway.backend._verified_capture
        def changed_capture():
            value = original()
            (self.project / "server.py").write_text("changed after capture\n", encoding="utf-8")
            return value
        self.gateway.backend._verified_capture = changed_capture
        blocked = self.call(1, "ping")
        self.assertTrue(blocked["isError"])
        self.assertIn("cópia verificada", blocked["structuredContent"]["reason"])
        self.assertIsNone(self.gateway.backend.process)

    def test_allowed_once_is_consumed_before_single_spawn(self):
        (self.project / "server.py").write_text((EXAMPLE / "server.py").read_text(encoding="utf-8") + "\n# reviewed change\n", encoding="utf-8")
        facade = MinimumMcp(self.manifest, self.store)
        pending = facade.call_tool("ping")["structuredContent"]
        dossier = facade.call_tool("sentry_get_pending_review", {"review_id": pending["review_id"]})["structuredContent"]
        verdict = {"review_id": pending["review_id"], "reviewed_hash": dossier["current_hash"], "dossier_hash": dossier["dossier_hash"], "policy_version": "mcp-sentry-review-v1", "decision": "allow", "justification": "controlled fixture", "risks": []}
        self.assertEqual(facade.call_tool("sentry_submit_verdict", {"verdict": verdict})["structuredContent"]["status"], "awaiting_human_approval")
        before_operator = self.call(1, "ping")
        self.assertTrue(before_operator["isError"])
        self.assertEqual(before_operator["structuredContent"]["status"], "security_blocked")
        self.assertIsNone(self.gateway.backend.process)
        lifecycle = self.call(0, "sentry_security_status")["structuredContent"]["backend_lifecycle"]
        self.assertEqual(lifecycle["spawn_attempts"], 0)
        self.assertEqual(approve_review_execution(self.manifest, self.store, pending["review_id"], dossier["current_hash"], dossier["dossier_hash"], "APPROVE_REVIEW_EXECUTION")["status"], "allowed_once")
        allowed_response = self.call(1, "ping")
        self.assertIn("content", allowed_response, allowed_response)
        self.assertEqual(allowed_response["content"][0]["text"], "pong")
        self.gateway.backend.close(); second = StdioGateway(self.manifest, self.store)
        self.addCleanup(second.backend.close)
        blocked = second.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "ping", "arguments": {}}})["result"]
        self.assertTrue(blocked["isError"])
        self.assertEqual(blocked["structuredContent"]["status"], "security_blocked")

    def test_blocked_update_preserves_zero_spawn_evidence(self):
        (self.project / "server.py").write_text("# inert simulated change\n", encoding="utf-8")
        pending = self.call(1, "ping")["structuredContent"]
        self.assertEqual(pending["status"], "security_review_required")
        dossier = self.call(2, "sentry_get_pending_review", {"review_id": pending["review_id"]})["structuredContent"]
        verdict = {
            "review_id": pending["review_id"], "reviewed_hash": dossier["current_hash"],
            "dossier_hash": dossier["dossier_hash"], "policy_version": dossier["policy_version"],
            "decision": "block", "justification": "inert FEICIT fixture", "risks": ["unapproved change"],
        }
        result = self.call(3, "sentry_submit_verdict", {"verdict": verdict})["structuredContent"]
        self.assertEqual(result["status"], "blocked")
        lifecycle = self.call(4, "sentry_security_status")["structuredContent"]["backend_lifecycle"]
        self.assertEqual(lifecycle["spawn_attempts"], 0)
        self.assertEqual(lifecycle["last_event"], "gateway_started")

    def test_lifecycle_write_failure_prevents_popen(self):
        with mock.patch.object(self.gateway.backend.lifecycle, "spawn_requested", side_effect=OSError("fixture audit failure")), mock.patch("mcp_sentry_gateway.gateway.subprocess.Popen") as popen:
            blocked = self.call(1, "ping")
        self.assertTrue(blocked["isError"])
        self.assertEqual(blocked["structuredContent"]["status"], "security_blocked")
        popen.assert_not_called()

    def test_lifecycle_evidence_never_writes_inside_protected_project(self):
        forbidden_store = self.project / "state-inside-project"
        with self.assertRaisesRegex(SentryError, "fora de project_root"):
            StdioGateway(self.manifest, forbidden_store)
        self.assertFalse(forbidden_store.exists())

    def test_status_is_bound_to_its_gateway_session_when_store_is_shared(self):
        first = self.call(1, "sentry_security_status")["structuredContent"]["backend_lifecycle"]
        second_gateway = StdioGateway(self.manifest, self.store)
        self.addCleanup(second_gateway.backend.close)
        second = second_gateway.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "sentry_security_status", "arguments": {}}})["result"]["structuredContent"]["backend_lifecycle"]
        first_again = self.call(3, "sentry_security_status")["structuredContent"]["backend_lifecycle"]
        self.assertNotEqual(first["gateway_session_id"], second["gateway_session_id"])
        self.assertEqual(first_again["gateway_session_id"], first["gateway_session_id"])

    def test_close_waits_for_start_and_preserves_lifecycle_order(self):
        entered, release = threading.Event(), threading.Event()
        original_started = self.gateway.backend.lifecycle.backend_started
        errors = []

        def paused_started():
            entered.set()
            release.wait(timeout=2)
            original_started()

        self.gateway.backend.lifecycle.backend_started = paused_started

        def start_backend():
            try:
                self.gateway.backend.start()
            except Exception as exc:  # collected and asserted below
                errors.append(exc)

        starter = threading.Thread(target=start_backend)
        closer = threading.Thread(target=self.gateway.backend.close)
        starter.start()
        self.assertTrue(entered.wait(timeout=1))
        closer.start()
        self.assertTrue(closer.is_alive())
        release.set()
        starter.join(timeout=3)
        closer.join(timeout=3)
        self.assertFalse(starter.is_alive())
        self.assertFalse(closer.is_alive())
        self.assertEqual(errors, [])
        lifecycle = self.gateway.backend.lifecycle.snapshot()
        self.assertEqual(lifecycle["spawn_attempts"], 1)
        self.assertEqual(lifecycle["last_event"], "backend_closed")

    def test_persisted_lifecycle_rejects_boolean_spawn_count(self):
        path = self.store / "relatorios-de-seguranca" / "backend-lifecycle-current.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["spawn_attempts"] = True
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(SentryError, "inválida"):
            read_backend_lifecycle(self.store)

    def test_stdio_output_contains_only_jsonrpc(self):
        incoming = StringIO('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"fixture","version":"1"}}}\n' + '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n')
        outgoing = StringIO(); self.gateway.serve(incoming, outgoing)
        lines = outgoing.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(json.loads(line)["jsonrpc"] == "2.0" for line in lines))

    def test_stdio_transport_is_forced_to_utf8_when_supported(self):
        class ReconfigurableStream:
            def __init__(self): self.encodings = []
            def reconfigure(self, *, encoding): self.encodings.append(encoding)
        reader, writer = ReconfigurableStream(), ReconfigurableStream()
        configure_stdio_utf8(reader, writer)
        self.assertEqual(reader.encodings, ["utf-8"])
        self.assertEqual(writer.encodings, ["utf-8"])

    def test_cancel_is_forwarded_while_a_tool_is_in_flight(self):
        requested, cancelled = threading.Event(), threading.Event()
        class BlockingBackend:
            def request(self, message):
                requested.set(); cancelled.wait(timeout=2)
                return {"jsonrpc": "2.0", "id": message["id"], "result": {"content": []}}
            def notify(self, message): cancelled.set()
            def close(self): pass
        self.gateway.backend = BlockingBackend()
        class Messages:
            def __iter__(self):
                yield json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ping", "arguments": {}}}) + "\n"
                self_case.assertTrue(requested.wait(timeout=1))
                yield json.dumps({"jsonrpc": "2.0", "method": "$/cancelRequest", "params": {"requestId": 1}}) + "\n"
        self_case = self
        out = StringIO(); self.gateway.serve(Messages(), out)
        self.assertTrue(cancelled.is_set())
        self.assertEqual(json.loads(out.getvalue())["id"], 1)

    def test_close_prevents_a_late_start(self):
        self.gateway.backend.close()
        with self.assertRaisesRegex(Exception, "encerrando"):
            self.gateway.backend.start()

    def test_failed_backend_initialized_notification_closes_backend_permanently(self):
        class BrokenStdin:
            def write(self, _): raise OSError("fixture write failure")
            def flush(self): raise AssertionError("flush must not run after failed write")
        class BrokenProcess:
            stdin = BrokenStdin()
        with self.assertRaisesRegex(SentryError, "notificação de inicialização"):
            self.gateway.backend._initialize_backend(BrokenProcess())

        self.gateway.backend._initialize_backend = lambda _: (_ for _ in ()).throw(SentryError("notificação de inicialização do backend falhou"))
        first = self.call(1, "ping")
        self.assertTrue(first["isError"])
        self.assertEqual(first["structuredContent"]["status"], "security_blocked")
        self.assertIsNone(self.gateway.backend.process)
        second = self.call(2, "ping")
        self.assertTrue(second["isError"])
        self.assertIn("encerrando", second["structuredContent"]["reason"])
