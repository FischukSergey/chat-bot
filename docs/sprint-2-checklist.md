# Sprint 2 Checklist

Источник: `docs/sprint-2-plan.md`.

**Статус:** закрыт 2026-09-18. Коллекция `budget_items`, 172 точки.

**Scope:** только бюджет. Договоры и обязательства — не в работе (все спринты).
Модели `Contract` / `Obligation` не заводим, добавим позже.

## 1) Подготовка

- [x] Маппинги Sprint 1 на месте и утверждены.
- [x] Qdrant поднят, URL в `.env`.
- [x] Embeddings endpoint отвечает, размер вектора совпадает с конфигом.

Проверка (2026-09-18):

- Канон бюджета: `data/mappings/budget.yaml` (утверждён в Sprint 1).
  `contracts.yaml` / `obligations.yaml` нет — файлов нет, в Sprint 2 не пишем.
- `QDRANT_URL=http://127.0.0.1:6333`; `GET /readyz` → `all shards are ready`.
- `POST /v1/embeddings` модель `text-embedding-qwen3-embedding-0.6b`:
  длина вектора **1024** = `VECTOR_SIZE` в `.env`.

## 2) Модели и идентификаторы

- [x] Модель `BudgetItem`.
- [x] Стабильный `id` бюджета (бизнес-ключ, не номер строки).
- [ ] Модели `Contract`, `Obligation`. — позже, вместе с выгрузками.
- [ ] Единая нормализация `contract_number`. — позже.

Канон бюджета: `ingest/models.py`. Id — UUID5 (`ingest/ids.py`):
`source_file + sheet + expense_kind + sheet_code`.

## 3) Парсер

- [x] Чтение `.xlsx` по строке шапки из YAML.
- [x] Маппинг колонок → канон, неизвестные → `extra`.
- [x] Бюджет: путь `l1`…`l5`, `ancestor_codes`.
- [x] В индекс бюджета попадают только листья.
- [ ] Парсер договоров. — позже.
- [ ] Парсер обязательств. — позже.

`ingest/budget.py` → `parse_budget`. Прогон на `БДР для индексации.xlsx`:
172 листа, 0 reject. Суммы листьев = итогам блоков
(9 566 769.39 произв. + 978 978.47 управл.).
Родители `production:1`, `production:1.8` не в результате;
листья `production:1.8.2`, `management:1.1.2`;
схлопнутые `production:2`, `production:3`, `management:3`;
`management:2.1` — лист, родитель `management:2` нет.
В Qdrant пока не пишем.

## 4) Валидация и остаток

- [x] Обязательные поля, суммы, даты, год → rejects.
- [x] Файл rejects с причиной и строкой.
- [x] Сверка `remain_free` vs `limit - obligation` (epsilon 0.01).
- [x] При расхождении: warning, в индекс значение Excel.
- [x] `remain_free_source` = `excel` | `computed`.
- [x] `remain_unexecuted` из Excel или расчёт.

`ingest/validate.py`, `ingest/rejects.py`. На живой смете колонок контроля нет:
`remain_free` не считаем (172 листа, source пустой, warning 0, файл rejects
не пишется). Если появится excel-остаток — в точку он, при расхождении с
`limit − принятые` — warning. Нет колонки, есть принятые — `computed`.
Rejects: `data/rejects/{файл}.{utc}.jsonl` (строка + причина). Дат в смете нет.

## 5) Эмбеддинги и Qdrant

- [x] Детерминированный `text`.
- [x] Клиент embeddings, батч, ретраи.
- [x] Создание коллекции `budget_items` и payload indexes.
- [x] Upsert батчами.
- [x] `delete-source` по `source_file`.

`ingest/text.py`, `embed.py`, `store.py`, `index.py`. Коллекция только `budget_items`
(COSINE, size из `VECTOR_SIZE`). Точку без вектора не пишем. Смена размера —
ошибка, коллекцию молча не дропаем. Прогон: 2 листа (электроэнергия произв./управл.)
→ count 2 → `delete-source` → count 0. CLI `load` всего файла — пункт 6.

