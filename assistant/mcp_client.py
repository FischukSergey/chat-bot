"""HTTP-клиент к MCP Sprint 3: GET /health и POST /tools/{name}."""

from __future__ import annotations

from typing import Any

import httpx

from assistant.settings import Settings, load_settings

ALLOWED_TOOLS = frozenset({"search_records", "budget_summary", "ingest_status"})


class MCPError(RuntimeError):
    def __init__(self, status: int, kind: str, message: str) -> None:
        super().__init__(f"{kind}: {message}")
        self.status = status
        self.kind = kind
        self.message = message

    def as_payload(self) -> dict[str, str]:
        return {"error": self.kind, "message": self.message}


class MCPClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self._own_client = client is None
        self._client = client or httpx.Client(timeout=self.settings.mcp_timeout)

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> MCPClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def health(self) -> dict[str, Any]:
        resp = self._client.get(f"{self.settings.mcp_url}/health")
        resp.raise_for_status()
        body = resp.json()
        if not isinstance(body, dict):
            raise MCPError(resp.status_code, "error", "health: ожидался объект")
        return body

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        if name not in ALLOWED_TOOLS:
            raise MCPError(404, "not_found", f'tool "{name}" не реализован')
        resp = self._client.post(
            f"{self.settings.mcp_url}/tools/{name}",
            json=arguments or {},
        )
        try:
            body: Any = resp.json()
        except ValueError:
            body = {"error": "error", "message": resp.text[:300]}
        if resp.status_code >= 400:
            kind = "error"
            message = resp.text[:300]
            if isinstance(body, dict):
                kind = str(body.get("error") or kind)
                message = str(body.get("message") or message)
            raise MCPError(resp.status_code, kind, message)
        return body
