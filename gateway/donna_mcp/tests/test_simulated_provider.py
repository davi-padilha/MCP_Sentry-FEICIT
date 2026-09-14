from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest

from donna_mcp.audit import AuditLog
from donna_mcp.providers.simulated import SimulatedProvider


class SimulatedProviderConcurrencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.provider = SimulatedProvider(
            root / "state.json",
            AuditLog(root / "audit.jsonl"),
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_two_updates_cannot_consume_the_same_etag(self) -> None:
        created = self.provider.create_event(
            title="Concorrencia",
            start="2030-01-20T14:00:00-03:00",
            end="2030-01-20T14:30:00-03:00",
            attendees=[],
            description="",
            location="",
            send_updates=False,
        )
        start_together = threading.Barrier(3)
        successes: list[dict] = []
        errors: list[Exception] = []

        def update(hour: int) -> None:
            start_together.wait(timeout=5)
            try:
                result = self.provider.update_event(
                    created["id"],
                    start=f"2030-01-20T{hour:02d}:00:00-03:00",
                    end=f"2030-01-20T{hour:02d}:30:00-03:00",
                    send_updates=False,
                    expected_etag=created["etag"],
                )
                successes.append(result)
            except Exception as exc:  # pragma: no cover - assercao abaixo
                errors.append(exc)

        threads = [
            threading.Thread(target=update, args=(15,)),
            threading.Thread(target=update, args=(16,)),
        ]
        for thread in threads:
            thread.start()
        start_together.wait(timeout=5)
        for thread in threads:
            thread.join(timeout=5)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], RuntimeError)
        current = self.provider.get_event(created["id"])
        self.assertEqual(current["etag"], successes[0]["etag"])
        self.assertEqual(current["start"], successes[0]["start"])


if __name__ == "__main__":
    unittest.main()
