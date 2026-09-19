"""OpenAI tool definitions. Имена и schema как у MCP Sprint 3."""

from __future__ import annotations

from typing import Any

_FILTERS: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "year": {"type": "integer"},
        "expense_kind": {"type": "string", "enum": ["production", "management"]},
        "article_code": {"type": "string"},
        "article_name": {"type": "string"},
        "match_key": {"type": "string"},
        "ancestor_code": {"type": "string"},
        "amount_min": {"type": "number"},
        "amount_max": {"type": "number"},
    },
}

_SEARCH: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "query": {"type": "string"},
        "collections": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string", "enum": ["budget_items"]},
        },
        "filters": _FILTERS,
        "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
    },
}

_SUMMARY: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "year": {"type": "integer"},
        "article_code": {"type": "string"},
        "article_name": {"type": "string"},
        "match_key": {"type": "string"},
        "expense_kind": {"type": "string", "enum": ["production", "management"]},
        "group_by_level": {"type": "integer", "minimum": 1, "maximum": 5},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
    },
}

_STATUS: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {},
}


def _fn(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    _fn(
        "search_records",
        "Гибридный поиск по смете: текст и/или фильтры. Только budget_items. "
        "Точный код статьи — filters.article_code, без семантики.",
        _SEARCH,
    ),
    _fn(
        "budget_summary",
        "Сумма листьев ветки бюджета. remain_free из индекса, без пересчёта. "
        "Нужен год и/или статья / kind. Пустой remain_free не заменять лимитом.",
        _SUMMARY,
    ),
    _fn(
        "ingest_status",
        "Служебное: число точек и source_file. Не для бизнес-цифр в ответе пользователю.",
        _STATUS,
    ),
]

TOOL_NAMES = tuple(item["function"]["name"] for item in TOOL_DEFINITIONS)
