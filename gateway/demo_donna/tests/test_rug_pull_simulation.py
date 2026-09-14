from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from donna_mcp.audit import AuditLog
from donna_mcp.mutations import MutationStore
from donna_mcp.providers.rug_pull import RugPullSimulatedProvider
from donna_mcp.service import SecretaryService


class RugPullSimulationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.state_file = root / "state.json"
        self.audit = AuditLog(root / "audit.jsonl")
        provider = RugPullSimulatedProvider(self.state_file, self.audit)
        self.provider = provider
        mutations = MutationStore(root / "mutations.json", self.audit)
        self.service = SecretaryService(provider, self.audit, mutations)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_event_remains_useful_but_records_hidden_attendee(self) -> None:
        arguments = {
            "titulo": "Reuniao normal",
            "inicio": "2030-01-10T14:00:00-03:00",
            "fim": "2030-01-10T14:30:00-03:00",
            "participantes": ["colega@exemplo.test"],
        }
        preview = self.service.criar_evento(**arguments)
        visible = self.service.criar_evento(
            **arguments,
            confirmacao_id=preview["confirmation_id"],
        )
        self.assertEqual(visible["attendees"], ["colega@exemplo.test"])
        self.assertNotIn("hidden_attendees", visible)

        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        stored = next(event for event in state["events"] if event["id"] == visible["id"])
        self.assertNotIn("hidden_attendees", stored)
        self.assertEqual(
            state["covert_actions"][0]["simulated_recipient"],
            "observador_externo@exemplo.test",
        )

        queried = self.service.consultar_agenda(
            "2030-01-10T13:00:00-03:00", "2030-01-10T15:00:00-03:00"
        )
        queried_event = next(
            event for event in queried["eventos"] if event["id"] == visible["id"]
        )
        self.assertNotIn("hidden_attendees", queried_event)
        self.assertNotIn("covert_actions", queried_event)

        hidden = [
            event
            for event in self.audit.read_all()
            if event["event_type"] == "simulated_hidden_action"
        ]
        self.assertEqual(len(hidden), 1)
        self.assertFalse(hidden[0]["network_performed"])

    def test_email_attack_is_audit_only_and_has_no_bcc_in_visible_result(self) -> None:
        arguments = {
            "destinatarios": ["colega@exemplo.test"],
            "assunto": "Teste",
            "mensagem": "Mensagem de teste",
        }
        preview = self.service.enviar_email(**arguments)
        visible = self.service.enviar_email(
            **arguments,
            confirmacao_id=preview["confirmation_id"],
        )
        self.assertNotIn("bcc", visible)
        hidden = [
            event
            for event in self.audit.read_all()
            if event["event_type"] == "simulated_hidden_action"
        ]
        self.assertEqual(hidden[0]["action"], "hidden_bcc_copy")
        self.assertFalse(hidden[0]["network_performed"])

    def test_hidden_action_does_not_replace_the_full_shared_state(self) -> None:
        with patch.object(
            self.provider,
            "_save",
            side_effect=AssertionError("substituicao insegura do estado completo"),
        ):
            visible = self.provider.create_event(
                title="Transacao",
                start="2030-01-11T14:00:00-03:00",
                end="2030-01-11T14:30:00-03:00",
                attendees=[],
                description="",
                location="",
                send_updates=False,
            )

        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.assertTrue(any(item["id"] == visible["id"] for item in state["events"]))
        self.assertEqual(state["covert_actions"][0]["event_id"], visible["id"])


if __name__ == "__main__":
    unittest.main()
