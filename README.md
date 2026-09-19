# Бюджетный ассистент

ИИ-ассистент для быстрого поиска по **бюджету**, **договорам** и **обязательствам**.
Исходные данные — Excel. Поиск — RAG: парсинг → индексация → Qdrant → MCP → LLM.

Стек: **Python** (ingest, эмбеддинги, RAG), **Go** (MCP-сервер и API), **Qdrant**.

Запуск и отладка — через [Taskfile](https://taskfile.dev). Не вызывать сырой `docker compose`, если есть `task local:*`.

```bash
cp .env.example .env   # имена моделей и VECTOR_SIZE — после настройки LM Studio
task --list            # все команды
task local:up          # Qdrant, дождаться healthy
task local:ps
task local:logs
task local:down        # остановить, volume оставить
task lint              # golangci-lint в Docker — тот же вызов, что CI
task                   # fmt + lint + test + build
```

## Локальный контур

**Qdrant** — единственный сервис compose на этом этапе. UI: http://127.0.0.1:6333/dashboard.

```bash
task local:up
curl -sf http://127.0.0.1:6333/readyz   # должно ответить ok / 200
# UI: http://127.0.0.1:6333/dashboard
```

Коллекцию `budget_items` создаёт ingest при первом `load`:

```bash
task ingest -- load "data/incoming/БДР для индексации.xlsx"
```

**LM Studio** (на хосте, не в Docker): сервер `http://127.0.0.1:1234/v1`.
Нужны две модели: чат (`LLM_MODEL`) и отдельная embedding (`EMBEDDINGS_MODEL`).
`VECTOR_SIZE` — длина массива `POST /v1/embeddings`, не скрытая размерность чата.
Смена embedding-модели = пересоздать коллекции и переиндексировать.

MCP: `task mcp` — HTTP `:7345` (`/health`, `POST /tools/{name}`).
stdio: `task mcp -- --stdio`.
Ассистент: `task assistant` (CLI), `task assistant -- serve` — HTTP `:7346`
(`/health`, `POST /chat`).

Excel класть в `data/incoming/`. Маппинг колонок — `data/mappings/`
([как читать YAML](data/mappings/README.md)). Боевые `.xlsx` и `.env` в git не входят.

## Документы

| Документ | Содержание |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Архитектура, компоненты, потоки данных, хранение |
| [docs/FUNCTIONALITY.md](docs/FUNCTIONALITY.md) | Функционал ассистента, MCP-инструменты, сценарии |
| [docs/PLAN.md](docs/PLAN.md) | Этапы, спринты, критерии готовности, риски |
| [docs/sprint-1-plan.md](docs/sprint-1-plan.md) | Спринт 1: каркас + маппинг Excel |
| [docs/sprint-2-plan.md](docs/sprint-2-plan.md) | Спринт 2: ingest → Qdrant |
| [docs/sprint-3-plan.md](docs/sprint-3-plan.md) | Спринт 3: MCP-сервер |
| [docs/api-sprint-3.md](docs/api-sprint-3.md) | Контракт MCP tools |
| [docs/sprint-4-plan.md](docs/sprint-4-plan.md) | Спринт 4: RAG-ассистент |
| [docs/api-sprint-4.md](docs/api-sprint-4.md) | Контракт `POST /chat` |
| [docs/sprint-5-plan.md](docs/sprint-5-plan.md) | Спринт 5: упаковка v1 |
| [docs/sprint-6-plan.md](docs/sprint-6-plan.md) | Спринт 6: усиление после v1 |

Чек-листы: `docs/sprint-N-checklist.md`.

## Коротко

Пользователь спрашивает на естественном языке («какие обязательства по договору с X?»).
Ассистент через MCP ищет в Qdrant (семантика + фильтры по метаданным) и отвечает с опорой на найденные записи.
