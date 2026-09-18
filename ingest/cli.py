"""CLI: load и delete-source для бюджета."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from ingest.budget import parse_budget
from ingest.index import index_budget_items
from ingest.settings import load_settings
from ingest.store import collection_count, delete_source, existing_ids


@dataclass
class LoadReport:
    accepted: int
    updated: int
    rejected: int
    warnings: int
    count: int
    source_file: str
    rejects_path: Path | None


def cmd_load(xlsx: Path) -> LoadReport:
    if not xlsx.is_file():
        raise FileNotFoundError(xlsx)
    cfg = load_settings()
    parsed = parse_budget(xlsx)
    ids = [item.point_id() for item in parsed.items]
    existed = existing_ids(ids, cfg)
    updated = sum(1 for pid in ids if pid in existed)
    accepted = len(ids) - updated
    if parsed.items:
        index_budget_items(parsed.items, cfg)
    return LoadReport(
        accepted=accepted,
        updated=updated,
        rejected=len(parsed.rejected),
        warnings=len(parsed.warnings),
        count=collection_count(cfg),
        source_file=xlsx.name,
        rejects_path=parsed.rejects_path,
    )


def cmd_delete_source(target: str) -> int:
    name = Path(target).name
    delete_source(name)
    return collection_count()


def print_load_report(report: LoadReport) -> None:
    print(f"источник: {report.source_file}")
    print(f"принято: {report.accepted}")
    print(f"обновлено: {report.updated}")
    print(f"отклонено: {report.rejected}")
    print(f"warning: {report.warnings}")
    print(f"точек в коллекции: {report.count}")
    if report.rejects_path:
        print(f"rejects: {report.rejects_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python3 -m ingest", description="Загрузка сметы в Qdrant")
    sub = parser.add_subparsers(dest="cmd", required=False)
    load_p = sub.add_parser("load", help="разобрать Excel и upsert в budget_items")
    load_p.add_argument("file", type=Path)
    del_p = sub.add_parser("delete-source", help="снять точки файла по source_file")
    del_p.add_argument("file", help="путь или имя файла, как в payload source_file")
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0
    try:
        if args.cmd == "load":
            print_load_report(cmd_load(args.file))
            return 0
        left = cmd_delete_source(args.file)
        print(f"удалён source_file={Path(args.file).name}; точек в коллекции: {left}")
        return 0
    except Exception as exc:  # noqa: BLE001 — CLI печатает и выходит
        print(f"ошибка: {exc}", file=sys.stderr)
        return 1
