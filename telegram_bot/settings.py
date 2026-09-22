"""Настройки бота из .env. RAG и LLM здесь не конфигурируем."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())


_load_dotenv(ENV_FILE)


def _float_env(name: str, default: float, *, minimum: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} должен быть числом") from exc
    if value < minimum:
        raise ValueError(f"{name} должен быть >= {minimum}")
    return value


@dataclass(frozen=True)
class Settings:
    assistant_url: str
    chat_timeout: float


def load_settings() -> Settings:
    url = (os.environ.get("ASSISTANT_URL") or "http://127.0.0.1:7346").strip()
    timeout = _float_env("TELEGRAM_CHAT_TIMEOUT", 0, minimum=0)
    if timeout <= 0:
        timeout = _float_env("ASSISTANT_LLM_TIMEOUT", 180, minimum=1)
    return Settings(assistant_url=url.rstrip("/"), chat_timeout=timeout)
