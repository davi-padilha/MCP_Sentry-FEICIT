import json, shutil, sys, tempfile, unittest, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "gateway" / "src"))
from mcp_sentry_gateway.core import SentryError, approve, capture, inspect, run

MANIFEST = Path(__file__).parents[1] / "examples" / "mcp_minimo" / "manifest.json"

class T1Tests(unittest.TestCase):
    def test_approve_and_inspect_are_deterministic(self):
        store = Path(tempfile.gettempdir()) / ("mcp-sentry-t1-test-" + uuid.uuid4().hex)
        self.assertEqual(approve(MANIFEST, store)["status"], "approved")
        self.assertEqual(inspect(MANIFEST, store)["status"], "unchanged")
        self.assertIn("blocked_by_t1", run(MANIFEST, store)["execution"])
        with self.assertRaises(SentryError): approve(MANIFEST, store)

    def test_store_inside_project_is_refused(self):
        with self.assertRaises(SentryError): approve(MANIFEST, MANIFEST.parent / "state")

    def test_bare_python_is_bound_to_the_approving_interpreter(self):
        command = capture(MANIFEST)["manifest"]["configuration"]["command"]
        self.assertNotEqual(command[0], "python")
        self.assertTrue(Path(command[0]).is_absolute())

    def test_runtime_paths_only_accept_safe_configuration_paths(self):
        temp = Path(tempfile.gettempdir()) / ("mcp-sentry-runtime-paths-" + uuid.uuid4().hex)
        self.addCleanup(shutil.rmtree, temp, True)
        project = temp / "project"; shutil.copytree(MANIFEST.parent, project)
        manifest_path = project / "manifest.json"
        def rejected(mutator):
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8")); mutator(manifest)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(SentryError): approve(manifest_path, temp / uuid.uuid4().hex)
        rejected(lambda data: data["metadata"].update({"runtime_paths": {"token": "runtime/x"}}))
        rejected(lambda data: data["configuration"].update({"runtime_paths": {"MCP_SECRETARY_TOKEN_FILE": "runtime/x"}}))
        rejected(lambda data: data["configuration"].update({"runtime_paths": {"MCP_SECRETARY_AUDIT_FILE": "../escape"}}))
        rejected(lambda data: data["configuration"].update({"runtime_paths": {"MCP_SECRETARY_AUDIT_FILE": 1}}))
        rejected(lambda data: data["configuration"].update({"runtime_paths": {"MCP_SECRETARY_AUDIT_FILE": ["runtime/x"]}}))
        rejected(lambda data: data["configuration"].update({"runtime_paths": {"MCP_SECRETARY_AUDIT_FILE": {"path": "runtime/x"}}}))
