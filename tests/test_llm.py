"""Разбор OpenAI chat completions с tool_calls."""

from __future__ import annotations

import unittest

import httpx

from assistant.llm import LLMClient, LLMError, parse_turn
from assistant.settings import Settings


def _settings() -> Settings:
    return Settings(
        mcp_url="http://mcp.test",
        llm_url="http://llm.test/v1",
        llm_model="qwen/test",
        max_tool_rounds=2,
        mcp_timeout=5.0,
        llm_timeout=5.0,
        max_tokens=128,
        disable_thinking=True,
    )


class ParseTurnTest(unittest.TestCase):
    def test_tool_call_arguments_json(self) -> None:
        turn = parse_turn(
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "search_records",
                                "arguments": '{"filters":{"article_code":"production:1.8.2"}}',
                            },
                        }
                    ],
                },
            }
        )
        self.assertEqual(turn.content, "")
        self.assertEqual(len(turn.tool_calls), 1)
        self.assertEqual(turn.tool_calls[0].name, "search_records")
        self.assertEqual(turn.tool_calls[0].arguments["filters"]["article_code"], "production:1.8.2")

    def test_broken_arguments_marked(self) -> None:
        turn = parse_turn(
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "x",
                            "function": {"name": "budget_summary", "arguments": "article="},
                        }
                    ]
                }
            }
        )
        self.assertIn("_parse_error", turn.tool_calls[0].arguments)


class LLMClientTest(unittest.TestCase):
    def test_complete_sends_tools_and_disables_thinking(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            body = httpx.Response(200, content=request.content).json()
            self.assertEqual(body["model"], "qwen/test")
            self.assertEqual(body["tool_choice"], "auto")
            self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
            self.assertEqual(body["tools"][0]["function"]["name"], "search_records")
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": "в индексе нет"},
                        }
                    ]
                },
            )

        client = LLMClient(_settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
        turn = client.complete(
            [{"role": "user", "content": "?"}],
            tools=[{"type": "function", "function": {"name": "search_records", "parameters": {}}}],
        )
        self.assertEqual(turn.content, "в индексе нет")

    def test_http_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        client = LLMClient(_settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
        with self.assertRaises(LLMError):
            client.complete([{"role": "user", "content": "hi"}])


if __name__ == "__main__":
    unittest.main()
