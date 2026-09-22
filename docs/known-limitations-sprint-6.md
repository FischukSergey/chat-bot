# Known limitations Sprint 6

Стенд: VPS + DeepSeek API (чат) + Telegram long polling. Scope по-прежнему
только `budget_items`. Лимиты v1 из [known-limitations-sprint-5.md](known-limitations-sprint-5.md)
остаются в силе.

## Данные уходят в облако

Чат идёт на `https://api.deepseek.com` с `LLM_API_KEY`. В облако попадают:

- текст вопроса пользователя;
- системный промпт;
- JSON ответов MCP (`search_records` / `budget_summary` / `ingest_status`) —
  имена статей, коды, лимиты, путь, файл / лист / строка.

Эмбеддинги и Qdrant на облако не отправляются. Для режима «смета не наружу»
нужна своя GPU / локальный LLM — это не Sprint 6.

В облако не уходит `chat_template_kwargs` (это для локального Qwen).
У DeepSeek thinking по умолчанию включён; клиент шлёт
`thinking: {type: disabled}`, иначе после tool call бывает 400.

## Чат ≠ эмбеддинги

- Чат: DeepSeek (`deepseek-flash`), не OpenRouter.
- Эмбеддинги: та же модель и `VECTOR_SIZE`, что индекс
  (`text-embedding-qwen3-embedding-0.6b`, 1024). Не DeepSeek Embeddings.
- Смена embedding-модели без `local:down:clean` + полного ingest ломает поиск.

## Telegram

- Один процесс `getUpdates`. Локальный `task telegram` и `task local:telegram`
  на VPS одновременно нельзя.
- Webhook не используем, порт бота наружу не публикуем.
- Чужой `chat_id` индекс не трогает (allowlist). Молчание или отказ — не утечка сумм.
- `TELEGRAM_ALLOWED_CHAT_ID` — целое без кавычек.
- Ответ бота может занять десятки секунд (таймаут ≥ `ASSISTANT_LLM_TIMEOUT`).
  Отдельного «ищу в смете…» нет.

## VPS

- Порты `:6333` / `:7345` / `:7346` только на `127.0.0.1`. Это не замена firewall.
- `task local:down:clean` на стенде сотрёт индекс. Тасков `prod:*` нет.
- Контейнеры ходят к эмбеддингам через `host.docker.internal`. Нужен listen
  и на docker0 (`172.17.0.1:1234`), не только `127.0.0.1`.
- Sidecar llama.cpp на ~4 ГиБ: большой `-c`/`-ub` съедает RAM (ingest/DNS
  начинают падать). Для сметы хватает `-c 512 --parallel 1`.
- 1 vCPU / 2 GiB с эмбеддингами на той же машине — мало.

## Не входит

- Webhook, домен, TLS, публичный `POST /chat`.
- HTTP-загрузка Excel, веб-чат, CSV, сверка реестра.
- Договоры / обязательства.
- SSO, роли, hardening сверх allowlist и bind на localhost.
