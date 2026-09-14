from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch

from donna_mcp.audit import AuditLog
from donna_mcp.mutations import MutationStore
from donna_mcp.providers.simulated import SimulatedProvider
from donna_mcp.service import SecretaryService


class TimeoutAfterDraftProvider(SimulatedProvider):
    def create_draft(self, **kwargs: object) -> dict:
        super().create_draft(**kwargs)
        raise TimeoutError("resposta perdida depois da criacao do rascunho")


class SecretaryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.audit = AuditLog(root / "audit.jsonl")
        self.provider = SimulatedProvider(root / "state.json", self.audit)
        self.mutations = MutationStore(root / "mutations.json", self.audit)
        self.service = SecretaryService(
            self.provider,
            self.audit,
            self.mutations,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_creates_event_and_draft_in_combined_workflow(self) -> None:
        arguments = {
            "titulo": "Reuniao de teste",
            "inicio": "2030-01-10T14:00:00-03:00",
            "fim": "2030-01-10T14:30:00-03:00",
            "participantes": ["aluno@exemplo.test", "professor@exemplo.test"],
            "pauta": "Revisar a demonstracao.",
            "comunicacao": "rascunho",
        }
        preview = self.service.organizar_reuniao(**arguments)
        self.assertEqual(preview["status"], "confirmation_required")
        result = self.service.organizar_reuniao(
            **arguments,
            confirmacao_id=preview["confirmation_id"],
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["evento"]["status"], "confirmed")
        self.assertEqual(result["comunicacao"]["status"], "draft")
        self.assertEqual(len(result["evento"]["attendees"]), 2)

    def test_confirmation_retry_is_idempotent(self) -> None:
        arguments = {
            "titulo": "Reuniao de teste",
            "inicio": "2030-01-10T14:00:00-03:00",
            "fim": "2030-01-10T14:30:00-03:00",
            "participantes": ["aluno@exemplo.test"],
        }
        preview = self.service.criar_evento(**arguments)
        first = self.service.criar_evento(
            **arguments,
            confirmacao_id=preview["confirmation_id"],
        )
        replay = self.service.criar_evento(
            **arguments,
            confirmacao_id=preview["confirmation_id"],
        )
        self.assertEqual(first["id"], replay["id"])
        self.assertFalse(first["confirmation"]["idempotent_replay"])
        self.assertTrue(replay["confirmation"]["idempotent_replay"])
        created = [
            event
            for event in self.provider._load()["events"]
            if event["id"] == first["id"]
        ]
        self.assertEqual(len(created), 1)

    def test_reschedule_retry_returns_persisted_result(self) -> None:
        creation = {
            "titulo": "Evento a remarcar",
            "inicio": "2030-01-21T14:00:00-03:00",
            "fim": "2030-01-21T14:30:00-03:00",
        }
        prepared = self.service.criar_evento(**creation)
        created = self.service.criar_evento(
            **creation,
            confirmacao_id=prepared["confirmation_id"],
        )
        reschedule = {
            "event_id": created["id"],
            "novo_inicio": "2030-01-21T15:00:00-03:00",
            "novo_fim": "2030-01-21T15:30:00-03:00",
        }
        preview = self.service.remarcar_evento(**reschedule)
        first = self.service.remarcar_evento(
            **reschedule,
            confirmacao_id=preview["confirmation_id"],
        )
        replay = self.service.remarcar_evento(
            **reschedule,
            confirmacao_id=preview["confirmation_id"],
        )

        self.assertEqual(replay["start"], first["start"])
        self.assertEqual(replay["etag"], first["etag"])
        self.assertTrue(replay["confirmation"]["idempotent_replay"])

    def test_cancellation_retry_works_after_event_no_longer_exists(self) -> None:
        creation = {
            "titulo": "Evento a excluir",
            "inicio": "2030-01-22T14:00:00-03:00",
            "fim": "2030-01-22T14:30:00-03:00",
        }
        prepared = self.service.criar_evento(**creation)
        created = self.service.criar_evento(
            **creation,
            confirmacao_id=prepared["confirmation_id"],
        )
        preview = self.service.cancelar_evento(created["id"])
        first = self.service.cancelar_evento(
            created["id"],
            confirmacao_id=preview["confirmation_id"],
        )
        replay = self.service.cancelar_evento(
            created["id"],
            confirmacao_id=preview["confirmation_id"],
        )

        self.assertEqual(first["status"], "cancelled")
        self.assertEqual(replay["id"], first["id"])
        self.assertTrue(replay["confirmation"]["idempotent_replay"])

    def test_concurrent_cancellation_returns_result_to_both_callers(self) -> None:
        creation = {
            "titulo": "Evento a excluir uma vez",
            "inicio": "2030-01-23T14:00:00-03:00",
            "fim": "2030-01-23T14:30:00-03:00",
        }
        prepared = self.service.criar_evento(**creation)
        created = self.service.criar_evento(
            **creation,
            confirmacao_id=prepared["confirmation_id"],
        )
        preview = self.service.cancelar_evento(created["id"])
        confirmation_id = preview["confirmation_id"]

        initial_replays = threading.Barrier(2)
        replay_counter_lock = threading.Lock()
        replay_calls = 0
        original_replay = self.mutations.replay_if_final

        def synchronized_replay(**kwargs: object) -> dict | None:
            nonlocal replay_calls
            with replay_counter_lock:
                replay_calls += 1
                synchronize = replay_calls <= 2
            result = original_replay(**kwargs)
            if synchronize:
                initial_replays.wait(timeout=5)
            return result

        snapshot_counter_lock = threading.Lock()
        snapshot_calls = 0
        first_execution_finished = threading.Event()
        original_snapshot = self.service._event_snapshot

        def coordinated_snapshot(event_id: str) -> dict:
            nonlocal snapshot_calls
            with snapshot_counter_lock:
                snapshot_calls += 1
                call_number = snapshot_calls
            if call_number == 2 and not first_execution_finished.wait(timeout=5):
                raise TimeoutError("a primeira exclusao nao terminou")
            return original_snapshot(event_id)

        results: list[dict] = []
        errors: list[Exception] = []

        def cancel() -> None:
            try:
                results.append(
                    self.service.cancelar_evento(
                        created["id"],
                        confirmacao_id=confirmation_id,
                    )
                )
            except Exception as exc:  # pragma: no cover - assercao abaixo
                errors.append(exc)
            finally:
                first_execution_finished.set()

        with (
            patch.object(
                self.mutations,
                "replay_if_final",
                side_effect=synchronized_replay,
            ),
            patch.object(
                self.service,
                "_event_snapshot",
                side_effect=coordinated_snapshot,
            ),
        ):
            threads = [threading.Thread(target=cancel) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 2)
        self.assertEqual({result["status"] for result in results}, {"cancelled"})
        self.assertEqual({result["id"] for result in results}, {created["id"]})
        self.assertEqual(
            sorted(
                result["confirmation"]["idempotent_replay"]
                for result in results
            ),
            [False, True],
        )

    def test_finds_free_slots_without_overlapping_event(self) -> None:
        arguments = {
            "titulo": "Ocupado",
            "inicio": "2030-01-10T14:00:00-03:00",
            "fim": "2030-01-10T15:00:00-03:00",
        }
        preview = self.service.criar_evento(**arguments)
        self.service.criar_evento(
            **arguments,
            confirmacao_id=preview["confirmation_id"],
        )
        result = self.service.encontrar_horarios_livres(
            inicio="2030-01-10T13:00:00-03:00",
            fim="2030-01-10T16:00:00-03:00",
            duracao_minutos=30,
            limite=10,
        )
        starts = {slot["inicio"] for slot in result["horarios_livres"]}
        self.assertIn("2030-01-10T13:00:00-03:00", starts)
        self.assertNotIn("2030-01-10T14:00:00-03:00", starts)
        self.assertNotIn("2030-01-10T14:30:00-03:00", starts)
        self.assertIn("2030-01-10T15:00:00-03:00", starts)

    def test_rejects_conflicting_event_unless_explicitly_allowed(self) -> None:
        busy_arguments = {
            "titulo": "Ocupado",
            "inicio": "2030-01-10T14:00:00-03:00",
            "fim": "2030-01-10T15:00:00-03:00",
        }
        preview = self.service.criar_evento(**busy_arguments)
        self.service.criar_evento(
            **busy_arguments,
            confirmacao_id=preview["confirmation_id"],
        )
        with self.assertRaisesRegex(ValueError, "conflita"):
            self.service.criar_evento(
                titulo="Conflito",
                inicio="2030-01-10T14:30:00-03:00",
                fim="2030-01-10T15:30:00-03:00",
            )

    def test_reports_unknown_when_draft_times_out_after_effect(self) -> None:
        root = Path(self.temp_dir.name)
        provider = TimeoutAfterDraftProvider(
            root / "ambiguous-state.json",
            self.audit,
        )
        service = SecretaryService(provider, self.audit, self.mutations)
        arguments = {
            "titulo": "Reuniao parcial",
            "inicio": "2030-01-11T14:00:00-03:00",
            "fim": "2030-01-11T14:30:00-03:00",
            "participantes": ["aluno@exemplo.test"],
            "pauta": "Testar falha parcial.",
            "comunicacao": "rascunho",
        }
        preview = service.organizar_reuniao(**arguments)
        result = service.organizar_reuniao(
            **arguments,
            confirmacao_id=preview["confirmation_id"],
        )
        self.assertEqual(result["status"], "partial_unknown")
        self.assertEqual(result["evento"]["status"], "confirmed")
        self.assertEqual(result["comunicacao"]["status"], "unknown")
        self.assertEqual(result["confirmation"]["status"], "unknown")
        self.assertFalse(result["confirmation"]["retry_allowed"])
        self.assertEqual(len(provider._load()["drafts"]), 1)
        with self.assertRaisesRegex(ValueError, "resultado.*incerto"):
            service.organizar_reuniao(
                **arguments,
                confirmacao_id=preview["confirmation_id"],
            )

    def test_partial_unknown_survives_secondary_audit_failure(self) -> None:
        root = Path(self.temp_dir.name)
        provider = TimeoutAfterDraftProvider(
            root / "audit-failure-state.json",
            self.audit,
        )
        service = SecretaryService(provider, self.audit, self.mutations)
        arguments = {
            "titulo": "Reuniao com auditoria indisponivel",
            "inicio": "2030-01-17T14:00:00-03:00",
            "fim": "2030-01-17T14:30:00-03:00",
            "participantes": ["aluno@exemplo.test"],
            "pauta": "Preservar resposta informativa.",
            "comunicacao": "rascunho",
        }
        preview = service.organizar_reuniao(**arguments)
        original_record = self.audit.record

        def fail_only_partial_audit(event_type: str, **details: object) -> dict:
            if event_type == "meeting_workflow_partial_failure":
                raise PermissionError("auditoria parcial indisponivel")
            return original_record(event_type, **details)

        with patch.object(self.audit, "record", side_effect=fail_only_partial_audit):
            result = service.organizar_reuniao(
                **arguments,
                confirmacao_id=preview["confirmation_id"],
            )

        self.assertEqual(result["status"], "partial_unknown")
        self.assertEqual(result["confirmation"]["status"], "unknown")
        self.assertIn("audit_warning", result["comunicacao"])
        self.assertEqual(len(provider._load()["drafts"]), 1)

    def test_cancel_preview_identifies_the_current_event(self) -> None:
        arguments = {
            "titulo": "Evento a cancelar",
            "inicio": "2030-01-12T14:00:00-03:00",
            "fim": "2030-01-12T14:30:00-03:00",
        }
        prepared = self.service.criar_evento(**arguments)
        created = self.service.criar_evento(
            **arguments,
            confirmacao_id=prepared["confirmation_id"],
        )

        preview = self.service.cancelar_evento(created["id"])

        current = preview["preview"]["evento_atual"]
        self.assertEqual(current["titulo"], arguments["titulo"])
        self.assertEqual(current["inicio"], arguments["inicio"])
        self.assertEqual(current["fim"], arguments["fim"])

    def test_event_change_invalidates_existing_confirmation(self) -> None:
        arguments = {
            "titulo": "Evento mutavel",
            "inicio": "2030-01-13T14:00:00-03:00",
            "fim": "2030-01-13T14:30:00-03:00",
        }
        prepared = self.service.criar_evento(**arguments)
        created = self.service.criar_evento(
            **arguments,
            confirmacao_id=prepared["confirmation_id"],
        )
        cancellation = self.service.cancelar_evento(created["id"])
        self.provider.update_event(
            created["id"],
            start="2030-01-13T15:00:00-03:00",
            end="2030-01-13T15:30:00-03:00",
            send_updates=False,
        )

        with self.assertRaisesRegex(ValueError, "dados mudaram"):
            self.service.cancelar_evento(
                created["id"],
                confirmacao_id=cancellation["confirmation_id"],
            )

    def test_description_change_invalidates_existing_confirmation(self) -> None:
        arguments = {
            "titulo": "Evento com descricao",
            "inicio": "2030-01-15T14:00:00-03:00",
            "fim": "2030-01-15T14:30:00-03:00",
            "descricao": "Descricao original",
        }
        prepared = self.service.criar_evento(**arguments)
        created = self.service.criar_evento(
            **arguments,
            confirmacao_id=prepared["confirmation_id"],
        )
        cancellation = self.service.cancelar_evento(created["id"])
        state = self.provider._load()
        event = next(item for item in state["events"] if item["id"] == created["id"])
        event["description"] = "Descricao alterada externamente"
        self.provider._save(state)

        with self.assertRaisesRegex(ValueError, "dados mudaram"):
            self.service.cancelar_evento(
                created["id"],
                confirmacao_id=cancellation["confirmation_id"],
            )

    def test_provider_precondition_blocks_change_after_confirmation_read(self) -> None:
        arguments = {
            "titulo": "Evento com versao",
            "inicio": "2030-01-16T14:00:00-03:00",
            "fim": "2030-01-16T14:30:00-03:00",
        }
        prepared = self.service.criar_evento(**arguments)
        created = self.service.criar_evento(
            **arguments,
            confirmacao_id=prepared["confirmation_id"],
        )
        stale_etag = created["etag"]
        self.provider.update_event(
            created["id"],
            start="2030-01-16T15:00:00-03:00",
            end="2030-01-16T15:30:00-03:00",
            send_updates=False,
        )

        with self.assertRaisesRegex(RuntimeError, "mudou depois da confirmacao"):
            self.provider.delete_event(
                created["id"],
                send_updates=False,
                expected_etag=stale_etag,
            )
        self.assertEqual(self.provider.get_event(created["id"])["status"], "confirmed")

    def test_meeting_requires_at_least_one_participant(self) -> None:
        with self.assertRaisesRegex(ValueError, "pelo menos um participante"):
            self.service.organizar_reuniao(
                titulo="Reuniao vazia",
                inicio="2030-01-14T14:00:00-03:00",
                fim="2030-01-14T14:30:00-03:00",
                participantes=[],
                pauta="Sem participantes.",
            )

    def test_rejects_naive_datetime(self) -> None:
        with self.assertRaisesRegex(ValueError, "fuso horario"):
            self.service.consultar_agenda(
                "2030-01-10T13:00:00", "2030-01-10T14:00:00"
            )

    def test_rejects_invalid_email(self) -> None:
        with self.assertRaisesRegex(ValueError, "Endereco invalido"):
            self.service.criar_rascunho_email(
                ["endereco-invalido"], "Assunto", "Mensagem"
            )

    def test_email_reads_validate_limits_and_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "limite"):
            self.service.buscar_emails(limite=21)
        with self.assertRaisesRegex(ValueError, "message_id invalido"):
            self.service.ler_email("id com espacos")
        with self.assertRaisesRegex(ValueError, "limite_bytes"):
            self.service.ler_anexo_email("msg-1", "att-1", limite_bytes=2_000_000)

    def test_email_search_is_read_only_and_marks_content_untrusted(self) -> None:
        result = self.service.buscar_emails()

        self.assertEqual(result["consulta"], "in:inbox")
        self.assertEqual(result["emails"], [])
        self.assertTrue(result["conteudo_nao_confiavel"])


if __name__ == "__main__":
    unittest.main()
