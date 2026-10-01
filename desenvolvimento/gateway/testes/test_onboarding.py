"""Exercise the end-user Codex preparation flow without changing real config."""

import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp_sentry_gateway.core import SentryError, approve
from mcp_sentry_gateway.cli import main as cli_main
from mcp_sentry_gateway.onboarding import doctor, prepare_codex
from test_gateway_universal import SERVER_SOURCE


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="mcp-sentry-client-test-", dir=Path(__file__).parent))
        self.addCleanup(shutil.rmtree, self.temp, True)
        self.project = self.temp / "server"
        self.project.mkdir()
        (self.project / "server.py").write_text(SERVER_SOURCE, encoding="utf-8")
        self.config = self.temp / "config"
        self.config.mkdir()
        self.manifest = self.config / "manifest.json"
        self.fragment = self.config / "codex.toml"
        self.store = self.temp / "state"

    def args(self):
        return argparse.Namespace(
            name="example", project_root=self.project, inspect_root=["server.py"],
            manifest=self.manifest, store=self.store, fragment=self.fragment,
            passthrough_name=None, backend_command=["--", sys.executable, "server.py"],
        )

    def test_prepare_review_approve_and_diagnose(self):
        result = prepare_codex(self.args())
        self.assertEqual(result["status"], "prepared_for_review")
        self.assertFalse(result["approved"])
        self.assertFalse(self.store.exists())
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual([tool["name"] for tool in manifest["metadata"]["tools"]], ["echo"])
        fragment = tomllib.loads(self.fragment.read_text(encoding="utf-8"))
        self.assertEqual(set(fragment["mcp_servers"]), {"example", "mcp_sentry_review_example"})
        self.assertEqual(doctor(self.manifest, self.store)["status"], "needs_attention")
        approve(self.manifest, self.store)
        self.assertEqual(doctor(self.manifest, self.store)["status"], "ready")
        self.assertEqual(doctor(self.manifest, self.store, self.fragment, "example")["status"], "ready")
        changed = self.fragment.read_text(encoding="utf-8").replace('"execution"', '"review"', 1)
        self.fragment.write_text(changed, encoding="utf-8")
        self.assertEqual(doctor(self.manifest, self.store, self.fragment, "example")["status"], "needs_attention")

    def test_does_not_overwrite_existing_file(self):
        self.fragment.write_text("keep me", encoding="utf-8")
        with self.assertRaisesRegex(SentryError, "não sobrescrevo"):
            prepare_codex(self.args())
        self.assertEqual(self.fragment.read_text(encoding="utf-8"), "keep me")
        self.assertFalse(self.manifest.exists())

    def test_rejects_same_output_path(self):
        args = self.args()
        args.fragment = args.manifest
        with self.assertRaisesRegex(SentryError, "caminhos diferentes"):
            prepare_codex(args)

    def test_prepare_uses_absolute_project_path_across_windows_drives(self):
        with mock.patch("mcp_sentry_gateway.onboarding.os.path.relpath",
                        side_effect=ValueError("path is on mount 'E:', start on mount 'C:'")):
            result = prepare_codex(self.args())
        self.assertEqual(result["status"], "prepared_for_review")
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(manifest["project_root"], str(self.project.resolve()))
        self.assertEqual(doctor(self.manifest, self.store)["status"], "needs_attention")

    def test_discovery_uses_configured_backend_timeout(self):
        args = self.args()
        args.backend_timeout_sec = 37
        with mock.patch("mcp_sentry_gateway.onboarding.discover_tools", return_value=[{
            "name": "echo", "inputSchema": {"type": "object"},
        }]) as discover:
            prepare_codex(args)
        self.assertEqual(discover.call_args.args[-1], 37)

    def test_cli_routes_prepare_command(self):
        argv = [
            "mcp-sentry", "prepare-codex", "--name", "example",
            "--project-root", str(self.project), "--inspect-root", "server.py",
            "--manifest", str(self.manifest), "--store", str(self.store),
            "--fragment", str(self.fragment), "--", sys.executable, "server.py",
        ]
        output = io.StringIO()
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(output):
            self.assertEqual(cli_main(), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "prepared_for_review")


if __name__ == "__main__":
    unittest.main()
