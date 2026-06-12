from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen
import json

from ..config import Settings


class LocalAgentError(RuntimeError):
    pass


@dataclass
class LocalAgentResponse:
    status: str
    response: dict[str, Any] | None = None
    error: str | None = None
    status_code: int | None = None
    endpoint: str | None = None

    @property
    def text(self) -> str:
        if not self.response:
            return ""
        choices = self.response.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        content = message.get("content")
        return content if isinstance(content, str) else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "status_code": self.status_code,
            "endpoint": self.endpoint,
            "error": self.error,
            "response": self.response,
            "text": self.text,
        }


class LocalAgentClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def health(self) -> dict[str, Any]:
        result = self._request_json("GET", self.settings.local_health_url, None)
        return {
            "ok": result.status in {"success", "empty_success"},
            "status": result.status,
            "status_code": result.status_code,
            "endpoint": result.endpoint,
            "error": result.error,
            "response": result.response,
        }

    def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        model: str | None = None,
    ) -> LocalAgentResponse:
        max_tokens = max_tokens or self.settings.local_max_tokens
        temperature = self.settings.local_temperature if temperature is None else temperature
        model = model or self.settings.local_model

        primary_payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        primary = self._request_json("POST", self.settings.local_agent_url, primary_payload)
        if primary.status == "success":
            return primary

        fallback_url = self._v1_chat_url(self.settings.local_agent_url)
        if fallback_url != self.settings.local_agent_url:
            fallback_payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            fallback = self._request_json("POST", fallback_url, fallback_payload)
            if fallback.status == "success":
                return fallback
            fallback.error = f"primary failed: {primary.error}; fallback failed: {fallback.error}"
            return fallback

        return primary

    def _request_json(self, method: str, url: str, payload: dict[str, Any] | None) -> LocalAgentResponse:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.settings.local_timeout_sec) as response:
                raw = response.read()
                status_code = response.status
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return LocalAgentResponse(
                status="http_error",
                error=body or str(exc),
                status_code=exc.code,
                endpoint=url,
            )
        except (URLError, TimeoutError, OSError) as exc:
            return LocalAgentResponse(status="connection_error", error=str(exc), endpoint=url)

        if not raw:
            return LocalAgentResponse(status="empty_success", response={}, status_code=status_code, endpoint=url)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            parsed = {"raw": raw.decode("utf-8", errors="replace")}
        return LocalAgentResponse(status="success", response=parsed, status_code=status_code, endpoint=url)

    @staticmethod
    def _v1_chat_url(primary_url: str) -> str:
        parsed = urlparse(primary_url)
        return urlunparse((parsed.scheme, parsed.netloc, "/v1/chat/completions", "", "", ""))
