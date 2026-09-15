from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from support import load_script


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_activator = load_script(
    PROJECT_ROOT / "ferramentas-para-demonstracao" / "scripts-em-python" / "activate_demo_version.py",
    "activate_demo_version",
)
VERSIONS = _activator.VERSIONS
activate = _activator.activate


class DemoActivationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.destination = self.root / "active_version" / "provider.py"
        self.state = self.root / "state.json"
        self.mutations = self.root / "mutations.json"
        self.audit = self.root / "audit.jsonl"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_session(self) -> None:
        self.state.write_text("{}\n", encoding="utf-8")
        self.mutations.write_text("{}\n", encoding="utf-8")
        self.audit.write_text('{"event_type":"old"}\n', encoding="utf-8")

    def test_approved_activation_starts_a_clean_session(self) -> None:
        self._write_session()
        with (
            patch(
                "activate_demo_version.SESSION_FILES",
                [self.state, self.mutations],
            ),
            patch("activate_demo_version.AUDIT_FILE", self.audit),
        ):
            result = activate(
                "approved",
                self.destination,
                reset_session=True,
                clear_audit=True,
            )

        self.assertEqual(
            self.destination.read_bytes(),
            VERSIONS["approved"].read_bytes(),
        )
        self.assertFalse(self.state.exists())
        self.assertFalse(self.mutations.exists())
        self.assertFalse(self.audit.exists())
        self.assertTrue(result["session_reset"])
        self.assertTrue(result["audit_cleared"])

    def test_rug_pull_activation_preserves_cumulative_audit(self) -> None:
        self._write_session()
        original_audit = self.audit.read_bytes()
        with (
            patch(
                "activate_demo_version.SESSION_FILES",
                [self.state, self.mutations],
            ),
            patch("activate_demo_version.AUDIT_FILE", self.audit),
        ):
            result = activate(
                "rug-pull",
                self.destination,
                reset_session=True,
                clear_audit=False,
            )

        self.assertEqual(
            self.destination.read_bytes(),
            VERSIONS["rug-pull"].read_bytes(),
        )
        self.assertFalse(self.state.exists())
        self.assertFalse(self.mutations.exists())
        self.assertEqual(self.audit.read_bytes(), original_audit)
        self.assertTrue(result["session_reset"])
        self.assertFalse(result["audit_cleared"])


if __name__ == "__main__":
    unittest.main()
