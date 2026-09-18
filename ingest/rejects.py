"""Отчёт об отклонённых строках: data/rejects/*.jsonl."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_REJECTS_DIR = Path(__file__).resolve().parent.parent / "data" / "rejects"


def write_rejects(
    rejected: list[tuple[int, str]],
    *,
    source_file: str,
    sheet: str,
    dest_dir: Path | None = None,
) -> Path | None:
    if not rejected:
        return None
    dest = dest_dir or DEFAULT_REJECTS_DIR
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = Path(source_file).stem.replace(" ", "_")
    path = dest / f"{stem}.{stamp}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for row, reason in rejected:
            fh.write(
                json.dumps(
                    {
                        "source_file": source_file,
                        "sheet": sheet,
                        "row": row,
                        "reason": reason,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return path
