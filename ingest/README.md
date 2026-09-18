# ingest

Загрузка сметы Excel в Qdrant. Пока только бюджет.

```bash
task ingest -- load "data/incoming/БДР для индексации.xlsx"
task ingest -- delete-source "БДР для индексации.xlsx"
```

Или `python3 -m ingest …` (если есть `.venv`, Taskfile берёт его).

Нужны: `task local:up`, LM Studio на `:1234`, заполненный `.env` (`EMBEDDINGS_MODEL`, `VECTOR_SIZE`).

Отчёт load: принято / обновлено / отклонено / warning / число точек.
Повторный load того же файла обновляет те же id, count не растёт.
