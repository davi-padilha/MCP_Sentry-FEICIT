from __future__ import annotations

import base64
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from donna_mcp.audit import AuditLog
from donna_mcp.providers.google import GoogleProvider


class GoogleProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.audit = AuditLog(Path(self.temp_dir.name) / "audit.jsonl")
        self.provider = GoogleProvider.__new__(GoogleProvider)
        self.provider.calendar_id = "primary"
        self.provider.timezone = ZoneInfo("America/Sao_Paulo")
        self.provider.audit = self.audit
        self.provider.calendar = MagicMock()
        self.provider.gmail = MagicMock()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_event_uses_calendar_api_and_normalizes_result(self) -> None:
        execute = self.provider.calendar.events.return_value.insert.return_value.execute
        execute.return_value = {
            "id": "google-event-1",
            "summary": "Reuniao real",
            "start": {"dateTime": "2030-01-10T14:00:00-03:00"},
            "end": {"dateTime": "2030-01-10T14:30:00-03:00"},
            "attendees": [{"email": "colega@example.com"}],
            "status": "confirmed",
            "htmlLink": "https://calendar.google.test/event",
        }
        result = self.provider.create_event(
            title="Reuniao real",
            start="2030-01-10T14:00:00-03:00",
            end="2030-01-10T14:30:00-03:00",
            attendees=["colega@example.com"],
            description="Pauta",
            location="Sala",
            send_updates=True,
        )
        self.assertEqual(result["id"], "google-event-1")
        self.assertEqual(result["attendees"], ["colega@example.com"])
        call = self.provider.calendar.events.return_value.insert.call_args.kwargs
        self.assertEqual(call["calendarId"], "primary")
        self.assertEqual(call["sendUpdates"], "all")

    def test_create_event_uses_deterministic_google_id_when_confirmed(self) -> None:
        execute = self.provider.calendar.events.return_value.insert.return_value.execute
        execute.return_value = {
            "id": "stable-google-event",
            "start": {"dateTime": "2030-01-10T14:00:00-03:00"},
            "end": {"dateTime": "2030-01-10T14:30:00-03:00"},
        }

        self.provider.create_event(
            title="Reuniao real",
            start="2030-01-10T14:00:00-03:00",
            end="2030-01-10T14:30:00-03:00",
            attendees=[],
            description="",
            location="",
            send_updates=False,
            idempotency_key="confirmation-123",
        )

        body = self.provider.calendar.events.return_value.insert.call_args.kwargs["body"]
        self.assertRegex(body["id"], r"^s[0-9a-v]+$")
        self.assertEqual(
            body["extendedProperties"]["private"]["secretaryIdempotencyKey"],
            "confirmation-123",
        )

    def test_create_draft_uses_gmail_api(self) -> None:
        execute = (
            self.provider.gmail.users.return_value.drafts.return_value.create.return_value.execute
        )
        execute.return_value = {"id": "draft-1", "message": {"id": "message-1"}}
        result = self.provider.create_draft(
            recipients=["colega@example.com"],
            subject="Assunto",
            body="Mensagem",
            cc=[],
        )
        self.assertEqual(result["status"], "draft")
        call = (
            self.provider.gmail.users.return_value.drafts.return_value.create.call_args.kwargs
        )
        self.assertEqual(call["userId"], "me")
        self.assertIn("raw", call["body"]["message"])

    def test_search_emails_returns_metadata_without_marking_read(self) -> None:
        messages = self.provider.gmail.users.return_value.messages.return_value
        messages.list.return_value.execute.return_value = {
            "messages": [{"id": "abc123", "threadId": "thread-1"}]
        }
        messages.get.return_value.execute.return_value = {
            "id": "abc123",
            "threadId": "thread-1",
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "Trecho da mensagem",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Pessoa <pessoa@example.com>"},
                    {"name": "Subject", "value": "Assunto"},
                    {"name": "Date", "value": "Thu, 20 Aug 2026 10:00:00 -0300"},
                ]
            },
        }

        result = self.provider.search_emails(query="in:inbox", limit=5)

        self.assertEqual(result[0]["id"], "abc123")
        self.assertEqual(result[0]["subject"], "Assunto")
        list_call = messages.list.call_args.kwargs
        self.assertEqual(list_call["q"], "in:inbox")
        self.assertFalse(list_call["includeSpamTrash"])
        get_call = messages.get.call_args.kwargs
        self.assertEqual(get_call["format"], "metadata")

    def test_get_email_decodes_body_and_lists_attachments(self) -> None:
        encoded_body = base64.urlsafe_b64encode("Olá!".encode()).decode()
        messages = self.provider.gmail.users.return_value.messages.return_value
        messages.get.return_value.execute.return_value = {
            "id": "abc123",
            "threadId": "thread-1",
            "snippet": "Olá!",
            "labelIds": ["INBOX"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "Pessoa <pessoa@example.com>"},
                    {"name": "Subject", "value": "=?utf-8?q?Reuni=C3=A3o?="},
                ],
                "mimeType": "multipart/mixed",
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "filename": "",
                        "body": {"data": encoded_body, "size": 5},
                    },
                    {
                        "mimeType": "application/pdf",
                        "filename": "pauta.pdf",
                        "body": {"attachmentId": "att-1", "size": 1234},
                    },
                ],
            },
        }

        result = self.provider.get_email("abc123")

        self.assertEqual(result["subject"], "Reunião")
        self.assertEqual(result["body_text"], "Olá!")
        self.assertEqual(result["attachments"][0]["attachment_id"], "att-1")
        self.assertEqual(result["attachments"][0]["filename"], "pauta.pdf")

    def test_get_email_attachment_is_bounded_and_returns_text(self) -> None:
        content = b"coluna,valor\nitem,1\n"
        encoded = base64.urlsafe_b64encode(content).decode().rstrip("=")
        messages = self.provider.gmail.users.return_value.messages.return_value
        messages.get.return_value.execute.return_value = {
            "payload": {
                "mimeType": "multipart/mixed",
                "parts": [
                    {
                        "mimeType": "text/csv",
                        "filename": "dados.csv",
                        "body": {"attachmentId": "att-1", "size": len(content)},
                    }
                ],
            }
        }
        (
            messages.attachments.return_value.get.return_value.execute
        ).return_value = {"data": encoded, "size": len(content)}

        result = self.provider.get_email_attachment(
            "abc123",
            "att-1",
            max_bytes=1024,
        )

        self.assertEqual(result["filename"], "dados.csv")
        self.assertEqual(result["text"], content.decode())
        self.assertEqual(result["content_base64url"], encoded)

        with self.assertRaisesRegex(ValueError, "excede"):
            self.provider.get_email_attachment(
                "abc123",
                "att-1",
                max_bytes=2,
            )

    def test_list_events_reads_all_pages(self) -> None:
        execute = self.provider.calendar.events.return_value.list.return_value.execute
        execute.side_effect = [
            {
                "items": [
                    {
                        "id": "event-1",
                        "start": {"dateTime": "2030-01-10T14:00:00-03:00"},
                        "end": {"dateTime": "2030-01-10T14:30:00-03:00"},
                    }
                ],
                "nextPageToken": "page-2",
            },
            {
                "items": [
                    {
                        "id": "event-2",
                        "start": {"dateTime": "2030-01-10T15:00:00-03:00"},
                        "end": {"dateTime": "2030-01-10T15:30:00-03:00"},
                    }
                ]
            },
        ]
        result = self.provider.list_events(
            "2030-01-10T13:00:00-03:00",
            "2030-01-10T18:00:00-03:00",
        )
        self.assertEqual([event["id"] for event in result], ["event-1", "event-2"])
        calls = self.provider.calendar.events.return_value.list.call_args_list
        self.assertIsNone(calls[0].kwargs["pageToken"])
        self.assertEqual(calls[1].kwargs["pageToken"], "page-2")

    def test_update_event_does_not_notify_without_explicit_request(self) -> None:
        get_execute = self.provider.calendar.events.return_value.get.return_value.execute
        get_execute.return_value = {"id": "event-1"}
        update_execute = (
            self.provider.calendar.events.return_value.update.return_value.execute
        )
        update_execute.return_value = {
            "id": "event-1",
            "start": {"dateTime": "2030-01-10T15:00:00-03:00"},
            "end": {"dateTime": "2030-01-10T15:30:00-03:00"},
        }
        self.provider.update_event(
            "event-1",
            start="2030-01-10T15:00:00-03:00",
            end="2030-01-10T15:30:00-03:00",
            send_updates=False,
        )
        call = self.provider.calendar.events.return_value.update.call_args.kwargs
        self.assertEqual(call["sendUpdates"], "none")

    def test_update_and_delete_use_confirmed_event_etag(self) -> None:
        events = self.provider.calendar.events.return_value
        events.get.return_value.execute.return_value = {
            "id": "event-1",
            "etag": "newer-etag",
        }
        update_request = events.update.return_value
        update_request.headers = {}
        update_request.execute.return_value = {
            "id": "event-1",
            "start": {"dateTime": "2030-01-10T15:00:00-03:00"},
            "end": {"dateTime": "2030-01-10T15:30:00-03:00"},
        }
        self.provider.update_event(
            "event-1",
            start="2030-01-10T15:00:00-03:00",
            end="2030-01-10T15:30:00-03:00",
            send_updates=False,
            expected_etag="confirmed-etag",
        )
        self.assertEqual(update_request.headers["If-Match"], "confirmed-etag")

        delete_request = events.delete.return_value
        delete_request.headers = {}
        self.provider.delete_event(
            "event-1",
            send_updates=False,
            expected_etag="confirmed-etag",
        )
        self.assertEqual(delete_request.headers["If-Match"], "confirmed-etag")

    def test_all_day_event_is_normalized_with_configured_timezone(self) -> None:
        normalized = self.provider._normalize_event(
            {
                "id": "all-day",
                "summary": "Dia inteiro",
                "start": {"date": "2030-01-10"},
                "end": {"date": "2030-01-11"},
            }
        )
        self.assertEqual(normalized["start"], "2030-01-10T00:00:00-03:00")
        self.assertEqual(normalized["end"], "2030-01-11T00:00:00-03:00")


if __name__ == "__main__":
    unittest.main()
