# Sprint 5 Checklist

Источник: `docs/sprint-5-plan.md`.

**Scope:** только бюджет. Упаковка v1 без реестров договоров и обязательств.

## 1) Подготовка

- [ ] Sprint 4 закрыт на живом индексе (нет выдуманных сумм на золотом наборе).
- [ ] Контрольный набор файлов для репетиции согласован.

## 2) Compose и образы

- [ ] Dockerfile `mcp_server`.
- [ ] Dockerfile `assistant`.
- [ ] Способ запуска ingest из контура (`compose run` или документ).
- [ ] Сервисы `qdrant`, `mcp-server`, `assistant` в compose.
- [ ] Volume Qdrant.
- [ ] `.env.example` полный, секретов в git нет.

## 3) Здоровье и логи

- [ ] Healthcheck mcp.
- [ ] Healthcheck assistant.
- [ ] Зависимость старта от ready Qdrant.
- [ ] Понятно, как смотреть логи.

## 4) Документация

- [ ] README: подъём контура.
- [ ] README: ingest и переиндексация.
- [ ] README: как задать вопрос (CLI / `POST /chat`).
- [ ] Заметка про LM Studio / embeddings URL с хоста.

## 5) Репетиция с нуля

- [ ] `compose down -v` + up на dev.
- [ ] Ingest контрольных файлов.
- [ ] Три вопроса из золотого набора — цифры сходятся.
- [ ] Повторный ingest — число точек стабильно.
- [ ] Протокол репетиции записан.

## 6) Критерии готовности (DoD)

- [ ] Сценарий с нуля воспроизводим по README.
- [ ] Health зелёный у mcp и assistant.
- [ ] v1 можно отдавать оператору без Sprint 6.

## 7) Демо

- [ ] Живой прогон «с нуля» на встрече.
- [ ] Показать README.
- [ ] Зафиксировать known limitations v1 / Sprint 5.
