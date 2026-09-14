import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import uuid
from io import StringIO
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / "gateway" / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from mcp_sentry_gateway.core import SentryError, accept_current, approve, capture, digest, execution_envelope, load_execution_envelope, promote_execution_envelope
from mcp_sentry_gateway.gateway import BACKEND_STDERR_LIMIT_BYTES, StdioGateway
from mcp_sentry_gateway.mcp_facade import MinimumMcp
from mcp_sentry_gateway.review import approve_review_execution
from support.temporary_config import (
    SENTRY_ENTRY_NAME,
    cleanup_temporary_sentry_config,
    temporary_sentry_only_config,
    validate_sentry_only_config,
)

EXAMPLE = Path(__file__).parents[1] / "examples" / "mcp_minimo"


class T6CPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.gettempdir()) / ("mcp-sentry-t6c-test-" + uuid.uuid4().hex)
        self.project = self.temp / "project"; shutil.copytree(EXAMPLE, self.project)
        self.manifest, self.store = self.project / "manifest.json", self.temp / "state"
        approve(self.manifest, self.store); self.gateway = StdioGateway(self.manifest, self.store)

    def tearDown(self):
        self.gateway.backend.close(); shutil.rmtree(self.temp, ignore_errors=True)

    def call(self):
        return self.gateway.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ping", "arguments": {}}})["result"]

    def test_execution_envelope_blocks_changed_command_until_separate_operator_attestation(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8")); data["configuration"]["cwd"] = "changed"
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(SentryError, "envelope"):
            self.gateway.backend._verified_capture()
        self.assertIsNone(self.gateway.backend.process)
        facade = MinimumMcp(self.manifest, self.store)
        pending = facade.call_tool("ping")["structuredContent"]
        dossier = facade.call_tool("sentry_get_pending_review", {"review_id": pending["review_id"]})["structuredContent"]
        verdict = {"review_id": pending["review_id"], "reviewed_hash": dossier["current_hash"], "dossier_hash": dossier["dossier_hash"], "policy_version": dossier["policy_version"], "decision": "allow", "justification": "fixture allow cannot promote launch envelope", "risks": []}
        self.assertEqual(facade.call_tool("sentry_submit_verdict", {"verdict": verdict})["structuredContent"]["status"], "awaiting_human_approval")
        self.assertEqual(approve_review_execution(self.manifest, self.store, pending["review_id"], dossier["current_hash"], dossier["dossier_hash"], "APPROVE_REVIEW_EXECUTION")["status"], "allowed_once")
        blocked = self.call()
        self.assertTrue(blocked["isError"]); self.assertIn("envelope", blocked["structuredContent"]["reason"])
        self.assertIsNone(self.gateway.backend.process)
        with self.assertRaisesRegex(SentryError, "atestação operacional"):
            promote_execution_envelope(self.manifest, self.store, "no")
        promoted = promote_execution_envelope(self.manifest, self.store, "PROMOTE_EXECUTION_ENVELOPE")
        self.assertEqual(promoted["status"], "execution_envelope_promoted")

    def test_every_launch_field_is_bound_and_accept_current_cannot_promote_it(self):
        trusted = load_execution_envelope(self.store)
        for field, replacement in (
            ("project_root", "another-root"),
            ("inspect_roots", ["another-root/server.py"]),
            ("command", ["other-python", "server.py"]),
            ("cwd", "another-root"),
            ("runtime_paths", {"MCP_SECRETARY_AUDIT_FILE": "another-root/audit.txt"}),
            ("passthrough_names", ["OTHER_NAME"]),
        ):
            candidate = dict(trusted); candidate[field] = replacement
            self.assertNotEqual(candidate, trusted, field)
        before = (self.store / "trusted-execution-envelope.json").read_bytes()
        self.project.joinpath("server.py").write_text('def ping(): return "changed"\n', encoding="utf-8")
        accept_current(self.manifest, self.store)
        self.assertEqual((self.store / "trusted-execution-envelope.json").read_bytes(), before)
        self.assertEqual(execution_envelope(capture(self.manifest)), trusted)

    def test_backend_environment_is_minimal_and_secret_passthrough_value_never_enters_store(self):
        captured = {}
        class Process:
            stdin, stdout, stderr = StringIO(), StringIO(), StringIO()
            poll = lambda self: 0
        def popen(*args, **kwargs): captured.update(kwargs["env"]); return Process()
        trusted_values = {
            "MCP_SECRETARY_TOKEN_FILE": "C:/secret/token.json",
            "MCP_SECRETARY_TIMEZONE": "America/Sao_Paulo",
            "MCP_SECRETARY_CALENDAR_ID": "controlled-calendar",
            "MCP_SECRETARY_AUDIT_FILE": "C:/private/audit.jsonl",
            "MCP_SECRETARY_MUTATION_STORE_FILE": "C:/private/mutations.json",
        }
        with mock.patch.dict(os.environ, {"UNRELATED_PARENT_SECRET": "do-not-inherit", **trusted_values}, clear=False), mock.patch("mcp_sentry_gateway.gateway.subprocess.Popen", popen):
            current = capture(self.manifest)
            expected = digest(json.dumps(current, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
            self.gateway.backend._copy_and_spawn(expected)
        self.assertEqual(captured["MCP_SECRETARY_TOKEN_FILE"], "C:/secret/token.json")
        for name, value in trusted_values.items(): self.assertEqual(captured[name], value)
        self.assertNotIn("UNRELATED_PARENT_SECRET", captured)
        for artifact in self.store.rglob("*"):
            if artifact.is_file():
                text = artifact.read_text(encoding="utf-8")
                for value in trusted_values.values(): self.assertNotIn(value, text)

    def test_stderr_is_drained_and_capped(self):
        class Process: stderr = StringIO("x" * (BACKEND_STDERR_LIMIT_BYTES + 10))
        self.gateway.backend._start_stderr_drain(Process())
        self.gateway.backend._stderr_thread.join(timeout=1)
        self.assertTrue(self.gateway.backend.stderr_truncated)
        self.assertLessEqual(len(self.gateway.backend.stderr_text.encode("utf-8")), BACKEND_STDERR_LIMIT_BYTES)

    def test_verified_copy_cleanup_failure_is_observable_and_path_is_retained(self):
        copy_root = self.store / "verified-runs" / "cleanup-fixture"
        copy_root.mkdir(parents=True)
        self.gateway.backend.copy_root = copy_root
        with mock.patch("mcp_sentry_gateway.gateway.shutil.rmtree", side_effect=OSError("fixture cleanup failure")):
            with self.assertRaisesRegex(SentryError, "falha ao remover cópia verificada"):
                self.gateway.backend.close()
        self.assertEqual(self.gateway.backend.copy_root, copy_root)
        self.assertTrue(copy_root.is_dir())

    def test_cleanup_failure_does_not_mask_primary_backend_failure(self):
        self.gateway.backend.start = lambda: None
        self.gateway.backend._round_trip = lambda *_: (_ for _ in ()).throw(
            SentryError("falha primária do backend")
        )
        with mock.patch.object(
            self.gateway.backend,
            "close",
            side_effect=SentryError("falha ao remover cópia verificada: fixture"),
        ):
            with self.assertRaises(SentryError) as raised:
                self.gateway.backend.request({"jsonrpc": "2.0", "id": 1})
        message = str(raised.exception)
        self.assertIn("falha primária do backend", message)
        self.assertIn("falha ao remover cópia verificada", message)

    def test_copy_failure_removes_partial_verified_tree_before_returning(self):
        with mock.patch(
            "mcp_sentry_gateway.gateway.shutil.copyfile",
            side_effect=OSError("fixture copy failure"),
        ):
            with self.assertRaisesRegex(SentryError, "falha ao criar cópia verificada"):
                self.gateway.backend.request({"jsonrpc": "2.0", "id": 1})
        self.assertIsNone(self.gateway.backend.process)
        self.assertIsNone(self.gateway.backend.copy_root)
        verified_runs = self.store / "verified-runs"
        self.assertFalse(verified_runs.exists() and any(verified_runs.iterdir()))

    def test_timeout_closes_the_backend_before_returning_a_failure(self):
        self.gateway.backend.start = lambda: setattr(self.gateway.backend, "process", object())
        self.gateway.backend._round_trip = lambda *_: (_ for _ in ()).throw(SentryError("timeout da resposta do backend"))
        self.gateway.backend.close = mock.Mock()
        with self.assertRaisesRegex(SentryError, "timeout"):
            self.gateway.backend.request({"jsonrpc": "2.0", "id": 1})
        self.gateway.backend.close.assert_called_once()

    def test_timeout_covers_a_blocking_backend_write_as_well_as_read(self):
        class BlockingStdin:
            def write(self, _): time.sleep(0.05)
            def flush(self): pass
        class Process:
            stdin, stdout = BlockingStdin(), StringIO()
            poll = lambda self: None
        with mock.patch("mcp_sentry_gateway.gateway.BACKEND_REQUEST_TIMEOUT_SECONDS", 0.01):
            with self.assertRaisesRegex(SentryError, "timeout"):
                self.gateway.backend._round_trip(Process(), {"jsonrpc": "2.0", "id": 1})

    def test_temporary_config_is_in_memory_sentry_only_and_detects_direct_bypass(self):
        self.assertEqual(SENTRY_ENTRY_NAME, "Donna_via_Sentry")
        self.assertRegex(SENTRY_ENTRY_NAME, r"^[A-Za-z0-9_:@/.-]+$")
        self.assertNotIn(" ", SENTRY_ENTRY_NAME)
        config = temporary_sentry_only_config(self.manifest, self.store)
        self.assertEqual(validate_sentry_only_config(config), config)
        self.assertEqual(cleanup_temporary_sentry_config(config), {"mcpServers": {}})
        config["mcpServers"]["Donna"] = {"command": "direct-donna", "args": []}
        with self.assertRaisesRegex(SentryError, "bypass"):
            validate_sentry_only_config(config)
        disguised = temporary_sentry_only_config(self.manifest, self.store)
        disguised["mcpServers"][SENTRY_ENTRY_NAME]["command"] = "direct-donna"
        with self.assertRaisesRegex(SentryError, "inválida"):
            validate_sentry_only_config(disguised)


if __name__ == "__main__": unittest.main()
