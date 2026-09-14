import json
import sys
import tomllib
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / "gateway" / "src"))

from mcp_sentry_gateway.core import SentryError
from mcp_sentry_gateway.t7_preflight import (
    GOOGLE_SCOPES,
    SENTRY_ENTRY_NAME,
    codex_platform_mcp_fingerprint,
    read_codex_platform_mcp_contract,
    render_sentry_only_codex_block,
    validate_applied_sentry_only_config,
    validate_capability_report,
    validate_exact_google_scopes,
)


class T7PreflightTests(unittest.TestCase):
    def values(self):
        root = Path("C:/T7")
        return {
            "python": root / "venv/Scripts/python.exe", "manifest": root / "manifest.json",
            "store": root / "store", "credentials": root / "credentials.json",
            "token": root / "token.json", "audit": root / "audit.jsonl",
            "mutations": root / "mutations.json", "calendar_id": "controlled-calendar",
        }

    def test_private_config_has_one_sentry_entry_and_pins_the_host_timeout(self):
        block = render_sentry_only_codex_block(**self.values())
        self.assertIn(f"[mcp_servers.{SENTRY_ENTRY_NAME}]", block)
        parsed = tomllib.loads(block)
        self.assertEqual(set(parsed["mcp_servers"]), {SENTRY_ENTRY_NAME})
        self.assertEqual(set(parsed["mcp_servers"][SENTRY_ENTRY_NAME]["env"]), {
            "MCP_SECRETARY_MODE", "MCP_SECRETARY_CREDENTIALS_FILE",
            "MCP_SECRETARY_TOKEN_FILE", "MCP_SECRETARY_AUDIT_FILE",
            "MCP_SECRETARY_MUTATION_STORE_FILE", "MCP_SECRETARY_TIMEZONE",
            "MCP_SECRETARY_CALENDAR_ID",
        })
        self.assertIn('"mcp_sentry_gateway.gateway"', block)
        self.assertNotIn("donna_mcp]", block)
        self.assertIn("tool_timeout_sec = 120", block)

    def test_relative_paths_are_rejected(self):
        with self.assertRaisesRegex(SentryError, "absoluto"):
            render_sentry_only_codex_block(
                python="python.exe", manifest="C:/T7/manifest.json", store="C:/T7/store",
                credentials="C:/T7/credentials.json", token="C:/T7/token.json",
                audit="C:/T7/audit.jsonl", mutations="C:/T7/mutations.json",
            )

    def test_scope_validation_requires_literal_set_equality(self):
        token = Path("C:/T7/token.json")
        with mock.patch.object(Path, "read_text", return_value=json.dumps({"scopes": sorted(GOOGLE_SCOPES)})):
            self.assertEqual(validate_exact_google_scopes(token), sorted(GOOGLE_SCOPES))
        with mock.patch.object(Path, "read_text", return_value=json.dumps({"scopes": [*sorted(GOOGLE_SCOPES), "extra"]})):
            with self.assertRaisesRegex(SentryError, "exatamente"):
                validate_exact_google_scopes(token)

    def test_effective_config_rejects_direct_donna_or_another_mcp(self):
        values = self.values()
        expected = render_sentry_only_codex_block(**values)
        config = Path("C:/T7/config.toml")
        with mock.patch.object(Path, "read_text", return_value=expected):
            validate_applied_sentry_only_config(config, **values)
        bypass = expected + '\n[mcp_servers.donna_mcp]\ncommand = "python.exe"\nargs = []\n'
        with mock.patch.object(Path, "read_text", return_value=bypass):
            with self.assertRaisesRegex(SentryError, "bypass"):
                validate_applied_sentry_only_config(config, **values)
        unrelated = expected + '\n[mcp_servers.unrelated]\ncommand = "other.exe"\nargs = []\n'
        with mock.patch.object(Path, "read_text", return_value=unrelated):
            with self.assertRaisesRegex(SentryError, "bypass"):
                validate_applied_sentry_only_config(
                    config, allow_codex_platform_mcp=True, **values,
                )

    def test_interoperability_allows_only_constrained_codex_node_repl(self):
        values = self.values()
        expected = render_sentry_only_codex_block(**values)
        node_repl = '''
[mcp_servers.node_repl]
command = "codex-node-repl"
args = []
startup_timeout_sec = 20
[mcp_servers.node_repl.env]
CODEX_HOME = "private"
CODEX_CLI_PATH = "private"
NODE_REPL_NODE_PATH = "private"
'''
        config = Path("C:/T7/config.toml")
        fingerprint = codex_platform_mcp_fingerprint(tomllib.loads(node_repl)["mcp_servers"]["node_repl"])
        with mock.patch.object(Path, "read_text", return_value=expected + node_repl):
            validate_applied_sentry_only_config(
                config, allow_codex_platform_mcp=True,
                codex_platform_mcp_sha256=fingerprint, **values,
            )
        with mock.patch.object(Path, "read_text", return_value=expected + node_repl):
            with self.assertRaisesRegex(SentryError, "bypass"):
                validate_applied_sentry_only_config(config, **values)
        with mock.patch.object(Path, "read_text", return_value=expected + node_repl):
            with self.assertRaisesRegex(SentryError, "plataforma inválida"):
                validate_applied_sentry_only_config(
                    config, allow_codex_platform_mcp=True, **values,
                )
        unsafe_node_repl = node_repl.replace('args = []', 'args = ["-m", "donna_mcp"]')
        with mock.patch.object(Path, "read_text", return_value=expected + unsafe_node_repl):
            with self.assertRaisesRegex(SentryError, "plataforma inválida"):
                validate_applied_sentry_only_config(
                    config, allow_codex_platform_mcp=True,
                    codex_platform_mcp_sha256=fingerprint, **values,
                )
        extra_env = node_repl.replace('NODE_REPL_NODE_PATH = "private"',
                                      'NODE_REPL_NODE_PATH = "private"\nEXTRA = "private"')
        with mock.patch.object(Path, "read_text", return_value=expected + extra_env):
            with self.assertRaisesRegex(SentryError, "plataforma inválida"):
                validate_applied_sentry_only_config(
                    config, allow_codex_platform_mcp=True,
                    codex_platform_mcp_sha256=fingerprint, **values,
                )

    def test_effective_config_rejects_sentry_entry_with_divergent_arguments(self):
        values = self.values()
        divergent = render_sentry_only_codex_block(**values).replace("tool_timeout_sec = 120", "tool_timeout_sec = 121")
        with mock.patch.object(Path, "read_text", return_value=divergent):
            with self.assertRaisesRegex(SentryError, "diverge"):
                validate_applied_sentry_only_config(Path("C:/T7/config.toml"), **values)

    def test_platform_contract_requires_exact_schema_and_digest(self):
        contract = Path("C:/T7/node-repl-contract.json")
        digest = "a" * 64
        with mock.patch.object(Path, "read_text", return_value=json.dumps({
            "schema_version": 1, "entry_sha256": digest,
        })):
            self.assertEqual(read_codex_platform_mcp_contract(contract), digest)
        with mock.patch.object(Path, "read_text", return_value=json.dumps({
            "schema_version": 1, "entry_sha256": digest, "extra": True,
        })):
            with self.assertRaisesRegex(SentryError, "schema"):
                read_codex_platform_mcp_contract(contract)
        with mock.patch.object(Path, "read_text", return_value=json.dumps({
            "schema_version": 1, "entry_sha256": "A" * 64,
        })):
            with self.assertRaisesRegex(SentryError, "fingerprint"):
                read_codex_platform_mcp_contract(contract)

    def test_interoperability_records_parallel_capabilities_without_claiming_isolation(self):
        report = {
            "schema_version": 1,
            "capabilities": {name: False for name in ("shell", "terminal", "automated_browser", "external_file_write", "direct_network", "other_mcp")},
            "negative_probes": {name: "blocked" for name in ("shell", "terminal", "automated_browser", "external_file_write", "direct_network", "other_mcp")},
        }
        with mock.patch.object(Path, "read_text", return_value=json.dumps(report)):
            result = validate_capability_report(Path("C:/T7/capabilities.json"))
        self.assertTrue(result["isolated"])
        report["capabilities"]["shell"] = True
        report["negative_probes"]["shell"] = "available"
        with mock.patch.object(Path, "read_text", return_value=json.dumps(report)):
            self.assertFalse(validate_capability_report(Path("C:/T7/capabilities.json"))["isolated"])
        with mock.patch.object(Path, "read_text", return_value=json.dumps(report)):
            with self.assertRaisesRegex(SentryError, "capacidade paralela"):
                validate_capability_report(Path("C:/T7/capabilities.json"), require_isolation=True)

    def test_capability_report_rejects_a_contradictory_absent_capability_probe(self):
        report = {
            "schema_version": 1,
            "capabilities": {name: False for name in ("shell", "terminal", "automated_browser", "external_file_write", "direct_network", "other_mcp")},
            "negative_probes": {name: "blocked" for name in ("shell", "terminal", "automated_browser", "external_file_write", "direct_network", "other_mcp")},
        }
        report["negative_probes"]["shell"] = "not_probed"
        with mock.patch.object(Path, "read_text", return_value=json.dumps(report)):
            with self.assertRaisesRegex(SentryError, "ausente exige"):
                validate_capability_report(Path("C:/T7/capabilities.json"))


if __name__ == "__main__":
    unittest.main()
