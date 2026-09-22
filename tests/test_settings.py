"""Настройки assistant из окружения."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from assistant.settings import load_settings


class SettingsTest(unittest.TestCase):
    def test_mcp_url_from_addr(self) -> None:
        values = {
            "LLM_MODEL": "qwen/test",
            "LLM_URL": "http://127.0.0.1:1234/v1",
            "MCP_URL": "",
            "MCP_HTTP_ADDR": "127.0.0.1:7345",
            "ASSISTANT_MAX_TOOL_ROUNDS": "2",
            "ASSISTANT_MCP_TIMEOUT": "",
            "ASSISTANT_LLM_TIMEOUT": "",
            "ASSISTANT_MAX_TOKENS": "",
            "LLM_DISABLE_THINKING": "",
            "LLM_API_KEY": " sk-or-test ",
        }

        def _get(key: str, default: str | None = None) -> str | None:
            return values.get(key, default)

        with patch("os.environ.get", side_effect=_get):
            cfg = load_settings()
        self.assertEqual(cfg.mcp_url, "http://127.0.0.1:7345")
        self.assertEqual(cfg.max_tool_rounds, 2)
        self.assertTrue(cfg.disable_thinking)
        self.assertEqual(cfg.llm_api_key, "sk-or-test")

    def test_empty_api_key_is_blank(self) -> None:
        values = {
            "LLM_MODEL": "qwen/test",
            "LLM_URL": "http://127.0.0.1:1234/v1",
            "MCP_HTTP_ADDR": "127.0.0.1:7345",
            "LLM_API_KEY": "  ",
        }

        def _get(key: str, default: str | None = None) -> str | None:
            return values.get(key, default)

        with patch("os.environ.get", side_effect=_get):
            cfg = load_settings()
        self.assertEqual(cfg.llm_api_key, "")

    def test_empty_model_fails(self) -> None:
        with patch("os.environ.get", side_effect=lambda key, default=None: ""):
            with self.assertRaises(ValueError):
                load_settings()


if __name__ == "__main__":
    unittest.main()
