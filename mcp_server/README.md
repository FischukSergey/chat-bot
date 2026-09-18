# mcp_server

Один слой `internal/tools.Call`. Два транспорта:

```bash
task mcp                         # HTTP :7345
task mcp -- --stdio              # MCP JSON-RPC на stdin/stdout
```

```bash
curl -sf http://127.0.0.1:7345/health
curl -sf http://127.0.0.1:7345/tools/search_records \
  -H 'Content-Type: application/json' \
  -d '{"filters":{"article_code":"production:1.8.2"}}'
```

stdio (NDJSON, лог на stderr):

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"ingest_status","arguments":{}}}' \
  | task mcp -- --stdio
```

Tools: `search_records`, `budget_summary`, `ingest_status`.
Лог каждой команды: `tool`, `latency_ms`, `hits`, `error` (JSON в stderr).
Адрес HTTP: `MCP_HTTP_ADDR` (по умолчанию `127.0.0.1:7345`).
