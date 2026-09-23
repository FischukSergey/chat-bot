"""Цикл long polling: getUpdates → POST /chat → sendMessage."""

from __future__ import annotations

import sys
import time
from typing import Any, Callable

from telegram_bot.chat import AssistantClient, ChatError, ChatReply
from telegram_bot.telegram import TelegramClient, TelegramError


def is_allowed(chat_id: int, allowed_chat_id: int | None) -> bool:
    return allowed_chat_id is not None and chat_id == allowed_chat_id


def parse_question(update: dict[str, Any]) -> tuple[int, str] | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat = message.get("chat")
    if not isinstance(chat, dict) or chat.get("id") is None:
        return None
    try:
        chat_id = int(chat["id"])
    except (TypeError, ValueError):
        return None
    text = message.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    return chat_id, text.strip()


def handle_update(
    update: dict[str, Any],
    assistant: AssistantClient,
    telegram: TelegramClient,
) -> None:
    parsed = parse_question(update)
    if parsed is None:
        return
    chat_id, question = parsed
    if not is_allowed(chat_id, telegram.settings.allowed_chat_id):
        return
    try:
        reply = assistant.ask(question)
    except ChatError as exc:
        telegram.send_message(chat_id, f"не удалось ответить: {exc}")
        return
    telegram.send_message(chat_id, format_reply(reply))


def format_source(src: dict[str, Any]) -> str:
    parts: list[str] = []
    if src.get("source_file"):
        parts.append(str(src["source_file"]))
    if src.get("sheet"):
        parts.append(str(src["sheet"]))
    if src.get("row") is not None:
        parts.append(f"стр. {src['row']}")
    if src.get("article_code"):
        parts.append(str(src["article_code"]))
    return " / ".join(parts)


def format_reply(reply: ChatReply) -> str:
    text = reply.answer.strip()
    lines = [format_source(src) for src in reply.sources]
    lines = [line for line in lines if line]
    if not lines:
        return text
    if len(lines) == 1:
        block = f"Источник: {lines[0]}"
    else:
        listed = "\n".join(f"- {line}" for line in lines)
        block = f"Источники:\n{listed}"
    if not text:
        return block
    return f"{text}\n\n{block}"


def next_offset(
    updates: list[dict[str, Any]],
    offset: int | None,
) -> int | None:
    if not updates:
        return offset
    last = updates[-1].get("update_id")
    try:
        return int(last) + 1
    except (TypeError, ValueError):
        return offset


def poll_once(
    telegram: TelegramClient,
    assistant: AssistantClient,
    offset: int | None,
) -> int | None:
    updates = telegram.get_updates(offset)
    for update in updates:
        handle_update(update, assistant, telegram)
    return next_offset(updates, offset)


def run_polling(
    telegram: TelegramClient,
    assistant: AssistantClient,
    *,
    should_stop: Callable[[], bool] | None = None,
) -> None:
    telegram.delete_webhook()
    offset: int | None = None
    while should_stop is None or not should_stop():
        try:
            offset = poll_once(telegram, assistant, offset)
        except TelegramError as exc:
            if should_stop is not None and should_stop():
                return
            print(f"telegram poll: {exc}", file=sys.stderr, flush=True)
            time.sleep(1)
