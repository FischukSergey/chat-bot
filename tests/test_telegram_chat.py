"""Тонкий клиент POST /chat, без оркестратора."""

from __future__ import annotations

import unittest

import httpx

from telegram_bot.chat import AssistantClient, ChatError
from telegram_bot.settings import Settings


def _settings() -> Settings:
    return Settings(
        assistant_url="http://assistant.test:7346",
        chat_timeout=5.0,
    )


class AssistantClientTest(unittest.TestCase):
    def test_ask_posts_only_question(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.url.path, "/chat")
            body = httpx.Response(200, content=request.content).json()
            self.assertEqual(list(body), ["question"])
            self.assertEqual(body["question"], "лимит production:1.8.2")
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

        client = AssistantClient(
            _settings(),
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        reply = client.ask("  лимит production:1.8.2  ")
        self.assertEqual(reply.answer, "лимит 124970.30")
        self.assertEqual(reply.sources[0]["row"], 23)
        self.assertEqual(reply.tools_used, ["search_records"])

    def test_empty_question_skips_http(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError(f"не ждать HTTP: {request.url}")

        client = AssistantClient(
            _settings(),
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        with self.assertRaises(ChatError):
            client.ask("   ")

    def test_http_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                502,
                json={"error": "error", "message": "llm down"},
            )

        client = AssistantClient(
            _settings(),
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        with self.assertRaises(ChatError) as ctx:
            client.ask("hi")
        self.assertIn("502", str(ctx.exception))
        self.assertIn("llm down", str(ctx.exception))


class NoOrchestratorImportTest(unittest.TestCase):
    def test_package_does_not_import_orchestrator(self) -> None:
        import telegram_bot.chat as chat_mod

        self.assertNotIn("assistant.orchestrator", chat_mod.__dict__)
        self.assertNotIn("assistant.app", chat_mod.__dict__)
        self.assertFalse(hasattr(chat_mod, "Orchestrator"))


if __name__ == "__main__":
    unittest.main()
