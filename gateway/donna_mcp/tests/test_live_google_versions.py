from __future__ import annotations

import base64
from email import message_from_bytes
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock

from donna_mcp.audit import AuditLog


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVATOR_PATH = PROJECT_ROOT / "scripts" / "python" / "activate_google_live_version.py"
RUG_PULL_PATH = PROJECT_ROOT / "examples" / "demo_versions" / "google_live" / "rug_pull" / "provider.py"


def _load_activator():
    spec = importlib.util.spec_from_file_location("activate_google_live_version", ACTIVATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LiveGoogleVersionTests(unittest.TestCase):
    def test_activation_replaces_the_same_active_file(self) -> None:
        activator = _load_activator()
        with TemporaryDirectory() as temporary:
            active = Path(temporary) / "active" / "provider.py"
            approved_hash = activator.activate("approved", active)
            approved_source = active.read_text(encoding="utf-8")
            rug_hash = activator.activate("rug-pull", active)
            rug_source = active.read_text(encoding="utf-8")

        self.assertNotEqual(approved_hash, rug_hash)
        self.assertNotEqual(approved_source, rug_source)
        self.assertIn("hidden_recipient", rug_source)

    def test_rug_pull_adds_bcc_without_exposing_it_in_result(self) -> None:
        namespace: dict[str, object] = {"__name__": "test_rug_pull_provider"}
        exec(RUG_PULL_PATH.read_text(encoding="utf-8"), namespace)
        provider_class = namespace["ActiveGoogleProvider"]
        provider = provider_class.__new__(provider_class)
        with TemporaryDirectory() as temporary:
            provider.audit = AuditLog(Path(temporary) / "audit.jsonl")
            provider.gmail = MagicMock()
            send = provider.gmail.users.return_value.messages.return_value.send
            send.return_value.execute.return_value = {"id": "message-1"}
            result = provider.send_email(
                recipients=["destinatario@example.com"],
                subject="Mensagem de teste",
                body="Conteudo controlado.",
                cc=[],
            )
            raw = send.call_args.kwargs["body"]["raw"]
            events = provider.audit.read_all()

        message = message_from_bytes(base64.urlsafe_b64decode(raw))
        self.assertEqual(message["Bcc"], "23000315@liberato.com.br")
        self.assertNotIn("bcc", result)
        self.assertEqual(events[-1]["event_type"], "hidden_bcc_copy")
