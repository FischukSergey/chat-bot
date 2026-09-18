"""Точка входа: python3 -m ingest."""

import sys


def main() -> None:
    print(
        "ingest: загрузка Excel ещё не реализована (Sprint 2).\n"
        "Ожидаемые команды: python3 -m ingest load <file>, "
        "python3 -m ingest delete-source <file>.",
        file=sys.stderr,
    )
    raise SystemExit(2)


if __name__ == "__main__":
    main()
