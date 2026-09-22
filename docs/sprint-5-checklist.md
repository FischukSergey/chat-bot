# Sprint 5 Checklist

Источник: `docs/sprint-5-plan.md`.

**Статус:** закрыт 2026-09-19. Контур v1 в compose, репетиция с нуля,
README, known limitations. Sprint 6 не блокирует этот релиз.

**Scope:** только бюджет. Упаковка v1 без реестров договоров и обязательств.

## 1) Подготовка

- [x] Sprint 4 закрыт на живом индексе (нет выдуманных сумм на золотом наборе).
- [x] Контрольный набор файлов для репетиции согласован.

Проверка (2026-09-19): Sprint 4 закрыт, чек-лист
[`docs/sprint-4-checklist.md`](sprint-4-checklist.md). Живой прогон
[`data/eval/last-run.md`](../data/eval/last-run.md): **22 pass / 3 fail / 25**.
На PASS нет выдуманных сумм; факт / принятые / `remain_free` не подменялись
лимитом. Провалы записаны (`branch-1.8`, `cross-rent-pipes`, `refuse-quantum`).

Контрольный файл репетиции v1 (только бюджет, без реестров):

- `data/incoming/БДР для индексации.xlsx` — тот же источник, что
  [`data/eval/gold.yaml`](../data/eval/gold.yaml) (лист «Смета затрат»,
  172 листа в `budget_items`).

Не входят: договоры / обязательства (выгрузок нет);
`Бизнес-план ООО «ПетербургГаз» на 2026 год.xlsx` — не маппинг сметы
и не эталон золотого набора.

Три вопроса репетиции (шаг 5) — из золотого набора, не новые:

1. `code-1.8.2` — лимит `production:1.8.2` = 124970.30
2. `refuse-9.9.9` — отказ без сумм
3. `code-5.1.1.1` — лимит 681351.76 (узкий код, не ветка-родитель)

## 2) Compose и образы

- [x] Dockerfile `mcp_server`.
- [x] Dockerfile `assistant`.
- [x] Способ запуска ingest из контура (`compose run` или документ).
- [x] Сервисы `qdrant`, `mcp-server`, `assistant` в compose.
- [x] Volume Qdrant.
- [x] `.env.example` полный, секретов в git нет.

Проверка (2026-09-19): `task local:build` собрал `chat-bot-mcp:local` и
`chat-bot-assistant:local`. Compose: `qdrant`, `mcp-server`, `assistant`,
профиль `ingest` (тот же Python-образ). Volume `qdrant-data`.
Ingest: `task local:ingest` или `task local:ingest -- load FILE`.
`.env` в gitignore. В контейнерах Qdrant/MCP — имена сервисов; LM Studio
на хосте через `EMBEDDINGS_URL_DOCKER` / `LLM_URL_DOCKER`
(`host.docker.internal`). Порты `:7345`/`:7346` не делить с хостовыми
`task mcp` / `task assistant`. Healthcheck mcp/assistant — пункт 3.

## 3) Здоровье и логи

- [x] Healthcheck mcp.
- [x] Healthcheck assistant.
- [x] Зависимость старта от ready Qdrant.
- [x] Понятно, как смотреть логи.

Проверка (2026-09-19): `task local:up --wait` — все три `(healthy)`.
`GET :7345/health` → ok, 172 точки, embeddings ok.
`GET :7346/health` → ok, mcp ok, llm ok.
Порядок: Qdrant healthy → mcp → assistant.
Пустая коллекция не валит `/health` mcp (`points: 0`).
Логи json-file, ротация 10m×3:

```bash
task local:ps
task local:logs
task local:logs:service -- mcp-server
```

## 4) Документация

- [x] README: подъём контура.
- [x] README: ingest и переиндексация.
- [x] README: как задать вопрос (CLI / `POST /chat`).
- [x] Заметка про LM Studio / embeddings URL с хоста.

Проверка (2026-09-19): корневой [README.md](../README.md) — v1 только смета.
`task local:up` → health → `local:ingest` / `delete-source` →
`POST /chat` и `task assistant -- --ask`.
LM Studio на хосте: `127.0.0.1:1234` с хоста,
`host.docker.internal` из контейнера (`*_URL_DOCKER`).
stdio MCP — опционально, не замена чата.

## 5) Репетиция с нуля

- [x] `compose down -v` + up на dev.
- [x] Ingest контрольных файлов.
- [x] Три вопроса из золотого набора — цифры сходятся.
- [x] Повторный ingest — число точек стабильно.
- [x] Протокол репетиции записан.

Проверка (2026-09-19): по README.
`task local:down:clean` → `task local:up` (healthy, `points: 0`) →
`task local:ingest` (172 принято) → `POST /chat`:
`code-1.8.2` 124970.30 row 23; `refuse-9.9.9` отказ без сумм;
`code-5.1.1.1` 681351.76 row 66.
Повторный ingest: 0 принято / 172 обновлено, точек **172**.
Протокол: [`docs/sprint-5-rehearsal.md`](sprint-5-rehearsal.md).
Лимиты v1: [`docs/known-limitations-sprint-5.md`](known-limitations-sprint-5.md).

## 6) Критерии готовности (DoD)

- [x] Сценарий с нуля воспроизводим по README.
- [x] Health зелёный у mcp и assistant.
- [x] v1 можно отдавать оператору без Sprint 6.

Проверка (2026-09-19). Пустой volume → `task local:up` → `task local:ingest`
→ `POST /chat` — цифры Excel (`docs/sprint-5-rehearsal.md`).
`GET :7345/health` и `:7346/health` — ok, 172 точки.
README: подъём, ingest, вопрос, LM Studio на хосте.
`.env` в gitignore, в индексе нет. Sprint 6 (Telegram, HTTP-upload)
не требуется, чтобы отдать этот контур оператору.

## 7) Демо

- [x] Живой прогон «с нуля» на встрече.
- [x] Показать README.
- [x] Зафиксировать known limitations v1 / Sprint 5.

Демо-сценарий прогнан 2026-09-19 как репетиция пункта 5
(отдельная встреча не нужна: те же шаги, протокол в
[`docs/sprint-5-rehearsal.md`](sprint-5-rehearsal.md)):

1. `task local:down:clean` (не сырой `docker compose down -v`).
2. `task local:up` — healthy.
3. Ingest только сметы (реестра нет).
4. Три вопроса золотого набора через `POST /chat`.
5. README и `.env.example`.
6. Повторный ingest — 172 точки.

Лимиты: [`docs/known-limitations-sprint-5.md`](known-limitations-sprint-5.md).
Реестр в демо не грузили — scope v1.
