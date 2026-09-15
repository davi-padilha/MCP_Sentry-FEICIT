from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class EntrypointIsolationTests(unittest.TestCase):
    def _inspect_imports(self, script_name: str) -> dict[str, bool]:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = dict(os.environ)
            environment.update(
                {
                    "MCP_SECRETARY_AUDIT_FILE": str(root / "audit.jsonl"),
                    "MCP_SECRETARY_SIMULATED_STATE_FILE": str(root / "state.json"),
                    "MCP_SECRETARY_MUTATION_STORE_FILE": str(
                        root / "mutations.json"
                    ),
                }
            )
            entrypoints = PROJECT_ROOT / "inicializacao-do-mcp"
            code = (
                f"import sys; sys.path.insert(0, {str(entrypoints)!r}); import {script_name}, json; "
                "print(json.dumps({"
                "'google_api': 'googleapiclient' in sys.modules, "
                "'google_oauth': 'google_auth_oauthlib' in sys.modules, "
                "'rug_provider': 'donna_mcp.providers.rug_pull' in sys.modules"
                "}))"
            )
            completed = subprocess.run(
                [sys.executable, "-c", code],
                cwd=PROJECT_ROOT,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
            return json.loads(completed.stdout.strip())

    def test_approved_entrypoint_loads_neither_google_nor_rug_provider(self) -> None:
        imports = self._inspect_imports("server_aprovado")
        self.assertEqual(
            imports,
            {"google_api": False, "google_oauth": False, "rug_provider": False},
        )

    def test_rug_entrypoint_loads_no_google_libraries(self) -> None:
        imports = self._inspect_imports("server_rug_pull_simulado")
        self.assertFalse(imports["google_api"])
        self.assertFalse(imports["google_oauth"])
        self.assertTrue(imports["rug_provider"])


if __name__ == "__main__":
    unittest.main()
