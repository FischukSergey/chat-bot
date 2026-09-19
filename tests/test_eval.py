"""Скорер золотого набора: числа ±0.01, отказ, без галлюцинаций."""

from __future__ import annotations

import unittest

from assistant.eval import extract_numbers, score_case
from assistant.orchestrator import ChatResult


def _case(**expect) -> dict:
    return {"id": "t", "expect": expect}


class ExtractNumbersTest(unittest.TestCase):
    def test_spaced_ru(self) -> None:
        nums = extract_numbers("лимит 124 970,30 тыс. руб.")
        self.assertTrue(any(abs(n - 124970.30) < 0.01 for n in nums))
        self.assertFalse(any(abs(n - 970.30) < 0.01 for n in nums))

    def test_raw_float(self) -> None:
        nums = extract_numbers("124970.2976739696")
        self.assertTrue(any(abs(n - 124970.29767396959) < 0.01 for n in nums))


class ScoreCaseTest(unittest.TestCase):
    def test_pass_limit(self) -> None:
        result = ChatResult(
            answer="Лимит 124970.30 тыс. руб. по production:1.8.2, факт не заполнен.",
            sources=[{"article_code": "production:1.8.2", "row": 23}],
        )
        fails = score_case(
            _case(
                article_codes=["production:1.8.2"],
                numbers=[124970.29767396959],
                null_fields=["fact"],
                allow_numbers=[23],
            ),
            result,
        )
        self.assertEqual(fails, [])

    def test_refuse_hallucination(self) -> None:
        result = ChatResult(answer="В индексе нет, лимит 500000.")
        fails = score_case(_case(refusal=True), result)
        self.assertTrue(any("отказе" in f for f in fails))

    def test_refuse_ok(self) -> None:
        result = ChatResult(answer="В индексе нет таких записей.")
        self.assertEqual(score_case(_case(refusal=True), result), [])

    def test_question_echo_not_hallucination(self) -> None:
        result = ChatResult(answer="В индексе нет записей по статье production:99.99.")
        fails = score_case({"id": "t", "question": "Что в смете по статье production:99.99?", "expect": {"refusal": True}}, result)
        self.assertEqual(fails, [])

    def test_zero(self) -> None:
        result = ChatResult(answer="По production:5.1.3 аренда автотранспорта лимит 0 тыс. руб.")
        fails = score_case(
            _case(article_codes=["production:5.1.3"], numbers=[0], contains=["автотранспорт"]),
            result,
        )
        self.assertEqual(fails, [])


if __name__ == "__main__":
    unittest.main()
