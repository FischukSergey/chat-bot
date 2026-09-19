"""Вопрос → LLM (tools) → MCP → ответ. Число кругов tool calls ограничено."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from assistant.llm import LLMClient, LLMTurn, ToolCall
from assistant.mcp_client import ALLOWED_TOOLS, MCPClient, MCPError
from assistant.prompt import system_prompt
from assistant.settings import Settings, load_settings
from assistant.tools import TOOL_DEFINITIONS

EMPTY_ANSWER = "В индексе нет таких записей."
FAILED_ANSWER = "Не удалось сформулировать ответ по результатам инструментов."


class ToolRunner(Protocol):
    def call(self, name: str, arguments: dict[str, Any] | None = None) -> Any: ...


class Completer(Protocol):
    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
    ) -> LLMTurn: ...


@dataclass
class ChatResult:
    answer: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    rounds: int = 0
    hits: int = 0
    latency_ms: int = 0


class Orchestrator:
    def __init__(
        self,
        settings: Settings,
        mcp: ToolRunner,
        llm: Completer,
    ) -> None:
        self.settings = settings
        self.mcp = mcp
        self.llm = llm

    def ask(self, question: str) -> ChatResult:
        started = time.perf_counter()
        text = question.strip()
        if not text:
            return ChatResult(answer=EMPTY_ANSWER)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt()},
            {"role": "user", "content": text},
        ]
        tools_used: list[str] = []
        payloads: list[Any] = []
        rounds = 0
        while True:
            allow_tools = rounds < self.settings.max_tool_rounds
            turn = self.llm.complete(
                messages,
                tools=TOOL_DEFINITIONS if allow_tools else None,
                tool_choice="auto" if allow_tools else "none",
            )
            if turn.tool_calls and allow_tools:
                messages.append(_assistant_tool_message(turn))
                for call in turn.tool_calls:
                    payload = self._run_tool(call)
                    payloads.append(payload)
                    tools_used.append(call.name)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": _tool_content(payload),
                        }
                    )
                rounds += 1
                continue
            if turn.content:
                answer = turn.content
            elif _all_empty(payloads):
                answer = EMPTY_ANSWER
            else:
                answer = _fallback_from_tools(payloads) or FAILED_ANSWER
            return ChatResult(
                answer=answer,
                sources=extract_sources(payloads),
                tools_used=tools_used,
                rounds=rounds,
                hits=hit_count(payloads),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

    def _run_tool(self, call: ToolCall) -> Any:
        if call.arguments.get("_parse_error"):
            return {
                "error": "validation",
                "message": f"не разобрать arguments tool {call.name!r}",
            }
        if call.name not in ALLOWED_TOOLS:
            return {"error": "not_found", "message": f'tool "{call.name}" не реализован'}
        try:
            return self.mcp.call(call.name, call.arguments)
        except MCPError as exc:
            return exc.as_payload()


def ask(question: str, *, settings: Settings | None = None) -> ChatResult:
    from assistant.app import App

    with App.open(settings) as app:
        return app.ask(question)


def extract_sources(payloads: list[Any]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for body in payloads:
        if not isinstance(body, dict):
            continue
        for hit in body.get("hits") or []:
            if not isinstance(hit, dict):
                continue
            src = hit.get("source") if isinstance(hit.get("source"), dict) else {}
            fields = hit.get("fields") if isinstance(hit.get("fields"), dict) else {}
            item = _source_item(src, fields.get("article_code"))
            key = tuple(sorted(item.items()))
            if item and key not in seen:
                seen.add(key)
                out.append(item)
        for row in body.get("rows") or []:
            if not isinstance(row, dict) or not row.get("code"):
                continue
            item = {"article_code": str(row["code"])}
            key = tuple(sorted(item.items()))
            if key not in seen:
                seen.add(key)
                out.append(item)
    return out


def _source_item(src: dict[str, Any], article_code: Any) -> dict[str, Any]:
    item: dict[str, Any] = {}
    if src.get("source_file"):
        item["source_file"] = src["source_file"]
    if src.get("sheet"):
        item["sheet"] = src["sheet"]
    if src.get("row") is not None:
        item["row"] = src["row"]
    if article_code:
        item["article_code"] = str(article_code)
    return item


def _assistant_tool_message(turn: LLMTurn) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": turn.content or None,
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": json.dumps(call.arguments, ensure_ascii=False),
                },
            }
            for call in turn.tool_calls
        ],
    }


def _tool_content(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


def hit_count(payloads: list[Any]) -> int:
    total = 0
    for body in payloads:
        if not isinstance(body, dict) or body.get("error"):
            continue
        if "hits" in body:
            total += len(body.get("hits") or [])
        elif "rows" in body:
            total += len(body.get("rows") or [])
    return total


def _fallback_from_tools(payloads: list[Any]) -> str | None:
    """Если модель молчит, берём total.limit из последнего budget_summary."""
    for body in reversed(payloads):
        if not isinstance(body, dict) or body.get("error"):
            continue
        total = body.get("total")
        if not isinstance(total, dict) or total.get("limit") is None:
            continue
        unit = total.get("amount_unit") or "thousand_rub"
        parts = [f"Лимит: {json.dumps(total['limit'], ensure_ascii=False)} {unit}."]
        codes: list[str] = []
        for row in body.get("rows") or []:
            if isinstance(row, dict) and row.get("code"):
                codes.append(str(row["code"]))
        if codes:
            shown = codes[:12]
            extra = "…" if len(codes) > 12 else ""
            parts.append("Статьи: " + ", ".join(shown) + extra + ".")
        return " ".join(parts)
    return None


def _all_empty(payloads: list[Any]) -> bool:
    if not payloads:
        return False
    for body in payloads:
        if not isinstance(body, dict) or body.get("error"):
            return False
        if body.get("hits"):
            return False
        if body.get("rows"):
            return False
        if body.get("collections"):
            return False
    return True
