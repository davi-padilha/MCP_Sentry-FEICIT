import json, os, shutil, subprocess, sys, tempfile, unittest, uuid
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / "codigo_gateway"))
from mcp_sentry_gateway.core import approve
from mcp_sentry_gateway.gateway import StdioGateway

GATEWAY_ROOT = Path(__file__).parents[1]
DONNA = GATEWAY_ROOT.parent / "demonstracao-donna"
TEMPLATE = GATEWAY_ROOT / "configuracao_demo" / "CONFIGURACAO_DA_DONNA.json"
def _donna_python():
    override = os.getenv("MCP_SENTRY_DONNA_PYTHON")
    if override:
        return str(Path(override).resolve())
    for candidate in (
        DONNA / ".venv" / "Scripts" / "python.exe",
        DONNA / ".venv" / "bin" / "python",
    ):
        if candidate.is_file():
            return str(candidate.resolve())
    # A clean checkout must use the suite environment and fail explicitly when
    # the pinned Donna dependency is not installed; this test is never skipped.
    return str(Path(sys.executable).resolve())

DONNA_PYTHON = _donna_python()


class T5Tests(unittest.TestCase):
    def test_clean_checkout_uses_suite_interpreter_instead_of_skipping(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            Path, "is_file", return_value=False
        ):
            self.assertEqual(_donna_python(), str(Path(sys.executable).resolve()))

    def test_simulated_donna_runs_only_from_verified_copy(self):
        dependency = subprocess.run(
            [DONNA_PYTHON, "-c", "import importlib.metadata as m; assert m.version('mcp') == '1.29.0'"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            dependency.returncode,
            0,
            "Donna simulation requires the pinned mcp==1.29.0 in "
            f"{DONNA_PYTHON}: {dependency.stderr.strip()}",
        )
        temp = Path(tempfile.gettempdir()) / ("mcp-sentry-t5-test-" + uuid.uuid4().hex)
        self.addCleanup(shutil.rmtree, temp, True)
        project = temp / "donna"
        shutil.copytree(
            DONNA,
            project,
            ignore=shutil.ignore_patterns(".venv", "dados-gerados-pelo-mcp", "versao-em-uso-do-mcp", "local_data", "__pycache__", "*.pyc"),
        )
        state = temp / "state"; state.mkdir()
        active = project / "versao-em-uso-do-mcp/simulacao-controlada/provider.py"
        active.parent.mkdir(parents=True)
        shutil.copyfile(project / "versoes-para-demonstracao/simulacao-controlada/versao-aprovada/provider.py", active)
        manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(manifest["configuration"]["runtime_paths"]["MCP_SECRETARY_ACTIVE_PROVIDER_FILE"], "versao-em-uso-do-mcp/simulacao-controlada/provider.py")
        manifest["project_root"] = "../donna"
        manifest["configuration"]["command"][0] = DONNA_PYTHON
        manifest_path = state / "manifest.json"; manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        store = temp / "store"; approve(manifest_path, store)
        gateway = StdioGateway(manifest_path, store); self.addCleanup(gateway.backend.close)
        response = gateway.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "descrever_donna", "arguments": {}}})["result"]
        self.assertFalse(response.get("isError"), response)
        self.assertIn("content", response)
        self.assertTrue(gateway.backend.copy_root.is_dir())
        self.assertFalse((project / "dados-gerados-pelo-mcp" / "estado-da-simulacao.json").exists())
        gateway.backend.close()
        shutil.copyfile(project / "versoes-para-demonstracao/simulacao-controlada/alteracao-maliciosa-simulada/provider.py", active)
        changed = StdioGateway(manifest_path, store)
        self.addCleanup(changed.backend.close)
        blocked = changed.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "enviar_email", "arguments": {"destinatarios": ["demo@example.test"], "assunto": "Teste", "mensagem": "Teste"}}})["result"]
        self.assertNotIn("isError", blocked)
        self.assertEqual(blocked["structuredContent"]["status"], "security_review_required")
        self.assertEqual(blocked["structuredContent"]["semantic_review_status"], "not_evaluated")
        self.assertNotIn("assessment", blocked["structuredContent"])
        self.assertIsNone(changed.backend.process)
