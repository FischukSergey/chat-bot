# assistant

Python-оркестратор RAG: вопрос → LLM с tool calling → HTTP MCP → ответ и sources.

LLM — OpenAI-compatible (`LLM_URL`, обычно LM Studio `localhost:1234/v1`).
MCP — HTTP Sprint 3 (`POST /tools/{name}`), не stdio.

```bash
task mcp
task assistant                                          # CLI-чат
task assistant -- --ask "Какой лимит по статье production:1.8.2?"
task assistant -- serve                                 # HTTP :7346
```

`GET /health` и `POST /chat` (`question` → `answer`, `sources`, `tools_used`).
Адрес: `ASSISTANT_HTTP_ADDR` (по умолчанию `127.0.0.1:7346`).

Золотой набор: `data/eval/gold.yaml`, прогон `task assistant -- eval`
(отчёт `data/eval/last-run.yaml`).

Правила ответа — `assistant/prompts/system.md`: цифры только из tools, отказ если пусто,
факт ≠ принятые, `remain_free` не пересчитывать.

Лимит кругов tool calls: `ASSISTANT_MAX_TOOL_ROUNDS` (по умолчанию 2).
В stderr JSON-лог: `question`, `tools`, `hits`, `latency_ms`.
