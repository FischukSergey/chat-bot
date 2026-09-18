"""Нормализация имён статей и match_key."""

from __future__ import annotations

import re
from typing import Any

_TRAILING = re.compile(r"[ .,;:]+$")


def normalize_article_name(raw: str) -> str:
    s = raw.replace("ё", "е").replace("Ё", "е").lower()
    s = re.sub(r"\s+", " ", s).strip()
    return _TRAILING.sub("", s)


def apply_name_aliases(norm: str, mapping: dict[str, Any]) -> str:
    for item in mapping.get("match_key", {}).get("name_aliases") or []:
        if normalize_article_name(item["from"]) == norm:
            return normalize_article_name(item["to"])
    return norm


def match_key_for(
    name_norm: str,
    parent_norm: str | None,
    mapping: dict[str, Any],
) -> str:
    cfg = mapping.get("match_key") or {}
    qualify = {normalize_article_name(x) for x in cfg.get("qualify_with_parent_if_name_in") or []}
    if name_norm in qualify and parent_norm:
        return f"{parent_norm} / {name_norm}"
    return name_norm
