"""Точка входа: python3 -m telegram_bot — long polling."""

from __future__ import annotations

import sys

from telegram_bot.chat import AssistantClient
from telegram_bot.poll import run_polling
from telegram_bot.settings import load_settings
from telegram_bot.telegram import TelegramClient


def main(argv: list[str] | None = None) -> int:
    del argv
    cfg = load_settings()
    if not cfg.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN пуст", file=sys.stderr)
        return 2
    if cfg.allowed_chat_id is None:
        print("TELEGRAM_ALLOWED_CHAT_ID пуст", file=sys.stderr)
        return 2
    print("telegram long polling getUpdates", file=sys.stderr, flush=True)
    with TelegramClient(cfg) as telegram:
        with AssistantClient(cfg) as assistant:
            run_polling(telegram, assistant)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
