"""Валидация листьев и сверка остатка. Остаток из сметы без принятых не считаем."""

from __future__ import annotations

from dataclasses import dataclass

from ingest.models import BudgetItem

REMAIN_FREE_EPSILON = 0.01

REQUIRED_FIELDS = (
    "expense_kind",
    "article_code",
    "article_name",
    "article_name_norm",
    "match_key",
    "article_level",
    "year",
    "limit_amount",
    "amount_unit",
    "currency",
)


@dataclass(frozen=True)
class RemainWarning:
    row: int | None
    sheet: str
    article_code: str
    excel: float
    computed: float
    delta: float


def missing_required(item: BudgetItem) -> str | None:
    for name in REQUIRED_FIELDS:
        val = getattr(item, name)
        if val is None or val == "":
            return f"нет поля {name}"
    if not (2000 <= item.year <= 2100):
        return f"год вне диапазона: {item.year}"
    if not (1 <= item.article_level <= 5):
        return f"article_level вне 1…5: {item.article_level}"
    return None


def apply_remain_rules(
    item: BudgetItem,
    epsilon: float = REMAIN_FREE_EPSILON,
) -> RemainWarning | None:
    """Правило канона: без принятых remain_free не вычислять.

    Есть excel-остаток — пишем его, source=excel, сверка если есть obligation.
    Нет остатка, есть принятые — computed. Нет обоих — поля пустые.
    """
    has_obl = item.obligation_amount is not None
    has_excel = item.remain_free is not None

    if item.remain_unexecuted is None and has_obl and item.fact_amount is not None:
        item.remain_unexecuted = item.obligation_amount - item.fact_amount  # type: ignore[operator]

    if not has_obl and not has_excel:
        item.remain_free = None
        item.remain_free_source = None
        return None

    if has_excel:
        item.remain_free_source = "excel"
        if not has_obl:
            return None
        computed = item.limit_amount - item.obligation_amount  # type: ignore[operator]
        delta = abs(item.remain_free - computed)  # type: ignore[operator]
        if delta > epsilon:
            return RemainWarning(
                row=item.row,
                sheet=item.sheet,
                article_code=item.article_code,
                excel=float(item.remain_free),  # type: ignore[arg-type]
                computed=computed,
                delta=delta,
            )
        return None

    item.remain_free = item.limit_amount - item.obligation_amount  # type: ignore[operator]
    item.remain_free_source = "computed"
    return None
