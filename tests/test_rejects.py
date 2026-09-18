"""Rejects пишутся в jsonl с файлом, листом, строкой и причиной."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ingest.rejects import write_rejects


class WriteRejectsTest(unittest.TestCase):
    def test_empty_returns_none(self) -> None:
        self.assertIsNone(write_rejects([], source_file="a.xlsx", sheet="S"))

    def test_jsonl_has_row_and_reason(self) -> None:
        with TemporaryDirectory() as tmp:
            path = write_rejects(
                [(23, "limit_amount: empty")],
                source_file="БДР.xlsx",
                sheet="Смета затрат",
                dest_dir=Path(tmp),
            )
            self.assertIsNotNone(path)
            assert path is not None
            row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["row"], 23)
            self.assertEqual(row["reason"], "limit_amount: empty")
            self.assertEqual(row["sheet"], "Смета затрат")


if __name__ == "__main__":
    unittest.main()
