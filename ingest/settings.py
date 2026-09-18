"""Настройки ingest из .env и окружения. Коллекцию с vector_size=0 не создаём."""

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


@dataclass(frozen=True)
class Settings:
    qdrant_url: str
    collection: str
    embeddings_url: str
    embeddings_model: str
    vector_size: int


def load_settings() -> Settings:
    size = int(os.environ.get("VECTOR_SIZE") or "0")
    model = os.environ.get("EMBEDDINGS_MODEL") or ""
    if size <= 0:
        raise ValueError("VECTOR_SIZE должен быть > 0 (длина /v1/embeddings)")
    if not model:
        raise ValueError("EMBEDDINGS_MODEL пуст")
    return Settings(
        qdrant_url=os.environ.get("QDRANT_URL") or "http://127.0.0.1:6333",
        collection=os.environ.get("QDRANT_COLLECTION_BUDGET") or "budget_items",
        embeddings_url=(os.environ.get("EMBEDDINGS_URL") or "http://127.0.0.1:1234/v1").rstrip("/"),
        embeddings_model=model,
        vector_size=size,
    )
