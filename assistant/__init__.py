"""RAG-оркестратор: вопрос → MCP → ответ."""

from __future__ import annotations

from typing import Any

__version__ = "0.0.0"
__all__ = ["ChatResult", "ask"]


def __getattr__(name: str) -> Any:
    if name in {"ChatResult", "ask"}:
        from assistant.orchestrator import ChatResult, ask

        return ChatResult if name == "ChatResult" else ask
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
