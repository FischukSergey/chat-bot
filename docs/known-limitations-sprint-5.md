# Known limitations v1 / Sprint 5

Scope: только `budget_items`. Telegram, HTTP-загрузка Excel, CSV, сверка
реестра со статьёй — Sprint 6, не блокер релиза этого контура.

## Данные

- Договоров и обязательств в индексе нет. Вопрос про договор — отказ
  «в индексе только смета».
- В живой смете факт, принятые и `remain_free` = `null`. Ассистент их
  не считает и не подменяет лимитом.
- Единица сумм — `thousand_rub`. Модель иногда дублирует сумму в рублях (×1000).
- Родительская статья не индексируется отдельной точкой. Имя родителя
  ищется по пути листьев; узкий код листа — `search_records`.

## Контур

- LLM и embeddings — LM Studio **на хосте**. Из контейнера URL —
  `host.docker.internal` (`EMBEDDINGS_URL_DOCKER` / `LLM_URL_DOCKER`).
  Без живого `:1234` `/health` mcp/assistant = 503.
- `task local:down:clean` удаляет volume Qdrant вместе с индексом.
- Хостовые `task mcp` / `task assistant -- serve` конфликтуют с compose
  на `:7345` / `:7346`.
- Чат LM Studio + MCP stdio — не замена `POST /chat` (нет лимита кругов
  и нашего промпта).

## Качество ответов

- Золотой набор Sprint 4: 22 pass / 3 fail (`data/eval/last-run.md`).
  Провалы: пустой текст LLM после tools (`branch-1.8`, `cross-rent-pipes`);
  отказ + чужие суммы (`refuse-quantum`). После правок пути/fallback
  аренда газопроводов в CLI отвечает; полный eval в репетиции v1 не гоняли.
- `ASSISTANT_MAX_TOOL_ROUNDS=2`.
- Семантика «похожее имя» может подтянуть соседние статьи.

## Не входит в v1

- SSO, роли, публичный интернет.
- Compose не содержит LM Studio.
- Реестры договоров / обязательств.
