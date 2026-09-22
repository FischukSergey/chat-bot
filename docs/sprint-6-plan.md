# Sprint 6 — детальный план (стенд на VPS + Telegram)

Источник: `docs/PLAN.md` этап 6, `docs/sprint-5-plan.md`.

**Scope:** только бюджет. Деплой контура v1 на VPS и доступ из Telegram.
Договоры / обязательства, HTTP-ingest, веб-чат, CSV, сверка реестра — не в этом спринте.

Sprint 4 и 5 закрыты. Этот спринт не часть «доказательства RAG»; v1 уже можно
крутить локально. Цель — первый удалённый стенд.

## 1) Цель спринта

С VPS пользователь пишет боту в Telegram и получает ответ по смете
из того же `POST /chat`, что CLI.

К концу спринта должно быть:

- чат LLM — облако **OpenRouter** (DeepSeek / Flash), ключ в клиенте ассистента;
- эмбеддинги **те же**, что в индексе (`EMBEDDINGS_MODEL`, `VECTOR_SIZE` не менять);
- сервис Telegram: **long polling** на `api.telegram.org`, без webhook и без
  открытого порта бота;
- compose на VPS: qdrant + mcp + assistant + bot;
- наружу не торчат `:6333` / `:7345` / `:7346`;
- README: как выкатить и какие секреты нужны.

## 2) Входные условия

- v1 в compose, ingest CLI, MCP, ассистент, золотой набор.
- Репетиция Sprint 5 с нуля записана.
- Аккаунт OpenRouter и ключ (или заведём в спринте).
- Бот у [@BotFather](https://t.me/BotFather), токен не в git.
- VPS с Docker (CPU достаточно: GPU для чата не нужна).

## 3) Границы Sprint 6

### Входит

- `Authorization: Bearer` в LLM-клиенте (`LLM_API_KEY` / OpenRouter).
- `LLM_URL=https://openrouter.ai/api/v1`, модель с tool calling
  (ориентир: DeepSeek Flash / актуальный id на OpenRouter; проверить tools живьём).
- Не слать в облако `chat_template_kwargs` (это для локального Qwen).
- Эмбеддинги: тот же endpoint/модель, что построил индекс. На VPS — URL,
  доступный контейнерам (маленький локальный сервер той же модели или
  уже существующий совместимый `/v1/embeddings`). Не OpenRouter embeddings
  и не новая модель без переиндексации.
- Клиент Telegram → только `POST {ASSISTANT}/chat`. Оркестратор не копировать.
- Long polling. Allowlist `TELEGRAM_ALLOWED_CHAT_ID`.
- Таймаут на ответ чата ≥ таймаута LLM (у вопроса бывает 20+ с).
- Firewall: SSH (и больше ничего для бота). `task prod:*` / SSH-таски не добавлять.
- Документация деплоя и known limitations (ключ, данные сметы в облако).

### Не входит

- Webhook, домен, TLS, белый IP для Telegram.
- Публичный `POST /chat` в интернет.
- HTTP-загрузка Excel, веб-виджет, CSV, сверка реестра (бэклог после 6).
- Своя GPU / замена эмбеддинг-модели.
- SSO, роли, PostgreSQL.
- Прод-hardening сверх allowlist и закрытых портов.

## 4) Sprint backlog

## A. Клиент LLM: OpenRouter

- Настройка: `LLM_URL`, `LLM_MODEL`, `LLM_API_KEY` (не коммитить).
- `GET /models` и `POST /chat/completions` с Bearer.
- Локальный LM Studio остаётся опцией: ключ пустой — заголовок не слать.
- Прогон трёх вопросов репетиции Sprint 5 на OpenRouter (не весь gold обязателен).

## B. Telegram-бот

- Отдельный тонкий сервис (Python), не второй RAG.
- Long polling `getUpdates`.
- Текст сообщения → `{"question": "..."}` → `answer` (+ коротко sources).
- Чужой chat_id — молча или отказ, без вызова MCP.
- Переменные: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_CHAT_ID`,
  `ASSISTANT_URL=http://assistant:7346`.

## C. Compose и VPS

- Сервис `telegram-bot` в `deploy/docker-compose.yml` (можно profile `telegram`).
- Порты 7345/7346/6333 на хост VPS не публиковать (или bind `127.0.0.1`, если ingest с той же машины).
- `.env.example`: ключ OpenRouter, токен бота, allowlist, `EMBEDDINGS_URL` для VPS.
- Выкат: SSH вручную, `git pull`, `.env`, `task local:up`, `task local:ingest`.
  Без новых task `prod:*`.
- Не вызывать `local:down:clean` на проде.

## D. Документация и регрессия

- README: стенд VPS, секреты, Telegram, чем embeddings отличаются от LLM.
- Контрольные вопросы: `code-1.8.2`, `refuse-9.9.9`, `code-5.1.1.1` в боте.
- Золотой набор локально не должен развалиться из‑за ключа (пустой ключ = как сейчас).

## 5) Разбивка по дням (ориентир)

### Дни 1–2

- Ключ в `llm.py`, `.env`, проверка OpenRouter на `1.8.2` / `9.9.9`.
- Зафиксировать id модели с рабочими tools.

### Дни 3–5

- Бот long polling + allowlist + тесты без живого Telegram (мок API).
- Compose-сервис, локально: бот → assistant в docker-сети.

### Дни 6–8

- VPS: Docker, `.env`, ingest сметы, закрытые порты.
- Эмбеддинги на VPS той же моделью (sidecar или уже поднятый `/v1`).

### Дни 9–10

- Живой бот с телефона, README, known limitations, регрессия CLI.

## 6) Definition of Done (DoD)

Спринт закрыт, если:

- с разрешённого Telegram-чата вопрос доходит до `POST /chat` и ответ сходится с Excel
  на трёх контрольных кейсах;
- посторонний chat_id индекс не трогает;
- на VPS снаружи не открыты Qdrant / MCP / assistant;
- чат идёт в OpenRouter с ключом, эмбеддинги — прежняя модель и размер вектора;
- секреты не в git;
- README достаточно, чтобы повторить выкат;
- локальный сценарий Sprint 5 (CLI / `POST /chat` без ключа или с тем же клиентом) жив.

## 7) Демо-сценарий

1. Показать `.env.example` (без секретов) и закрытые порты на VPS.
2. Из разрешённого Telegram: лимит `production:1.8.2`.
3. `production:9.9.9` — отказ без сумм.
4. Со второго аккаунта (не в allowlist) — нет ответа по смете.
5. Показать, что webhook и `:7346` в интернет не используются.

## 8) Риски и меры

- Риск: OpenRouter-модель без нормальных tools.
  - Мера: выбрать id с `tools`, прогнать 1.8.2 до выката бота.

- Риск: смена эмбеддингов «заодно».
  - Мера: в DoD явный запрет; индекс не пересоздавать под другую модель.

- Риск: смета уходит в облако (вопрос + JSON tools).
  - Мера: записать в known limitations; для «данные не наружу» — отдельное решение (своя GPU).

- Риск: `getUpdates` два процесса сразу (локальный бот + VPS).
  - Мера: один инстанс polling; локально profile выключен по умолчанию.

- Риск: долгий LLM и «молчание» бота.
  - Мера: таймаут ≥ `ASSISTANT_LLM_TIMEOUT`, сообщение «ищу в смете…» по желанию.

## 9) Артефакты

- ключ в LLM-клиенте + `.env.example`;
- сервис Telegram (код + compose);
- README деплоя VPS;
- `docs/known-limitations-sprint-6.md`;
- прогон трёх контрольных вопросов с бота.
