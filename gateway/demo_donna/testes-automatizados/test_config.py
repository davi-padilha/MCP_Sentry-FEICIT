from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from donna_mcp.config import SecretaryConfig


class SecretaryConfigTests(unittest.TestCase):
    def test_default_mode_is_safe_simulation(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = SecretaryConfig.from_env()
        self.assertEqual(config.mode, "simulated-safe")
        self.assertTrue(config.audit_file.is_absolute())

    def test_relative_paths_remain_inside_project(self) -> None:
        with patch.dict(
            os.environ,
            {"MCP_SECRETARY_AUDIT_FILE": "dados-gerados-pelo-mcp/custom.jsonl"},
            clear=True,
        ):
            config = SecretaryConfig.from_env()
        self.assertEqual(config.audit_file.name, "custom.jsonl")
        self.assertEqual(config.mutation_store_file.name, "estado-das-acoes.json")
        project_root = Path(__file__).resolve().parents[1]
        self.assertTrue(config.audit_file.is_relative_to(project_root))

    def test_invalid_mode_is_rejected(self) -> None:
        with patch.dict(
            os.environ, {"MCP_SECRETARY_MODE": "danger"}, clear=True
        ):
            with self.assertRaises(ValueError):
                SecretaryConfig.from_env()

if __name__ == "__main__":
    unittest.main()
