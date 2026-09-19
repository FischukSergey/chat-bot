"""HTTP: GET /health и POST /chat."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from assistant.app import App

CHAT_BODY_MAX = 1 << 20


def dispatch(app: App, method: str, path: str, raw: bytes) -> tuple[int, dict[str, Any]]:
    if method == "GET" and path == "/health":
        return app.health()
    if method == "POST" and path == "/chat":
        return handle_chat(app, raw)
    return 404, {"error": "not_found", "message": "только GET /health и POST /chat"}


def handle_chat(app: App, raw: bytes) -> tuple[int, dict[str, Any]]:
    if len(raw) > CHAT_BODY_MAX:
        return 400, {"error": "validation", "message": "слишком большое тело"}
    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 400, {"error": "validation", "message": "ожидался JSON"}
    if not isinstance(data, dict):
        return 400, {"error": "validation", "message": "ожидался объект"}
    question = data.get("question")
    if not isinstance(question, str) or not question.strip():
        return 400, {"error": "validation", "message": "нужен непустой question"}
    extra = set(data) - {"question"}
    if extra:
        return 400, {"error": "validation", "message": f"неизвестные поля: {sorted(extra)}"}
    try:
        result = app.ask(question)
    except Exception as exc:
        return 502, {"error": "error", "message": str(exc)}
    return 200, {
        "answer": result.answer,
        "sources": result.sources,
        "tools_used": result.tools_used,
    }


def serve(app: App, addr: str) -> None:
    host, _, port_s = addr.rpartition(":")
    if not host or not port_s.isdigit():
        raise ValueError(f"некорректный ASSISTANT_HTTP_ADDR: {addr}")
    httpd = ThreadingHTTPServer((host, int(port_s)), _handler(app))
    print(f"assistant HTTP {addr}  GET /health  POST /chat", file=sys.stderr, flush=True)
    httpd.serve_forever()


def _handler(app: App) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            self._dispatch()

        def do_POST(self) -> None:
            self._dispatch()

        def _dispatch(self) -> None:
            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length > 0 else b""
            code, body = dispatch(app, self.command, path, raw)
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler
