# Sprint 5 — детальный план (упаковка v1)

Источник: `docs/PLAN.md` этап 5, `docs/sprint-4-plan.md`.

**Scope:** только бюджет. v1 без реестров договоров и обязательств.

## 1) Цель спринта

Повторяемый запуск с нуля: compose → ingest файла → вопрос → корректный ответ.
Это закрытие **v1**, не новые фичи.

К концу спринта должно быть:

- `docker compose` на qdrant + mcp + assistant (ingest — документированная команда);
- `/health` у mcp и assistant;
- volume Qdrant, понятные логи;
- README: поднять, проиндексировать, спросить, переиндексировать;
- репетиция на чистом volume.

## 2) Входные условия (что уже готово после Sprint 4)

- Ingest CLI работает.
- MCP tools сходятся с Excel.
- Ассистент отвечает по золотому набору без выдуманных сумм.

## 3) Границы Sprint 5

### Входит в Sprint 5

- единый `deploy/docker-compose.yml` (или overlay) на контур v1;
- образы / Dockerfile для `mcp_server` и `assistant`;
- healthchecks, volume, сеть docker;
- README и runbook переиндексации;
- репетиция с нуля;
- список known limitations v1.

### Не входит в Sprint 5

- HTTP-загрузка Excel, Telegram, CSV, сверка реестра со статьёй (Sprint 6);
- production-hardening (SSO, роли, публичный интернет);
- смена канона данных.

## 4) Sprint backlog (детализация задач)

## A. Образы и compose

- Dockerfile `mcp_server` (один бинарник).
- Dockerfile `assistant` (+ зависимости Python).
- Ingest: либо одноразовый сервис `profiles`, либо инструкция `docker compose run ingest`.
- Сервисы: `qdrant`, `mcp-server`, `assistant`; зависимость от healthy Qdrant.
- Volume для данных Qdrant.
- Переменные только из `.env` / `.env.example`.

## B. Наблюдаемость и здоровье

- `/health` mcp и assistant в healthcheck compose.
- Куда писать логи, как смотреть (`docker compose logs`).
- Проверка, что диск volume переживает `compose restart`.

## C. Документация запуска

- README: требования (Docker, Excel, LLM/embeddings URL).
- Шаги: `compose up` → `ingest load` → CLI или `POST /chat`.
- Как удалить источник и загрузить файл заново.
- Как подключить MCP к LM Studio / Cursor (если HTTP/stdio описаны).
- Ссылки на спринтовые планы и канон.

## D. Репетиция с нуля

- `compose down -v` (осторожно, только на dev volume).
- Поднять контур, проиндексировать контрольный файл, задать 3 вопроса из золотого набора.
- Зафиксировать время и грабли в `docs/known-limitations-sprint-5.md`.

## 5) Разбивка по дням (ориентир на 10 рабочих дней)

Дней с запасом: часть уйдёт на «не взлетает у коллеги».

### День 1

- Dockerfile mcp и assistant.
- Сеть и зависимости в compose.

### День 2

- Healthchecks, volume, `.env.example` полный.

### День 3

- `compose run ingest` (или равносильный runbook).

### День 4

- Прогон контура на своей машине end-to-end.

### День 5

- README: установка и первый вопрос.

### День 6

- Runbook переиндексации и delete-source.

### День 7

- Репетиция `down -v` + с нуля.

### День 8

- Повтор репетиции (вторая попытка / другая машина, если есть).
- Фиксы путей, прав на volume, переменных.

### День 9

- Known limitations v1, сверка ссылок в docs.

### День 10

- Демо «с нуля за N минут».
- Freeze v1.

## 6) Definition of Done (DoD) для Sprint 5

Спринт считается завершённым, если:

- с пустого volume: compose up → ingest → вопрос в CLI/`POST /chat` → ответ сходится с Excel;
- `/health` mcp и assistant зелёные;
- README достаточно, чтобы повторить без устной инструкции автора;
- секреты не закоммичены;
- v1 объявлен: Sprint 6 не блокирует релиз этого контура.

## 7) Демо-сценарий

1. `docker compose down -v` на dev.
2. `docker compose up -d` — дождаться healthy.
3. Ingest контрольного бюджета и одного реестра.
4. Три вопроса из золотого набора.
5. Показать README и `.env.example`.
6. Переиндексация того же файла — count точек тот же.

## 8) Риски Sprint 5 и меры

- Риск: LLM/embeddings снаружи compose (LM Studio на хосте).
  - Мера: в README явно `host.docker.internal` / URL; без этого assistant не «магия».

- Риск: volume стёрли вместе с индексом на демо.
  - Мера: демо-скрипт предупреждает; контрольный файл лежит у оператора.

- Риск: README отстаёт от флагов CLI.
  - Мера: репетиция по README, не по памяти.

## 9) Артефакты по итогам спринта

- полный `deploy/docker-compose.yml` + Dockerfiles;
- актуальный README и `.env.example`;
- `docs/known-limitations-sprint-5.md` (лимиты v1);
- протокол репетиции с нуля.
