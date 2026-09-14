"""Sanitized, fail-closed evidence of backend process launch attempts."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .core import SentryError, write

LIFECYCLE_SCHEMA_VERSION = 1


def _now():
    return datetime.now(timezone.utc).isoformat()


def _path(store: Path):
    return store / "reports" / "backend-lifecycle-current.json"


def _session_path(store: Path, session_id: str):
    return store / "reports" / f"backend-lifecycle-{session_id}.json"


def read_backend_lifecycle(store: Path):
    """Read only the public, secret-free launch evidence for the current process."""
    try:
        data = json.loads(_path(store).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SentryError("evidência de ciclo de vida do backend ausente ou inválida") from exc
    required = {
        "schema_version", "gateway_session_id", "created_at", "updated_at",
        "spawn_attempts", "last_event",
    }
    if (
        not isinstance(data, dict)
        or set(data) != required
        or data.get("schema_version") != LIFECYCLE_SCHEMA_VERSION
        or not isinstance(data.get("gateway_session_id"), str)
        or not data["gateway_session_id"]
        or not isinstance(data.get("created_at"), str)
        or not isinstance(data.get("updated_at"), str)
        or type(data.get("spawn_attempts")) is not int
        or data["spawn_attempts"] < 0
        or data.get("last_event") not in {
            "gateway_started", "spawn_requested", "backend_started",
            "spawn_failed", "backend_closed",
        }
    ):
        raise SentryError("evidência de ciclo de vida do backend inválida")
    return data


class BackendLifecycle:
    """Persist a counter before every subprocess spawn attempt.

    A persisted zero therefore means that this gateway process never reached
    the subprocess boundary.  Evidence-write failure prevents the spawn.
    """

    def __init__(self, store: Path):
        self.store = store
        self._lock = threading.Lock()
        timestamp = _now()
        self._data = {
            "schema_version": LIFECYCLE_SCHEMA_VERSION,
            "gateway_session_id": uuid.uuid4().hex,
            "created_at": timestamp,
            "updated_at": timestamp,
            "spawn_attempts": 0,
            "last_event": "gateway_started",
        }
        self._persist()

    def _persist(self):
        # Keep immutable session addressing for the evidence package and a
        # stable current pointer for the MCP status surface.
        write(_session_path(self.store, self._data["gateway_session_id"]), self._data)
        write(_path(self.store), self._data)

    def _record(self, event: str, increment=False):
        with self._lock:
            if increment:
                self._data["spawn_attempts"] += 1
            self._data["last_event"] = event
            self._data["updated_at"] = _now()
            self._persist()

    def snapshot(self):
        with self._lock:
            return dict(self._data)

    def spawn_requested(self):
        # This durable write happens before subprocess.Popen. If it fails, the
        # backend is not started and the caller fails closed.
        self._record("spawn_requested", increment=True)

    def backend_started(self):
        self._record("backend_started")

    def spawn_failed(self):
        self._record("spawn_failed")

    def backend_closed(self):
        self._record("backend_closed")
