"""Системный промпт из репозитория, не из головы."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "system.md"


@lru_cache(maxsize=1)
def system_prompt() -> str:
    text = PROMPT_PATH.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError(f"пустой промпт: {PROMPT_PATH}")
    return text
