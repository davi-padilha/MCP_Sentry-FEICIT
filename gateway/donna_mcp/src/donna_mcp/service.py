"""Regras de negocio independentes do protocolo MCP."""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Any, Callable

from .audit import AuditLog
from .mutations import MutationStore, UnknownMutationOutcome
from .providers.base import SecretaryProvider


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GMAIL_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,512}$")
MAX_EMAIL_QUERY_LENGTH = 512
MAX_EMAIL_RESULTS = 20
MAX_ATTACHMENT_BYTES = 1_048_576


def _parse_datetime(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} deve usar ISO 8601, por exemplo 2026-08-20T14:00:00-03:00."
        ) from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} precisa incluir fuso horario.")
    return parsed


def _validate_period(start: str, end: str) -> tuple[datetime, datetime]:
    start_dt = _parse_datetime(start, "inicio")
    end_dt = _parse_datetime(end, "fim")
    if end_dt <= start_dt:
        raise ValueError("fim deve ser posterior a inicio.")
    return start_dt, end_dt


def _validate_emails(values: list[str], field_name: str) -> list[str]:
    normalized: list[str] = []
    for raw_value in values:
        value = raw_value.strip().lower()
        if not EMAIL_PATTERN.match(value):
            raise ValueError(f"Endereco invalido em {field_name}: {raw_value!r}")
        if value not in normalized:
            normalized.append(value)
    return normalized


