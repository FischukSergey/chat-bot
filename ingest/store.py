"""Qdrant: коллекция budget_items, indexes, upsert, delete-source."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from ingest.models import BudgetItem
from ingest.settings import Settings, load_settings

KEYWORD_INDEXES = (
    "article_code",
    "match_key",
    "expense_kind",
    "ancestor_codes",
    "source_file",
    "sheet",
    "article_name_norm",
)
INTEGER_INDEXES = ("year", "article_level", "row")
FLOAT_INDEXES = ("limit_amount", "fact_amount", "obligation_amount", "remain_free")


class StoreError(RuntimeError):
    pass


def connect(settings: Settings | None = None) -> tuple[QdrantClient, Settings]:
    cfg = settings or load_settings()
    return QdrantClient(url=cfg.qdrant_url), cfg


def ensure_collection(client: QdrantClient, cfg: Settings) -> None:
    names = {c.name for c in client.get_collections().collections}
    if cfg.collection not in names:
        client.create_collection(
            collection_name=cfg.collection,
            vectors_config=VectorParams(size=cfg.vector_size, distance=Distance.COSINE),
        )
    else:
        info = client.get_collection(cfg.collection)
        params = info.config.params.vectors
        size = params.size if hasattr(params, "size") else None
        if size is not None and size != cfg.vector_size:
            raise StoreError(
                f"коллекция {cfg.collection} size={size}, в .env VECTOR_SIZE={cfg.vector_size}. "
                "Молча не пересоздаём — дропните коллекцию и переиндексируйте."
            )
    for name in KEYWORD_INDEXES:
        _ensure_index(client, cfg.collection, name, PayloadSchemaType.KEYWORD)
    for name in INTEGER_INDEXES:
        _ensure_index(client, cfg.collection, name, PayloadSchemaType.INTEGER)
    for name in FLOAT_INDEXES:
        _ensure_index(client, cfg.collection, name, PayloadSchemaType.FLOAT)


def _ensure_index(client: QdrantClient, collection: str, field: str, schema: PayloadSchemaType) -> None:
    try:
        client.create_payload_index(collection_name=collection, field_name=field, field_schema=schema)
    except UnexpectedResponse as exc:
        msg = str(exc).lower()
        if exc.status_code in (409, 400) and "exist" in msg:
            return
        raise
    except Exception as exc:  # noqa: BLE001 — qdrant-client иногда кидает обёртку
        if "already exists" in str(exc).lower():
            return
        raise


def upsert_budget(
    items: list[BudgetItem],
    texts: list[str],
    vectors: list[list[float]],
    *,
    client: QdrantClient | None = None,
    settings: Settings | None = None,
    batch_size: int = 64,
) -> int:
    if not (len(items) == len(texts) == len(vectors)):
        raise StoreError("items / texts / vectors разной длины — точку без вектора не пишем")
    own_client = client is None
    qdrant, cfg = connect(settings) if own_client else (client, settings or load_settings())
    try:
        ensure_collection(qdrant, cfg)
        now = datetime.now(timezone.utc).isoformat()
        points = [
            PointStruct(
                id=item.point_id(),
                vector=vec,
                payload=_payload(item, text, now),
            )
            for item, text, vec in zip(items, texts, vectors, strict=True)
        ]
        for start in range(0, len(points), batch_size):
            qdrant.upsert(collection_name=cfg.collection, points=points[start : start + batch_size], wait=True)
        return len(points)
    finally:
        if own_client:
            qdrant.close()


def delete_source(
    source_file: str,
    *,
    client: QdrantClient | None = None,
    settings: Settings | None = None,
) -> None:
    own_client = client is None
    qdrant, cfg = connect(settings) if own_client else (client, settings or load_settings())
    try:
        names = {c.name for c in qdrant.get_collections().collections}
        if cfg.collection not in names:
            return
        qdrant.delete(
            collection_name=cfg.collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="source_file", match=MatchValue(value=source_file))]
                )
            ),
            wait=True,
        )
    finally:
        if own_client:
            qdrant.close()


def existing_ids(point_ids: list[str], settings: Settings | None = None) -> set[str]:
    if not point_ids:
        return set()
    qdrant, cfg = connect(settings)
    try:
        names = {c.name for c in qdrant.get_collections().collections}
        if cfg.collection not in names:
            return set()
        found = qdrant.retrieve(
            collection_name=cfg.collection,
            ids=point_ids,
            with_payload=False,
            with_vectors=False,
        )
        return {str(p.id) for p in found}
    finally:
        qdrant.close()


def collection_count(settings: Settings | None = None) -> int:
    qdrant, cfg = connect(settings)
    try:
        names = {c.name for c in qdrant.get_collections().collections}
        if cfg.collection not in names:
            return 0
        return int(qdrant.count(cfg.collection, exact=True).count)
    finally:
        qdrant.close()


def _payload(item: BudgetItem, text: str, indexed_at: str) -> dict[str, Any]:
    data = item.model_dump()
    data["text"] = text
    data["indexed_at"] = indexed_at
    return data
