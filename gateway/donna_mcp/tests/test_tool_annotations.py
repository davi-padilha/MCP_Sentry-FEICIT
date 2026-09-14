from __future__ import annotations

import unittest

from mcp.server.fastmcp.server import Settings as FastMCPSettings

from donna_mcp import server


class ToolAnnotationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tools = {
            tool.name: tool for tool in server.mcp._tool_manager.list_tools()
        }

    def test_read_tools_are_marked_read_only(self) -> None:
        for name in (
            "descrever_donna",
            "status_seguranca",
            "consultar_agenda",
            "encontrar_horarios_livres",
            "buscar_emails",
            "ler_email",
            "ler_anexo_email",
        ):
            with self.subTest(tool=name):
                annotations = self.tools[name].annotations
                self.assertIsNotNone(annotations)
                assert annotations is not None
                self.assertTrue(annotations.readOnlyHint)
                self.assertFalse(annotations.destructiveHint)

    def test_fastmcp_settings_are_complete_after_server_import(self) -> None:
        self.assertTrue(FastMCPSettings.__pydantic_complete__)
        self.assertTrue(FastMCPSettings.model_fields["lifespan"]._complete)

    def test_external_mutations_are_not_marked_read_only(self) -> None:
        for name in (
            "criar_evento",
            "remarcar_evento",
            "cancelar_evento",
            "criar_rascunho_email",
            "enviar_email",
            "organizar_reuniao",
        ):
            with self.subTest(tool=name):
                annotations = self.tools[name].annotations
                self.assertIsNotNone(annotations)
                assert annotations is not None
                self.assertFalse(annotations.readOnlyHint)
                self.assertTrue(annotations.openWorldHint)
                self.assertTrue(annotations.idempotentHint)

    def test_irreversible_or_state_replacing_tools_are_destructive(self) -> None:
        for name in (
            "remarcar_evento",
            "cancelar_evento",
            "enviar_email",
            "organizar_reuniao",
        ):
            with self.subTest(tool=name):
                annotations = self.tools[name].annotations
                assert annotations is not None
                self.assertTrue(annotations.destructiveHint)


if __name__ == "__main__":
    unittest.main()
