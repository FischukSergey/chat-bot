"""Прогон золотого набора: эталон из Excel, pass/fail, без выдуманных сумм."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from assistant.app import App
from assistant.orchestrator import ChatResult
from assistant.settings import ROOT

GOLD_PATH = ROOT / "data" / "eval" / "gold.yaml"
OUT_PATH = ROOT / "data" / "eval" / "last-run.yaml"

_NULL_PHRASES = (
    "не заполн",
    "не указан",
    "нет данных",
    "отсутств",
    "пуст",
    "null",
    "в смете не",
    "в индексе не",
)
_REFUSE_PHRASES = (
    "в индексе нет",
    "нет таких",
    "нет запис",
    "не найден",
    "только смета",
    "только информац",
    "годовой смете",
    "нет данных о договор",
    "нет договор",
    "нет обязательств",
    "коллекц",
    "только бюджет",
)

_NUM_SPACED = re.compile(r"(?<![\d])(\d{1,3}(?:[ \u00a0]\d{3})+(?:[.,]\d+)?)(?![\d])")
_NUM_PLAIN = re.compile(r"(?<![\d])(\d+[.,]\d+|\d{3,})(?![\d])")


def load_gold(path: Path = GOLD_PATH) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("cases"):
        raise ValueError(f"пустой золотой набор: {path}")
    return data


def extract_numbers(text: str) -> list[float]:
    remain = text.replace("\n", " ").replace("\t", " ")
    found: list[float] = []
    for rx in (_NUM_SPACED, _NUM_PLAIN):
        for match in rx.finditer(remain):
            raw = match.group(1).replace("\u00a0", "").replace(" ", "").replace(",", ".")
            try:
                found.append(float(raw))
            except ValueError:
                continue
        remain = rx.sub(" ", remain)
    return found


def _norm(text: str) -> str:
    return text.replace("\u00a0", " ").casefold()


def _close(actual: float, expected: float, tol: float) -> bool:
    return abs(actual - expected) <= tol


def _has_number(values: list[float], expected: float, tol: float, text: str = "") -> bool:
    if abs(expected) <= tol:
        compact = text.replace("\u00a0", "").replace(" ", "")
        if re.search(r"(?<![\d])0(?:[.,]0+)?(?![\d])", compact):
            return True
        return any(abs(v) <= tol for v in values)
    return any(_close(v, expected, tol) for v in values)


def _blob(result: ChatResult) -> str:
    return result.answer + "\n" + json.dumps(result.sources, ensure_ascii=False)


def score_case(
    case: dict[str, Any],
    result: ChatResult,
    *,
    tolerance: float = 0.01,
) -> list[str]:
    expect = case.get("expect") or {}
    tol = float(expect.get("tolerance") or tolerance)
    blob = _blob(result)
    low = _norm(blob)
    nums = extract_numbers(blob)
    failures: list[str] = []

    for code in expect.get("article_codes") or []:
        if str(code).casefold() not in low:
            failures.append(f"нет кода {code}")

    for needle in expect.get("contains") or []:
        if _norm(str(needle)) not in low:
            failures.append(f"нет фрагмента {needle!r}")

    any_needles = expect.get("contains_any") or []
    if any_needles and not any(_norm(str(n)) in low for n in any_needles):
        failures.append(f"нет ни одного из {any_needles}")

    for field in expect.get("null_fields") or []:
        if not any(p in low for p in _NULL_PHRASES):
            failures.append(f"{field}: нет признака пустого поля")
            break

    if expect.get("refusal") and not any(p in low for p in _REFUSE_PHRASES):
        failures.append("нет отказа")

    for raw in expect.get("numbers") or []:
        if not _has_number(nums, float(raw), tol, blob):
            failures.append(f"нет числа {raw}")

    allowed = [float(x) for x in (expect.get("numbers") or [])]
    allowed.extend(float(x) for x in (expect.get("allow_numbers") or []))
    allowed.extend(extract_numbers(str(case.get("question") or "")))
    if expect.get("refusal") or expect.get("must_not_hallucinate", True):
        for value in nums:
            if 2000 <= value <= 2100 and value.is_integer():
                continue
            if _explained(value, allowed, tol):
                continue
            if expect.get("refusal") and _money_like(value):
                failures.append(f"лишняя сумма при отказе {value}")
            elif not expect.get("refusal") and _money_like(value) and allowed:
                failures.append(f"лишняя сумма {value}")
    return failures


def _explained(value: float, allowed: list[float], tol: float) -> bool:
    for item in allowed:
        if _close(value, item, tol):
            return True
        if _close(value, item * 1000, max(1.0, tol * 1000)):
            return True
        if item >= 100 and _close(value, item / 1000, max(tol, 0.01)):
            return True
        if _is_fragment(value, item):
            return True
    return False


def _is_fragment(value: float, allowed: float) -> bool:
    left = f"{value:.8f}".rstrip("0").rstrip(".").replace(".", "")
    right = f"{allowed:.8f}".rstrip("0").rstrip(".").replace(".", "")
    return len(left) >= 3 and left in right


def _money_like(value: float) -> bool:
    if value >= 1000:
        return True
    return value >= 10 and abs(value - round(value)) > 1e-9


def run_eval(
    *,
    gold_path: Path = GOLD_PATH,
    out_path: Path = OUT_PATH,
    app: App | None = None,
) -> dict[str, Any]:
    gold = load_gold(gold_path)
    tol = float(gold.get("tolerance") or 0.01)
    own = app is None
    session = app or App.open()
    rows: list[dict[str, Any]] = []
    try:
        for case in gold["cases"]:
            print(f"... {case['id']}", flush=True)
            result = session.ask(str(case["question"]))
            failures = score_case(case, result, tolerance=tol)
            rows.append(
                {
                    "id": case["id"],
                    "type": case.get("type"),
                    "ok": not failures,
                    "failures": failures,
                    "tools": result.tools_used,
                    "hits": result.hits,
                    "latency_ms": result.latency_ms,
                    "answer": result.answer,
                }
            )
    finally:
        if own:
            session.close()
    passed = sum(1 for r in rows if r["ok"])
    report = {
        "ran_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "gold": str(gold_path),
        "pass": passed,
        "fail": len(rows) - passed,
        "total": len(rows),
        "cases": rows,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        yaml.safe_dump(report, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return report


def print_table(report: dict[str, Any]) -> None:
    print(f"pass={report['pass']} fail={report['fail']} total={report['total']}")
    print(f"{'id':<24} {'ok':<5} tools  failures")
    for row in report["cases"]:
        mark = "PASS" if row["ok"] else "FAIL"
        tools = ",".join(row.get("tools") or []) or "-"
        fails = "; ".join(row.get("failures") or [])
        print(f"{row['id']:<24} {mark:<5} {tools}  {fails}")


def rescore_report(report: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    by_id = {str(c["id"]): c for c in gold["cases"]}
    tol = float(gold.get("tolerance") or 0.01)
    rows = []
    for row in report["cases"]:
        case = by_id[str(row["id"])]
        result = ChatResult(answer=str(row.get("answer") or ""))
        failures = score_case(case, result, tolerance=tol)
        updated = dict(row)
        updated["failures"] = failures
        updated["ok"] = not failures
        rows.append(updated)
    passed = sum(1 for r in rows if r["ok"])
    report = dict(report)
    report["cases"] = rows
    report["pass"] = passed
    report["fail"] = len(rows) - passed
    report["total"] = len(rows)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Прогон data/eval/gold.yaml")
    parser.add_argument("--gold", type=Path, default=GOLD_PATH)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--rescore", type=Path, help="пересчитать last-run без LLM")
    args = parser.parse_args(argv)
    if args.rescore:
        report = rescore_report(yaml.safe_load(args.rescore.read_text(encoding="utf-8")), load_gold(args.gold))
        args.out.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False), encoding="utf-8")
    else:
        report = run_eval(gold_path=args.gold, out_path=args.out)
    print_table(report)
    print(f"отчёт: {args.out}")
    return 0 if report["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
