"""HTTP-клиент к POST /chat. Без MCP, LLM и оркестратора."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from telegram_bot.settings import Settings, load_settings


class ChatError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChatReply:
    answer: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)


class AssistantClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self._own_client = client is None
        timeout = self.settings.chat_timeout
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> AssistantClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def ask(self, question: str) -> ChatReply:
        text = question.strip()
        if not text:
            raise ChatError("нужен непустой question")
        resp = self._client.post(
            f"{self.settings.assistant_url}/chat",
            json={"question": text},
        )
        try:
            body: Any = resp.json()
        except ValueError as exc:
            code = resp.status_code
            raise ChatError(f"chat: ответ не JSON ({code})") from exc
        if resp.status_code >= 400:
            message = resp.text[:300]
            if isinstance(body, dict) and body.get("message"):
                message = str(body["message"])
            code = resp.status_code
            raise ChatError(f"chat HTTP {code}: {message}")
        answer = body.get("answer") if isinstance(body, dict) else None
        if not isinstance(body, dict) or not isinstance(answer, str):
            raise ChatError("chat: ожидались answer и sources")
        sources = body.get("sources") or []
        tools = body.get("tools_used") or []
        if not isinstance(sources, list) or not isinstance(tools, list):
            raise ChatError("chat: sources/tools_used должны быть списками")
        return ChatReply(
            answer=answer,
            sources=[row for row in sources if isinstance(row, dict)],
            tools_used=[str(name) for name in tools],
        )
