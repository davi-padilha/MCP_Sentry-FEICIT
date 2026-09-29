"""Exercise the Codex setup wizard against disposable configuration files."""

import json
import shutil
import sys
import tempfile
import tomllib
import unittest
import venv
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cliente"))

from mcp_sentry_gateway.core import SentryError, capture
from mcp_sentry_gateway.gateway import StdioGateway
from mcp_sentry_gateway.setup import run_setup
from test_gateway_universal import SERVER_SOURCE


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="mcp-sentry-setup-test-", dir=Path(__file__).parent))
        self.addCleanup(shutil.rmtree, self.temp, True)
        self.project = self.temp / "real-server"
        self.project.mkdir()
        self.script = self.project / "server.py"
        self.script.write_text(SERVER_SOURCE, encoding="utf-8")
        self.config = self.temp / "config.toml"
        self.state_root = self.temp / "states"
        self.config.write_text(
            'model = "some-model"\n\n'
            '[mcp_servers.example]\n'
            f'command = {json.dumps(sys.executable)}\n'
            f'args = [{json.dumps(str(self.script))}]\n'
            f'cwd = {json.dumps(str(self.project))}\n'
            'default_tools_approval_mode = "prompt"\n'
            'startup_timeout_sec = 60.0\n'
            'tool_timeout_sec = 120.0\n'
            'env = { SERVER_GREETING = "hi " }\n\n'
            '[mcp_servers.remote]\n'
            'url = "https://example.invalid/mcp"\n',
            encoding="utf-8",
        )
        self.original = self.config.read_bytes()

    def run_answers(self, *answers):
        values = iter(answers)
        messages = []
        result = run_setup(
            self.config, self.state_root, requested_name="example",
            input_fn=lambda: next(values), output=messages.append,
        )
        return result, "\n".join(messages)

    def test_setup_approves_and_connects_without_changing_unrelated_config(self):
        result, messages = self.run_answers("", "", "DESCOBRIR", "APROVAR", "SUBSTITUIR")
        self.assertEqual(result["status"], "connected_restart_required")
        self.assertEqual(result["tools"], 1)
        self.assertNotIn("hi ", messages)
        self.assertEqual(Path(result["backup"]).read_bytes(), self.original)
        configured = tomllib.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(configured["model"], "some-model")
        self.assertEqual(configured["mcp_servers"]["remote"]["url"], "https://example.invalid/mcp")
        execution = configured["mcp_servers"]["example"]
        self.assertEqual(execution["env"], {"SERVER_GREETING": "hi "})
        self.assertEqual(execution["env_vars"], ["SERVER_GREETING"])
        self.assertEqual(execution["default_tools_approval_mode"], "prompt")
        self.assertEqual(execution["startup_timeout_sec"], 60.0)
        self.assertEqual(execution["tool_timeout_sec"], 120.0)
        self.assertNotIn("cwd", execution)
        self.assertIn("--interface", execution["args"])
        self.assertIn("mcp_sentry_review_example", configured["mcp_servers"])
        self.assertTrue((self.state_root / "example" / "state" / "versao-aprovada.json").is_file())
        manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["configuration"]["command"][1], "server.py")
        self.assertEqual(manifest["configuration"]["cwd"], ".")
        self.assertEqual(manifest["configuration"]["backend_timeout_sec"], 120.0)
        gateway = StdioGateway(Path(result["manifest"]), self.state_root / "example" / "state", interface="execution")
        self.addCleanup(gateway.backend.close)
        response = gateway.handle({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "echo", "arguments": {"value": "working"}},
        })
        self.assertEqual(response["result"]["content"][0]["text"], "working")
        gateway.backend.close()
        self.script.write_text(SERVER_SOURCE + "\n# later change\n", encoding="utf-8")
        blocked_gateway = StdioGateway(Path(result["manifest"]), self.state_root / "example" / "state", interface="execution")
        self.addCleanup(blocked_gateway.backend.close)
        blocked = blocked_gateway.handle({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "echo", "arguments": {"value": "working"}},
        })
        self.assertEqual(blocked["result"]["structuredContent"]["status"], "security_review_required")
        self.assertEqual(blocked_gateway.backend.lifecycle.snapshot()["spawn_attempts"], 0)

    def test_declining_discovery_does_not_write(self):
        result, _ = self.run_answers("", "", "no")
        self.assertEqual(result["status"], "cancelled_before_discovery")
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertFalse(self.state_root.exists())

    def test_declining_baseline_leaves_config_unchanged(self):
        result, _ = self.run_answers("", "", "DESCOBRIR", "no")
        self.assertEqual(result["status"], "prepared_not_approved")
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertFalse((self.state_root / "example" / "state" / "versao-aprovada.json").exists())

    def test_declining_connection_keeps_approved_files_and_original_config(self):
        result, _ = self.run_answers("", "", "DESCOBRIR", "APROVAR", "no")
        self.assertEqual(result["status"], "approved_not_connected")
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertTrue((self.state_root / "example" / "state" / "versao-aprovada.json").exists())

    def test_retry_reuses_empty_config_directory_after_failed_prepare(self):
        (self.state_root / "example" / "config").mkdir(parents=True)
        result, messages = self.run_answers("", "", "DESCOBRIR", "APROVAR", "SUBSTITUIR")
        self.assertEqual(result["status"], "connected_restart_required")
        self.assertIn("reutilizando-a", messages)

    def test_existing_state_with_data_is_never_reused(self):
        directory = self.state_root / "example" / "config"
        directory.mkdir(parents=True)
        (directory / "notes.txt").write_text("keep", encoding="utf-8")
        with mock.patch("mcp_sentry_gateway.setup.prepare_codex") as prepare:
            with self.assertRaisesRegex(SentryError, "já existe um estado"):
                self.run_answers("", "", "DESCOBRIR")
        prepare.assert_not_called()
        self.assertEqual((directory / "notes.txt").read_text(encoding="utf-8"), "keep")
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_missing_inspection_path_fails_before_discovery(self):
        with mock.patch("mcp_sentry_gateway.setup.prepare_codex") as prepare:
            with self.assertRaisesRegex(SentryError, "inexistente ou vazio"):
                self.run_answers("", "server.py, absent.py")
        prepare.assert_not_called()
        self.assertFalse(self.state_root.exists())
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_state_inside_server_is_rejected_before_discovery(self):
        state_root = self.project / "sentry-state"
        with mock.patch("mcp_sentry_gateway.setup.prepare_codex") as prepare:
            with self.assertRaisesRegex(SentryError, "fora da pasta"):
                run_setup(self.config, state_root, requested_name="example",
                          input_fn=iter(("", "")).__next__, output=lambda _: None)
        prepare.assert_not_called()
        self.assertFalse(state_root.exists())

    def test_unrelated_array_table_survives_replacement(self):
        self.config.write_text(self.config.read_text(encoding="utf-8") +
                               '\n[[profiles]]\nname = "keep"\n', encoding="utf-8")
        result, _ = self.run_answers("", "", "DESCOBRIR", "APROVAR", "SUBSTITUIR")
        self.assertEqual(result["status"], "connected_restart_required")
        self.assertEqual(tomllib.loads(self.config.read_text(encoding="utf-8"))["profiles"],
                         [{"name": "keep"}])

    def test_inline_mcp_table_is_rejected_before_discovery(self):
        self.config.write_text(
            f'mcp_servers = {{ example = {{ command = {json.dumps(sys.executable)}, '
            f'args = [{json.dumps(str(self.script))}], cwd = {json.dumps(str(self.project))} }} }}\n',
            encoding="utf-8",
        )
        with mock.patch("mcp_sentry_gateway.setup.prepare_codex") as prepare:
            with self.assertRaisesRegex(SentryError, "entrada selecionada precisa estar"):
                self.run_answers("", "")
        prepare.assert_not_called()
        self.assertFalse(self.state_root.exists())

    def test_change_during_review_does_not_approve_or_rewire_client(self):
        answers = iter(("", "", "DESCOBRIR", "APROVAR"))
        def output(message):
            if message.startswith("Digite APROVAR"):
                self.script.write_text(SERVER_SOURCE + "\n# changed after display\n", encoding="utf-8")
        with self.assertRaisesRegex(SentryError, "mudaram durante a revisão"):
            run_setup(self.config, self.state_root, requested_name="example",
                      input_fn=answers.__next__, output=output)
        self.assertFalse((self.state_root / "example" / "state" / "versao-aprovada.json").exists())
        self.assertEqual(self.config.read_bytes(), self.original)

    def test_concurrent_config_edit_is_not_overwritten(self):
        answers = iter(("", "", "DESCOBRIR", "APROVAR", "SUBSTITUIR"))
        def output(message):
            if message.startswith("Digite SUBSTITUIR"):
                self.config.write_text(self.config.read_text(encoding="utf-8") +
                                       "\n# concurrent edit\n", encoding="utf-8")
        with self.assertRaisesRegex(SentryError, "mudou durante a preparação"):
            run_setup(self.config, self.state_root, requested_name="example",
                      input_fn=answers.__next__, output=output)
        self.assertTrue(self.config.read_text(encoding="utf-8").endswith("# concurrent edit\n"))
        self.assertTrue((self.state_root / "example" / "state" / "versao-aprovada.json").exists())

    def test_unsupported_option_fails_before_running_server(self):
        self.config.write_text(self.config.read_text(encoding="utf-8").replace(
            'env = { SERVER_GREETING = "hi " }',
            'env = { SERVER_GREETING = "hi " }\nenabled_tools = ["echo"]',
        ), encoding="utf-8")
        with self.assertRaisesRegex(SentryError, "não migradas"):
            self.run_answers()
        self.assertFalse(self.state_root.exists())

    def test_missing_script_fails_before_discovery_or_config_write(self):
        self.script.unlink()
        with self.assertRaisesRegex(SentryError, "script Python não existe"):
            self.run_answers("")
        self.assertEqual(self.config.read_bytes(), self.original)
        self.assertFalse(self.state_root.exists())

    def test_nested_cwd_runs_from_verified_subdirectory(self):
        source = self.temp / "source"
        nested = source / "app"
        nested.mkdir(parents=True)
        (nested / "server.py").write_text(SERVER_SOURCE, encoding="utf-8")
        self.config.write_text(self.config.read_text(encoding="utf-8")
            .replace(json.dumps(str(self.script)), json.dumps(str(nested / "server.py")))
            .replace(json.dumps(str(self.project)), json.dumps(str(nested))), encoding="utf-8")
        values = iter((str(source), "", "DESCOBRIR", "APROVAR", "SUBSTITUIR"))
        result = run_setup(self.config, self.state_root, requested_name="example",
                           input_fn=lambda: next(values), output=lambda _: None)
        manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["configuration"]["cwd"], "app")
        self.assertEqual(manifest["configuration"]["command"][1], "server.py")
        self.assertEqual(manifest["inspect_roots"], ["app/server.py"])
        gateway = StdioGateway(Path(result["manifest"]), self.state_root / "example" / "state", interface="execution")
        self.addCleanup(gateway.backend.close)
        response = gateway.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                   "params": {"name": "echo", "arguments": {"value": "nested"}}})
        self.assertEqual(response["result"]["content"][0]["text"], "nested")

    def test_mastertool_launcher_uses_verified_python_copy_and_blocks_changes(self):
        project = self.temp / "mastertool"
        scripts = project / "scripts"
        package = project / "mastertool_mcp"
        scripts.mkdir(parents=True)
        package.mkdir()
        (project / "server.py").write_text(SERVER_SOURCE, encoding="utf-8")
        module = package / "server.py"
        module.write_text("# module included in approved version\n", encoding="utf-8")
        (package / "__init__.py").write_text("", encoding="utf-8")
        nested = package / "helpers"
        nested.mkdir()
        (nested / "extra.py").write_text("# nested module\n", encoding="utf-8")
        venv.EnvBuilder(with_pip=False).create(project / ".venv")
        launcher = scripts / "run_server.cmd"
        launcher.write_text(
            '@echo off\nsetlocal\nset "SCRIPT_DIR=%~dp0"\n'
            'for %%I in ("%SCRIPT_DIR%..") do set "PACKAGE_ROOT=%%~fI"\n'
            'if not defined MASTERTOOL_MCP_WORKSPACE (\n'
            '  set "MASTERTOOL_MCP_WORKSPACE=%USERPROFILE%\\Documents\\MasterToolMCP"\n)\n'
            'if not defined MASTERTOOL_EXECUTABLE (\n'
            '  set "MASTERTOOL_EXECUTABLE=C:\\Program Files (x86)\\Altus\\MasterTool IEC\\MToolIEC.exe"\n)\n'
            'if exist "%PACKAGE_ROOT%\\.venv\\Scripts\\python.exe" (\n'
            '  "%PACKAGE_ROOT%\\.venv\\Scripts\\python.exe" "%PACKAGE_ROOT%\\server.py"\n'
            '  exit /b %ERRORLEVEL%\n)\n',
            encoding="utf-8",
        )
        self.config.write_text(
            '[mcp_servers.example]\n'
            f'command = {json.dumps(str(launcher))}\n'
            f'cwd = {json.dumps(str(project))}\n'
            'default_tools_approval_mode = "prompt"\n'
            'env = { MASTERTOOL_MCP_WORKSPACE = "" }\n', encoding="utf-8",
        )
        result, messages = self.run_answers("", "", "DESCOBRIR", "APROVAR", "SUBSTITUIR")
        self.assertEqual(result["status"], "connected_restart_required")
        self.assertIn("Launcher MasterTool reconhecido", messages)
        manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["configuration"]["command"],
                         [str((project / ".venv" / "Scripts" / "python.exe").resolve()), "server.py"])
        self.assertEqual(set(manifest["inspect_roots"]),
                         {"server.py", "mastertool_mcp/server.py", "mastertool_mcp/__init__.py",
                          "mastertool_mcp/helpers/extra.py"})
        self.assertTrue(all(not item["path"].startswith(".venv/") for item in
                            capture(Path(result["manifest"]))["files"]))
        configured = tomllib.loads(self.config.read_text(encoding="utf-8"))
        execution = configured["mcp_servers"]["example"]
        self.assertIn("MASTERTOOL_MCP_WORKSPACE", execution["env"])
        self.assertIn("MASTERTOOL_EXECUTABLE", execution["env"])
        self.assertTrue(execution["env"]["MASTERTOOL_MCP_WORKSPACE"])
        self.assertEqual(execution["default_tools_approval_mode"], "prompt")
        gateway = StdioGateway(Path(result["manifest"]), self.state_root / "example" / "state", interface="execution")
        self.addCleanup(gateway.backend.close)
        response = gateway.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                   "params": {"name": "echo", "arguments": {"value": "working"}}})
        self.assertEqual(response["result"]["content"][0]["text"], "working")
        gateway.backend.close()
        module.write_text("# later change\n", encoding="utf-8")
        blocked_gateway = StdioGateway(Path(result["manifest"]), self.state_root / "example" / "state", interface="execution")
        self.addCleanup(blocked_gateway.backend.close)
        blocked = blocked_gateway.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                          "params": {"name": "echo", "arguments": {"value": "working"}}})
        self.assertEqual(blocked["result"]["structuredContent"]["status"], "security_review_required")
        self.assertEqual(blocked_gateway.backend.lifecycle.snapshot()["spawn_attempts"], 0)

    def test_unknown_batch_launcher_is_rejected_without_changes(self):
        launcher = self.project / "other.cmd"
        launcher.write_text("@echo off\n", encoding="utf-8")
        self.config.write_text(self.config.read_text(encoding="utf-8")
                               .replace(json.dumps(sys.executable), json.dumps(str(launcher)))
                               .replace(f'args = [{json.dumps(str(self.script))}]', 'args = []'),
                               encoding="utf-8")
        original = self.config.read_bytes()
        with self.assertRaisesRegex(SentryError, "launcher .cmd não reconhecido"):
            self.run_answers("")
        self.assertEqual(self.config.read_bytes(), original)
        self.assertFalse(self.state_root.exists())


if __name__ == "__main__":
    unittest.main()
