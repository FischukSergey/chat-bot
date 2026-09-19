"""Оркестратор: круги tools, sources, отказ без выдуманных сумм."""

from __future__ import annotations

import unittest
from typing import Any

from assistant.llm import LLMTurn, ToolCall
from assistant.orchestrator import Orchestrator, extract_sources
from assistant.prompt import system_prompt
from assistant.settings import Settings
from assistant.tools import TOOL_DEFINITIONS, TOOL_NAMES


def _settings(*, rounds: int = 2) -> Settings:
    return Settings(
        mcp_url="http://mcp.test",
        llm_url="http://llm.test/v1",
        llm_model="test-model",
        max_tool_rounds=rounds,
        mcp_timeout=5.0,
        llm_timeout=5.0,
        max_tokens=128,
        disable_thinking=True,
    )


class FakeLLM:
    def __init__(self, turns: list[LLMTurn]) -> None:
        self.turns = list(turns)
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
    ) -> LLMTurn:
        self.calls.append({"tools": tools, "tool_choice": tool_choice, "messages": messages})
        if not self.turns:
            raise AssertionError("лишний вызов LLM")
        return self.turns.pop(0)


class FakeMCP:
    def __init__(self, results: dict[str, Any] | None = None) -> None:
        self.results = results or {}
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        self.calls.append((name, arguments))
        return self.results.get(name, {"hits": []})


class OrchestratorTest(unittest.TestCase):
    def test_one_tool_round_then_answer(self) -> None:
        llm = FakeLLM(
            [
                LLMTurn(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id="c1",
                            name="search_records",
                            arguments={"filters": {"article_code": "production:1.8.2"}},
                        )
                    ],
                ),
                LLMTurn(content="Лимит 124970.30 тыс. руб. по production:1.8.2."),
            ]
        )
        mcp = FakeMCP(
            {
                "search_records": {
                    "hits": [
                        {
                            "fields": {"article_code": "production:1.8.2"},
                            "source": {
                                "source_file": "БДР для индексации.xlsx",
                                "sheet": "Смета затрат",
                                "row": 23,
                            },
                        }
                    ]
                }
            }
        )
        result = Orchestrator(_settings(), mcp, llm).ask("лимит по production:1.8.2")
        self.assertEqual(result.rounds, 1)
        self.assertEqual(result.hits, 1)
        self.assertEqual(result.tools_used, ["search_records"])
        self.assertIn("124970.30", result.answer)
        self.assertEqual(result.sources[0]["row"], 23)
        self.assertEqual(result.sources[0]["article_code"], "production:1.8.2")
        self.assertEqual(len(llm.calls), 2)
        self.assertIsNotNone(llm.calls[0]["tools"])
        self.assertIsNotNone(llm.calls[1]["tools"])
        self.assertEqual(llm.calls[1]["tool_choice"], "auto")

    def test_max_rounds_blocks_second_tool_batch(self) -> None:
        llm = FakeLLM(
            [
                LLMTurn(
                    content="",
                    tool_calls=[
                        ToolCall(id="1", name="search_records", arguments={"query": "охрана"})
                    ],
                ),
                LLMTurn(
                    content="в индексе нет таких записей",
                    tool_calls=[
                        ToolCall(id="2", name="budget_summary", arguments={"year": 2026})
                    ],
                ),
            ]
        )
        mcp = FakeMCP({"search_records": {"hits": []}})
        result = Orchestrator(_settings(rounds=1), mcp, llm).ask("остаток по охране")
        self.assertEqual(mcp.calls, [("search_records", {"query": "охрана"})])
        self.assertEqual(result.tools_used, ["search_records"])
        self.assertEqual(result.rounds, 1)
        self.assertEqual(result.answer, "в индексе нет таких записей")
        self.assertEqual(len(llm.calls), 2)
        self.assertIsNone(llm.calls[1]["tools"])
        self.assertEqual(llm.calls[1]["tool_choice"], "none")

    def test_unknown_tool_not_sent_to_mcp(self) -> None:
        llm = FakeLLM(
            [
                LLMTurn(
                    content="",
                    tool_calls=[ToolCall(id="1", name="get_contract", arguments={"n": "1"})],
                ),
                LLMTurn(content="В индексе сейчас только смета."),
            ]
        )
        mcp = FakeMCP()
        result = Orchestrator(_settings(), mcp, llm).ask("договор 1")
        self.assertEqual(mcp.calls, [])
        self.assertEqual(result.tools_used, ["get_contract"])
        self.assertIn("смета", result.answer)

    def test_empty_question(self) -> None:
        result = Orchestrator(_settings(), FakeMCP(), FakeLLM([])).ask("  ")
        self.assertEqual(result.answer, "В индексе нет таких записей.")

    def test_fallback_from_budget_summary_when_llm_silent(self) -> None:
        llm = FakeLLM(
            [
                LLMTurn(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id="1",
                            name="budget_summary",
                            arguments={"article_name": "аренда газопроводов"},
                        )
                    ],
                ),
                LLMTurn(content=""),
            ]
        )
        mcp = FakeMCP(
            {
                "budget_summary": {
                    "total": {"limit": 1033066.45202, "amount_unit": "thousand_rub"},
                    "rows": [
                        {"code": "production:5.1.1.1"},
                        {"code": "production:5.1.1.3"},
                    ],
                }
            }
        )
        result = Orchestrator(_settings(), mcp, llm).ask("аренда газопроводов")
        self.assertIn("1033066.45202", result.answer)
        self.assertIn("production:5.1.1.1", result.answer)
        self.assertNotEqual(result.answer, "Не удалось сформулировать ответ по результатам инструментов.")


class SourcesAndPromptTest(unittest.TestCase):
    def test_extract_sources_from_hits_and_rows(self) -> None:
        sources = extract_sources(
            [
                {
                    "hits": [
                        {
                            "fields": {"article_code": "production:1.8.2"},
                            "source": {
                                "source_file": "a.xlsx",
                                "sheet": "Смета",
                                "row": 23,
                            },
                        }
                    ]
                },
                {"rows": [{"code": "production:1.8.1", "name": "тепло"}]},
            ]
        )
        self.assertEqual(sources[0]["row"], 23)
        self.assertEqual(sources[1]["article_code"], "production:1.8.1")

    def test_tool_definitions_only_budget(self) -> None:
        self.assertEqual(TOOL_NAMES, ("search_records", "budget_summary", "ingest_status"))
        self.assertNotIn("get_contract", str(TOOL_DEFINITIONS))

    def test_system_prompt_rules(self) -> None:
        text = system_prompt()
        self.assertIn("только из JSON tools", text)
        self.assertIn("в индексе нет таких записей", text)
        self.assertIn("remain_free", text)
        self.assertIn("Не сливай факт и принятые", text)
        self.assertIn("источники", text)
        self.assertIn("Не вызывай `get_contract`", text)
        self.assertIn("Родитель не индексируется отдельно", text)


if __name__ == "__main__":
    unittest.main()
