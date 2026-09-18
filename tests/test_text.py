"""Детерминированный text статьи."""

from __future__ import annotations

import unittest

from ingest.models import BudgetItem
from ingest.text import render_budget_text


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
        self.assertTrue(a.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
