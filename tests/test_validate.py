"""Сверка remain_free: без принятых не считаем, excel не затираем."""

from __future__ import annotations

import unittest

from ingest.models import BudgetItem
from ingest.validate import apply_remain_rules, missing_required


def _item(**kwargs) -> BudgetItem:
    base = dict(
        source_file="t.xlsx",
        sheet="Смета",
        row=10,
        expense_kind="production",
        sheet_code="1.8.2",
        article_code="production:1.8.2",
        article_name="электроэнергия",
        article_name_norm="электроэнергия",
        match_key="электроэнергия",
        article_level=3,
        year=2026,
        limit_amount=100.0,
    )
    base.update(kwargs)
    return BudgetItem(**base)


class RemainRulesTest(unittest.TestCase):
    def test_smeta_without_control_leaves_remain_empty(self) -> None:
        item = _item()
        warn = apply_remain_rules(item)
        self.assertIsNone(warn)
        self.assertIsNone(item.remain_free)
        self.assertIsNone(item.remain_free_source)

    def test_excel_remain_kept_on_mismatch(self) -> None:
        item = _item(obligation_amount=40.0, remain_free=70.0)
        warn = apply_remain_rules(item)
        self.assertIsNotNone(warn)
        self.assertEqual(item.remain_free, 70.0)
        self.assertEqual(item.remain_free_source, "excel")
        assert warn is not None
        self.assertAlmostEqual(warn.computed, 60.0)
        self.assertGreater(warn.delta, 0.01)

    def test_computed_when_no_excel_column(self) -> None:
        item = _item(obligation_amount=25.0)
        warn = apply_remain_rules(item)
        self.assertIsNone(warn)
        self.assertEqual(item.remain_free, 75.0)
        self.assertEqual(item.remain_free_source, "computed")

    def test_unexecuted_from_amounts(self) -> None:
        item = _item(obligation_amount=40.0, fact_amount=10.0)
        apply_remain_rules(item)
        self.assertEqual(item.remain_unexecuted, 30.0)

    def test_required_year(self) -> None:
        item = _item(year=1900)
        self.assertIn("год", missing_required(item) or "")


if __name__ == "__main__":
    unittest.main()
