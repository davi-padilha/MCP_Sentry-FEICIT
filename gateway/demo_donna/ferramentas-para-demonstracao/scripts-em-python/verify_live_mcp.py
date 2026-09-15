"""Confirma o startup do MCP Google sem ler ou alterar dados da conta."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER = PROJECT_ROOT / "inicializacao-do-mcp" / "server_google.py"
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


async def verify() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        cwd=str(PROJECT_ROOT),
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            response = await session.list_tools()
            names = {tool.name for tool in response.tools}
            if names != EXPECTED_TOOLS:
                raise RuntimeError(
                    f"Tools divergentes: esperado={sorted(EXPECTED_TOOLS)}, "
                    f"obtido={sorted(names)}"
                )
            security_result = await session.call_tool("status_seguranca", {})
            if security_result.isError:
                raise RuntimeError("status_seguranca retornou erro.")
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "mode": "live-google",
                        "tools": sorted(names),
                        "google_data_read": False,
                        "google_mutation_performed": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )


if __name__ == "__main__":
    asyncio.run(verify())
