"""OpenAI-compatible chat completions с tool calling."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from assistant.settings import Settings, load_settings


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    raw_arguments: str = ""


@dataclass(frozen=True)
class LLMTurn:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = ""


class LLMClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self._own_client = client is None
        self._client = client or httpx.Client(timeout=self.settings.llm_timeout)

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> LLMClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _auth_headers(self) -> dict[str, str]:
        key = self.settings.llm_api_key.strip()
        if not key:
            return {}
        return {"Authorization": f"Bearer {key}"}

    def _is_cloud_llm(self) -> bool:
        if self.settings.llm_api_key.strip():
            return True
        host = self.settings.llm_url.lower()
        return "openrouter.ai" in host or "api.deepseek.com" in host

    def _is_deepseek_api(self) -> bool:
        return "api.deepseek.com" in self.settings.llm_url.lower()

    def models(self) -> list[str]:
        resp = self._client.get(f"{self.settings.llm_url}/models", headers=self._auth_headers())
        if resp.status_code >= 400:
            raise LLMError(f"models HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        return [str(row["id"]) for row in data.get("data") or [] if row.get("id")]

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
    ) -> LLMTurn:
        payload: dict[str, Any] = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": self.settings.max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        if self.settings.disable_thinking:
            if self._is_deepseek_api():
                payload["thinking"] = {"type": "disabled"}
            elif not self._is_cloud_llm():
                payload["chat_template_kwargs"] = {"enable_thinking": False}
        resp = self._client.post(
            f"{self.settings.llm_url}/chat/completions",
            json=payload,
            headers=self._auth_headers(),
        )
        if resp.status_code >= 400:
            raise LLMError(f"chat HTTP {resp.status_code}: {resp.text[:400]}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMError("chat: ответ не JSON") from exc
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("chat: пустой choices")
        return parse_turn(choices[0])


def parse_turn(choice: dict[str, Any]) -> LLMTurn:
    msg = choice.get("message") or {}
    content = msg.get("content")
    if content is None:
        content = ""
    if not isinstance(content, str):
        content = str(content)
    calls: list[ToolCall] = []
    for i, raw in enumerate(msg.get("tool_calls") or []):
        if not isinstance(raw, dict):
            continue
        fn = raw.get("function") or {}
        args_raw = fn.get("arguments")
        parsed, raw_text = _parse_arguments(args_raw)
        call_id = str(raw.get("id") or f"call_{i}")
        calls.append(
            ToolCall(
                id=call_id,
                name=str(fn.get("name") or ""),
                arguments=parsed,
                raw_arguments=raw_text,
            )
        )
    return LLMTurn(
        content=content.strip(),
        tool_calls=calls,
        finish_reason=str(choice.get("finish_reason") or ""),
    )


def _parse_arguments(raw: Any) -> tuple[dict[str, Any], str]:
    if raw is None:
        return {}, ""
    if isinstance(raw, dict):
        return raw, json.dumps(raw, ensure_ascii=False)
    if not isinstance(raw, str):
        return {}, str(raw)
    text = raw.strip()
    if not text:
        return {}, ""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"_parse_error": text}, text
    if isinstance(parsed, dict):
        return parsed, text
    return {"_parse_error": text}, text
