"""Long polling getUpdates без живого Telegram и без webhook."""

from __future__ import annotations

import unittest
from typing import Any

import httpx

from telegram_bot.chat import AssistantClient, ChatReply
from telegram_bot.poll import (
    format_reply,
    is_allowed,
    parse_question,
    poll_once,
    run_polling,
)
from telegram_bot.settings import Settings
from telegram_bot.telegram import TelegramClient


def _settings() -> Settings:
    return Settings(
        assistant_url="http://assistant.test:7346",
        chat_timeout=5.0,
        telegram_bot_token="tok",
        telegram_api_url="https://api.telegram.test",
        poll_timeout=1,
        allowed_chat_id=77,
    )


def _update(update_id: int, chat_id: int, text: str | None) -> dict[str, Any]:
    message: dict[str, Any] = {"chat": {"id": chat_id}}
    if text is not None:
        message["text"] = text
    return {"update_id": update_id, "message": message}


class ParseQuestionTest(unittest.TestCase):
    def test_text_message(self) -> None:
        self.assertEqual(
            parse_question(_update(1, 42, "  лимит 1.8.2  ")),
            (42, "лимит 1.8.2"),
        )

    def test_skip_sticker_and_empty(self) -> None:
        self.assertIsNone(parse_question(_update(1, 42, None)))
        self.assertIsNone(parse_question(_update(1, 42, "   ")))
        self.assertIsNone(parse_question({"update_id": 1}))

    def test_string_chat_id_and_bad_id(self) -> None:
        update = {
            "update_id": 2,
            "message": {"chat": {"id": "42"}, "text": "код 1.8.2"},
        }
        self.assertEqual(parse_question(update), (42, "код 1.8.2"))
        bad = {
            "update_id": 3,
            "message": {"chat": {"id": "x"}, "text": "лимит"},
        }
        self.assertIsNone(parse_question(bad))


class AllowlistTest(unittest.TestCase):
    def test_only_configured_chat(self) -> None:
        self.assertTrue(is_allowed(77, 77))
        self.assertFalse(is_allowed(78, 77))
        self.assertFalse(is_allowed(77, None))

    def test_foreign_chat_skips_assistant(self) -> None:
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.url.path)
            if request.url.path.endswith("/getUpdates"):
                return httpx.Response(
                    200,
                    json={
                        "ok": True,
                        "result": [_update(3, 999, "лимит production:1.8.2")],
                    },
                )
            self.fail(f"чужой чат не должен ходить в {request.url.path}")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        http = httpx.Client(transport=transport)
        telegram = TelegramClient(_settings(), client=http)
        assistant = AssistantClient(_settings(), client=http)
        poll_once(telegram, assistant, None)
        self.assertTrue(any(p.endswith("/getUpdates") for p in seen))
        self.assertFalse(any(p.endswith("/chat") for p in seen))
        self.assertFalse(any(p.endswith("/sendMessage") for p in seen))

    def test_empty_allowlist_skips_even_same_chat(self) -> None:
        seen: list[str] = []
        cfg = Settings(
            assistant_url="http://assistant.test:7346",
            chat_timeout=5.0,
            telegram_bot_token="tok",
            telegram_api_url="https://api.telegram.test",
            poll_timeout=1,
            allowed_chat_id=None,
        )

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.url.path)
            if request.url.path.endswith("/getUpdates"):
                return httpx.Response(
                    200,
                    json={"ok": True, "result": [_update(4, 77, "лимит")]},
                )
            self.fail(f"без allowlist не ждать {request.url.path}")
            return httpx.Response(404)

        http = httpx.Client(transport=httpx.MockTransport(handler))
        poll_once(TelegramClient(cfg, client=http), AssistantClient(cfg, client=http), None)
        self.assertFalse(any(p.endswith("/chat") for p in seen))


class FormatReplyTest(unittest.TestCase):
    def test_answer_and_one_source(self) -> None:
        text = format_reply(
            ChatReply(
                answer="лимит 124970.30",
                sources=[
                    {
                        "source_file": "БДР.xlsx",
                        "sheet": "Смета затрат",
                        "row": 23,
                        "article_code": "production:1.8.2",
                    }
                ],
            )
        )
        self.assertIn("лимит 124970.30", text)
        self.assertIn("Источник:", text)
        self.assertIn("БДР.xlsx", text)
        self.assertIn("Смета затрат", text)
        self.assertIn("стр. 23", text)
        self.assertIn("production:1.8.2", text)

    def test_refuse_without_sources(self) -> None:
        text = format_reply(ChatReply(answer="В индексе нет таких записей."))
        self.assertEqual(text, "В индексе нет таких записей.")
        self.assertNotIn("Источник", text)


class PollTest(unittest.TestCase):
    def test_poll_once_uses_get_updates_not_webhook(self) -> None:
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            seen.append(path)
            if path.endswith("/getUpdates"):
                body = httpx.Response(200, content=request.content).json()
                self.assertEqual(body["timeout"], 1)
                self.assertEqual(body["allowed_updates"], ["message"])
                self.assertEqual(body["offset"], 10)
                return httpx.Response(
                    200,
                    json={
                        "ok": True,
                        "result": [_update(10, 77, "лимит production:1.8.2")],
                    },
                )
            if path.endswith("/chat"):
                return httpx.Response(
                    200,
                    json={
                        "answer": "лимит 124970.30",
                        "sources": [
                            {
                                "source_file": "БДР.xlsx",
                                "sheet": "Смета затрат",
                                "row": 23,
                                "article_code": "production:1.8.2",
                            }
                        ],
                        "tools_used": ["search_records"],
                    },
                )
            if path.endswith("/sendMessage"):
                body = httpx.Response(200, content=request.content).json()
                self.assertEqual(body["chat_id"], 77)
                self.assertIn("124970.30", body["text"])
                self.assertIn("стр. 23", body["text"])
                self.assertIn("production:1.8.2", body["text"])
                return httpx.Response(200, json={"ok": True, "result": {}})
            self.fail(f"неожиданный путь {path}")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        http = httpx.Client(transport=transport)
        telegram = TelegramClient(_settings(), client=http)
        assistant = AssistantClient(_settings(), client=http)
        nxt = poll_once(telegram, assistant, 10)
        self.assertEqual(nxt, 11)
        self.assertTrue(any(p.endswith("/getUpdates") for p in seen))
        self.assertTrue(any(p.endswith("/chat") for p in seen))
        self.assertTrue(any(p.endswith("/sendMessage") for p in seen))
        webhook = any("setWebhook" in p or "webhook" in p for p in seen)
        self.assertFalse(webhook)

    def test_run_polling_deletes_webhook_then_get_updates(self) -> None:
        seen: list[str] = []
        n = {"i": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request.url.path)
            if request.url.path.endswith("/deleteWebhook"):
                self.assertNotIn("setWebhook", request.url.path)
                return httpx.Response(200, json={"ok": True, "result": True})
            if request.url.path.endswith("/getUpdates"):
                n["i"] += 1
                return httpx.Response(200, json={"ok": True, "result": []})
            self.fail(f"неожиданный путь {request.url.path}")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        http = httpx.Client(transport=transport)
        telegram = TelegramClient(_settings(), client=http)
        assistant = AssistantClient(_settings(), client=http)
        run_polling(telegram, assistant, should_stop=lambda: n["i"] >= 1)
        self.assertTrue(seen[0].endswith("/deleteWebhook"))
        self.assertTrue(any(p.endswith("/getUpdates") for p in seen))
        self.assertFalse(any("setWebhook" in p for p in seen))


if __name__ == "__main__":
    unittest.main()
