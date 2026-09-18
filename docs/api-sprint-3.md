# API Sprint 3 — контракт MCP tools

Утверждено 2026-09-18. Scope: только бюджет. Реализуем три tools.
`get_contract` и `list_obligations` в код не пишем — выгрузок нет.

Имена tools стабильные. Невалидный вход — ошибка валидации (HTTP 4xx / MCP error),
не пустой список хитов.

Общие лимиты поиска: `limit` 1…20, по умолчанию 8 (`configs/default.yaml`).
Порог score стартово 0.4; ниже порога хит не возвращаем.

## Общие типы

### `Source`

Откуда строка в Excel. Поля как в payload ingest.

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["source_file", "sheet"],
  "properties": {
    "source_file": { "type": "string" },
    "sheet": { "type": "string" },
    "row": { "type": ["integer", "null"] }
  }
}
```

Пример: `БДР для индексации.xlsx` / `Смета затрат` / `23`.

### `MoneyFields`

Суммы как в индексе: число или `null`. Ноль не подставляем, если в точке пусто.
Единица и валюта обязательны на объекте (у сметы `thousand_rub` / `RUB`).

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "limit", "fact", "obligation", "remain_free", "remain_unexecuted",
    "amount_unit", "currency"
  ],
  "properties": {
    "limit": { "type": ["number", "null"] },
    "fact": { "type": ["number", "null"] },
    "obligation": { "type": ["number", "null"] },
    "remain_free": { "type": ["number", "null"] },
    "remain_unexecuted": { "type": ["number", "null"] },
    "amount_unit": { "type": "string" },
    "currency": { "type": "string" }
  }
}
```

Сложение в `budget_summary`: по каждому полю сумма не-`null`. Если все значения
поля `null` — в `total` тоже `null`. Не считать `limit − obligation` и не
заменять пустой `remain_free` лимитом.

### `BudgetFilters`

Фильтры `search_records` / `budget_summary` на этот спринт.

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "year": { "type": "integer" },
    "expense_kind": { "type": "string", "enum": ["production", "management"] },
    "article_code": { "type": "string" },
    "article_name": { "type": "string" },
    "match_key": { "type": "string" },
    "ancestor_code": { "type": "string" },
    "amount_min": { "type": "number" },
    "amount_max": { "type": "number" }
  }
}
```

`amount_min` / `amount_max` режут `limit_amount`.
`ancestor_code` — «всё под статьёй», match по payload `ancestor_codes`.
Поля договоров (`contract_number`, `inn`, `status`, даты) во вход не принимаем:
неизвестное поле → ошибка валидации.

---

## `search_records`

Гибрид: непустой `query` → embedding той же модели, что ingest, плюс filter.
Пустой / отсутствующий `query` → только filter (scroll).

Коллекции: только `budget_items`. Запрос `contracts` / `obligations` — ошибка
валидации, не тихий пропуск.

Вход:

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "query": { "type": "string" },
    "collections": {
      "type": "array",
      "minItems": 1,
      "items": { "type": "string", "enum": ["budget_items"] },
      "default": ["budget_items"]
    },
    "filters": { "$ref": "#/BudgetFilters" },
    "limit": { "type": "integer", "minimum": 1, "maximum": 20, "default": 8 }
  }
}
```

Выход: `{ "hits": [ { "collection", "id", "score", "fields", "source" } ] }`.
`score` — Cosine Qdrant; при filter-only можно `null`.
`fields` — канон листа (код, имя, kind, год, путь, суммы, `text` не обязателен).

---

## `budget_summary`

Агрегат по листьям. Родитель — фильтр `ancestor_codes`, не точка.
`remain_free` из индекса, в MCP не пересчитываем.

Вход (нужен хотя бы один указатель ветки **или** явный широкий запрос с `year`):

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "year": { "type": "integer" },
    "article_code": { "type": "string" },
    "article_name": { "type": "string" },
    "match_key": { "type": "string" },
    "expense_kind": { "type": "string", "enum": ["production", "management"] },
    "group_by_level": { "type": "integer", "minimum": 1, "maximum": 5 },
    "limit": { "type": "integer", "minimum": 1, "maximum": 50, "default": 20 }
  }
}
```

Без `article_*` / `match_key` / `expense_kind` и без `year` — ошибка
(слишком широко). Голый `year` допустим: все листья года, дальше топ-N.

Выход:

```json
{
  "type": "object",
  "required": ["filter", "total", "rows", "need_refine"],
  "properties": {
    "filter": { "type": "object" },
    "total": { "$ref": "#/MoneyFields" },
    "rows": { "type": "array" },
    "need_refine": { "type": "boolean" }
  }
}
```

`rows`: листья или свёртка `group_by_level` — `{ code, name, level, ...MoneyFields }`.
Строк больше `limit` → топ-N по `limit`, `need_refine: true`.
Родителя и детей как независимые статьи в одном `rows` не смешиваем.

Контроль на живой смете: `remain_free` / факт / принятые у точек `null` —
в `total` те же поля `null`, лимит не выдаём как «остаток».

---

## `ingest_status`

Служебный. Без входных полей (пустой объект).

Выход:

```json
{
  "type": "object",
  "required": ["collections"],
  "properties": {
    "collections": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "points"],
        "properties": {
          "name": { "type": "string" },
          "points": { "type": "integer" },
          "source_files": { "type": "array", "items": { "type": "string" } },
          "last_indexed_at": { "type": ["string", "null"] }
        }
      }
    }
  }
}
```

Сейчас одна коллекция `budget_items`. Чужих имён не выдумываем.

---

## Позже (не Sprint 3)

`get_contract`, `list_obligations` — целевые в `FUNCTIONALITY.md`.
Вызов сейчас: tool неизвестен / не реализован, не пустая «карточка».

## Транспорт

Один слой `tools.Call`.

- HTTP: `POST /tools/{name}` (тело — JSON аргументов).
- stdio MCP: NDJSON JSON-RPC, `tools/list` и `tools/call`.
- Невалидный вход: HTTP 400 / MCP `isError: true`, не пустой список.
- Неизвестный tool (`get_contract`): HTTP 404 / MCP `isError: true`.

## Контрольные записи (живая смета)

Источник: `БДР для индексации.xlsx`, лист «Смета затрат», ingest = Excel.

| Запрос | Ожидание |
|---|---|
| `search_records` `article_code=production:1.8.2` | 1 хит, лимит 124970.29767396959, факт/остаток `null`, row 23 |
| `search_records` `article_code=production:9.9.9` | `hits: []` |
| `budget_summary` `production:1.8` + production | 3 листа, total.limit 136220.7035623236, remain/fact/obligation `null` |
| `budget_summary` year 2026 + production, limit 50 | total.limit 9 566 769.39, `need_refine: true` |
| `ingest_status` | 172 точки, один `source_file` |

## Ошибки

| Ситуация | Ответ |
|---|---|
| Лишнее / неизвестное поле, плохой enum, `limit` вне диапазона | валидация, не поиск |
| Коллекция не `budget_items` | валидация |
| Ничего не нашли | `hits: []` / `rows: []`, HTTP 200 |
| Qdrant / embeddings недоступны | 5xx / MCP error |
