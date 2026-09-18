"""Точка входа: python3 -m assistant."""

import sys


def main() -> None:
    print(
        "assistant: чат ещё не реализован (Sprint 4).\n"
        "Ожидаемые команды: python3 -m assistant (CLI) и POST /chat.",
        file=sys.stderr,
    )
    raise SystemExit(2)


if __name__ == "__main__":
    main()
