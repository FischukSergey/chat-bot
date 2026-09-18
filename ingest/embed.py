"""OpenAI-compatible embeddings: батч, ретраи на 5xx. Точку без вектора не отдаём."""

from __future__ import annotations

import time
from typing import Any

import httpx

from ingest.settings import Settings, load_settings


class EmbedError(RuntimeError):
    pass


def embed_texts(
    texts: list[str],
    settings: Settings | None = None,
    *,
    batch_size: int = 16,
    retries: int = 3,
) -> list[list[float]]:
    if not texts:
        return []
    cfg = settings or load_settings()
    out: list[list[float]] = []
    with httpx.Client(timeout=120.0) as client:
        for start in range(0, len(texts), batch_size):
            chunk = texts[start : start + batch_size]
            out.extend(_embed_batch(client, cfg, chunk, retries=retries))
    return out


def _embed_batch(
    client: httpx.Client,
    cfg: Settings,
    texts: list[str],
    *,
    retries: int,
) -> list[list[float]]:
    url = f"{cfg.embeddings_url}/embeddings"
    payload: dict[str, Any] = {"model": cfg.embeddings_model, "input": texts}
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = client.post(url, json=payload)
            if resp.status_code >= 500 or resp.status_code == 429:
                last_exc = EmbedError(f"embeddings HTTP {resp.status_code}: {resp.text[:200]}")
                time.sleep(0.5 * (2**attempt))
                continue
            if resp.status_code >= 400:
                raise EmbedError(f"embeddings HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            rows = sorted(data.get("data") or [], key=lambda r: r.get("index", 0))
            vectors = [list(r["embedding"]) for r in rows]
            if len(vectors) != len(texts):
                raise EmbedError(f"ожидали {len(texts)} векторов, пришло {len(vectors)}")
            for vec in vectors:
                if len(vec) != cfg.vector_size:
                    raise EmbedError(
                        f"длина вектора {len(vec)} ≠ VECTOR_SIZE {cfg.vector_size}"
                    )
            return vectors
        except httpx.HTTPError as exc:
            last_exc = exc
            time.sleep(0.5 * (2**attempt))
    raise EmbedError(f"embeddings недоступны после {retries} попыток: {last_exc}")
