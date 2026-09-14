"""Deterministic T4 review-flow fixtures; this module never calls an AI service.

It models the two client-side protocol paths so they can be tested without
claiming that any MCP client will autonomously make a follow-up tool call.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcp_sentry_gateway.core import SentryError


_FIXTURE_FIELDS = {"decision", "justification", "risks"}


class FixtureError(ValueError):
    """A test fixture cannot be converted into a safe structured verdict."""


@dataclass(frozen=True)
class FlowResult:
    path: str
    initial_response: dict
    pages_read: int
    verdict_response: dict | None


def _fixture_verdict(dossier: dict, fixture: dict) -> dict:
    """Bind an explicit fixture to the exact review currently being read."""
    if not isinstance(fixture, dict) or set(fixture) != _FIXTURE_FIELDS:
        raise FixtureError("schema de fixture de veredito inválido")
    if fixture.get("decision") not in {"allow", "block"}:
        raise FixtureError("decisão da fixture inválida")
    if not isinstance(fixture.get("justification"), str) or not fixture["justification"].strip():
        raise FixtureError("justificativa da fixture inválida")
    if not isinstance(fixture.get("risks"), list) or not all(isinstance(risk, str) for risk in fixture["risks"]):
        raise FixtureError("riscos da fixture inválidos")
    return {
        "review_id": dossier["review_id"],
        "reviewed_hash": dossier["current_hash"],
        "dossier_hash": dossier["dossier_hash"],
        "policy_version": dossier["policy_version"],
        **fixture,
    }


class FixtureReviewFlow:
    """Exercise the client protocol with caller-supplied, structured fixtures.

    The caller must choose the fixture. This is not a policy engine and does
    not infer a decision from untrusted code, metadata, or configuration.
    """

    def __init__(self, mcp):
        self.mcp = mcp

    @staticmethod
    def _content(response):
        content = response.get("structuredContent") if isinstance(response, dict) else None
        if not isinstance(content, dict):
            raise SentryError("resposta MCP de controle inválida")
        return content

    def _read_all_pages(self, review_id: str, page_size: int) -> tuple[dict, int]:
        if not isinstance(page_size, int) or not 1 <= page_size <= 100:
            raise FixtureError("paginação da fixture inválida")
        first = self._content(self.mcp.call_tool("sentry_get_pending_review", {
            "review_id": review_id, "page": 1, "page_size": page_size,
        }))
        total = first["total_changes"]
        pages = [first]
        for page in range(2, (total + page_size - 1) // page_size + 1):
            pages.append(self._content(self.mcp.call_tool("sentry_get_pending_review", {
                "review_id": review_id, "page": page, "page_size": page_size,
            })))
        if sum(len(page["changes"]) for page in pages) != total:
            raise SentryError("leitura incompleta do dossiê")
        return first, len(pages)

    def _complete(self, path: str, initial_response: dict, fixture: dict, page_size: int) -> FlowResult:
        initial = self._content(initial_response)
        if initial.get("status") not in {"security_review_required", "review_required"}:
            raise FixtureError("não há revisão pendente para a fixture")
        dossier, pages_read = self._read_all_pages(initial["review_id"], page_size)
        verdict = _fixture_verdict(dossier, fixture)
        submitted = self._content(self.mcp.call_tool("sentry_submit_verdict", {"verdict": verdict}))
        return FlowResult(path=path, initial_response=initial_response, pages_read=pages_read, verdict_response=submitted)

    def attempt_tool(self, name: str, arguments: dict | None, fixture: dict | None = None, page_size: int = 20) -> FlowResult:
        """Path B: an approved-tool attempt starts review in the same turn.

        With no fixture, review remains pending and the caller can use fallback
        A later. A completed allow still requires reconnection; this method
        intentionally does not repeat the original tool call.
        """
        initial = self.mcp.call_tool(name, arguments or {})
        if fixture is None:
            return FlowResult(path="B", initial_response=initial, pages_read=0, verdict_response=None)
        return self._complete("B", initial, fixture, page_size)

    def review_pending_explicitly(self, fixture: dict, page_size: int = 20) -> FlowResult:
        """Path A: model the user explicitly requesting analysis of a review."""
        initial = self.mcp.call_tool("sentry_security_status")
        return self._complete("A", initial, fixture, page_size)
