"""Adaptador real para Google Calendar e Gmail.

Os imports das bibliotecas Google sao tardios para que testes e simulacoes nao
precisem delas nem carreguem credenciais por acidente.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import date, datetime, time
from email.header import decode_header, make_header
from email.message import EmailMessage
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..audit import AuditLog


GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
]

EMAIL_METADATA_HEADERS = ["From", "To", "Cc", "Subject", "Date", "Message-ID"]
MAX_EMAIL_BODY_CHARACTERS = 100_000


class _TextFromHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(self.parts)


def load_google_credentials(
    credentials_file: Path,
    token_file: Path,
    *,
    allow_interactive: bool = False,
) -> Any:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:  # pragma: no cover - depende do ambiente real
        raise RuntimeError(
            "Dependencias Google ausentes. Instale requirements.txt do subprojeto."
        ) from exc

    credentials = None
    if token_file.exists():
        token_info = json.loads(token_file.read_text(encoding="utf-8"))
        token_scopes = token_info.get("scopes", [])
        if isinstance(token_scopes, str):
            token_scopes = token_scopes.split()
        if set(GOOGLE_SCOPES).issubset(set(token_scopes)):
            credentials = Credentials.from_authorized_user_file(
                str(token_file), GOOGLE_SCOPES
            )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        if not allow_interactive:
            raise RuntimeError(
                "Google ainda nao autorizado. Execute scripts/authenticate_google.py "
                "antes de iniciar o servidor live-google."
            )
        if not credentials_file.exists():
            raise FileNotFoundError(
                f"Credencial OAuth nao encontrada: {credentials_file}"
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_file), GOOGLE_SCOPES
        )
        credentials = flow.run_local_server(port=0)

    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


class GoogleProvider:
    """Executa operacoes reais na conta Google autorizada."""

    name = "live-google"

    def __init__(
        self,
        *,
        credentials_file: Path,
        token_file: Path,
        calendar_id: str,
        timezone_name: str,
        audit: AuditLog,
    ) -> None:
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover - depende do ambiente real
            raise RuntimeError(
                "Dependencias Google ausentes. Instale requirements.txt do subprojeto."
            ) from exc

        credentials = load_google_credentials(
            credentials_file,
            token_file,
            allow_interactive=False,
        )
        self.calendar = build("calendar", "v3", credentials=credentials)
        self.gmail = build("gmail", "v1", credentials=credentials)
        self.calendar_id = calendar_id
        self.timezone = ZoneInfo(timezone_name)
        self.audit = audit

    def list_events(self, start: str, end: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token = None
        while True:
            response = (
                self.calendar.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=start,
                    timeMax=end,
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=2500,
                    pageToken=page_token,
                )
                .execute()
            )
            items.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        events = [self._normalize_event(item) for item in items]
        self.audit.record("calendar_read", provider=self.name, count=len(events))
        return events

    def get_event(self, event_id: str) -> dict[str, Any]:
        item = (
            self.calendar.events()
            .get(calendarId=self.calendar_id, eventId=event_id)
            .execute()
        )
        event = self._normalize_event(item)
        self.audit.record(
            "calendar_event_read",
            provider=self.name,
            event_id=event_id,
        )
        return event

    def search_emails(
        self,
        *,
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        response = (
            self.gmail.users()
            .messages()
            .list(
                userId="me",
                q=query or None,
                maxResults=limit,
                includeSpamTrash=False,
            )
            .execute()
        )
        messages: list[dict[str, Any]] = []
        for reference in response.get("messages", []):
            raw = (
                self.gmail.users()
                .messages()
                .get(
                    userId="me",
                    id=reference["id"],
                    format="metadata",
                    metadataHeaders=EMAIL_METADATA_HEADERS,
                )
                .execute()
            )
            messages.append(self._normalize_email_summary(raw))
        self.audit.record(
            "email_search",
            provider=self.name,
            count=len(messages),
            query_sha256=hashlib.sha256(query.encode("utf-8")).hexdigest(),
        )
        return messages

    def get_email(self, message_id: str) -> dict[str, Any]:
        raw = (
            self.gmail.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        result = self._normalize_email(raw)
        self.audit.record(
            "email_read",
            provider=self.name,
            message_id=message_id,
            attachment_count=len(result["attachments"]),
        )
        return result

    def get_email_attachment(
        self,
        message_id: str,
        attachment_id: str,
        *,
        max_bytes: int,
    ) -> dict[str, Any]:
        raw_message = (
            self.gmail.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        part = self._find_attachment_part(
            raw_message.get("payload", {}),
            attachment_id,
        )
        if part is None:
            raise KeyError(f"Anexo nao encontrado: {attachment_id}")
        declared_size = int(part.get("body", {}).get("size", 0))
        if declared_size > max_bytes:
            raise ValueError(
                f"Anexo tem {declared_size} bytes e excede o limite de {max_bytes}."
            )
        raw_attachment = (
            self.gmail.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )
        encoded = str(raw_attachment.get("data", ""))
        content = self._decode_base64url(encoded)
        if len(content) > max_bytes:
            raise ValueError(
                f"Anexo tem {len(content)} bytes e excede o limite de {max_bytes}."
            )
        mime_type = str(part.get("mimeType", "application/octet-stream"))
        result: dict[str, Any] = {
            "message_id": message_id,
            "attachment_id": attachment_id,
            "filename": str(part.get("filename", "")),
            "mime_type": mime_type,
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "content_encoding": "base64url",
            "content_base64url": encoded,
        }
        if self._is_textual_mime(mime_type):
            result["text"] = content.decode("utf-8", errors="replace")
        self.audit.record(
            "email_attachment_read",
            provider=self.name,
            message_id=message_id,
            attachment_id=attachment_id,
            size=len(content),
            sha256=result["sha256"],
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
        body = {
            "summary": title,
            "description": description,
            "location": location,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
            "attendees": [{"email": email} for email in attendees],
        }
        if idempotency_key:
            body["id"] = self._calendar_event_id(idempotency_key)
            body["extendedProperties"] = {
                "private": {"secretaryIdempotencyKey": idempotency_key}
            }
        try:
            created = (
                self.calendar.events()
                .insert(
                    calendarId=self.calendar_id,
                    body=body,
                    sendUpdates="all" if send_updates else "none",
                )
                .execute()
            )
        except Exception as exc:
            status = getattr(getattr(exc, "resp", None), "status", None)
            if not idempotency_key or status != 409:
                raise
            created = (
                self.calendar.events()
                .get(calendarId=self.calendar_id, eventId=body["id"])
                .execute()
            )
        event = self._normalize_event(created)
        self.audit.record(
            "calendar_event_created",
            provider=self.name,
            event_id=event["id"],
            attendees=list(attendees),
            send_updates=send_updates,
        )
        return event

    def update_event(
        self,
        event_id: str,
        *,
        start: str,
        end: str,
        send_updates: bool,
        expected_etag: str | None = None,
    ) -> dict[str, Any]:
        event = (
            self.calendar.events()
            .get(calendarId=self.calendar_id, eventId=event_id)
            .execute()
        )
        event["start"] = {"dateTime": start}
        event["end"] = {"dateTime": end}
        request = self.calendar.events().update(
            calendarId=self.calendar_id,
            eventId=event_id,
            body=event,
            sendUpdates="all" if send_updates else "none",
        )
        if expected_etag:
            request.headers["If-Match"] = expected_etag
        updated = request.execute()
        normalized = self._normalize_event(updated)
        self.audit.record(
            "calendar_event_updated",
            provider=self.name,
            event_id=event_id,
            send_updates=send_updates,
        )
        return normalized

    def delete_event(
        self,
        event_id: str,
        *,
        send_updates: bool,
        expected_etag: str | None = None,
    ) -> dict[str, Any]:
        request = self.calendar.events().delete(
            calendarId=self.calendar_id,
            eventId=event_id,
            sendUpdates="all" if send_updates else "none",
        )
        if expected_etag:
            request.headers["If-Match"] = expected_etag
        request.execute()
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
        raw = self._encode_message(
            recipients, subject, body, cc, idempotency_key=idempotency_key
        )
        draft = (
            self.gmail.users()
            .drafts()
            .create(userId="me", body={"message": {"raw": raw}})
            .execute()
        )
        result = {
            "id": draft["id"],
            "message_id": draft.get("message", {}).get("id"),
            "recipients": list(recipients),
            "cc": list(cc),
            "subject": subject,
            "status": "draft",
        }
        self.audit.record(
            "email_draft_created",
            provider=self.name,
            draft_id=result["id"],
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
        raw = self._encode_message(
            recipients, subject, body, cc, idempotency_key=idempotency_key
        )
        sent = (
            self.gmail.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )
        result = {
            "id": sent["id"],
            "thread_id": sent.get("threadId"),
            "recipients": list(recipients),
            "cc": list(cc),
            "subject": subject,
            "status": "sent",
        }
        self.audit.record(
            "email_sent",
            provider=self.name,
            message_id=result["id"],
            recipients=list(recipients),
        )
        return result

    @staticmethod
    def _encode_message(
        recipients: list[str],
        subject: str,
        body: str,
        cc: list[str],
        *,
        idempotency_key: str | None = None,
    ) -> str:
        message = EmailMessage()
        message.set_content(body)
        message["To"] = ", ".join(recipients)
        if cc:
            message["Cc"] = ", ".join(cc)
        message["Subject"] = subject
        if idempotency_key:
            message["X-Secretary-Idempotency-Key"] = idempotency_key
        return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")

    @staticmethod
    def _calendar_event_id(idempotency_key: str) -> str:
        # Google aceita IDs em base32hex; o digest torna a chave opaca e estavel.
        return "s" + base64.b32hexencode(
            hashlib.sha256(idempotency_key.encode("utf-8")).digest()
        ).decode("ascii").lower().rstrip("=")

    def _normalize_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": event.get("id"),
            "title": event.get("summary", "(sem titulo)"),
            "start": self._normalize_boundary(event.get("start", {})),
            "end": self._normalize_boundary(event.get("end", {})),
            "attendees": [
                attendee.get("email")
                for attendee in event.get("attendees", [])
                if attendee.get("email")
            ],
            "description": event.get("description", ""),
            "location": event.get("location", ""),
            "status": event.get("status", "confirmed"),
            "etag": event.get("etag"),
            "html_link": event.get("htmlLink"),
        }

    def _normalize_email_summary(self, message: dict[str, Any]) -> dict[str, Any]:
        headers = self._headers(message.get("payload", {}))
        return {
            "id": message.get("id"),
            "thread_id": message.get("threadId"),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "cc": headers.get("cc", ""),
            "subject": headers.get("subject", "(sem assunto)"),
            "date": headers.get("date", ""),
            "snippet": message.get("snippet", ""),
            "label_ids": list(message.get("labelIds", [])),
        }

    def _normalize_email(self, message: dict[str, Any]) -> dict[str, Any]:
        payload = message.get("payload", {})
        summary = self._normalize_email_summary(message)
        plain_parts: list[str] = []
        html_parts: list[str] = []
        attachments: list[dict[str, Any]] = []
        self._collect_message_parts(payload, plain_parts, html_parts, attachments)
        if plain_parts:
            body_text = "\n\n".join(part for part in plain_parts if part)
        else:
            body_text = "\n\n".join(part for part in html_parts if part)
        truncated = len(body_text) > MAX_EMAIL_BODY_CHARACTERS
        return {
            **summary,
            "message_id_header": self._headers(payload).get("message-id", ""),
            "body_text": body_text[:MAX_EMAIL_BODY_CHARACTERS],
            "body_truncated": truncated,
            "attachments": attachments,
        }

    def _collect_message_parts(
        self,
        part: dict[str, Any],
        plain_parts: list[str],
        html_parts: list[str],
        attachments: list[dict[str, Any]],
    ) -> None:
        body = part.get("body", {})
        attachment_id = body.get("attachmentId")
        filename = str(part.get("filename", ""))
        mime_type = str(part.get("mimeType", "application/octet-stream"))
        if attachment_id:
            attachments.append(
                {
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "mime_type": mime_type,
                    "size": int(body.get("size", 0)),
                }
            )
        elif body.get("data") and not filename:
            decoded = self._decode_base64url(str(body["data"])).decode(
                "utf-8",
                errors="replace",
            )
            if mime_type == "text/plain":
                plain_parts.append(decoded)
            elif mime_type == "text/html":
                parser = _TextFromHtml()
                parser.feed(decoded)
                html_parts.append(parser.text())
        for child in part.get("parts", []):
            self._collect_message_parts(child, plain_parts, html_parts, attachments)

    @classmethod
    def _find_attachment_part(
        cls,
        part: dict[str, Any],
        attachment_id: str,
    ) -> dict[str, Any] | None:
        if part.get("body", {}).get("attachmentId") == attachment_id:
            return part
        for child in part.get("parts", []):
            found = cls._find_attachment_part(child, attachment_id)
            if found is not None:
                return found
        return None

    @staticmethod
    def _headers(payload: dict[str, Any]) -> dict[str, str]:
        result: dict[str, str] = {}
        for header in payload.get("headers", []):
            name = str(header.get("name", "")).lower()
            if not name:
                continue
            value = str(header.get("value", ""))
            try:
                result[name] = str(make_header(decode_header(value)))
            except (LookupError, UnicodeError):
                result[name] = value
        return result

    @staticmethod
    def _decode_base64url(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)

    @staticmethod
    def _is_textual_mime(mime_type: str) -> bool:
        normalized = mime_type.lower().split(";", 1)[0]
        return normalized.startswith("text/") or normalized in {
            "application/json",
            "application/ld+json",
            "application/xml",
            "application/javascript",
        }

    def _normalize_boundary(self, boundary: dict[str, Any]) -> str | None:
        if boundary.get("dateTime"):
            return str(boundary["dateTime"])
        if boundary.get("date"):
            day = date.fromisoformat(str(boundary["date"]))
            return datetime.combine(day, time.min, self.timezone).isoformat()
        return None
