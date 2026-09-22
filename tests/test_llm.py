"""Разбор OpenAI chat completions с tool_calls."""

from __future__ import annotations

import unittest

import httpx

from assistant.llm import LLMClient, LLMError, parse_turn
from assistant.settings import Settings


def _settings(*, llm_api_key: str = "", llm_url: str = "http://llm.test/v1") -> Settings:
    return Settings(
        mcp_url="http://mcp.test",
        llm_url=llm_url,
        llm_model="qwen/test",
        max_tool_rounds=2,
        mcp_timeout=5.0,
        llm_timeout=5.0,
        max_tokens=128,
        disable_thinking=True,
        llm_api_key=llm_api_key,
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

    def test_bearer_on_models_and_chat(self) -> None:
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(f"{request.method} {request.url.path}")
            self.assertEqual(request.headers.get("Authorization"), "Bearer sk-or-live")
            if request.url.path.endswith("/models"):
                return httpx.Response(200, json={"data": [{"id": "openrouter/test"}]})
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": "ok"},
                        }
                    ]
                },
            )

        client = LLMClient(
            _settings(llm_api_key="sk-or-live"),
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        self.assertEqual(client.models(), ["openrouter/test"])
        turn = client.complete([{"role": "user", "content": "hi"}])
        self.assertEqual(turn.content, "ok")
        self.assertEqual(seen, ["GET /v1/models", "POST /v1/chat/completions"])

    def test_cloud_omits_chat_template_kwargs(self) -> None:
        cases = (
            _settings(llm_api_key="sk-or-live"),
            _settings(llm_url="https://openrouter.ai/api/v1"),
            _settings(llm_url="https://api.deepseek.com"),
        )

        def handler(request: httpx.Request) -> httpx.Response:
            body = httpx.Response(200, content=request.content).json()
            self.assertNotIn("chat_template_kwargs", body)
            if "api.deepseek.com" in str(request.url):
                self.assertEqual(body.get("thinking"), {"type": "disabled"})
            else:
                self.assertNotIn("thinking", body)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": "ok"},
                        }
                    ]
                },
            )

        for cfg in cases:
            client = LLMClient(
                cfg,
                client=httpx.Client(transport=httpx.MockTransport(handler)),
            )
            turn = client.complete([{"role": "user", "content": "hi"}])
            self.assertEqual(turn.content, "ok")

    def test_empty_key_omits_authorization(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertNotIn("authorization", request.headers)
            if request.url.path.endswith("/models"):
                return httpx.Response(
                    200,
                    json={"data": [{"id": "qwen/test"}]},
                )
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": "ok"},
                        }
                    ]
                },
            )

        for key in ("", "   "):
            client = LLMClient(
                _settings(llm_api_key=key),
                client=httpx.Client(transport=httpx.MockTransport(handler)),
            )
            self.assertEqual(client.models(), ["qwen/test"])
            turn = client.complete([{"role": "user", "content": "hi"}])
            self.assertEqual(turn.content, "ok")

    def test_http_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        client = LLMClient(_settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
        with self.assertRaises(LLMError):
            client.complete([{"role": "user", "content": "hi"}])


if __name__ == "__main__":
    unittest.main()
