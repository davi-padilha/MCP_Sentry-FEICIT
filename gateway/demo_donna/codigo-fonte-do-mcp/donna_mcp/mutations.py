"""Confirmacao duravel e idempotencia para operacoes externas."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
from tempfile import NamedTemporaryFile
import threading
from typing import Any, Callable, Iterator

from .audit import AuditLog


CONFIRMATION_TTL_MINUTES = 15
_THREAD_LOCKS: dict[Path, threading.RLock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


class UnknownMutationOutcome(RuntimeError):
    """Carrega o resultado parcial de uma operacao com efeito final incerto."""

    def __init__(self, result: dict[str, Any], message: str) -> None:
        super().__init__(message)
        self.result = deepcopy(result)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _payload_digest(
    scope: str,
    action: str,
    payload: dict[str, Any],
) -> str:
    canonical = json.dumps(
        {"scope": scope, "action": action, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _thread_lock_for(path: Path) -> threading.RLock:
    resolved = path.resolve()
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(resolved, threading.RLock())


class MutationStore:
    """Persiste confirmacoes, reivindicacoes e resultados sem repetir efeitos."""

    def __init__(
        self,
        path: Path,
        audit: AuditLog,
        *,
        scope: str = "default",
    ) -> None:
        self.path = path
        self.audit = audit
        self.scope = scope
        self.lock_path = path.with_suffix(path.suffix + ".lock")
        self._thread_lock = _thread_lock_for(path)

    def prepare(
        self,
        *,
        action: str,
        payload: dict[str, Any],
        preview: dict[str, Any],
        request_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        confirmation_id = secrets.token_urlsafe(18)
        created_at = _utc_now()
        expires_at = created_at + timedelta(minutes=CONFIRMATION_TTL_MINUTES)
        with self._locked_records() as records:
            records[confirmation_id] = {
                "action": action,
                "payload_sha256": _payload_digest(self.scope, action, payload),
                "request_sha256": _payload_digest(
                    self.scope,
                    action,
                    request_payload if request_payload is not None else payload,
                ),
                "status": "pending",
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
            }
            self._save(records)
        self.audit.record(
            "mutation_confirmation_requested",
            action=action,
            confirmation_id=confirmation_id,
            expires_at=expires_at.isoformat(),
        )
        return {
            "status": "confirmation_required",
            "action": action,
            "confirmation_id": confirmation_id,
            "expires_at": expires_at.isoformat(),
            "preview": deepcopy(preview),
            "instruction": (
                "Apresente a previa ao usuario. Repita a mesma chamada com "
                "confirmacao_id somente depois de obter confirmacao explicita."
            ),
        }

    def execute(
        self,
        *,
        action: str,
        payload: dict[str, Any],
        confirmation_id: str,
        operation: Callable[[str], dict[str, Any]],
        request_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Reivindica antes do efeito e nunca repete um resultado incerto."""

        payload_sha256 = _payload_digest(self.scope, action, payload)
        replay = self._claim(
            action=action,
            payload_sha256=payload_sha256,
            request_sha256=_payload_digest(
                self.scope,
                action,
                request_payload if request_payload is not None else payload,
            ),
            confirmation_id=confirmation_id,
        )
        if replay is not None:
            return replay

        try:
            self.audit.record(
                "mutation_execution_claimed",
                action=action,
                confirmation_id=confirmation_id,
            )
            result = operation(confirmation_id)
        except UnknownMutationOutcome as exc:
            self._mark_unknown_best_effort(
                confirmation_id,
                stage="operation_failed_or_ambiguous",
                error_type=type(exc).__name__,
            )
            try:
                self.audit.record(
                    "mutation_execution_unknown",
                    action=action,
                    confirmation_id=confirmation_id,
                    error_type=type(exc).__name__,
                )
            except Exception:
                pass
            return self._decorate_unknown_result(
                exc.result,
                confirmation_id=confirmation_id,
            )
        except Exception as exc:
            self._mark_unknown_best_effort(
                confirmation_id,
                stage="operation_failed_or_ambiguous",
                error_type=type(exc).__name__,
            )
            try:
                self.audit.record(
                    "mutation_execution_unknown",
                    action=action,
                    confirmation_id=confirmation_id,
                    error_type=type(exc).__name__,
                )
            except Exception:
                pass
            raise

        try:
            self._mark_executed(
                confirmation_id=confirmation_id,
                payload_sha256=payload_sha256,
                result=result,
            )
        except Exception as exc:
            self._mark_unknown_best_effort(
                confirmation_id,
                stage="result_persistence_failed",
                error_type=type(exc).__name__,
            )
            raise RuntimeError(
                "A acao pode ter sido realizada, mas o resultado nao foi "
                "persistido. Nao repita a confirmacao; reconcilie no provedor."
            ) from exc

        self.audit.record(
            "mutation_executed",
            action=action,
            confirmation_id=confirmation_id,
        )
        return self._decorate_result(
            result,
            confirmation_id=confirmation_id,
            idempotent_replay=False,
        )

    def replay_if_final(
        self,
        *,
        action: str,
        request_payload: dict[str, Any],
        confirmation_id: str,
    ) -> dict[str, Any] | None:
        """Resolve estados finais antes de reler um recurso que pode ter sumido."""

        request_sha256 = _payload_digest(self.scope, action, request_payload)
        with self._locked_records() as records:
            record = records.get(confirmation_id)
            if not record:
                raise ValueError("confirmacao_id desconhecido. Solicite uma nova previa.")
            if record.get("action") != action:
                raise ValueError("confirmacao_id pertence a outra operacao.")
            if record.get("request_sha256") != request_sha256:
                raise ValueError(
                    "Os dados da chamada diferem da previa. Solicite nova confirmacao."
                )

            status = record.get("status")
            if status == "executed":
                return self._decorate_result(
                    deepcopy(record.get("result", {})),
                    confirmation_id=confirmation_id,
                    idempotent_replay=True,
                )
            if status == "executing":
                raise ValueError(
                    "Esta confirmacao ja esta em execucao. Nao a repita; se a "
                    "execucao foi interrompida, reconcilie o resultado no provedor."
                )
            if status == "unknown":
                raise ValueError(
                    "O resultado desta confirmacao e incerto. Nao repita a acao; "
                    "reconcilie o estado no provedor e solicite uma nova previa."
                )
            if status != "pending":
                raise ValueError("confirmacao_id nao esta pendente.")

            expires_at = datetime.fromisoformat(str(record["expires_at"]))
            if _utc_now() > expires_at:
                record["status"] = "expired"
                record["expired_at"] = _utc_now().isoformat()
                self._save(records)
                raise ValueError("confirmacao_id expirado. Solicite uma nova previa.")
        return None

    def _claim(
        self,
        *,
        action: str,
        payload_sha256: str,
        request_sha256: str,
        confirmation_id: str,
    ) -> dict[str, Any] | None:
        with self._locked_records() as records:
            record = records.get(confirmation_id)
            if not record:
                raise ValueError("confirmacao_id desconhecido. Solicite uma nova previa.")
            if record.get("action") != action:
                raise ValueError("confirmacao_id pertence a outra operacao.")
            if record.get("request_sha256") != request_sha256:
                raise ValueError(
                    "Os dados da chamada diferem da previa. Solicite nova confirmacao."
                )

            status = record.get("status")
            if status == "executed":
                result = deepcopy(record.get("result", {}))
                return self._decorate_result(
                    result,
                    confirmation_id=confirmation_id,
                    idempotent_replay=True,
                )
            if status == "executing":
                raise ValueError(
                    "Esta confirmacao ja esta em execucao. Nao a repita; se a "
                    "execucao foi interrompida, reconcilie o resultado no provedor."
                )
            if status == "unknown":
                raise ValueError(
                    "O resultado desta confirmacao e incerto. Nao repita a acao; "
                    "reconcilie o estado no provedor e solicite uma nova previa."
                )

            if record.get("payload_sha256") != payload_sha256:
                raise ValueError(
                    "Os dados mudaram depois da previa. Solicite uma nova confirmacao."
                )

            expires_at = datetime.fromisoformat(str(record["expires_at"]))
            if _utc_now() > expires_at:
                record["status"] = "expired"
                record["expired_at"] = _utc_now().isoformat()
                self._save(records)
                raise ValueError("confirmacao_id expirado. Solicite uma nova previa.")
            if status != "pending":
                raise ValueError("confirmacao_id nao esta pendente.")

            record["status"] = "executing"
            record["execution_started_at"] = _utc_now().isoformat()
            record["execution_owner"] = {
                "pid": os.getpid(),
                "thread": threading.get_ident(),
            }
            self._save(records)
        return None

    def _mark_executed(
        self,
        *,
        confirmation_id: str,
        payload_sha256: str,
        result: dict[str, Any],
    ) -> None:
        with self._locked_records() as records:
            record = records.get(confirmation_id)
            if not record or record.get("payload_sha256") != payload_sha256:
                raise RuntimeError("Registro da execucao mudou inesperadamente.")
            if record.get("status") != "executing":
                raise RuntimeError("Execucao nao possui reivindicacao ativa.")
            record["status"] = "executed"
            record["executed_at"] = _utc_now().isoformat()
            record["result"] = deepcopy(result)
            self._save(records)

    def _mark_unknown_best_effort(
        self,
        confirmation_id: str,
        *,
        stage: str,
        error_type: str,
    ) -> None:
        try:
            with self._locked_records() as records:
                record = records.get(confirmation_id)
                if not record or record.get("status") != "executing":
                    return
                record["status"] = "unknown"
                record["unknown_at"] = _utc_now().isoformat()
                record["ambiguity_stage"] = stage
                record["error_type"] = error_type
                self._save(records)
        except Exception:
            # O estado duravel anterior e "executing", que tambem impede repeticao.
            pass

    @staticmethod
    def _decorate_result(
        result: dict[str, Any],
        *,
        confirmation_id: str,
        idempotent_replay: bool,
    ) -> dict[str, Any]:
        decorated = deepcopy(result)
        decorated["confirmation"] = {
            "status": "executed",
            "confirmation_id": confirmation_id,
            "idempotent_replay": idempotent_replay,
        }
        return decorated

    @staticmethod
    def _decorate_unknown_result(
        result: dict[str, Any],
        *,
        confirmation_id: str,
    ) -> dict[str, Any]:
        decorated = deepcopy(result)
        decorated["confirmation"] = {
            "status": "unknown",
            "confirmation_id": confirmation_id,
            "idempotent_replay": False,
            "retry_allowed": False,
        }
        return decorated

    @contextmanager
    def _locked_records(self) -> Iterator[dict[str, dict[str, Any]]]:
        with self._thread_lock:
            with self._file_lock():
                yield self._load()

    @contextmanager
    def _file_lock(self) -> Iterator[None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+b") as stream:
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

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError("Registro de confirmacoes indisponivel.") from exc
        if not isinstance(value, dict):
            raise RuntimeError("Registro de confirmacoes invalido.")
        return value

    def _save(self, records: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                newline="\n",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary_path = Path(stream.name)
                json.dump(records, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
