"""Checks for the separately distributed, server-agnostic gateway package."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp_sentry_gateway.core import SentryError, approve, capture, execution_envelope, load, load_execution_envelope
from mcp_sentry_gateway.gateway import StdioGateway


SERVER_SOURCE = '''import json, os, sys
ready = False
for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "independent-example", "version": "1"}}
    elif method == "notifications/initialized":
        ready = True
        continue
    elif method == "tools/list" and ready:
        result = {"tools": [{"name": "echo", "description": os.environ.get("SERVER_TOOL_DESCRIPTION", "Echo a value"), "inputSchema": {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]}}]}
    elif method == "tools/call" and ready and request.get("params", {}).get("name") == "echo":
        value = request["params"]["arguments"]["value"]
        result = {"content": [{"type": "text", "text": os.environ.get("SERVER_GREETING", "") + value}]}
    else:
        result = {"isError": True, "content": [{"type": "text", "text": "unsupported"}]}
    if "id" in request:
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}) + "\\n")
        sys.stdout.flush()
'''


class UniversalGatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="mcp-sentry-client-test-", dir=Path(__file__).parent))
        self.addCleanup(shutil.rmtree, self.temp, True)
        self.project = self.temp / "independent-server"
        self.project.mkdir()
        (self.project / "server.py").write_text(SERVER_SOURCE, encoding="utf-8")
        self.config = self.temp / "configuration"
        self.config.mkdir()
        self.manifest = self.config / "manifest.json"
        self.state = self.temp / "state"
        self.manifest_data = {
            "manifest_version": 1,
            "project_root": "../independent-server",
            "inspect_roots": ["server.py"],
            "metadata": {"tools": [{"name": "echo", "description": "Echo a value", "inputSchema": {
                "type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]
            }}]},
            "configuration": {"command": ["python", "server.py"], "cwd": "."},
        }
        self.save_manifest()

    def save_manifest(self):
        self.manifest.write_text(json.dumps(self.manifest_data), encoding="utf-8")

    @staticmethod
    def request(number, method, params=None):
        result = {"jsonrpc": "2.0", "id": number, "method": method}
        if params is not None:
            result["params"] = params
        return result

    def test_unrelated_server_runs_and_catalog_has_no_demo_identity(self):
        approve(self.manifest, self.state)
        gateway = StdioGateway(self.manifest, self.state, interface="execution")
        self.addCleanup(gateway.backend.close)
        initialized = gateway.handle(self.request(1, "initialize", {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1"},
        }))
        self.assertEqual(initialized["result"]["serverInfo"]["name"], "mcp-sentry-gateway")
        self.assertNotIn("Donna", json.dumps(initialized))
        catalog = gateway.handle(self.request(2, "tools/list"))["result"]["tools"]
        self.assertEqual([tool["name"] for tool in catalog], ["echo"])
        self.assertNotIn("Donna", json.dumps(catalog))
        result = gateway.handle(self.request(3, "tools/call", {"name": "echo", "arguments": {"value": "hello"}}))
        self.assertEqual(result["result"]["content"][0]["text"], "hello")
        self.assertEqual(gateway.backend.lifecycle.snapshot()["spawn_attempts"], 1)

    def test_changed_server_stays_stopped_and_review_is_independent(self):
        approve(self.manifest, self.state)
        (self.project / "server.py").write_text(SERVER_SOURCE + "\n# changed\n", encoding="utf-8")
        execution = StdioGateway(self.manifest, self.state, interface="execution")
        self.addCleanup(execution.backend.close)
        blocked = execution.handle(self.request(1, "tools/call", {"name": "echo", "arguments": {"value": "x"}}))
        self.assertEqual(blocked["result"]["structuredContent"]["status"], "security_review_required")
        self.assertEqual(execution.backend.lifecycle.snapshot()["spawn_attempts"], 0)
        review = StdioGateway(self.manifest, self.state, interface="review")
        self.assertIsNone(review.backend)
        evidence = review.handle(self.request(2, "tools/call", {"name": "sentry_review_current_block", "arguments": {}}))
        self.assertEqual(evidence["result"]["structuredContent"]["changes"][0]["path"], "server.py")
        self.assertNotIn("Donna", json.dumps(evidence))

    def test_environment_names_are_configurable_and_bound_to_baseline(self):
        (self.project / "data.txt").write_text("fixture", encoding="utf-8")
        self.manifest_data["inspect_roots"].append("data.txt")
        self.manifest_data["configuration"]["runtime_paths"] = {"SERVER_DATA_FILE": "data.txt"}
        self.manifest_data["configuration"]["passthrough_names"] = ["SERVER_GREETING"]
        self.save_manifest()
        approve(self.manifest, self.state)
        with mock.patch.dict(os.environ, {"SERVER_GREETING": "hello "}):
            gateway = StdioGateway(self.manifest, self.state, interface="execution")
            self.addCleanup(gateway.backend.close)
            result = gateway.handle(self.request(1, "tools/call", {"name": "echo", "arguments": {"value": "world"}}))
        self.assertEqual(result["result"]["content"][0]["text"], "hello world")
        self.manifest_data["configuration"]["passthrough_names"] = ["OTHER_ENV"]
        self.save_manifest()
        changed = StdioGateway(self.manifest, self.state, interface="execution")
        self.addCleanup(changed.backend.close)
        blocked = changed.handle(self.request(2, "tools/call", {"name": "echo", "arguments": {"value": "world"}}))
        self.assertEqual(blocked["result"]["structuredContent"]["status"], "security_review_required")
        self.assertEqual(changed.backend.lifecycle.snapshot()["spawn_attempts"], 0)
        self.assertNotEqual(execution_envelope(capture(self.manifest)), load_execution_envelope(self.state))

    def test_invalid_environment_mapping_is_rejected(self):
        self.manifest_data["configuration"]["runtime_paths"] = {"SERVER_TOKEN": "data.txt"}
        self.save_manifest()
        with self.assertRaisesRegex(SentryError, "runtime_paths"):
            load(self.manifest)
        self.manifest_data["configuration"]["runtime_paths"] = {}
        self.manifest_data["configuration"]["passthrough_names"] = ["KEY", "KEY"]
        self.save_manifest()
        with self.assertRaisesRegex(SentryError, "passthrough_names"):
            load(self.manifest)

    def test_runtime_catalog_change_blocks_tool_call(self):
        self.manifest_data["configuration"]["passthrough_names"] = ["SERVER_TOOL_DESCRIPTION"]
        self.save_manifest()
        approve(self.manifest, self.state)
        with mock.patch.dict(os.environ, {"SERVER_TOOL_DESCRIPTION": "Unexpected description"}):
            gateway = StdioGateway(self.manifest, self.state, interface="execution")
            self.addCleanup(gateway.backend.close)
            result = gateway.handle(self.request(1, "tools/call", {
                "name": "echo", "arguments": {"value": "hello"},
            }))
        self.assertEqual(result["result"]["structuredContent"]["status"], "security_blocked")
        self.assertIn("catálogo MCP", result["result"]["structuredContent"]["reason"])
        self.assertEqual(gateway.backend.lifecycle.snapshot()["spawn_attempts"], 1)

    def test_approval_does_not_replace_orphaned_execution_envelope(self):
        self.state.mkdir()
        envelope = self.state / "configuracao-de-execucao-aprovada.json"
        envelope.write_text('{"existing":"do not replace"}', encoding="utf-8")
        with self.assertRaisesRegex(SentryError, "envelope de execução já existe"):
            approve(self.manifest, self.state)
        self.assertEqual(envelope.read_text(encoding="utf-8"), '{"existing":"do not replace"}')
        self.assertFalse((self.state / "versao-aprovada.json").exists())

    def test_capture_rejects_symlink_to_file_outside_project(self):
        outside = self.temp / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.project / "linked.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        self.manifest_data["inspect_roots"].append("linked.txt")
        self.save_manifest()
        with self.assertRaisesRegex(SentryError, "escapa project_root"):
            capture(self.manifest)


if __name__ == "__main__":
    unittest.main()
