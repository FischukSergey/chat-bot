"""HTTP-клиент MCP: успех, валидация, неизвестный tool."""

from __future__ import annotations

import unittest

import httpx

from assistant.mcp_client import MCPClient, MCPError
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


class MCPClientTest(unittest.TestCase):
    def test_call_posts_json_and_returns_body(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.method, "POST")
            self.assertEqual(str(request.url), "http://mcp.test/tools/search_records")
            self.assertEqual(json_body(request), {"filters": {"article_code": "production:1.8.2"}})
            return httpx.Response(200, json={"hits": [{"fields": {"limit_amount": 1.0}}]})

        client = MCPClient(_settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
        body = client.call("search_records", {"filters": {"article_code": "production:1.8.2"}})
        self.assertEqual(body["hits"][0]["fields"]["limit_amount"], 1.0)

    def test_validation_error_is_mcp_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                json={"error": "validation", "message": 'unknown field "contract_number"'},
            )

        client = MCPClient(_settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
        with self.assertRaises(MCPError) as cm:
            client.call("search_records", {"filters": {"contract_number": "1"}})
        self.assertEqual(cm.exception.status, 400)
        self.assertEqual(cm.exception.kind, "validation")

    def test_unknown_local_tool_does_not_hit_http(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError(f"unexpected {request.url}")

        client = MCPClient(_settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
        with self.assertRaises(MCPError) as cm:
            client.call("get_contract", {})
        self.assertEqual(cm.exception.kind, "not_found")

    def test_health(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "http://mcp.test/health")
            return httpx.Response(200, json={"status": "ok", "points": 172})

        client = MCPClient(_settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
        self.assertEqual(client.health()["points"], 172)


def json_body(request: httpx.Request) -> object:
    return httpx.Response(200, content=request.content).json()


if __name__ == "__main__":
    unittest.main()
