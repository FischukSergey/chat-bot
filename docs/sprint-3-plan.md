# Sprint 3 — детальный план (MCP-сервер)

Источник: `docs/PLAN.md` этап 3, `docs/FUNCTIONALITY.md` (контракт tools), `docs/sprint-2-plan.md`.

## 1) Цель спринта

Сделать единственный доступ к индексу: Go MCP-сервер с теми же tools для LLM и для ручных вызовов.

К концу спринта должно быть:

- tools: `search_records`, `get_contract`, `list_obligations`, `budget_summary`, `ingest_status`;
- JSON Schema на вход/выход, жёсткая валидация;
- гибридный поиск: filter + vector;
- транспорт stdio и HTTP;
- ручной вызов `get_contract` / `list_obligations` / `budget_summary` совпадает с цифрами Excel.

## 2) Входные условия (что уже готово после Sprint 2)

- Три коллекции в Qdrant наполнены с payload и векторами.
- Канонические поля и `source` (файл, лист, строка) лежат в точке.
- Embeddings — тот же endpoint и та же модель, что при ingest.
- Контракт tools описан в `FUNCTIONALITY.md`.

## 3) Границы Sprint 3

### Входит в Sprint 3

- бинарник `mcp_server` на Go;
- слой `tools` + валидация schema;
- клиент Qdrant (filter, scroll, search);
- embeddings для текстового `search_records`;
- агрегация `budget_summary` по листьям (`ancestor_codes`, `group_by_level`);
- stdio MCP и HTTP (тот же слой tools);
- структурированные логи: tool, latency, hits;
- ручные сценарии проверки цифр.

### Не входит в Sprint 3

- системный промпт и tool calling ассистента (Sprint 4);
- подключение к агенту LM Studio как обязательный DoD (желательно проверить, не блокер);
- Telegram / веб-чат (Sprint 6);
- сверка суммы реестра обязательств со статьёй бюджета.

## 4) Sprint backlog (детализация задач)

## A. Каркас Go-сервера

- Модуль, конфиг (Qdrant URL, embeddings URL, порог score, лимиты).
- Пакеты: `internal/config`, `internal/qdrant`, `internal/embed`, `internal/tools`, `internal/mcp`.
- `/health` на HTTP-транспорте.

## B. Контракты tools (schema)

- Зафиксировать JSON Schema 1:1 с `FUNCTIONALITY.md`.
- Общие типы: `Source`, `MoneyFields`, фильтры.
- Ошибки: невалидный вход — 4xx / MCP error, не «пустой поиск».
- Черновик `docs/api-sprint-3.md` (как в my-chat: контракт на спринт).

## C. Qdrant + embeddings

- Filter builder: `contract_number`, `inn`, `status`, `year`, `budget_article`,
  `ancestor_codes`, диапазоны дат и сумм.
- Vector search + payload filter; score threshold из конфига.
- Если `query` пустой — только filter (для `list_obligations`).
- Embeddings-клиент: тот же модель/размер, что ingest.

## D. Реализация tools

- `search_records` — 1…20 хитов, несколько коллекций.
- `get_contract` — карточка + обязательства + суммы accepted / reflected;
  несколько договоров — список, без угадывания.
- `list_obligations` — фильтры + `total_amount` при одной валюте.
- `budget_summary` — листья по ветке, `total` из полей индекса
  (`remain_free` не пересчитывать), `group_by_level`, топ-N + «уточните».
- `ingest_status` — count по коллекциям, `source_file`, время последней индексации
  (если поле есть).

## E. Транспорт и наблюдаемость

- stdio MCP (`tools/list`, `tools/call`).
- HTTP: JSON RPC или простые `POST /tools/{name}` — один слой `tools`.
- Логи: имя tool, latency, hits, ошибка валидации.

## F. Проверка цифр

- Сценарии из Excel: известный договор, известная статья, пустой поиск.
- Сравнить `remain_free` / лимит / факт / принятые с файлом.
- Unit-тесты filter builder и свёртки `group_by_level` на фикстурах payload.

## 5) Разбивка по дням (ориентир на 10 рабочих дней)

### День 1

- Каркас сервиса, конфиг, `/health`.
- Черновик schema всех tools.

### День 2

- Клиент Qdrant: filter + retrieve.
- Клиент embeddings.

### День 3

- `ingest_status`, `list_obligations` (без вектора).

### День 4

- `get_contract`.

### День 5

- `search_records` (hybrid).

### День 6

- `budget_summary` (ветка, total, group_by_level).

### День 7

- stdio MCP.
- HTTP обёртка тех же handlers.

### День 8

- Валидация schema, логи, лимиты, порог score.

### День 9

- Сверка цифр с Excel, фиксы фильтров и нормализации номера.
- Тесты на фикстурах.

### День 10

- Документ контракта `docs/api-sprint-3.md`.
- Демо и freeze.

## 6) Definition of Done (DoD) для Sprint 3

Спринт считается завершённым, если:

- все пять tools отвечают по schema;
- `get_contract` и `list_obligations` по известному номеру дают суммы Excel;
- `budget_summary` по известной ветке: лимит / факт / принятые / `remain_free` как в файле;
- пустой результат — пустой список, не выдуманные поля;
- stdio и HTTP вызывают один код tools;
- `/health` зелёный.

## 7) Демо-сценарий

1. Индекс Sprint 2 на месте.
2. HTTP: `list_obligations` по `contract_number` — сверка с Excel.
3. `get_contract` — карточка + обязательства.
4. `budget_summary` по статье-родителю — сумма листьев, `remain_free` из индекса.
5. `search_records` с текстом «охрана» — релевантные листья / обязательства.
6. Запрос с несуществующим номером — пусто, без ошибки 500.
7. (Опционально) подключить stdio к LM Studio / Cursor.

## 8) Риски Sprint 3 и меры

- Риск: локальная модель плохо эмбеддит запрос относительно ingest-модели.
  - Мера: один и тот же embeddings endpoint; модель в конфиге, не «какая загружена в UI».

- Риск: filter по сырому номеру договора не бьёт.
  - Мера: фильтровать по нормализованному полю.

- Риск: `budget_summary` суммирует родителей, если они ошиблись в индекс.
  - Мера: фильтр только листьев; если в Sprint 2 родители просочились — чинить ingest, не MCP.

- Риск: слишком широкая ветка.
  - Мера: топ-N и флаг `need_refine` в ответе.

## 9) Артефакты по итогам спринта

- бинарник / сервис `mcp_server`;
- `docs/api-sprint-3.md`;
- ручной runbook вызова tools;
- тесты filter / summary;
- логи tool calls.
