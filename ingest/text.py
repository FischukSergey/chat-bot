"""Детерминированный text для эмбеддинга — шаблон из budget.yaml."""

from __future__ import annotations

import re
from typing import Any

from ingest.mapping import load_budget_mapping
from ingest.models import BudgetItem

_MULTI_SLASH = re.compile(r"(?: / )+")


def render_budget_text(item: BudgetItem, template: str | None = None) -> str:
    tpl = template if template is not None else load_budget_mapping()["text_template"]
    data: dict[str, Any] = item.model_dump()
    for key, val in list(data.items()):
        if val is None:
            data[key] = ""
    text = str(tpl).format(**data)
    text = _MULTI_SLASH.sub(" / ", text)
    text = re.sub(r" / \n", "\n", text)
    return text.strip() + "\n"
