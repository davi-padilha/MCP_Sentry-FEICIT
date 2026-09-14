"""Provedor local persistente, seguro sob concorrencia de processos."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import threading
from typing import Any, Iterator
from uuid import uuid4

from ..audit import AuditLog


_STATE_THREAD_LOCKS: dict[Path, threading.RLock] = {}
_STATE_THREAD_LOCKS_GUARD = threading.Lock()


def _state_thread_lock_for(path: Path) -> threading.RLock:
    resolved = path.resolve()
    with _STATE_THREAD_LOCKS_GUARD:
        return _STATE_THREAD_LOCKS.setdefault(resolved, threading.RLock())


class SimulatedProvider:
    """Calendario e caixa postal persistentes, totalmente locais."""

    name = "simulated-safe"

    def __init__(self, state_file: Path, audit: AuditLog) -> None:
        self.state_file = state_file
        self.lock_file = state_file.with_suffix(state_file.suffix + ".lock")
        self.audit = audit
        self._thread_lock = _state_thread_lock_for(state_file)
        self._ensure_state()

    def _ensure_state(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with self._thread_lock:
            with self._file_lock():
                if self.state_file.exists():
                    return
                self._save_unlocked(
                    {
                        "events": [
                            {
                                "id": "demo-aula",
                                "title": "Aula de orientacao",
                                "start": "2030-01-10T16:00:00-03:00",
                                "end": "2030-01-10T17:00:00-03:00",
                                "attendees": ["professor@exemplo.test"],
                                "description": "Evento sintetico inicial.",
                                "location": "Sala de demonstracao",
                                "status": "confirmed",
                                "etag": "sim-seed-1",
                            }
                        ],
                        "drafts": [],
                        "sent": [],
                        "inbox": [],
                    }
                )

    def _load(self) -> dict[str, Any]:
        """Leitura compatível para painel e testes, protegida por lock."""

        with self._state_transaction(write=False) as state:
            return deepcopy(state)

    def _save(self, state: dict[str, Any]) -> None:
        """Substituicao compatível e atômica de um estado completo."""

        with self._thread_lock:
            with self._file_lock():
                self._save_unlocked(state)

    @contextmanager
    def _state_transaction(self, *, write: bool) -> Iterator[dict[str, Any]]:
        """Mantem check e write sob o mesmo lock thread/processo."""

        with self._thread_lock:
            with self._file_lock():
                state = self._load_unlocked()
                yield state
                if write:
                    self._save_unlocked(state)

    @contextmanager
    def _file_lock(self) -> Iterator[None]:
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_file.open("a+b") as stream:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - exercitado em ambientes POSIX
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def _load_unlocked(self) -> dict[str, Any]:
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def _save_unlocked(self, state: dict[str, Any]) -> None:
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="\n",
                dir=self.state_file.parent,
                prefix=f".{self.state_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary_path = Path(stream.name)
                json.dump(state, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.state_file)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def list_events(self, start: str, end: str) -> list[dict[str, Any]]:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        with self._state_transaction(write=False) as state:
            events = []
            for event in state["events"]:
                event_start = datetime.fromisoformat(event["start"])
                event_end = datetime.fromisoformat(event["end"])
                if event_start < end_dt and event_end > start_dt:
                    events.append(deepcopy(event))
        self.audit.record("calendar_read", provider=self.name, count=len(events))
        return sorted(events, key=lambda item: item["start"])

    def get_event(self, event_id: str) -> dict[str, Any]:
        with self._state_transaction(write=False) as state:
            event = next(
                (item for item in state["events"] if item["id"] == event_id),
                None,
            )
            if event is None:
                raise KeyError(f"Evento nao encontrado: {event_id}")
            result = deepcopy(event)
        self.audit.record(
            "calendar_event_read",
            provider=self.name,
            event_id=event_id,
        )
        return result

    def search_emails(
        self,
        *,
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        needle = query.lower().replace("in:inbox", "").strip()
        with self._state_transaction(write=False) as state:
            messages = []
            for message in reversed(state.get("inbox", [])):
                searchable = " ".join(
                    str(message.get(field, ""))
                    for field in ("from", "to", "subject", "snippet", "body_text")
                ).lower()
                if needle and needle not in searchable:
                    continue
                messages.append(
                    {
                        key: deepcopy(message.get(key))
                        for key in (
                            "id",
                            "thread_id",
                            "from",
                            "to",
                            "subject",
                            "date",
                            "snippet",
                            "label_ids",
                            "attachments",
                        )
                    }
                )
                if len(messages) >= limit:
                    break
        self.audit.record("email_search", provider=self.name, count=len(messages))
        return messages

    def get_email(self, message_id: str) -> dict[str, Any]:
        with self._state_transaction(write=False) as state:
            message = next(
                (item for item in state.get("inbox", []) if item.get("id") == message_id),
                None,
            )
            if message is None:
                raise KeyError(f"E-mail nao encontrado: {message_id}")
            result = deepcopy(message)
        self.audit.record("email_read", provider=self.name, message_id=message_id)
        return result

    def get_email_attachment(
        self,
        message_id: str,
        attachment_id: str,
        *,
        max_bytes: int,
    ) -> dict[str, Any]:
        message = self.get_email(message_id)
        attachment = next(
            (
                item
                for item in message.get("attachments", [])
                if item.get("attachment_id") == attachment_id
            ),
            None,
        )
        if attachment is None:
            raise KeyError(f"Anexo nao encontrado: {attachment_id}")
        size = int(attachment.get("size", 0))
        if size > max_bytes:
            raise ValueError(
                f"Anexo tem {size} bytes e excede o limite de {max_bytes}."
            )
        result = deepcopy(attachment)
        self.audit.record(
            "email_attachment_read",
            provider=self.name,
            message_id=message_id,
            attachment_id=attachment_id,
            size=size,
        )
        return result

    def create_event(
        self,
        *,
        title: str,
        start: str,
        end: str,
        attendees: list[str],
        description: str,
        location: str,
        send_updates: bool,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        event_id = (
            f"evt-{hashlib.sha256(idempotency_key.encode()).hexdigest()[:20]}"
            if idempotency_key
            else f"evt-{uuid4().hex[:12]}"
        )
        with self._state_transaction(write=True) as state:
            existing = next(
                (item for item in state["events"] if item["id"] == event_id),
                None,
            )
            if existing is not None:
                return deepcopy(existing)
            event = {
                "id": event_id,
                "title": title,
                "start": start,
                "end": end,
                "attendees": list(attendees),
                "description": description,
                "location": location,
                "send_updates": send_updates,
                "status": "confirmed",
                "etag": f"sim-{uuid4().hex}",
            }
            state["events"].append(event)
            result = deepcopy(event)
        self.audit.record(
            "calendar_event_created",
            provider=self.name,
            event_id=event_id,
            attendees=list(attendees),
        )
        return result

    def update_event(
        self,
        event_id: str,
        *,
        start: str,
        end: str,
        send_updates: bool,
        expected_etag: str | None = None,
    ) -> dict[str, Any]:
        with self._state_transaction(write=True) as state:
            event = next(
                (item for item in state["events"] if item["id"] == event_id),
                None,
            )
            if event is None:
                raise KeyError(f"Evento nao encontrado: {event_id}")
            if expected_etag and event.get("etag") != expected_etag:
                raise RuntimeError(
                    "Evento mudou depois da confirmacao; operacao bloqueada."
                )
            event["start"] = start
            event["end"] = end
            event["send_updates"] = send_updates
            event["etag"] = f"sim-{uuid4().hex}"
            result = deepcopy(event)
        self.audit.record(
            "calendar_event_updated",
            provider=self.name,
            event_id=event_id,
            send_updates=send_updates,
        )
        return result

    def delete_event(
        self,
        event_id: str,
        *,
        send_updates: bool,
        expected_etag: str | None = None,
    ) -> dict[str, Any]:
        with self._state_transaction(write=True) as state:
            target = next(
                (event for event in state["events"] if event["id"] == event_id),
                None,
            )
            if target is None:
                raise KeyError(f"Evento nao encontrado: {event_id}")
            if expected_etag and target.get("etag") != expected_etag:
                raise RuntimeError(
                    "Evento mudou depois da confirmacao; operacao bloqueada."
                )
            state["events"] = [
                event for event in state["events"] if event["id"] != event_id
            ]
        self.audit.record(
            "calendar_event_deleted",
            provider=self.name,
            event_id=event_id,
            send_updates=send_updates,
        )
        return {"id": event_id, "status": "cancelled"}

    def create_draft(
        self,
        *,
        recipients: list[str],
        subject: str,
        body: str,
        cc: list[str],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        draft_id = (
            f"draft-{hashlib.sha256(idempotency_key.encode()).hexdigest()[:20]}"
            if idempotency_key
            else f"draft-{uuid4().hex[:12]}"
        )
        with self._state_transaction(write=True) as state:
            existing = next(
                (item for item in state["drafts"] if item["id"] == draft_id),
                None,
            )
            if existing is not None:
                return deepcopy(existing)
            draft = {
                "id": draft_id,
                "recipients": list(recipients),
                "cc": list(cc),
                "subject": subject,
                "body": body,
                "status": "draft",
            }
            state["drafts"].append(draft)
            result = deepcopy(draft)
        self.audit.record(
            "email_draft_created",
            provider=self.name,
            draft_id=draft_id,
            recipients=list(recipients),
        )
        return result

    def send_email(
        self,
        *,
        recipients: list[str],
        subject: str,
        body: str,
        cc: list[str],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        message_id = (
            f"msg-{hashlib.sha256(idempotency_key.encode()).hexdigest()[:20]}"
            if idempotency_key
            else f"msg-{uuid4().hex[:12]}"
        )
        with self._state_transaction(write=True) as state:
            existing = next(
                (item for item in state["sent"] if item["id"] == message_id),
                None,
            )
            if existing is not None:
                return deepcopy(existing)
            message = {
                "id": message_id,
                "recipients": list(recipients),
                "cc": list(cc),
                "subject": subject,
                "body": body,
                "status": "sent",
            }
            state["sent"].append(message)
            result = deepcopy(message)
        self.audit.record(
            "email_sent",
            provider=self.name,
            message_id=message_id,
            recipients=list(recipients),
        )
        return result
