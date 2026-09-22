# Бюджетный ассистент

v1 отвечает **только по смете** (`budget_items`). Договоры и обязательства
в индексе нет — на такой вопрос будет отказ.

Данные — Excel. Контур: ingest → Qdrant → MCP → ассистент (RAG).
Стек: **Python** (ingest, оркестратор), **Go** (MCP), **Qdrant**.
LLM и эмбеддинги — **LM Studio на хосте**, не в Docker.

Запуск — через [Taskfile](https://taskfile.dev). Не вызывать сырой
`docker compose`, если есть `task local:*`.

```bash
cp .env.example .env   # заполнить модели и VECTOR_SIZE
task --list
task local:up          # qdrant + mcp + assistant, дождаться healthy
task local:ps
task local:logs
task local:down        # остановить, volume (индекс) оставить
task local:down:clean  # остановить и стереть индекс
task                   # fmt + lint + test + build
```

## Требования

- Docker и [Task](https://taskfile.dev)
- LM Studio: сервер `http://127.0.0.1:1234/v1`, **две** модели
  (чат + отдельная embedding)
- Excel сметы в `data/incoming/` (боевые `.xlsx` и `.env` в git не входят)

## LM Studio с хоста

Контейнеры не поднимают модель. Из контейнера хост — это
`host.docker.internal` (поля `EMBEDDINGS_URL_DOCKER` / `LLM_URL_DOCKER`
в `.env`). С хоста CLI ходит в `127.0.0.1:1234`.

1. Запустить LM Studio, включить локальный сервер на `:1234`.
2. В `GET http://127.0.0.1:1234/v1/models` взять `id` чата и эмбеддинга.
3. В `.env`: `LLM_MODEL`, `EMBEDDINGS_MODEL`.
4. `VECTOR_SIZE` = `len(data[0].embedding)` у `POST /v1/embeddings`,
   не скрытая размерность чат-модели. Коллекцию с `vector_size=0` не создавать.
5. Смена embedding-модели = другое пространство → дроп коллекции
   (`task local:down:clean`) и полная переиндексация.

Без живого LM Studio `/health` у mcp и assistant будет 503.

## Поднять контур

```bash
cp .env.example .env          # один раз, заполнить модели
task local:up                 # --wait: qdrant → mcp → assistant
curl -sf http://127.0.0.1:7345/health
curl -sf http://127.0.0.1:7346/health
# Qdrant UI: http://127.0.0.1:6333/dashboard
```

Порты: Qdrant `6333`, MCP `7345`, ассистент `7346`.
Не держать одновременно хостовые `task mcp` / `task assistant` —
те же порты.

Логи (json-file, ротация 10m×3):

```bash
task local:logs
task local:logs:service -- mcp-server
```

## Ingest и переиндексация

Коллекцию `budget_items` создаёт первый `load`. Контрольный файл v1 —
`data/incoming/БДР для индексации.xlsx`.

В контуре (контейнер, тот же образ что assistant):

```bash
task local:ingest
# или другой файл из data/incoming/
task local:ingest -- load "data/incoming/БДР для индексации.xlsx"
```

С хоста (`.venv`, Qdrant уже в compose):

```bash
task ingest -- load "data/incoming/БДР для индексации.xlsx"
```

Повторный `load` того же файла обновляет точки, число не плодит.
Снять источник и загрузить заново:

```bash
task ingest -- delete-source "БДР для индексации.xlsx"
task ingest -- load "data/incoming/БДР для индексации.xlsx"
# в контуре:
task local:ingest -- delete-source "БДР для индексации.xlsx"
```

Маппинг колонок — `data/mappings/` ([YAML](data/mappings/README.md)).
Отчёт rejects — `data/rejects/`.

## Задать вопрос

Контур должен быть healthy, индекс — не пустой.

Через HTTP ассистента в Docker:

```bash
curl -sf http://127.0.0.1:7346/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"Какой лимит по статье production:1.8.2?"}'
```

CLI с хоста (тот же оркестратор, MCP на `:7345`):

```bash
task assistant -- --ask "Какой лимит по статье production:1.8.2?"
task assistant                 # цикл, /quit — выход
```

Контракт: [docs/api-sprint-4.md](docs/api-sprint-4.md)
(`question` → `answer`, `sources`, `tools_used`).
Прямой вызов tools: [docs/api-sprint-3.md](docs/api-sprint-3.md).

Хостовый `task assistant -- serve` не нужен, если уже `task local:up`.

Опционально MCP в Cursor / LM Studio (не замена `POST /chat`):

```bash
task mcp -- --stdio
```

## Документы

| Документ | Содержание |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Архитектура, компоненты, потоки данных |
| [docs/FUNCTIONALITY.md](docs/FUNCTIONALITY.md) | Функционал, MCP-инструменты, сценарии |
| [docs/PLAN.md](docs/PLAN.md) | Этапы, спринты, критерии готовности |
| [docs/api-sprint-3.md](docs/api-sprint-3.md) | Контракт MCP tools |
| [docs/api-sprint-4.md](docs/api-sprint-4.md) | Контракт `POST /chat` |
| [docs/sprint-5-plan.md](docs/sprint-5-plan.md) | Спринт 5: упаковка v1 |
| [docs/sprint-5-rehearsal.md](docs/sprint-5-rehearsal.md) | Репетиция с нуля |
| [docs/known-limitations-sprint-5.md](docs/known-limitations-sprint-5.md) | Лимиты v1 |

Чек-листы: `docs/sprint-N-checklist.md`.
