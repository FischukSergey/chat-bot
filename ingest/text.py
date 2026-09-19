"""Детерминированный text для эмбеддинга — шаблон из budget.yaml."""

from __future__ import annotations

import re
from typing import Any

from ingest.mapping import load_budget_mapping
from ingest.models import BudgetItem
from ingest.names import normalize_article_name

_MULTI_SLASH = re.compile(r"(?: / )+")


def path_names(item: BudgetItem) -> list[str]:
    """Имена предков и листа, без пустых и подряд идущих дублей."""
    raw = [
        item.l1_name,
        item.l2_name,
        item.l3_name,
        item.l4_name,
        item.l5_name,
        item.article_name,
    ]
    out: list[str] = []
    seen_norm: set[str] = set()
    for name in raw:
        text = (name or "").strip()
        if not text:
            continue
        key = normalize_article_name(text)
        if not key or key in seen_norm:
            continue
        seen_norm.add(key)
        out.append(text)
    return out


def ancestor_names(item: BudgetItem) -> list[str]:
    """Только родители, без имени листа."""
    leaf = normalize_article_name(item.article_name)
    return [n for n in path_names(item) if normalize_article_name(n) != leaf]


def render_budget_text(item: BudgetItem, template: str | None = None) -> str:
    tpl = template if template is not None else load_budget_mapping()["text_template"]
    names = path_names(item)
    data: dict[str, Any] = item.model_dump()
    data["path_text"] = " / ".join(names)
    data["ancestor_text"] = ", ".join(ancestor_names(item))
    for key, val in list(data.items()):
        if val is None:
            data[key] = ""
    text = str(tpl).format(**data)
    text = _MULTI_SLASH.sub(" / ", text)
    text = re.sub(r" / \n", "\n", text)
    return text.strip() + "\n"
