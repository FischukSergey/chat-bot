# Sprint 2 Checklist

Источник: `docs/sprint-2-plan.md`.

## 1) Подготовка

- [ ] Маппинги Sprint 1 на месте и утверждены.
- [ ] Qdrant поднят, URL в `.env`.
- [ ] Embeddings endpoint отвечает, размер вектора совпадает с конфигом.

## 2) Модели и идентификаторы

- [ ] Модели `BudgetItem`, `Contract`, `Obligation`.
- [ ] Стабильный `id` (бизнес-ключ или `source_file + sheet + row`).
- [ ] Единая нормализация `contract_number`.

## 3) Парсер

- [ ] Чтение `.xlsx` по строке шапки из YAML.
- [ ] Маппинг колонок → канон, неизвестные → `extra`.
- [ ] Бюджет: путь `l1`…`l5`, `ancestor_codes`.
- [ ] В индекс бюджета попадают только листья.
- [ ] Парсер договоров.
- [ ] Парсер обязательств.

## 4) Валидация и остаток

- [ ] Обязательные поля, суммы, даты, год → rejects.
- [ ] Файл rejects с причиной и строкой.
- [ ] Сверка `remain_free` vs `limit - obligation` (epsilon 0.01).
- [ ] При расхождении: warning, в индекс значение Excel.
- [ ] `remain_free_source` = `excel` | `computed`.
- [ ] `remain_unexecuted` из Excel или расчёт.

## 5) Эмбеддинги и Qdrant

- [ ] Детерминированный `text`.
- [ ] Клиент embeddings, батч, ретраи.
- [ ] Создание трёх коллекций и payload indexes.
- [ ] Upsert батчами.
- [ ] `delete-source` по `source_file`.

## 6) CLI и тесты

- [ ] `python3 -m ingest load <file>`.
- [ ] `python3 -m ingest delete-source <file>`.
- [ ] Отчёт: принято / обновлено / отклонено / warning.
- [ ] Unit-тесты: остаток, иерархия, нормализация номера.
- [ ] Повторный load — то же число точек.

## 7) Критерии готовности (DoD)

- [ ] Load трёх типов файлов проходит с отчётом.
- [ ] Нет дублей после повторного load.
- [ ] `contract_number` находится в Qdrant Console.
- [ ] Родители бюджета не проиндексированы.
- [ ] `remain_free` в точке = Excel.

## 8) Демо

- [ ] Показать отчёт load бюджета.
- [ ] Показать карточку листа в Console (лимит / факт / принятые / остаток / путь).
- [ ] Показать идемпотентный повторный load.
- [ ] Показать delete-source и повторную загрузку.
- [ ] Зафиксировать known limitations Sprint 2.
