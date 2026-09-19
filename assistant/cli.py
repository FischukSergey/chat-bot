"""Интерактивный CLI-чат: вопрос → ответ и sources."""

from __future__ import annotations

import json
import sys

from assistant.app import App
from assistant.orchestrator import ChatResult
from assistant.settings import Settings, load_settings


def print_result(result: ChatResult, file=None) -> None:
    out = file or sys.stdout
    print(result.answer, file=out)
    print("---", file=out)
    print(
        json.dumps(
            {
                "sources": result.sources,
                "tools_used": result.tools_used,
                "rounds": result.rounds,
            },
            ensure_ascii=False,
            indent=2,
        ),
        file=out,
    )


def run_chat(
    *,
    settings: Settings | None = None,
    app: App | None = None,
    stdin=None,
    stdout=None,
) -> int:
    inp = stdin or sys.stdin
    out = stdout or sys.stdout
    print("ассистент сметы. /quit — выход.", file=out)
    own = app is None
    session = app or App.open(settings or load_settings())
    try:
        while True:
            try:
                print("> ", end="", file=out, flush=True)
                line = inp.readline()
            except KeyboardInterrupt:
                print(file=out)
                return 0
            if line == "":
                print(file=out)
                return 0
            text = line.strip()
            if not text:
                continue
            if text.lower() in {"/quit", "/exit", "quit"}:
                return 0
            result = session.ask(text)
            print_result(result, file=out)
            print(file=out)
    finally:
        if own:
            session.close()
    return 0
