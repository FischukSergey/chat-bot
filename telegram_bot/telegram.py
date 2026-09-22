"""Клиент Bot API: long polling getUpdates, без webhook."""

from __future__ import annotations

from typing import Any

import httpx

from telegram_bot.settings import Settings, load_settings


class TelegramError(RuntimeError):
    pass


class TelegramClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self._own_client = client is None
        timeout = self.settings.poll_timeout + 10
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> TelegramClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _url(self, method: str) -> str:
        token = self.settings.telegram_bot_token
        if not token:
            raise TelegramError("TELEGRAM_BOT_TOKEN пуст")
        return f"{self.settings.telegram_api_url}/bot{token}/{method}"

    def _call(self, method: str, payload: dict[str, Any]) -> Any:
        resp = self._client.post(self._url(method), json=payload)
        try:
            body: Any = resp.json()
        except ValueError as exc:
            raise TelegramError(f"{method}: ответ не JSON") from exc
        if resp.status_code >= 400 or not (
            isinstance(body, dict) and body.get("ok")
        ):
            desc = ""
            if isinstance(body, dict):
                desc = str(body.get("description") or body.get("error") or "")
            raise TelegramError(f"{method} HTTP {resp.status_code}: {desc}")
        return body.get("result")

    def delete_webhook(self) -> None:
        self._call("deleteWebhook", {"drop_pending_updates": False})

    def get_updates(self, offset: int | None = None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": int(self.settings.poll_timeout),
            "allowed_updates": ["message"],
        }
        if offset is not None:
            payload["offset"] = offset
        result = self._call("getUpdates", payload)
        if result is None:
            return []
        if not isinstance(result, list):
            raise TelegramError("getUpdates: ожидался список")
        return [row for row in result if isinstance(row, dict)]

    def send_message(self, chat_id: int, text: str) -> None:
        body = text.strip() or "пустой ответ"
        self._call("sendMessage", {"chat_id": chat_id, "text": body})
