from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from entrypoints import dashboard
from donna_mcp.audit import AuditLog


class DashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.audit = AuditLog(Path(self.temp_dir.name) / "audit.jsonl")
        self.original_audit = dashboard.AUDIT
        dashboard.AUDIT = self.audit
        self.server = dashboard.ThreadingHTTPServer(
            (dashboard.HOST, 0), dashboard.DashboardHandler
        )
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        dashboard.AUDIT = self.original_audit
        self.temp_dir.cleanup()

    def test_page_explains_the_three_scenario_outcomes(self) -> None:
        with urlopen(f"{self.base_url}/", timeout=2) as response:
            html = response.read().decode("utf-8")

        self.assertIn('id="scenario-approved"', html)
        self.assertIn('id="scenario-rug-pull"', html)
        self.assertIn('id="scenario-sentry"', html)
        self.assertIn("Fluxo normal observado", html)
        self.assertIn("Ação oculta simulada observada", html)
        self.assertIn("Alteração bloqueada antes do efeito", html)
        self.assertIn("complete ? completedText : pendingText", html)
        self.assertIn('data-label="Horário UTC"', html)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_audit_api_returns_and_clears_events(self) -> None:
        self.audit.record(
            "simulated_hidden_action",
            provider="simulated-updated-active",
            network_performed=False,
        )

        with urlopen(f"{self.base_url}/api/audit", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["event_type"], "simulated_hidden_action")

        request = Request(f"{self.base_url}/api/audit", method="DELETE")
        with urlopen(request, timeout=2) as response:
            self.assertEqual(
                json.loads(response.read().decode("utf-8")),
                {"status": "cleared"},
            )
        self.assertEqual(self.audit.read_all(), [])

    def test_unknown_route_returns_404(self) -> None:
        with self.assertRaises(HTTPError) as error:
            urlopen(f"{self.base_url}/missing", timeout=2)
        self.assertEqual(error.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
