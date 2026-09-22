# Sprint 6 Checklist

Источник: `docs/sprint-6-plan.md`.

**Scope:** только бюджет. VPS + DeepSeek API (чат) + Telegram long polling.
HTTP-ingest, веб, CSV, сверка, договоры — не отмечаем и не делаем.

## 0) Ворота

- [x] Sprint 4 закрыт на живом индексе.
- [x] Sprint 5: запуск с нуля по README.
- [x] Scope зафиксирован: DeepSeek API + те же эмбеддинги + Telegram long polling.

## 1) Облачный чат (DeepSeek API)

- [x] `LLM_API_KEY` в настройки; Bearer на `/models` и `/chat/completions`.
- [x] Пустой ключ — поведение как сейчас (LM Studio без заголовка).
- [x] В облако не уходит `chat_template_kwargs`.
- [x] `LLM_URL` / `LLM_MODEL` — DeepSeek API, модель с tool calling.
- [x] Эмбеддинги: те же `EMBEDDINGS_MODEL` и `VECTOR_SIZE`, без переиндексации «под облако».
- [x] Живые `code-1.8.2` и `refuse-9.9.9` через новый LLM.

## 2) Telegram-бот

- [x] Тонкий клиент к `POST /chat`, оркестратор не скопирован.
- [x] Long polling (`getUpdates`), не webhook.
- [x] Allowlist `TELEGRAM_ALLOWED_CHAT_ID`.
- [x] В ответе текст и sources (файл / лист / строка / код).
- [x] Юнит-тесты на allowlist и разбор `question` (без живого Telegram).

## 3) Compose и VPS

- [x] Сервис бота в compose (профиль или отдельный сервис).
- [x] На VPS не публиковать `:6333` / `:7345` / `:7346` наружу.
- [x] `.env.example`: DeepSeek, токен бота, allowlist, embeddings URL для VPS.
- [x] Выкат по README (SSH вручную, без `task prod:*`).
- [x] Ingest контрольной сметы на сервере, число точек стабильно.
- [x] Секреты не в git.

## 4) Регрессия и документация

- [ ] Три контрольных вопроса с бота: `1.8.2`, `9.9.9`, `5.1.1.1`.
- [ ] Локальный CLI / `POST /chat` не сломан.
- [ ] README: VPS, Telegram, OpenRouter vs эмбеддинги.
- [ ] `docs/known-limitations-sprint-6.md` (облако видит текст сметы в tools).

## 5) Демо

- [ ] Разрешённый чат — цифры Excel.
- [ ] Чужой чат — без данных индекса.
- [ ] Показать, что нет webhook и публичного `:7346`.
