from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.10 sem parser TOML na stdlib
    tomllib = None

from support import load_script


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_portable_config = load_script(
    PROJECT_ROOT / "ferramentas-para-demonstracao" / "scripts-em-python" / "portable_config.py",
    "portable_config",
)
legacy_managed_markers = _portable_config.legacy_managed_markers
managed_markers = _portable_config.managed_markers
merge_managed_block = _portable_config.merge_managed_block
render_client_manifest = _portable_config.render_client_manifest
render_codex_block = _portable_config.render_codex_block
server_name_for = _portable_config.server_name_for
write_atomic_with_backup = _portable_config.write_atomic_with_backup


class PortableCodexConfigTests(unittest.TestCase):
    def _block(self, profile: str = "default") -> str:
        root = Path(r"C:\Users\Pessoa\MCP Sentry")
        data = Path(r"C:\Users\Pessoa\AppData\Local\MCP-Sentry\data")
        return render_codex_block(
            profile=profile,
            python=data / "venv" / "Scripts" / "python.exe",
            server=root / "inicializacao-do-mcp" / "server_google.py",
            cwd=root,
            timezone_name="America/Sao_Paulo",
            calendar_id="primary",
            credentials=data / "credentials.json",
            token=data / "token.json",
            audit=data / "audit.jsonl",
            mutations=data / "mutations.json",
        )

    @unittest.skipIf(tomllib is None, "tomllib requer Python 3.11+")
    def test_render_is_valid_toml_and_uses_write_approval(self) -> None:
        assert tomllib is not None
        parsed = tomllib.loads(self._block())
        server = parsed["mcp_servers"]["donna_mcp"]
        self.assertEqual(server["default_tools_approval_mode"], "writes")
        self.assertEqual(server["env"]["MCP_SECRETARY_MODE"], "live-google")
        self.assertNotIn("MCP_SECRETARY_SENTRY_ENFORCE", server["env"])

    def test_generic_client_manifest_describes_same_stdio_connection(self) -> None:
        root = Path(r"C:\Users\Pessoa\MCP Sentry")
        data = Path(r"C:\Users\Pessoa\AppData\Local\MCP-Sentry\data")
        payload = json.loads(
            render_client_manifest(
                profile="desk",
                python=data / "venv" / "Scripts" / "python.exe",
                server=root / "inicializacao-do-mcp" / "server_google.py",
                cwd=root,
                timezone_name="America/Sao_Paulo",
                calendar_id="primary",
                credentials=data / "credentials.json",
                token=data / "token.json",
                audit=data / "audit.jsonl",
                mutations=data / "mutations.json",
            )
        )
        self.assertEqual(payload["name"], "donna_mcp_desk")
        self.assertEqual(payload["transport"], "stdio")
        self.assertEqual(
            payload["args"],
            [str(root / "inicializacao-do-mcp" / "server_google.py")],
        )
        self.assertEqual(payload["env"]["MCP_SECRETARY_MODE"], "live-google")

    def test_merge_preserves_unrelated_configuration(self) -> None:
        current = 'model = "gpt-test"\n\n[mcp_servers.outro]\nurl = "https://example.test/mcp"\n'
        merged = merge_managed_block(current, profile="default", block=self._block())
        parsed = tomllib.loads(merged)
        self.assertEqual(parsed["model"], "gpt-test")
        self.assertIn("outro", parsed["mcp_servers"])
        self.assertIn("donna_mcp", parsed["mcp_servers"])

    def test_reinstall_replaces_only_its_managed_block(self) -> None:
        first = merge_managed_block("", profile="desk", block=self._block("desk"))
        changed = self._block("desk").replace("tool_timeout_sec = 120", "tool_timeout_sec = 180")
        second = merge_managed_block(first, profile="desk", block=changed)
        begin, end = managed_markers("desk")
        self.assertEqual(second.count(begin), 1)
        self.assertEqual(second.count(end), 1)
        self.assertIn("tool_timeout_sec = 180", second)

    def test_registration_replaces_the_legacy_managed_connection(self) -> None:
        old_begin, old_end = legacy_managed_markers("default")
        legacy = (
            f'{old_begin}\n'
            '[mcp_servers.secretario_google]\n'
            'command = "python"\n'
            f'{old_end}\n'
        )

        merged = merge_managed_block(
            legacy,
            profile="default",
            block=self._block(),
        )

        self.assertNotIn("secretario_google", merged)
        self.assertIn("donna_mcp", merged)

    def test_unmanaged_duplicate_is_rejected(self) -> None:
        current = "[mcp_servers.secretario_google]\ncommand = \"python\"\n"
        with self.assertRaisesRegex(ValueError, "fora do bloco gerenciado"):
            merge_managed_block(current, profile="default", block=self._block())

    def test_unmanaged_tool_subtable_is_rejected(self) -> None:
        current = (
            "[mcp_servers.secretario_google.tools.enviar_email]\n"
            'approval_mode = "prompt"\n'
        )
        with self.assertRaisesRegex(ValueError, "fora do bloco gerenciado"):
            merge_managed_block(current, profile="default", block=self._block())

    def test_duplicate_managed_markers_are_rejected(self) -> None:
        block = self._block()
        with self.assertRaisesRegex(ValueError, "mais de um bloco"):
            merge_managed_block(block + block, profile="default", block=block)

    def test_invalid_profile_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Profile invalido"):
            server_name_for("desk.home")

    def test_atomic_write_creates_backup_only_after_change(self) -> None:
        with TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.toml"
            self.assertIsNone(write_atomic_with_backup(config, "first\n"))
            self.assertIsNone(write_atomic_with_backup(config, "first\n"))
            backup = write_atomic_with_backup(config, "second\n")
            self.assertIsNotNone(backup)
            assert backup is not None
            self.assertEqual(backup.read_text(encoding="utf-8"), "first\n")
            self.assertEqual(config.read_text(encoding="utf-8"), "second\n")


if __name__ == "__main__":
    unittest.main()
