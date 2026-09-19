"""CLI-чат ассистента: выход и печать ответа."""

from __future__ import annotations

import io
import json
import unittest
from typing import Any
from unittest.mock import patch

from assistant.app import App
from assistant.cli import print_result, run_chat
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
    def call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        return {"hits": []}


class StubLLM:
    def complete(self, messages: list[dict[str, Any]], **kwargs: Any) -> LLMTurn:
        return LLMTurn(content="ok")


class FixedApp(App):
    def ask(self, question: str) -> ChatResult:
        return ChatResult(answer=f"[{question}]", sources=[], tools_used=["search_records"])


class AssistantCliTest(unittest.TestCase):
    def test_quit(self) -> None:
        out = io.StringIO()
        code = run_chat(app=FixedApp(_settings(), StubMCP(), StubLLM()), stdin=io.StringIO("/quit\n"), stdout=out)
        self.assertEqual(code, 0)
        self.assertIn("ассистент сметы", out.getvalue())

    def test_one_question_then_eof(self) -> None:
        out = io.StringIO()
        code = run_chat(
            app=FixedApp(_settings(), StubMCP(), StubLLM()),
            stdin=io.StringIO("лимит?\n"),
            stdout=out,
        )
        self.assertEqual(code, 0)
        self.assertIn("[лимит?]", out.getvalue())
        self.assertIn("search_records", out.getvalue())

    def test_print_result_json(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            print_result(ChatResult(answer="нет", sources=[], tools_used=[]))
        self.assertIn("нет", buf.getvalue())
        meta = json.loads(buf.getvalue().split("---", 1)[1])
        self.assertEqual(meta["tools_used"], [])


if __name__ == "__main__":
    unittest.main()
