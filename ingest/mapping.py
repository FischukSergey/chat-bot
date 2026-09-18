"""Загрузка YAML-маппинга бюджета."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_MAPPING = Path(__file__).resolve().parent.parent / "data" / "mappings" / "budget.yaml"


def load_budget_mapping(path: Path | None = None) -> dict[str, Any]:
    src = path or DEFAULT_MAPPING
    data = yaml.safe_load(src.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("kind") != "budget":
        raise ValueError(f"ожидали kind=budget в {src}")
    return data
