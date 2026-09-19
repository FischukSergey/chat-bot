"""Структурированные логи в stderr: вопрос, tools, hits, latency."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any


def event(**fields: Any) -> None:
    payload = {
        "time": datetime.now(timezone.utc).astimezone().isoformat(),
        "level": "INFO",
        **fields,
    }
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr, flush=True)


def log_chat(
    *,
    question: str,
    tools: list[str],
    hits: int,
    latency_ms: int,
    rounds: int,
    error: str = "",
) -> None:
    event(
        msg="chat",
        question=question,
        tools=tools,
        hits=hits,
        latency_ms=latency_ms,
        rounds=rounds,
        error=error,
    )
