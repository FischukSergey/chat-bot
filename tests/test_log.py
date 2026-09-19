"""JSON-лог чата: вопрос, tools, hits, latency."""

from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from assistant.log import log_chat


class LogChatTest(unittest.TestCase):
    def test_fields(self) -> None:
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            log_chat(
                question="лимит?",
                tools=["search_records"],
                hits=1,
                latency_ms=42,
                rounds=1,
            )
        row = json.loads(buf.getvalue())
        self.assertEqual(row["msg"], "chat")
        self.assertEqual(row["question"], "лимит?")
        self.assertEqual(row["tools"], ["search_records"])
        self.assertEqual(row["hits"], 1)
        self.assertEqual(row["latency_ms"], 42)
        self.assertEqual(row["rounds"], 1)
        self.assertEqual(row["error"], "")


if __name__ == "__main__":
    unittest.main()
