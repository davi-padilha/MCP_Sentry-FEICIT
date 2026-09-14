"""Verifica o servidor canônico e as versões simuladas da Donna."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER = PROJECT_ROOT / "entrypoints" / "server_demonstracao.py"
SNAPSHOTS = {
    "approved": PROJECT_ROOT / "examples" / "demo_versions" / "approved" / "provider.py",
    "rug-pull": PROJECT_ROOT / "examples" / "demo_versions" / "rug_pull" / "provider.py",
}
EXPECTED_TOOLS = {
    "descrever_donna",
    "status_seguranca",
    "consultar_agenda",
    "encontrar_horarios_livres",
    "buscar_emails",
    "ler_email",
    "ler_anexo_email",
    "criar_evento",
    "remarcar_evento",
    "cancelar_evento",
    "criar_rascunho_email",
    "enviar_email",
    "organizar_reuniao",
}


def _structured(result: object) -> dict:
    value = getattr(result, "structuredContent", None)
    if isinstance(value, dict):
        return value
    raise RuntimeError(f"Resposta MCP sem conteudo estruturado: {result!r}")


def _read_audit(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


async def _verify_mode(
    version: str,
    root: Path,
    *,
    reset_session: bool,
) -> dict[str, dict]:
    root.mkdir(parents=True, exist_ok=True)
    if reset_session:
        for filename in ("state.json", "mutations.json"):
            path = root / filename
            if path.exists():
                path.unlink()
    active_provider = root / "active_version" / "provider.py"
    active_provider.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SNAPSHOTS[version], active_provider)

    environment = dict(os.environ)
    environment.update(
        {
            "MCP_SECRETARY_AUDIT_FILE": str(root / "audit.jsonl"),
            "MCP_SECRETARY_SIMULATED_STATE_FILE": str(root / "state.json"),
            "MCP_SECRETARY_MUTATION_STORE_FILE": str(root / "mutations.json"),
            "MCP_SECRETARY_ACTIVE_PROVIDER_FILE": str(active_provider),
            "MCP_SECRETARY_APPROVED_PROVIDER_FILE": str(SNAPSHOTS["approved"]),
        }
    )
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        cwd=str(PROJECT_ROOT),
        env=environment,
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_response = await session.list_tools()
            definitions = {
                tool.name: tool.model_dump(
                    mode="json", by_alias=True, exclude_none=True
                )
                for tool in tools_response.tools
            }
            names = set(definitions)
            if names != EXPECTED_TOOLS:
                raise RuntimeError(
                    f"Tools divergentes: esperado={sorted(EXPECTED_TOOLS)}, "
                    f"obtido={sorted(names)}"
                )

            status_result = await session.call_tool("status_seguranca", {})
            if status_result.isError:
                raise RuntimeError("status_seguranca retornou erro.")
            security = _structured(status_result)
            if security["enabled"]:
                raise RuntimeError("Donna canônica não deve embutir o guard legado.")

            meeting_arguments = {
                "titulo": "Verificacao MCP",
                "inicio": "2030-01-10T14:00:00-03:00",
                "fim": "2030-01-10T14:30:00-03:00",
                "participantes": ["participante@exemplo.test"],
                "pauta": "Validar o fluxo MCP por stdio.",
                "comunicacao": "rascunho",
            }
            prepared = await session.call_tool(
                "organizar_reuniao",
                meeting_arguments,
            )
            if prepared.isError:
                raise RuntimeError("organizar_reuniao nao preparou a operacao.")
            prepared_payload = _structured(prepared)
            if prepared_payload["status"] != "confirmation_required":
                raise RuntimeError("Operacao mutavel nao exigiu confirmacao.")

            confirmed_arguments = {
                **meeting_arguments,
                "confirmacao_id": prepared_payload["confirmation_id"],
            }
            created = await session.call_tool(
                "organizar_reuniao",
                confirmed_arguments,
            )
            if created.isError:
                raise RuntimeError("organizar_reuniao retornou erro.")
            payload = _structured(created)
            if payload["evento"]["status"] != "confirmed":
                raise RuntimeError("Evento simulado nao foi confirmado.")
            if payload["comunicacao"]["status"] != "draft":
                raise RuntimeError("Rascunho simulado nao foi criado.")

            replay = await session.call_tool(
                "organizar_reuniao",
                confirmed_arguments,
            )
            replay_payload = _structured(replay)
            if replay_payload["evento"]["id"] != payload["evento"]["id"]:
                raise RuntimeError("A repeticao criou um evento duplicado.")
            if not replay_payload["confirmation"]["idempotent_replay"]:
                raise RuntimeError("A repeticao nao foi marcada como idempotente.")
            return definitions


async def verify() -> None:
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        sequence_root = root / "three-stage-sequence"

        approved_definitions = await _verify_mode(
            "approved",
            sequence_root,
            reset_session=True,
        )
        approved_events = _read_audit(sequence_root / "audit.jsonl")
        rug_definitions = await _verify_mode(
            "rug-pull",
            sequence_root,
            reset_session=True,
        )
        after_rug_events = _read_audit(sequence_root / "audit.jsonl")
        rug_events = after_rug_events[len(approved_events) :]
        if approved_definitions != rug_definitions:
            raise RuntimeError(
                "As versoes nao expoem schemas e descricoes MCP identicos."
            )

        approved_hidden = [
            event
            for event in approved_events
            if event["event_type"] == "simulated_hidden_action"
        ]
        rug_hidden = [
            event
            for event in rug_events
            if event["event_type"] == "simulated_hidden_action"
        ]
        if approved_hidden:
            raise RuntimeError("A versao aprovada registrou uma acao oculta.")
        if not rug_hidden:
            raise RuntimeError("O rug pull sem protecao nao produziu o efeito oculto.")
        if any(event.get("network_performed") for event in rug_hidden):
            raise RuntimeError("A simulacao de ataque declarou uso de rede.")

        print(
            json.dumps(
                {
                    "status": "ok",
                    "sequence": [
                        "approved-unprotected",
                        "rug-pull-unprotected",
                    ],
                    "canonical_server": str(SERVER),
                    "tools": sorted(approved_definitions),
                    "tool_definitions_identical": True,
                    "confirmation_required": True,
                    "idempotent_retry": True,
                    "rug_pull_hidden_actions": len(rug_hidden),
                    "attack_network_used": False,
                    "external_gateway_required_for_protection": True,
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    asyncio.run(verify())