class SecretaryService:
    """Compoe operacoes de agenda e e-mail sobre um provedor intercambiavel."""

    def __init__(
        self,
        provider: SecretaryProvider,
        audit: AuditLog,
        mutations: MutationStore,
    ) -> None:
        self.provider = provider
        self.audit = audit
        self.mutations = mutations

    def consultar_agenda(self, inicio: str, fim: str) -> dict[str, Any]:
        _validate_period(inicio, fim)
        events = self.provider.list_events(inicio, fim)
        return {"inicio": inicio, "fim": fim, "eventos": events, "total": len(events)}

    def buscar_emails(
        self,
        consulta: str = "in:inbox",
        limite: int = 10,
    ) -> dict[str, Any]:
        query = consulta.strip()
        if len(query) > MAX_EMAIL_QUERY_LENGTH:
            raise ValueError(
                f"consulta deve ter no maximo {MAX_EMAIL_QUERY_LENGTH} caracteres."
            )
        if limite < 1 or limite > MAX_EMAIL_RESULTS:
            raise ValueError(f"limite deve ficar entre 1 e {MAX_EMAIL_RESULTS}.")
        emails = self.provider.search_emails(query=query, limit=limite)
        return {
            "consulta": query,
            "emails": emails,
            "total": len(emails),
            "conteudo_nao_confiavel": True,
        }

    def ler_email(self, message_id: str) -> dict[str, Any]:
        normalized_id = self._validate_gmail_id(message_id, "message_id")
        result = self.provider.get_email(normalized_id)
        return {**result, "conteudo_nao_confiavel": True}

    def ler_anexo_email(
        self,
        message_id: str,
        attachment_id: str,
        limite_bytes: int = 262_144,
    ) -> dict[str, Any]:
        normalized_message_id = self._validate_gmail_id(message_id, "message_id")
        normalized_attachment_id = self._validate_gmail_id(
            attachment_id,
            "attachment_id",
        )
        if limite_bytes < 1 or limite_bytes > MAX_ATTACHMENT_BYTES:
            raise ValueError(
                f"limite_bytes deve ficar entre 1 e {MAX_ATTACHMENT_BYTES}."
            )
        result = self.provider.get_email_attachment(
            normalized_message_id,
            normalized_attachment_id,
            max_bytes=limite_bytes,
        )
        return {**result, "conteudo_nao_confiavel": True}

    @staticmethod
    def _validate_gmail_id(value: str, field_name: str) -> str:
        normalized = value.strip()
        if not GMAIL_ID_PATTERN.fullmatch(normalized):
            raise ValueError(f"{field_name} invalido.")
        return normalized

    def encontrar_horarios_livres(
        self,
        inicio: str,
        fim: str,
        duracao_minutos: int = 30,
        limite: int = 5,
    ) -> dict[str, Any]:
        start_dt, end_dt = _validate_period(inicio, fim)
        if duracao_minutos < 15 or duracao_minutos > 480:
            raise ValueError("duracao_minutos deve ficar entre 15 e 480.")
        if limite < 1 or limite > 20:
            raise ValueError("limite deve ficar entre 1 e 20.")

        busy: list[tuple[datetime, datetime]] = []
        for event in self.provider.list_events(inicio, fim):
            if not event.get("start") or not event.get("end"):
                continue
            event_start = _parse_datetime(event["start"], "evento.inicio")
            event_end = _parse_datetime(event["end"], "evento.fim")
            busy.append((event_start, event_end))

        duration = timedelta(minutes=duracao_minutos)
        cursor = start_dt
        free_slots: list[dict[str, str]] = []
        while cursor + duration <= end_dt and len(free_slots) < limite:
            candidate_end = cursor + duration
            overlap = any(
                cursor < busy_end and candidate_end > busy_start
                for busy_start, busy_end in busy
            )
            if not overlap:
                free_slots.append(
                    {"inicio": cursor.isoformat(), "fim": candidate_end.isoformat()}
                )
            cursor += timedelta(minutes=30)

        self.audit.record(
            "free_slots_calculated",
            provider=self.provider.name,
            count=len(free_slots),
            duration_minutes=duracao_minutos,
        )
        return {
            "janela": {"inicio": inicio, "fim": fim},
            "duracao_minutos": duracao_minutos,
            "horarios_livres": free_slots,
        }

    def criar_evento(
        self,
        titulo: str,
        inicio: str,
        fim: str,
        participantes: list[str] | None = None,
        descricao: str = "",
        local: str = "",
        enviar_convites: bool = False,
        permitir_conflito: bool = False,
        confirmacao_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_period(inicio, fim)
        if not titulo.strip():
            raise ValueError("titulo nao pode ser vazio.")
        attendees = _validate_emails(participantes or [], "participantes")
        conflicts = (
            []
            if confirmacao_id
            else self._check_conflicts(
                inicio,
                fim,
                allow_conflict=permitir_conflito,
            )
        )
        payload = {
            "titulo": titulo.strip(),
            "inicio": inicio,
            "fim": fim,
            "participantes": attendees,
            "descricao": descricao.strip(),
            "local": local.strip(),
            "enviar_convites": enviar_convites,
            "permitir_conflito": permitir_conflito,
        }
        preview = {**payload, "conflitos_encontrados": conflicts}
        return self._prepare_or_execute(
            action="criar_evento",
            payload=payload,
            preview=preview,
            confirmation_id=confirmacao_id,
            operation=lambda key: self._create_event_now(payload, key),
        )

    def remarcar_evento(
        self,
        event_id: str,
        novo_inicio: str,
        novo_fim: str,
        enviar_atualizacoes: bool = False,
        permitir_conflito: bool = False,
        confirmacao_id: str | None = None,
    ) -> dict[str, Any]:
        _validate_period(novo_inicio, novo_fim)
        if not event_id.strip():
            raise ValueError("event_id nao pode ser vazio.")
        normalized_id = event_id.strip()
        request_payload = {
            "event_id": normalized_id,
            "novo_inicio": novo_inicio,
            "novo_fim": novo_fim,
            "enviar_atualizacoes": enviar_atualizacoes,
            "permitir_conflito": permitir_conflito,
        }
        if confirmacao_id:
            replay = self.mutations.replay_if_final(
                action="remarcar_evento",
                request_payload=request_payload,
                confirmation_id=confirmacao_id,
            )
            if replay is not None:
                return replay
        current_event = self._event_snapshot(normalized_id)
        conflicts = (
            []
            if confirmacao_id
            else self._check_conflicts(
                novo_inicio,
                novo_fim,
                allow_conflict=permitir_conflito,
                exclude_event_id=normalized_id,
            )
        )
        payload = {
            **request_payload,
            "evento_atual": current_event,
        }
        return self._prepare_or_execute(
            action="remarcar_evento",
            payload=payload,
            preview={**payload, "conflitos_encontrados": conflicts},
            confirmation_id=confirmacao_id,
            operation=lambda key: self._update_event_now(payload),
            request_payload=request_payload,
        )

    def cancelar_evento(
        self,
        event_id: str,
        enviar_atualizacoes: bool = False,
        confirmacao_id: str | None = None,
    ) -> dict[str, Any]:
        if not event_id.strip():
            raise ValueError("event_id nao pode ser vazio.")
        normalized_id = event_id.strip()
        request_payload = {
            "event_id": normalized_id,
            "enviar_atualizacoes": enviar_atualizacoes,
        }
        if confirmacao_id:
            replay = self.mutations.replay_if_final(
                action="cancelar_evento",
                request_payload=request_payload,
                confirmation_id=confirmacao_id,
            )
            if replay is not None:
                return replay
        try:
            current_event = self._event_snapshot(normalized_id)
        except Exception:
            if confirmacao_id:
                replay = self.mutations.replay_if_final(
                    action="cancelar_evento",
                    request_payload=request_payload,
                    confirmation_id=confirmacao_id,
                )
                if replay is not None:
                    return replay
            raise
        payload = {
            **request_payload,
            "evento_atual": current_event,
        }
        return self._prepare_or_execute(
            action="cancelar_evento",
            payload=payload,
            preview=payload,
            confirmation_id=confirmacao_id,
            operation=lambda key: self.provider.delete_event(
                normalized_id,
                send_updates=enviar_atualizacoes,
                expected_etag=current_event.get("etag"),
            ),
            request_payload=request_payload,
        )

    def criar_rascunho_email(
        self,
        destinatarios: list[str],
        assunto: str,
        mensagem: str,
        cc: list[str] | None = None,
        confirmacao_id: str | None = None,
    ) -> dict[str, Any]:
        recipients = _validate_emails(destinatarios, "destinatarios")
        carbon_copy = _validate_emails(cc or [], "cc")
        self._validate_message(recipients, assunto, mensagem)
        payload = {
            "destinatarios": recipients,
            "assunto": assunto.strip(),
            "mensagem": mensagem,
            "cc": carbon_copy,
        }
        return self._prepare_or_execute(
            action="criar_rascunho_email",
            payload=payload,
            preview=payload,
            confirmation_id=confirmacao_id,
            operation=lambda key: self.provider.create_draft(
                recipients=recipients,
                subject=payload["assunto"],
                body=mensagem,
                cc=carbon_copy,
                idempotency_key=key,
            ),
        )

    def enviar_email(
        self,
        destinatarios: list[str],
        assunto: str,
        mensagem: str,
        cc: list[str] | None = None,
        confirmacao_id: str | None = None,
    ) -> dict[str, Any]:
        recipients = _validate_emails(destinatarios, "destinatarios")
        carbon_copy = _validate_emails(cc or [], "cc")
        self._validate_message(recipients, assunto, mensagem)
        payload = {
            "destinatarios": recipients,
            "assunto": assunto.strip(),
            "mensagem": mensagem,
            "cc": carbon_copy,
        }
        return self._prepare_or_execute(
            action="enviar_email",
            payload=payload,
            preview=payload,
            confirmation_id=confirmacao_id,
            operation=lambda key: self.provider.send_email(
                recipients=recipients,
                subject=payload["assunto"],
                body=mensagem,
                cc=carbon_copy,
                idempotency_key=key,
            ),
        )

    def organizar_reuniao(
        self,
        titulo: str,
        inicio: str,
        fim: str,
        participantes: list[str],
        pauta: str,
        local: str = "",
        comunicacao: str = "rascunho",
        permitir_conflito: bool = False,
        confirmacao_id: str | None = None,
    ) -> dict[str, Any]:
        if comunicacao not in {"nenhuma", "rascunho", "enviar"}:
            raise ValueError("comunicacao deve ser nenhuma, rascunho ou enviar.")
        _validate_period(inicio, fim)
        if not titulo.strip():
            raise ValueError("titulo nao pode ser vazio.")
        attendees = _validate_emails(participantes, "participantes")
        if not attendees:
            raise ValueError("Informe pelo menos um participante para a reuniao.")
        conflicts = (
            []
            if confirmacao_id
            else self._check_conflicts(
                inicio,
                fim,
                allow_conflict=permitir_conflito,
            )
        )
        payload = {
            "titulo": titulo.strip(),
            "inicio": inicio,
            "fim": fim,
            "participantes": attendees,
            "pauta": pauta.strip(),
            "local": local.strip(),
            "comunicacao": comunicacao,
            "permitir_conflito": permitir_conflito,
        }
        preview = {**payload, "conflitos_encontrados": conflicts}
        return self._prepare_or_execute(
            action="organizar_reuniao",
            payload=payload,
            preview=preview,
            confirmation_id=confirmacao_id,
            operation=lambda key: self._organize_meeting_now(payload, key),
        )

    def _organize_meeting_now(
        self,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        self._check_conflicts(
            payload["inicio"],
            payload["fim"],
            allow_conflict=payload["permitir_conflito"],
        )
        attendees = payload["participantes"]
        event = self.provider.create_event(
            title=payload["titulo"],
            start=payload["inicio"],
            end=payload["fim"],
            attendees=attendees,
            description=payload["pauta"],
            location=payload["local"],
            send_updates=payload["comunicacao"] == "enviar",
            idempotency_key=f"{idempotency_key}:event",
        )

        email_result = None
        workflow_status = "completed"
        if payload["comunicacao"] == "rascunho":
            message = (
                f"Reuniao: {payload['titulo']}\nInicio: {payload['inicio']}\n"
                f"Fim: {payload['fim']}\n"
                f"Local: {payload['local'] or '(nao informado)'}\n\n"
                f"Pauta:\n{payload['pauta']}"
            )
            try:
                email_result = self.provider.create_draft(
                    recipients=attendees,
                    subject=f"Convite: {payload['titulo']}",
                    body=message,
                    cc=[],
                    idempotency_key=f"{idempotency_key}:draft",
                )
            except Exception as exc:
                workflow_status = "partial_unknown"
                email_result = {
                    "status": "unknown",
                    "error_type": type(exc).__name__,
                    "message": (
                        "Evento criado, mas nao foi possivel determinar se o "
                        "rascunho tambem foi criado. Reconcilie no Gmail e nao repita."
                    ),
                }
                try:
                    self.audit.record(
                        "meeting_workflow_partial_failure",
                        provider=self.provider.name,
                        event_id=event.get("id"),
                        failed_step="create_draft",
                        error_type=type(exc).__name__,
                    )
                except Exception as audit_exc:
                    email_result["audit_warning"] = (
                        "Falha adicional ao registrar a auditoria local; o "
                        "resultado continua incerto e nao deve ser repetido."
                    )
                    email_result["audit_error_type"] = type(audit_exc).__name__
                raise UnknownMutationOutcome(
                    {
                        "status": workflow_status,
                        "evento": event,
                        "comunicacao": email_result,
                    },
                    "Resultado do rascunho incerto depois da criacao do evento.",
                ) from exc
        elif payload["comunicacao"] == "enviar":
            email_result = {
                "status": "convites_enviados_pelo_google_calendar",
                "recipients": attendees,
            }

        self.audit.record(
            "meeting_workflow_completed",
            provider=self.provider.name,
            event_id=event.get("id"),
            communication=payload["comunicacao"],
            workflow_status=workflow_status,
        )
        return {
            "status": workflow_status,
            "evento": event,
            "comunicacao": email_result,
        }

    def _create_event_now(
        self,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        self._check_conflicts(
            payload["inicio"],
            payload["fim"],
            allow_conflict=payload["permitir_conflito"],
        )
        return self.provider.create_event(
            title=payload["titulo"],
            start=payload["inicio"],
            end=payload["fim"],
            attendees=payload["participantes"],
            description=payload["descricao"],
            location=payload["local"],
            send_updates=payload["enviar_convites"],
            idempotency_key=idempotency_key,
        )

    def _update_event_now(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._check_conflicts(
            payload["novo_inicio"],
            payload["novo_fim"],
            allow_conflict=payload["permitir_conflito"],
            exclude_event_id=payload["event_id"],
        )
        return self.provider.update_event(
            payload["event_id"],
            start=payload["novo_inicio"],
            end=payload["novo_fim"],
            send_updates=payload["enviar_atualizacoes"],
            expected_etag=payload["evento_atual"].get("etag"),
        )

    def _event_snapshot(self, event_id: str) -> dict[str, Any]:
        event = self.provider.get_event(event_id)
        return {
            "id": event.get("id"),
            "titulo": event.get("title", "(sem titulo)"),
            "inicio": event.get("start"),
            "fim": event.get("end"),
            "participantes": list(event.get("attendees", [])),
            "descricao": event.get("description", ""),
            "local": event.get("location", ""),
            "status": event.get("status", "confirmed"),
            "etag": event.get("etag"),
        }

    def _prepare_or_execute(
        self,
        *,
        action: str,
        payload: dict[str, Any],
        preview: dict[str, Any],
        confirmation_id: str | None,
        operation: Callable[[str], dict[str, Any]],
        request_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if confirmation_id:
            return self.mutations.execute(
                action=action,
                payload=payload,
                confirmation_id=confirmation_id,
                operation=operation,
                request_payload=request_payload,
            )
        return self.mutations.prepare(
            action=action,
            payload=payload,
            preview=preview,
            request_payload=request_payload,
        )

    def _check_conflicts(
        self,
        start: str,
        end: str,
        *,
        allow_conflict: bool,
        exclude_event_id: str | None = None,
    ) -> list[dict[str, Any]]:
        start_dt, end_dt = _validate_period(start, end)
        conflicts: list[dict[str, Any]] = []
        for event in self.provider.list_events(start, end):
            if event.get("id") == exclude_event_id or event.get("status") == "cancelled":
                continue
            if not event.get("start") or not event.get("end"):
                continue
            event_start = _parse_datetime(event["start"], "evento.inicio")
            event_end = _parse_datetime(event["end"], "evento.fim")
            if start_dt < event_end and end_dt > event_start:
                conflicts.append(
                    {
                        "id": event.get("id"),
                        "title": event.get("title", "(sem titulo)"),
                        "start": event["start"],
                        "end": event["end"],
                    }
                )
        if conflicts and not allow_conflict:
            raise ValueError(
                "O horario conflita com evento existente. Revise o horario ou "
                "use permitir_conflito=true apos confirmacao explicita."
            )
        return conflicts

    @staticmethod
    def _validate_message(
        recipients: list[str], subject: str, message: str
    ) -> None:
        if not recipients:
            raise ValueError("Informe pelo menos um destinatario.")
        if not subject.strip():
            raise ValueError("assunto nao pode ser vazio.")
        if not message.strip():
            raise ValueError("mensagem nao pode ser vazia.")
