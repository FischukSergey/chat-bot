"""Детерминированный text статьи."""

from __future__ import annotations

import unittest

from ingest.models import BudgetItem
from ingest.text import ancestor_names, path_names, render_budget_text


class TextRenderTest(unittest.TestCase):
    def test_stable_and_has_fields(self) -> None:
        item = BudgetItem(
            source_file="t.xlsx",
            sheet="Смета затрат",
            row=23,
            expense_kind="production",
            sheet_code="1.8.2",
            article_code="production:1.8.2",
            article_name="электроэнергия",
            article_name_norm="электроэнергия",
            match_key="электроэнергия",
            article_level=3,
            year=2026,
            limit_amount=124970.3,
            l1_name="Материальные расходы",
            l2_name="Коммунальные услуги",
            l3_name="электроэнергия",
        )
        a = render_budget_text(item)
        b = render_budget_text(item)
        self.assertEqual(a, b)
        self.assertIn("production:1.8.2", a)
        self.assertIn("электроэнергия", a)
        self.assertIn("2026", a)
        self.assertIn("Ветка: Материальные расходы / Коммунальные услуги", a)
        self.assertIn("Родители: Материальные расходы, Коммунальные услуги", a)
        self.assertTrue(a.endswith("\n"))
        self.assertEqual(
            path_names(item),
            ["Материальные расходы", "Коммунальные услуги", "электроэнергия"],
        )
        self.assertEqual(ancestor_names(item), ["Материальные расходы", "Коммунальные услуги"])

    def test_parent_name_in_leaf_text(self) -> None:
        item = BudgetItem(
            source_file="t.xlsx",
            sheet="Смета затрат",
            row=80,
            expense_kind="production",
            sheet_code="5.1.1.1",
            article_code="production:5.1.1.1",
            article_name='газопроводы АО "Газпром газораспределение"',
            article_name_norm="газопроводы ао",
            match_key="газопроводы ао",
            article_level=4,
            year=2026,
            limit_amount=681351.76,
            l2_name="аренда",
            l3_name="аренда газопроводов, в т.ч.",
        )
        text = render_budget_text(item)
        self.assertIn("аренда газопроводов, в т.ч.", text)
        self.assertIn("Родители:", text)
        self.assertEqual(
            ancestor_names(item),
            ["аренда", "аренда газопроводов, в т.ч."],
        )


if __name__ == "__main__":
    unittest.main()
