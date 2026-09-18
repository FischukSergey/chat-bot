"""Склейка text → embeddings → upsert. Без вектора в Qdrant не пишем."""

from __future__ import annotations

from ingest.embed import embed_texts
from ingest.models import BudgetItem
from ingest.settings import Settings, load_settings
from ingest.store import upsert_budget
from ingest.text import render_budget_text


def index_budget_items(items: list[BudgetItem], settings: Settings | None = None) -> int:
    if not items:
        return 0
    cfg = settings or load_settings()
    texts = [render_budget_text(item) for item in items]
    vectors = embed_texts(texts, cfg)
    return upsert_budget(items, texts, vectors, settings=cfg)
