# Бюджетный ассистент

ИИ-ассистент для быстрого поиска по **бюджету**, **договорам** и **обязательствам**.
Исходные данные — Excel. Поиск — RAG: парсинг → индексация → Qdrant → MCP → LLM.

Стек: **Python** (ingest, эмбеддинги, RAG), **Go** (MCP-сервер и API), **Qdrant**.

## Документы

| Документ | Содержание |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Архитектура, компоненты, потоки данных, хранение |
| [docs/FUNCTIONALITY.md](docs/FUNCTIONALITY.md) | Функционал ассистента, MCP-инструменты, сценарии |
| [docs/PLAN.md](docs/PLAN.md) | Этапы, спринты, критерии готовности, риски |
| [docs/sprint-1-plan.md](docs/sprint-1-plan.md) | Спринт 1: каркас + маппинг Excel |
| [docs/sprint-2-plan.md](docs/sprint-2-plan.md) | Спринт 2: ingest → Qdrant |
| [docs/sprint-3-plan.md](docs/sprint-3-plan.md) | Спринт 3: MCP-сервер |
| [docs/sprint-4-plan.md](docs/sprint-4-plan.md) | Спринт 4: RAG-ассистент |
| [docs/sprint-5-plan.md](docs/sprint-5-plan.md) | Спринт 5: упаковка v1 |
| [docs/sprint-6-plan.md](docs/sprint-6-plan.md) | Спринт 6: усиление после v1 |

Чек-листы: `docs/sprint-N-checklist.md`.

## Коротко

Пользователь спрашивает на естественном языке («какие обязательства по договору с X?»).
Ассистент через MCP ищет в Qdrant (семантика + фильтры по метаданным) и отвечает с опорой на найденные записи.
