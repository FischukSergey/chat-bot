"""CLI: справка и разбор аргументов без Qdrant."""

from __future__ import annotations

import unittest
from io import StringIO
from unittest.mock import patch

from ingest.cli import main


class CliHelpTest(unittest.TestCase):
    def test_help_exits_zero(self) -> None:
        buf = StringIO()
        with patch("sys.stdout", buf), self.assertRaises(SystemExit) as cm:
            main(["-h"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("load", buf.getvalue())

    def test_no_args_prints_help(self) -> None:
        buf = StringIO()
        with patch("sys.stdout", buf):
            code = main([])
        self.assertEqual(code, 0)
        self.assertIn("load", buf.getvalue())
        self.assertIn("delete-source", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
