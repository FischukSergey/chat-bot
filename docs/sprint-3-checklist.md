# Sprint 3 Checklist

Источник: `docs/sprint-3-plan.md`.

**Статус:** закрыт 2026-09-19. Tools: `search_records`, `budget_summary`, `ingest_status`.

**Scope:** только бюджет. `get_contract` / `list_obligations` не реализуем,
пока нет выгрузок. DoD — `search_records` и `budget_summary` по смете.

## 1) Подготовка и контракты

- [x] Индекс Sprint 2 доступен (`budget_items`, 172 точки на живой смете).
- [x] Утвердить JSON Schema tools в scope (как в `FUNCTIONALITY.md`).
- [x] Зафиксировать формат `source` и денежных полей.
- [x] Зафиксировать правило: `remain_free` в summary не пересчитывать.

Проверка (2026-09-18):

- `GET /readyz` → `all shards are ready`. `budget_items`: 172 точки, COSINE 1024,
  модель `text-embedding-qwen3-embedding-0.6b`.
- В Sprint 3 реализуем `search_records`, `budget_summary`, `ingest_status`.
  `get_contract` / `list_obligations` — schema не утверждаем к реализации,
  вызов = tool неизвестен.
- Контракт: `docs/api-sprint-3.md`. `Source` = `source_file` + `sheet` + `row`.
  Деньги: число или `null`, плюс `amount_unit` / `currency`; пустое не затираем нулём.
- `remain_free` в summary — как в точке. Все 172 листа сейчас `null` →
  `total.remain_free = null`, не `limit` и не `limit − obligation`.
  Сложение: сумма не-`null`; поле целиком пустое → `null`.

## 2) Каркас mcp_server

- [x] Go-модуль, конфиг, пакеты `qdrant` / `embed` / `tools` / `mcp`.
- [x] HTTP `/health`.
- [x] Клиент Qdrant (filter, search, scroll).
- [x] Клиент embeddings (та же модель, что ingest).

`mcp_server/internal/{config,qdrant,embed,tools,mcp,httpapi}`.
`task mcp` → `GET http://127.0.0.1:7345/health`:
status ok, qdrant ok, embeddings ok, `budget_items` 172,
модель `text-embedding-qwen3-embedding-0.6b`, size 1024.
Tools в health только имена, handlers — пункт 3.
Живой клиент: scroll/count/search `production:1.8.2` → 1 точка;
embed «электроэнергия…» → вектор 1024. `task lint` чистый.

## 3) Tools

- [x] `search_records` (hybrid, 1…20, только `budget_items`).
- [ ] `get_contract` (карточка + обязательства + суммы). — позже, нет реестра.
- [ ] `list_obligations` (фильтры + `total_amount`). — позже, нет реестра.
- [x] `budget_summary` (ветка, total, `group_by_level`, топ-N).
- [x] `ingest_status`.
- [x] Валидация входа; невалидный запрос ≠ пустой поиск.

`internal/tools.Call` — один слой. HTTP `POST /tools/{name}` для проверки
(stdio — пункт 4). Живой прогон:

- `search_records` filter `production:1.8.2` → 1 хит, лимит 124970.30,
  source лист 23. `query=электроэнергия` + kind production — hybrid.
- `budget_summary` `production:1.8` / production: 3 листа, total.limit
  136220.70, `remain_free`/`fact`/`obligation` = null.
- `ingest_status`: 172 точки, файл `БДР для индексации.xlsx`.
- `contract_number` во входе → 400 validation, не `hits: []`.
- `get_contract` → 404 not_found.

## 4) Транспорт и логи

- [x] stdio MCP (`tools/list`, `tools/call`).
- [x] HTTP к тому же слою tools.
- [x] Логи: tool, latency, hits.

`internal/mcp` — NDJSON JSON-RPC на stdin/stdout (`task mcp -- --stdio`).
HTTP `POST /tools/{name}` — тот же `tools.Call`. Лог JSON в stderr:
`tool`, `latency_ms`, `hits`, `error`. Живой stdio: `tools/list` — три имени;
`tools/call` search `production:1.8.2` → 1 хит; лог `hits=1 latency_ms=5`.
Валидация и неизвестный tool в MCP — `isError: true`, не пустые hits.

## 5) Проверка цифр и тесты

- [ ] `get_contract` по известному номеру = Excel. — позже, нет реестра.
- [ ] `list_obligations` по договору = Excel. — позже, нет реестра.
- [x] `budget_summary` по известной статье: лимит / факт / принятые / `remain_free` = Excel.
- [x] Несуществующий код статьи → пустой список.
- [x] Unit-тесты filter builder и `group_by_level`.
- [x] `docs/api-sprint-3.md`.

Сверка с парсером `БДР для индексации.xlsx` (ingest = Excel):

- `production:1.8.2`: лимит 124970.29767396959, факт/остаток `null`, row 23.
- ветка `production:1.8`: 3 листа, сумма 136220.7035623236, remain/fact/obligation `null`.
- production 2026: 9 566 769.39, 99 листьев, `need_refine` при limit 50.
- `production:9.9.9` → `hits: []`, не ошибка.
- Unit: `filter_test.go`, `groupByLevel`, топ-N (`need_refine`, total по всем листьям).
- Контракт обновлён: транспорт + таблица контрольных записей.

## 6) Критерии готовности (DoD)

- [x] Tools в scope отвечают по schema (`search_records`, `budget_summary`, `ingest_status`).
- [ ] Пять tools включая договоры. — позже, нет реестра.
- [x] Цифры совпадают с Excel на контрольных записях.
- [x] stdio и HTTP — один слой.
- [x] `/health` зелёный.

Проверка (2026-09-19): `GET /health` → ok, qdrant ok, embeddings ok,
172 точки, модель `text-embedding-qwen3-embedding-0.6b`. `go test ./...` OK.
HTTP и stdio зовут `tools.Call`.

## 7) Демо

- [x] Показать три контрольных вызова tools vs Excel.
- [x] Показать пустой поиск.
- [x] stdio `tools/list` + `tools/call` (Cursor/Studio — по желанию, не блокер).
- [x] Зафиксировать known limitations Sprint 3.

HTTP `127.0.0.1:7345`:

1. `search_records` `production:1.8.2` — лимит 124970.30, row 23.
2. `budget_summary` `production:1.8` / production — 3 листа, 136220.70,
   fact / obligation / remain_free = null.
3. `ingest_status` — 172, `БДР для индексации.xlsx`.
4. `production:9.9.9` — `{"hits":[]}`.

**Known limitations Sprint 3**

- Только бюджет. `get_contract` / `list_obligations` не реализованы (404 / isError).
- Коллекции `contracts` / `obligations` во входе — ошибка валидации.
- В живой смете нет факта, принятых и `remain_free`; MCP их не вычисляет.
- Единица сумм — `thousand_rub`.
- stdio — NDJSON JSON-RPC; подключение к Cursor/LM Studio не обязательный DoD.
- MCP на хосте (`task mcp`), не в compose. Embeddings — LM Studio на `:1234`.
- Ассистент и tool calling — Sprint 4.
