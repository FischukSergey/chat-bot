"""POST /chat и GET /health без живого LLM."""

from __future__ import annotations

import json
import unittest
from typing import Any

from assistant.app import App
from assistant.httpapi import dispatch
from assistant.llm import LLMTurn
from assistant.orchestrator import ChatResult
from assistant.settings import Settings


def _settings() -> Settings:
    return Settings(
        mcp_url="http://mcp.test",
        llm_url="http://llm.test/v1",
        llm_model="test-model",
        max_tool_rounds=2,
        mcp_timeout=5.0,
        llm_timeout=5.0,
        max_tokens=128,
        disable_thinking=True,
    )


class StubMCP:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        self.calls.append((name, arguments))
        return {"hits": []}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "points": 172}


class StubLLM:
    def complete(self, messages: list[dict[str, Any]], **kwargs: Any) -> LLMTurn:
        return LLMTurn(content="в индексе нет таких записей")

    def models(self) -> list[str]:
        return ["test-model"]


class FixedApp(App):
    def ask(self, question: str) -> ChatResult:
        return ChatResult(
            answer=f"ответ: {question}",
            sources=[{"article_code": "production:1.8.2", "row": 23}],
            tools_used=["search_records"],
            rounds=1,
            hits=1,
            latency_ms=12,
        )


class HttpApiTest(unittest.TestCase):
    def test_chat_ok(self) -> None:
        app = FixedApp(_settings(), StubMCP(), StubLLM())
        code, body = dispatch(
            app,
            "POST",
            "/chat",
            json.dumps({"question": "лимит по production:1.8.2"}).encode(),
        )
        self.assertEqual(code, 200)
        self.assertEqual(body["answer"], "ответ: лимит по production:1.8.2")
        self.assertEqual(body["tools_used"], ["search_records"])
        self.assertEqual(body["sources"][0]["row"], 23)
        self.assertNotIn("rounds", body)

    def test_chat_empty_question(self) -> None:
        app = FixedApp(_settings(), StubMCP(), StubLLM())
        code, body = dispatch(app, "POST", "/chat", b'{"question":"  "}')
        self.assertEqual(code, 400)
        self.assertEqual(body["error"], "validation")

    def test_chat_unknown_field(self) -> None:
        app = FixedApp(_settings(), StubMCP(), StubLLM())
        code, body = dispatch(app, "POST", "/chat", b'{"question":"x","foo":1}')
        self.assertEqual(code, 400)
        self.assertIn("foo", body["message"])

    def test_health_ok(self) -> None:
        app = App(_settings(), StubMCP(), StubLLM())
        code, body = dispatch(app, "GET", "/health", b"")
        self.assertEqual(code, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["mcp"], "ok")
        self.assertEqual(body["llm"], "ok")
        self.assertEqual(body["points"], 172)

    def test_unknown_path(self) -> None:
        app = App(_settings(), StubMCP(), StubLLM())
        code, body = dispatch(app, "GET", "/chat", b"")
        self.assertEqual(code, 404)
        self.assertEqual(body["error"], "not_found")


if __name__ == "__main__":
    unittest.main()
