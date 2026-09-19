"""Точка входа: python3 -m assistant | --ask | serve."""

from __future__ import annotations

import argparse
import sys

from assistant.cli import print_result, run_chat
from assistant.orchestrator import ask
from assistant.settings import load_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RAG-ассистент по смете")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["serve", "eval"],
        help="serve — HTTP; eval — прогон data/eval/gold.yaml",
    )
    parser.add_argument("--ask", metavar="QUESTION", help="один вопрос без цикла")
    parser.add_argument("--addr", help="адрес HTTP, по умолчанию ASSISTANT_HTTP_ADDR")
    args = parser.parse_args(argv)
    if args.command in {"serve", "eval"} and args.ask:
        print("нельзя совмещать serve/eval и --ask", file=sys.stderr)
        return 2
    if args.command == "eval":
        from assistant.eval import main as eval_main

        return eval_main([])
    if args.command == "serve":
        from assistant.app import App
        from assistant.httpapi import serve

        cfg = load_settings()
        with App.open(cfg) as app:
            serve(app, args.addr or cfg.http_addr)
        return 0
    if args.ask:
        print_result(ask(args.ask))
        return 0
    return run_chat()


if __name__ == "__main__":
    raise SystemExit(main())
