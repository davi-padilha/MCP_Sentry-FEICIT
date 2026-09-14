import json
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "gateway" / "src"))

from mcp_sentry_gateway.core import approve
from mcp_sentry_gateway.gateway import SERVER_INSTRUCTIONS, StdioGateway
from mcp_sentry_gateway.mcp_facade import CONTROL_TOOLS, MinimumMcp, PENDING_OUTPUT_SCHEMA, VERDICT_SCHEMA


EXAMPLE = Path(__file__).parents[1] / "examples" / "mcp_minimo"


class T6BMcpConformanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.gettempdir()) / ("mcp-sentry-t6b-test-" + uuid.uuid4().hex)
        self.project = self.temp / "project"; shutil.copytree(EXAMPLE, self.project)
        self.store = self.temp / "state"; self.manifest = self.project / "manifest.json"
        approve(self.manifest, self.store)
        self.gateway = StdioGateway(self.manifest, self.store)
        self.mcp = MinimumMcp(self.manifest, self.store)

    def tearDown(self):
        self.gateway.backend.close(); shutil.rmtree(self.temp, ignore_errors=True)

    @staticmethod
    def initialize(protocol="2025-06-18", capabilities=None, client_info=None):
        return {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": protocol, "capabilities": capabilities if capabilities is not None else {"roots": {"listChanged": True}},
            "clientInfo": client_info if client_info is not None else {"name": "fixture-client", "version": "1.0"},
        }}

    def test_initialize_instructions_negotiates_and_records_observation_without_authentication_claim(self):
        response = self.gateway.handle(self.initialize())["result"]
        self.assertEqual(response["protocolVersion"], "2025-06-18")
        self.assertEqual(response["instructions"], SERVER_INSTRUCTIONS)
        self.assertLessEqual(len(response["instructions"]), 512)
        self.assertIn("read every", response["instructions"])
        observations = list((self.store / "observations").glob("initialize-*.json"))
        self.assertEqual(len(observations), 1)
        record = json.loads(observations[0].read_text(encoding="utf-8"))
        self.assertEqual(record["clientInfo"]["name"], "fixture-client")
        self.assertEqual(record["selected_protocol_version"], "2025-06-18")
        self.assertIn("not proof", record["authentication"])
        self.assertIsNone(self.gateway.backend.process)

    def test_initialize_redacts_secret_shaped_observation_and_selected_version_reaches_backend(self):
        initialized = self.gateway.handle(self.initialize(client_info={
            "name": "fixture", "version": "1", "token": "fixture-secret",
            "api-key": "another-fixture-secret",
            "Authorization": "Bearer fixture-bearer-secret",
            "clientSecret": "fixture-client-secret",
        }))
        self.assertIn("result", initialized)
        record = json.loads(next((self.store / "observations").glob("initialize-*.json")).read_text(encoding="utf-8"))
        self.assertEqual(record["clientInfo"]["token"], "[REDACTED]")
        self.assertEqual(record["clientInfo"]["api-key"], "[REDACTED]")
        self.assertEqual(record["clientInfo"]["Authorization"], "[REDACTED]")
        self.assertEqual(record["clientInfo"]["clientSecret"], "[REDACTED]")
        serialized = json.dumps(record)
        self.assertNotIn("fixture-bearer-secret", serialized)
        self.assertNotIn("fixture-client-secret", serialized)
        response = self.gateway.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "ping", "arguments": {}}})["result"]
        self.assertEqual(response["content"][0]["text"], "pong")
        self.assertEqual(self.gateway.backend.protocol_version, "2025-06-18")

    def test_initialize_selects_a_supported_version_or_rejects_malformed_client_without_backend(self):
        negotiated = self.gateway.handle(self.initialize(protocol="2099-01-01"))["result"]
        self.assertEqual(negotiated["protocolVersion"], "2025-06-18")
        observation = json.loads(next((self.store / "observations").glob("initialize-*.json")).read_text(encoding="utf-8"))
        self.assertEqual(observation["observed_protocol_version"], "2099-01-01")
        self.assertEqual(observation["selected_protocol_version"], "2025-06-18")
        malformed = self.gateway.handle({"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        self.assertEqual(malformed["error"]["code"], -32602)
        self.assertIsNone(self.gateway.backend.process)
        self.assertEqual(len(list((self.store / "observations").glob("initialize-*.json"))), 1)

    def test_initialize_observation_redacts_string_embedded_secret_without_corrupting_json(self):
        response = self.gateway.handle(self.initialize(client_info={"name": "fixture", "version": "1", "notes": 'token="fixture-secret"'}))
        self.assertIn("result", response)
        record = json.loads(next((self.store / "observations").glob("initialize-*.json")).read_text(encoding="utf-8"))
        self.assertEqual(record["clientInfo"]["notes"], 'token="[REDACTED]"')

    def test_control_tools_publish_complete_verdict_and_output_schemas(self):
        tools = {tool["name"]: tool for tool in CONTROL_TOOLS}
        self.assertEqual(set(tools), {"sentry_security_status", "sentry_get_pending_review", "sentry_submit_verdict"})
        self.assertEqual(tools["sentry_submit_verdict"]["inputSchema"]["properties"]["verdict"], VERDICT_SCHEMA)
        self.assertFalse(VERDICT_SCHEMA["additionalProperties"])
        self.assertEqual(set(VERDICT_SCHEMA["required"]), {"review_id", "reviewed_hash", "dossier_hash", "policy_version", "decision", "justification", "risks"})
        self.assertIn("untrusted_content_notice", PENDING_OUTPUT_SCHEMA["required"])
        self.assertTrue(all("outputSchema" in tool for tool in CONTROL_TOOLS))
        for tool in CONTROL_TOOLS:
            self.assertEqual(tool["outputSchema"]["anyOf"][1]["required"], ["status", "reason"])

    def test_error_structured_content_uses_the_declared_error_schema_for_each_control_tool(self):
        missing_store = self.temp / "missing-state"
        missing_baseline = MinimumMcp(self.manifest, missing_store)
        for name, arguments in (
            ("sentry_security_status", {}),
            ("sentry_get_pending_review", {"review_id": "missing"}),
            ("sentry_submit_verdict", {"verdict": {}}),
        ):
            response = missing_baseline.call_tool(name, arguments)
            self.assertTrue(response["isError"])
            self.assertEqual(set(response["structuredContent"]), {"status", "reason"})
            self.assertEqual(response["structuredContent"]["status"], "security_blocked")
            self.assertIsInstance(response["structuredContent"]["reason"], str)
            self.assertEqual(json.loads(response["content"][0]["text"]), response["structuredContent"])

    def test_control_tools_fail_closed_for_non_object_or_extra_arguments(self):
        for name, arguments in (
            ("sentry_security_status", ["x"]),
            ("sentry_get_pending_review", ["x"]),
            ("sentry_submit_verdict", ["x"]),
            ("sentry_security_status", {"unexpected": True}),
            ("sentry_get_pending_review", {"review_id": "missing", "unexpected": True}),
            ("sentry_submit_verdict", {"verdict": {}, "unexpected": True}),
        ):
            response = self.gateway.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": name, "arguments": arguments}})["result"]
            self.assertTrue(response["isError"])
            self.assertEqual(set(response["structuredContent"]), {"status", "reason"})
            self.assertEqual(response["structuredContent"]["status"], "security_blocked")
            self.assertEqual(json.loads(response["content"][0]["text"]), response["structuredContent"])
        self.assertIsNone(self.gateway.backend.process)

    def test_public_verdict_schema_rejects_whitespace_only_justification(self):
        self.assertEqual(VERDICT_SCHEMA["properties"]["justification"]["pattern"], ".*\\S.*")

    def test_backend_rejects_an_unnegotiated_protocol_version(self):
        original_round_trip = self.gateway.backend._round_trip
        self.gateway.backend._round_trip = lambda process, message: (
            {"jsonrpc": "2.0", "id": message["id"], "result": {"protocolVersion": "2099-01-01"}}
            if message.get("method") == "initialize" else original_round_trip(process, message)
        )
        response = self.gateway.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "ping", "arguments": {}}})["result"]
        self.assertTrue(response["isError"])
        self.assertIn("não negociou", response["structuredContent"]["reason"])
        self.assertIsNone(self.gateway.backend.process)

    def test_every_control_response_has_matching_json_text_fallback(self):
        self.project.joinpath("server.py").write_text('def ping(): return "changed"\n', encoding="utf-8")
        pending = self.mcp.call_tool("ping")
        for response in (self.mcp.call_tool("sentry_security_status"), pending):
            self.assertEqual(json.loads(response["content"][0]["text"]), response["structuredContent"])
        review = self.mcp.call_tool("sentry_get_pending_review", {"review_id": pending["structuredContent"]["review_id"], "page": 1, "page_size": 1})
        self.assertEqual(json.loads(review["content"][0]["text"]), review["structuredContent"])
        dossier = review["structuredContent"]
        submitted = self.mcp.call_tool("sentry_submit_verdict", {"verdict": {
            "review_id": dossier["review_id"], "reviewed_hash": dossier["current_hash"], "dossier_hash": dossier["dossier_hash"],
            "policy_version": dossier["policy_version"], "decision": "block", "justification": "fixture", "risks": ["fixture"],
        }})
        self.assertEqual(json.loads(submitted["content"][0]["text"]), submitted["structuredContent"])

    def test_pagination_is_explicit_and_out_of_range_fails_closed(self):
        self.project.joinpath("server.py").write_text('def ping(): return "changed"\n', encoding="utf-8")
        pending = self.mcp.call_tool("ping")["structuredContent"]
        first = self.mcp.call_tool("sentry_get_pending_review", {"review_id": pending["review_id"], "page": 1, "page_size": 1})["structuredContent"]
        self.assertGreaterEqual(first["total_pages"], 1)
        self.assertEqual(first["has_more"], first["next_page"] is not None)
        pages, current = [], first
        while True:
            pages.extend(current["changes"])
            if not current["has_more"]:
                break
            current = self.mcp.call_tool("sentry_get_pending_review", {"review_id": pending["review_id"], "page": current["next_page"], "page_size": 1})["structuredContent"]
        self.assertEqual(len(pages), first["total_changes"])
        impossible = self.mcp.call_tool("sentry_get_pending_review", {"review_id": pending["review_id"], "page": first["total_pages"] + 1})
        self.assertTrue(impossible["isError"])
        self.assertEqual(impossible["structuredContent"]["status"], "security_blocked")

    def test_review_gate_keeps_same_turn_and_explicit_fallback_in_both_result_forms(self):
        self.project.joinpath("server.py").write_text('def ping(): return "changed"\n', encoding="utf-8")
        response = self.gateway.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "ping", "arguments": {}}})["result"]
        self.assertTrue(response["isError"])
        self.assertEqual(response["structuredContent"]["same_turn_action"], "sentry_get_pending_review")
        self.assertEqual(response["structuredContent"]["fallback_action"], "request_explicit_pending_review")
        self.assertEqual(json.loads(response["content"][0]["text"]), response["structuredContent"])


if __name__ == "__main__":
    unittest.main()
