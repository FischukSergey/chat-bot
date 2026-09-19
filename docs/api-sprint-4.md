# API Sprint 4 — контракт ассистента

Утверждено 2026-09-19. Scope: только бюджет. Ассистент читает индекс через
MCP Sprint 3 (`search_records`, `budget_summary`, `ingest_status`).
`get_contract` / `list_obligations` не вызываем — выгрузок нет.

Цифры в ответе — только из JSON tools. Пусто → отказ без сумм.
`remain_free` / факт / принятые из индекса, без пересчёта.

Tools: [api-sprint-3.md](api-sprint-3.md).
Промпт: [`assistant/prompts/system.md`](../assistant/prompts/system.md).
Золотой набор: [`data/eval/gold.yaml`](../data/eval/gold.yaml),
прогон [`data/eval/last-run.md`](../data/eval/last-run.md).

## Запуск

```bash
task mcp                          # HTTP :7345
task assistant                    # CLI-чат
task assistant -- --ask "…"       # один вопрос
task assistant -- serve           # HTTP :7346
task assistant -- eval            # прогон золотого набора
```

Адрес HTTP: `ASSISTANT_HTTP_ADDR` (по умолчанию `127.0.0.1:7346`).
MCP: `MCP_URL` / `MCP_HTTP_ADDR`. LLM: `LLM_URL`, `LLM_MODEL`.
Круги tool calls: `ASSISTANT_MAX_TOOL_ROUNDS` (по умолчанию 2).

## `GET /health`

Проверка MCP (`GET {MCP_URL}/health`) и LLM (`GET {LLM_URL}/models`).

```json
{
  "status": "ok",
  "mcp": "ok",
  "llm": "ok",
  "llm_model": "qwen/qwen3.6-35b-a3b",
  "mcp_url": "http://127.0.0.1:7345",
  "points": 172,
  "llm_models": ["qwen/qwen3.6-35b-a3b"]
}
```

`status=ok` и код 200 — оба бэкенда отвечают. Иначе 503, `mcp` / `llm` = `error`.

## `POST /chat`

Вход — только поле `question`. Лишние поля — ошибка валидации.

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["question"],
  "properties": {
    "question": { "type": "string", "minLength": 1 }
  }
}
```

Выход:

```json
{
  "type": "object",
  "required": ["answer", "sources", "tools_used"],
  "properties": {
    "answer": { "type": "string" },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "source_file": { "type": "string" },
          "sheet": { "type": "string" },
          "row": { "type": ["integer", "null"] },
          "article_code": { "type": "string" }
        }
      }
    },
    "tools_used": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

`sources` собираются из tool-результатов (`search_records.hits`,
`budget_summary.rows` — тогда часто только `article_code`).
`tools_used` — имена вызванных tools по порядку, без выдуманных.

Пример:

```bash
curl -s http://127.0.0.1:7346/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"Какой лимит по статье production:1.8.2?"}'
```

```json
{
  "answer": "По статье production:1.8.2 (электроэнергия) лимит составляет 124970.30 тысяч рублей. …",
  "sources": [
    {
      "source_file": "БДР для индексации.xlsx",
      "sheet": "Смета затрат",
      "row": 23,
      "article_code": "production:1.8.2"
    }
  ],
  "tools_used": ["search_records"]
}
```

## CLI

`task assistant` — цикл ввода. Ответ, затем JSON `sources` / `tools_used` / `rounds`.
`/quit` или EOF — выход.

## Логи

JSON в stderr на каждый вопрос: `question`, `tools`, `hits`, `latency_ms`, `rounds`, `error`.

## Ошибки

| Ситуация | Ответ |
|---|---|
| Нет / пустой `question`, лишнее поле, не JSON | 400 `validation` |
| Не `/health` и не `POST /chat` | 404 `not_found` |
| MCP / LLM упали во время вопроса | 502 `error` |
| В индексе пусто | 200, отказ в `answer`, без сумм |
| Неизвестный tool от модели | в tool-результат `not_found`, не карточка договора |

## Политика ответа

Задаётся промптом в репозитории, не в этом файле:

- сначала tools, потом текст;
- цифры только из JSON tools;
- «остаток» = `remain_free`; факт ≠ принятые;
- `null` ≠ 0 и ≠ лимит;
- язык ответа = язык вопроса;
- без юридических и бухгалтерских советов.

## Контрольные записи (живая смета)

Как в Sprint 3. Единица — `thousand_rub`.

| Вопрос | Ожидание |
|---|---|
| лимит `production:1.8.2` | 124970.30, row 23, факт/остаток не заполнены |
| сводка `production:1.8` | 3 листа, total.limit 136220.70 |
| `production:9.9.9` | отказ, без сумм |
| договор / обязательства | «в индексе только смета», без карточки |

## Золотой набор

25 вопросов, эталон = Excel. Типы: код статьи, ветка, остаток, факт vs принятые,
отказ, сквозной (имя → код / production vs management).

Прогон 2026-09-19: **22 pass / 3 fail**. Провалы не замазаны:
пустой текст модели после tools (`branch-1.8`, `cross-rent-pipes`);
отказ с чужими суммами (`refuse-quantum`).

## Known limitations

- Только бюджет. Договор / обязательство → отказ, не карточка.
- Факт, принятые, `remain_free` в живой смете `null`; ассистент не считает.
- Родитель не лежит листом в индексе — `search_records` по коду ветки пустой.
- Иногда пустой текст LLM после успешного tool; иногда чужие суммы на отказе.
- Ассистент на хосте, не в compose. LM Studio chat + stdio MCP — не замена `POST /chat`.
