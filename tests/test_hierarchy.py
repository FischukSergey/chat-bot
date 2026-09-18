"""Листья vs родители и схлопывание нулевых заглушек."""

from __future__ import annotations

import unittest
from pathlib import Path

from ingest.budget import ParseResult, RowRec, _pick_leaves, parse_budget

HIER = {"hierarchy": {"collapse_zero_stub_children": True}}
XLSX = Path(__file__).resolve().parent.parent / "data" / "incoming" / "БДР для индексации.xlsx"


def _rec(code: str, amount: float, row: int) -> RowRec:
    return RowRec(
        row=row,
        expense_kind="production",
        segs=code.split("."),
        sheet_code=code,
        name=code,
        limit_amount=amount,
        extra={},
    )


class PickLeavesTest(unittest.TestCase):
    def test_parent_with_money_children_not_indexed(self) -> None:
        recs = [
            _rec("1", 100, 1),
            _rec("1.1", 40, 2),
            _rec("1.2", 60, 3),
        ]
        result = ParseResult()
        leaves = _pick_leaves(recs, HIER, result)
        self.assertEqual({x.sheet_code for x in leaves}, {"1.1", "1.2"})
        self.assertIn((1, "parent_not_leaf"), result.skipped)

    def test_collapse_zero_stub_children(self) -> None:
        recs = [
            _rec("2", 300, 10),
            _rec("2.1", 0, 11),
            _rec("2.2", 0, 12),
        ]
        result = ParseResult()
        leaves = _pick_leaves(recs, HIER, result)
        self.assertEqual([x.sheet_code for x in leaves], ["2"])
        self.assertEqual({r for r, _ in result.skipped}, {11, 12})

    def test_true_zero_leaf_kept(self) -> None:
        recs = [_rec("5.2.1", 0, 20)]
        leaves = _pick_leaves(recs, HIER, ParseResult())
        self.assertEqual([x.sheet_code for x in leaves], ["5.2.1"])


@unittest.skipUnless(XLSX.is_file(), "нет боевой сметы в incoming")
class LiveHierarchyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.res = parse_budget(XLSX, write_reject_file=False)
        cls.codes = {i.article_code for i in cls.res.items}

    def test_parents_absent_leaves_present(self) -> None:
        self.assertNotIn("production:1", self.codes)
        self.assertNotIn("production:1.8", self.codes)
        self.assertIn("production:1.8.2", self.codes)
        self.assertIn("management:1.1.2", self.codes)

    def test_collapsed_fot_and_child_on_management(self) -> None:
        self.assertIn("production:2", self.codes)
        self.assertNotIn("production:2.1", self.codes)
        self.assertNotIn("management:2", self.codes)
        self.assertIn("management:2.1", self.codes)


if __name__ == "__main__":
    unittest.main()
