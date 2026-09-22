"""Настройки telegram_bot из окружения."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from telegram_bot.settings import load_settings


class TelegramSettingsTest(unittest.TestCase):
    def test_defaults(self) -> None:
        values = {"ASSISTANT_URL": "", "TELEGRAM_CHAT_TIMEOUT": ""}

        def _get(key: str, default: str | None = None) -> str | None:
            return values.get(key, default)

        with patch("os.environ.get", side_effect=_get):
            cfg = load_settings()
        self.assertEqual(cfg.assistant_url, "http://127.0.0.1:7346")
        self.assertEqual(cfg.chat_timeout, 180.0)

    def test_timeout_follows_llm_when_unset(self) -> None:
        values = {
            "ASSISTANT_URL": "http://assistant:7346/",
            "ASSISTANT_LLM_TIMEOUT": "200",
        }

        def _get(key: str, default: str | None = None) -> str | None:
            return values.get(key, default)

        with patch("os.environ.get", side_effect=_get):
            cfg = load_settings()
        self.assertEqual(cfg.assistant_url, "http://assistant:7346")
        self.assertEqual(cfg.chat_timeout, 200.0)


if __name__ == "__main__":
    unittest.main()
