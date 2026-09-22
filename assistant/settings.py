"""Настройки оркестратора из .env. Не требует VECTOR_SIZE — это ingest/MCP."""

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


def _truthy(raw: str | None, default: bool) -> bool:
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _int_env(name: str, default: int, *, minimum: int) -> int:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} должен быть целым") from exc
    if value < minimum:
        raise ValueError(f"{name} должен быть >= {minimum}")
    return value


@dataclass(frozen=True)
class Settings:
    mcp_url: str
    llm_url: str
    llm_model: str
    max_tool_rounds: int
    mcp_timeout: float
    llm_timeout: float
    max_tokens: int
    disable_thinking: bool
    http_addr: str = "127.0.0.1:7346"
    llm_api_key: str = ""


def load_settings() -> Settings:
    model = (os.environ.get("LLM_MODEL") or "").strip()
    if not model:
        raise ValueError("LLM_MODEL пуст")
    mcp_url = (os.environ.get("MCP_URL") or "").strip()
    if not mcp_url:
        addr = (os.environ.get("MCP_HTTP_ADDR") or "127.0.0.1:7345").strip()
        mcp_url = addr if addr.startswith("http") else f"http://{addr}"
    return Settings(
        mcp_url=mcp_url.rstrip("/"),
        llm_url=(os.environ.get("LLM_URL") or "http://127.0.0.1:1234/v1").rstrip("/"),
        llm_model=model,
        max_tool_rounds=_int_env("ASSISTANT_MAX_TOOL_ROUNDS", 2, minimum=1),
        mcp_timeout=float(_int_env("ASSISTANT_MCP_TIMEOUT", 30, minimum=1)),
        llm_timeout=float(_int_env("ASSISTANT_LLM_TIMEOUT", 180, minimum=1)),
        max_tokens=_int_env("ASSISTANT_MAX_TOKENS", 2048, minimum=16),
        disable_thinking=_truthy(os.environ.get("LLM_DISABLE_THINKING"), True),
        http_addr=(os.environ.get("ASSISTANT_HTTP_ADDR") or "127.0.0.1:7346").strip(),
        llm_api_key=(os.environ.get("LLM_API_KEY") or "").strip(),
    )
