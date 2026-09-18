"""Канонические записи ingest. Парсер мапит Excel сюда, не в Qdrant напрямую."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ingest.ids import make_point_id

ExpenseKind = Literal["production", "management"]
RemainFreeSource = Literal["excel", "computed"]


class SourceMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_file: str
    sheet: str
    row: int | None = None


class BudgetItem(SourceMeta):
    expense_kind: ExpenseKind
    sheet_code: str
    article_code: str
    article_name: str
    article_name_norm: str
    match_key: str
    article_level: int
    year: int
    limit_amount: float
    amount_unit: str = "thousand_rub"
    currency: str = "RUB"
    ancestor_codes: list[str] = Field(default_factory=list)
    l1_code: str | None = None
    l1_name: str | None = None
    l2_code: str | None = None
    l2_name: str | None = None
    l3_code: str | None = None
    l3_name: str | None = None
    l4_code: str | None = None
    l4_name: str | None = None
    l5_code: str | None = None
    l5_name: str | None = None
    fact_amount: float | None = None
    obligation_amount: float | None = None
    remain_free: float | None = None
    remain_free_source: RemainFreeSource | None = None
    remain_unexecuted: float | None = None
    unit: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    def point_id(self) -> str:
        return make_point_id(
            "budget_items",
            self.source_file,
            self.sheet,
            self.expense_kind,
            self.sheet_code,
        )
