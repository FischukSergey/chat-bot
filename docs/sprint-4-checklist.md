# Sprint 4 Checklist

Источник: `docs/sprint-4-plan.md`.

**Статус:** закрыт 2026-09-19. CLI + `POST /chat` на живом MCP, золотой набор 22/25.

**Scope:** только бюджет. Вопросы про договоры и обязательства не входят
в золотой набор, пока нет этих коллекций.

## 1) Подготовка

- [x] MCP Sprint 3 отвечает на контрольных статьях сметы
  (`search_records` / `budget_summary`, не номер договора).
- [x] `LLM_URL` доступен (LM Studio или иной).
- [x] Живой индекс, не мок tools.

Проверка (2026-09-19): `GET /health` → ok, 172 точки, модель
`text-embedding-qwen3-embedding-0.6b`. `search_records` `production:1.8.2` —
лимит 124970.30, row 23. `budget_summary` `production:1.8` — 3 листа,
136220.70, fact/obligation/remain_free = null. `production:9.9.9` → `hits: []`.
`contract_number` → 400, `get_contract` → 404. `LLM_URL` `/v1/models` и
`chat/completions` (`qwen/qwen3.6-35b-a3b`) отвечают.

## 2) Оркестратор

- [x] HTTP-клиент к MCP tools.
- [x] LLM-клиент с tool calling.
- [x] Ограничение числа кругов tool calls.
- [x] Системный промпт: только факты tools, отказ, факт ≠ принятые, sources.

Проверка (2026-09-19): `task assistant -- --ask` на живом MCP.
`production:1.8.2` — 1 круг, `search_records`, лимит и row 23.
`production:9.9.9` — отказ без сумм. Промпт: `assistant/prompts/system.md`.
`ASSISTANT_MAX_TOOL_ROUNDS=2`.

## 3) Интерфейсы

- [x] CLI-чат.
- [x] `POST /chat` (`answer`, `sources`, `tools_used`).
- [x] `/health`.
- [x] Структурированные логи (вопрос, tools, hits, latency).

Проверка (2026-09-19): `task assistant` — цикл, `/quit`.
`task assistant -- serve` `:7346`. `GET /health` → ok, 172 точки.
`POST /chat` `production:1.8.2` — лимит, row 23, `search_records`.
Пустой question → 400. Лог: `question`, `tools`, `hits`, `latency_ms`.

## 4) Золотой набор

- [x] 20–30 вопросов по боевым данным.
- [x] Типы: номер, сумма обязательств, остаток статьи, факт vs принятые, отказ, сквозной.
- [x] Эталоны из Excel.
- [x] Прогон и таблица pass/fail.
- [x] Нет галлюцинированных сумм на прогоне.

Проверка (2026-09-19): 25 вопросов в `data/eval/gold.yaml` по живой смете.
Типы адаптированы (нет реестра договоров): код статьи, ветка, remain,
факт vs принятые, отказ, сквозной/kind. Эталоны = ingest Excel.
Прогон: 22 pass / 3 fail. Таблица `data/eval/last-run.md`.
На PASS нет выдуманных сумм; факт/принятые/`remain_free` не подменялись лимитом.
Провалы: пустой текст LLM после `budget_summary` (`branch-1.8`,
`cross-rent-pipes`); отказ + чужие суммы (`refuse-quantum`).

## 5) Документация

- [x] `docs/api-sprint-4.md`.
- [x] Промпт лежит в репозитории (не только в голове).
- [x] `data/eval/gold.yaml` (или эквивалент).

`docs/api-sprint-4.md`. Промпт: `assistant/prompts/system.md`.
Набор: `data/eval/gold.yaml`, прогон `data/eval/last-run.md`.

## 6) Критерии готовности (DoD)

- [x] CLI и `POST /chat` работают на живом MCP.
- [x] Точный номер договора → правильная запись.
- [x] Пустой индекс/номер → отказ.
- [x] Факт и принятые в бюджетных ответах разведены.
- [x] Золотой набор прогнан, провалы записаны.

Проверка (2026-09-19). Договоров нет: «точный номер» = код статьи.
CLI и `POST /chat` на живом MCP (`:7345` / `:7346`).
`production:1.8.2` — лимит 124970.30, row 23, источник Excel.
`production:9.9.9` — отказ, без сумм.
Факт и принятые подписаны раздельно, оба «не заполнено», не «исполнено».
Золотой набор: 22/25, провалы в `data/eval/last-run.md`.

## 7) Демо

- [x] Четыре живых вопроса в CLI (карточка, остаток, обязательства, отказ).
- [x] Тот же отказ/успех через `POST /chat`.
- [x] Показать pass/fail золотого набора.
- [x] Зафиксировать known limitations Sprint 4.

CLI `task assistant -- --ask` (2026-09-19):

1. Карточка `production:1.8.2` — лимит, row 23, факт/принятые пустые.
2. Остаток той же статьи — `remain_free` не заполнен, рядом лимит / факт / принятые.
3. Факт и принятые — оба «не заполнено», лимит отдельно (реестра обязательств нет).
4. `production:9.9.9` — «в индексе нет», без сумм.

`POST /chat`: тот же успех (1.8.2) и отказ (9.9.9).
Таблица: `data/eval/last-run.md` (22 pass / 3 fail).

**Known limitations Sprint 4**

- Только бюджет. Вопрос про договор/обязательство — отказ «в индексе только смета»,
  не карточка. `get_contract` / `list_obligations` нет.
- В живой смете факт, принятые и `remain_free` = `null`. Ассистент их не считает.
  «Обязательства по договору» в демо заменены на факт/принятые статьи.
- Единица сумм — `thousand_rub`. Модель иногда дублирует сумму в рублях (×1000).
- Родительская статья (не лист) не находится `search_records` по `article_code`.
  Нужен `budget_summary`. Иногда LLM после tools возвращает пустой текст
  (`branch-1.8`, `cross-rent-pipes` в золотом наборе).
- Семантика «похожее имя» может подтянуть чужие статьи; на отказе модель
  иногда перечисляет их суммы (`refuse-quantum`).
- Локальная LLM (Qwen) с thinking: в оркестраторе thinking выключен.
  Чат LM Studio + MCP stdio — не DoD, без лимита кругов, эмбеддинги делят GPU.
- Ассистент на хосте (`task assistant -- serve`), не в compose (Sprint 5).
- Золотой набор 22/25. Провалы не замазаны. Telegram / виджет — Sprint 6.
