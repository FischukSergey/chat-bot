"""Стабильный id точки Qdrant: UUID5 от бизнес-ключа, не от номера строки."""

from __future__ import annotations

import uuid

_NAMESPACE = uuid.UUID("8f3c2e1a-6b14-4d90-9a7e-2c5d81f0b4e3")


def make_point_id(*parts: str) -> str:
    """Собрать UUID из непустых частей ключа.

    Пустые части отбрасываются. Порядок фиксирован вызывающим кодом.
    """
    key = "\0".join(p.strip() for p in parts if p.strip())
    if not key:
        raise ValueError("point id: пустой ключ")
    return str(uuid.uuid5(_NAMESPACE, key))
