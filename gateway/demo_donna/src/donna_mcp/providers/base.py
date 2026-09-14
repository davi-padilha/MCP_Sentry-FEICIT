"""Contrato dos provedores usados pela Donna MCP."""

from __future__ import annotations

from typing import Any, Protocol


class SecretaryProvider(Protocol):
    name: str

    def list_events(self, start: str, end: str) -> list[dict[str, Any]]: ...

    def get_event(self, event_id: str) -> dict[str, Any]: ...

    def search_emails(
        self,
        *,
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]: ...

    def get_email(self, message_id: str) -> dict[str, Any]: ...

    def get_email_attachment(
        self,
        message_id: str,
        attachment_id: str,
        *,
        max_bytes: int,
    ) -> dict[str, Any]: ...

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
    ) -> dict[str, Any]: ...

    def update_event(
        self,
        event_id: str,
        *,
        start: str,
        end: str,
        send_updates: bool,
        expected_etag: str | None = None,
    ) -> dict[str, Any]: ...

    def delete_event(
        self,
        event_id: str,
        *,
        send_updates: bool,
        expected_etag: str | None = None,
    ) -> dict[str, Any]: ...

    def create_draft(
        self,
        *,
        recipients: list[str],
        subject: str,
        body: str,
        cc: list[str],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]: ...

    def send_email(
        self,
        *,
        recipients: list[str],
        subject: str,
        body: str,
        cc: list[str],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]: ...
