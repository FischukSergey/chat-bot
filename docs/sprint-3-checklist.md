# Sprint 3 Checklist

Источник: `docs/sprint-3-plan.md`.

**Scope:** только бюджет. `get_contract` / `list_obligations` не реализуем,
пока нет выгрузок. DoD — `search_records` и `budget_summary` по смете.

## 1) Подготовка и контракты

- [ ] Индекс Sprint 2 доступен (`budget_items`, 172 точки на живой смете).
- [ ] Утвердить JSON Schema всех пяти tools (как в `FUNCTIONALITY.md`).
- [ ] Зафиксировать формат `source` и денежных полей.
- [ ] Зафиксировать правило: `remain_free` в summary не пересчитывать.

## 2) Каркас mcp_server

- [ ] Go-модуль, конфиг, пакеты `qdrant` / `embed` / `tools` / `mcp`.
- [ ] HTTP `/health`.
- [ ] Клиент Qdrant (filter, search, scroll).
- [ ] Клиент embeddings (та же модель, что ingest).

## 3) Tools

- [ ] `search_records` (hybrid, 1…20, несколько коллекций).
- [ ] `get_contract` (карточка + обязательства + суммы).
- [ ] `list_obligations` (фильтры + `total_amount`).
- [ ] `budget_summary` (ветка, total, `group_by_level`, топ-N).
- [ ] `ingest_status`.
- [ ] Валидация входа; невалидный запрос ≠ пустой поиск.

## 4) Транспорт и логи

- [ ] stdio MCP (`tools/list`, `tools/call`).
- [ ] HTTP к тому же слою tools.
- [ ] Логи: tool, latency, hits.

## 5) Проверка цифр и тесты

- [ ] `get_contract` по известному номеру = Excel.
- [ ] `list_obligations` по договору = Excel.
- [ ] `budget_summary` по известной статье: лимит / факт / принятые / `remain_free` = Excel.
- [ ] Несуществующий номер → пустой список.
- [ ] Unit-тесты filter builder и `group_by_level`.
- [ ] `docs/api-sprint-3.md`.

## 6) Критерии готовности (DoD)

- [ ] Пять tools работают по schema.
- [ ] Цифры совпадают с Excel на контрольных записях.
- [ ] stdio и HTTP — один слой.
- [ ] `/health` зелёный.

## 7) Демо

- [ ] Показать три контрольных вызова tools vs Excel.
- [ ] Показать пустой поиск.
- [ ] (Опционально) вызов из LM Studio / Cursor.
- [ ] Зафиксировать known limitations Sprint 3.