## 6) CLI и тесты

- [x] `python3 -m ingest load <file>`.
- [x] `python3 -m ingest delete-source <file>`.
- [x] Отчёт: принято / обновлено / отклонено / warning.
- [x] Unit-тесты: остаток, иерархия.
- [x] Повторный load — то же число точек.

`ingest/cli.py` (`task ingest -- load|delete-source`). Отчёт: принято /
обновлено / отклонено / warning / точек. Живой файл:
1-й load — принято 172, обновлено 0, count 172;
2-й load — принято 0, обновлено 172, count 172;
`delete-source` → count 0, повторный load → снова 172.
Тесты: `tests/test_validate.py`, `test_hierarchy.py`, `test_cli.py`
(+ ранее `test_text`, `test_rejects`) — 14, OK. Коллекция сейчас 172 точки.

## 7) Критерии готовности (DoD)

- [x] Load бюджета проходит с отчётом.
- [x] Нет дублей после повторного load.
- [ ] `contract_number` в Console. — позже, нет реестра.
- [x] Родители бюджета не проиндексированы.
- [x] `remain_free` в точке = Excel.

Проверка (2026-09-18), коллекция `budget_items` COSINE 1024:

- Load: принято 172 / обновлено 0 / отклонено 0 / warning 0 / точек 172.
- Повторный load: принято 0 / обновлено 172 / точек 172. Scroll: 172
  уникальных `article_code`, дублей id нет. Id парсера = id Qdrant.
- Родители `production:1`, `production:1.8`, `management:2` — 0 точек.
  Листья на месте: `production:1.8.2`, `management:1.1.2`, схлопнутые
  `production:2` / `production:3` / `management:3`, `management:2.1`.
- В живом Excel нет колонок остатка / факта / принятых: у всех 172 точек
  `remain_free`, `remain_free_source`, `fact_amount`, `obligation_amount`
  = `null` — как в файле, цифру из лимита не выдумали.
- `delete-source` → 0; повторный load → снова 172.
- Виды: 99 production + 73 management.

Карточка `production:1.8.2` (id `829dd902-2f8f-5b3e-943d-20c8f354e6cc`):
электроэнергия, лимит 124970.30, путь «Материальные расходы /
Коммунальные услуги / электроэнергия», год 2026, лист «Смета затрат»,
строка 23. Пара в управл. блоке: `management:1.1.2`, лимит 7494.08.

## 8) Демо

- [x] Показать отчёт load бюджета.
- [x] Показать карточку листа в Console (лимит / факт / принятые / остаток / путь).
- [x] Показать идемпотентный повторный load.
- [x] Показать delete-source и повторную загрузку.
- [x] Зафиксировать known limitations Sprint 2.

Отчёт и идемпотентность — пункт 6. Карточка — Qdrant UI
http://127.0.0.1:6333/dashboard, коллекция `budget_items`, фильтр
`article_code` = `production:1.8.2` (поля выше). Факт / принятые /
остаток в payload пустые — в смете колонок нет.

**Known limitations Sprint 2**

- Индекс только `budget_items`. Договоры и обязательства не грузим.
- В индекс только лист «Смета затрат»; ФинРез и KPI не индексируем.
- Два блока (`production` / `management`) — разные точки; контроль
  суммой по `match_key`.
- `remain_free` / `fact_amount` / обязательства из этого файла нет.
- Единица лимита — `thousand_rub`, как в маппинге.
- Смена embedding-модели / `VECTOR_SIZE` — ошибка, коллекцию молча
  не пересоздаём; нужен явный дроп и переиндексация.
- MCP и чат — Sprint 3–4. HTTP-загрузки Excel нет (CLI).
- В `.venv` сейчас `qdrant-client` 1.19.1 при сервере 1.15.1
  (`requirements.txt` пинит `<1.16`); предупреждение совместимости,
  запись точек работает.
