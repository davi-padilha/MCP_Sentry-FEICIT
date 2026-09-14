from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch

from donna_mcp.audit import AuditLog
from donna_mcp.mutations import MutationStore


class MutationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.path = root / "mutations.json"
        self.audit = AuditLog(root / "audit.jsonl")
        self.store = MutationStore(self.path, self.audit)
        self.payload = {"destinatarios": ["pessoa@example.com"]}

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _prepare(self) -> str:
        result = self.store.prepare(
            action="enviar_email",
            payload=self.payload,
            preview=self.payload,
        )
        return result["confirmation_id"]

    def test_concurrent_confirmation_executes_external_effect_once(self) -> None:
        confirmation_id = self._prepare()
        operation_started = threading.Event()
        allow_completion = threading.Event()
        effects: list[str] = []
        first_errors: list[Exception] = []

        def operation(key: str) -> dict[str, str]:
            effects.append(key)
            operation_started.set()
            allow_completion.wait(timeout=5)
            return {"status": "sent"}

        def first_call() -> None:
            try:
                self.store.execute(
                    action="enviar_email",
                    payload=self.payload,
                    confirmation_id=confirmation_id,
                    operation=operation,
                )
            except Exception as exc:  # pragma: no cover - assercao abaixo
                first_errors.append(exc)

        thread = threading.Thread(target=first_call)
        thread.start()
        self.assertTrue(operation_started.wait(timeout=5))
        with self.assertRaisesRegex(ValueError, "ja esta em execucao"):
            self.store.execute(
                action="enviar_email",
                payload=self.payload,
                confirmation_id=confirmation_id,
                operation=operation,
            )
        allow_completion.set()
        thread.join(timeout=5)

        self.assertFalse(thread.is_alive())
        self.assertEqual(first_errors, [])
        self.assertEqual(len(effects), 1)

    def test_failure_after_effect_becomes_unknown_and_is_not_retried(self) -> None:
        confirmation_id = self._prepare()
        effects = 0

        def ambiguous_operation(key: str) -> dict[str, str]:
            nonlocal effects
            effects += 1
            raise TimeoutError("resposta perdida depois do efeito")

        with self.assertRaises(TimeoutError):
            self.store.execute(
                action="enviar_email",
                payload=self.payload,
                confirmation_id=confirmation_id,
                operation=ambiguous_operation,
            )
        with self.assertRaisesRegex(ValueError, "resultado.*incerto"):
            self.store.execute(
                action="enviar_email",
                payload=self.payload,
                confirmation_id=confirmation_id,
                operation=lambda key: {"status": "sent"},
            )

        records = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(records[confirmation_id]["status"], "unknown")
        self.assertEqual(effects, 1)

    def test_failure_to_persist_result_does_not_allow_retry(self) -> None:
        confirmation_id = self._prepare()
        original_save = self.store._save
        effects = 0

        def fail_executed_save(records: dict) -> None:
            if records[confirmation_id].get("status") == "executed":
                raise PermissionError("falha simulada ao persistir resultado")
            original_save(records)

        def operation(key: str) -> dict[str, str]:
            nonlocal effects
            effects += 1
            return {"status": "sent"}

        with patch.object(self.store, "_save", side_effect=fail_executed_save):
            with self.assertRaisesRegex(RuntimeError, "pode ter sido realizada"):
                self.store.execute(
                    action="enviar_email",
                    payload=self.payload,
                    confirmation_id=confirmation_id,
                    operation=operation,
                )

        with self.assertRaisesRegex(ValueError, "resultado.*incerto"):
            self.store.execute(
                action="enviar_email",
                payload=self.payload,
                confirmation_id=confirmation_id,
                operation=operation,
            )
        self.assertEqual(effects, 1)

    def test_audit_failure_before_operation_prevents_external_effect(self) -> None:
        confirmation_id = self._prepare()
        effects = 0

        def operation(key: str) -> dict[str, str]:
            nonlocal effects
            effects += 1
            return {"status": "sent"}

        with patch.object(self.audit, "record", side_effect=PermissionError("audit")):
            with self.assertRaises(PermissionError):
                self.store.execute(
                    action="enviar_email",
                    payload=self.payload,
                    confirmation_id=confirmation_id,
                    operation=operation,
                )
        self.assertEqual(effects, 0)
        records = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(records[confirmation_id]["status"], "unknown")

    def test_confirmation_is_bound_to_its_runtime_security_scope(self) -> None:
        unprotected = MutationStore(
            self.path,
            self.audit,
            scope="simulated-active:sentry=False",
        )
        protected = MutationStore(
            self.path,
            self.audit,
            scope="simulated-active:sentry=True",
        )
        prepared = unprotected.prepare(
            action="enviar_email",
            payload=self.payload,
            preview=self.payload,
        )
        effects = 0

        def operation(key: str) -> dict[str, str]:
            nonlocal effects
            effects += 1
            return {"status": "sent"}

        with self.assertRaisesRegex(ValueError, "dados da chamada diferem"):
            protected.execute(
                action="enviar_email",
                payload=self.payload,
                confirmation_id=prepared["confirmation_id"],
                operation=operation,
            )

        self.assertEqual(effects, 0)
        records = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(
            records[prepared["confirmation_id"]]["status"],
            "pending",
        )


if __name__ == "__main__":
    unittest.main()
