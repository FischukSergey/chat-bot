"""Сборка оркестратора: один MCP + LLM на сессию CLI/HTTP."""

from __future__ import annotations

from typing import Any

from assistant.llm import LLMClient
from assistant.log import log_chat
from assistant.mcp_client import MCPClient
from assistant.orchestrator import ChatResult, Completer, Orchestrator, ToolRunner
from assistant.settings import Settings, load_settings


class App:
    def __init__(
        self,
        settings: Settings,
        mcp: ToolRunner,
        llm: Completer,
        *,
        own_clients: bool = False,
    ) -> None:
        self.settings = settings
        self.mcp = mcp
        self.llm = llm
        self._own_clients = own_clients
        self.orch = Orchestrator(settings, mcp, llm)

    @classmethod
    def open(cls, settings: Settings | None = None) -> App:
        cfg = settings or load_settings()
        return cls(cfg, MCPClient(cfg), LLMClient(cfg), own_clients=True)

    def close(self) -> None:
        if not self._own_clients:
            return
        for client in (self.mcp, self.llm):
            closer = getattr(client, "close", None)
            if closer is not None:
                closer()

    def __enter__(self) -> App:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def ask(self, question: str) -> ChatResult:
        error = ""
        try:
            result = self.orch.ask(question)
        except Exception as exc:
            error = str(exc)
            log_chat(
                question=question,
                tools=[],
                hits=0,
                latency_ms=0,
                rounds=0,
                error=error,
            )
            raise
        log_chat(
            question=question,
            tools=result.tools_used,
            hits=result.hits,
            latency_ms=result.latency_ms,
            rounds=result.rounds,
            error=error,
        )
        return result

    def health(self) -> tuple[int, dict[str, Any]]:
        body: dict[str, Any] = {
            "status": "ok",
            "mcp": "ok",
            "llm": "ok",
            "llm_model": self.settings.llm_model,
            "mcp_url": self.settings.mcp_url,
        }
        code = 200
        health_fn = getattr(self.mcp, "health", None)
        if health_fn is None:
            body["mcp"] = "error"
            body["status"] = "error"
            body["error"] = "mcp health недоступен"
            code = 503
        else:
            try:
                mcp = health_fn()
                if isinstance(mcp, dict):
                    if mcp.get("status") and mcp.get("status") != "ok":
                        body["mcp"] = "error"
                        body["status"] = "error"
                        code = 503
                    if "points" in mcp:
                        body["points"] = mcp["points"]
            except Exception as exc:
                body["mcp"] = "error"
                body["status"] = "error"
                body["error"] = str(exc)
                code = 503
        models_fn = getattr(self.llm, "models", None)
        if models_fn is None:
            body["llm"] = "error"
            body["status"] = "error"
            if "error" not in body:
                body["error"] = "llm models недоступен"
            code = 503
        else:
            try:
                models = models_fn()
                body["llm_models"] = models
            except Exception as exc:
                body["llm"] = "error"
                body["status"] = "error"
                if "error" not in body:
                    body["error"] = str(exc)
                code = 503
        return code, body
