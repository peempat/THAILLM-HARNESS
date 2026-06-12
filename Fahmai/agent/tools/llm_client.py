from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json

from ..config import Settings
from .local_agent import LocalAgentClient


@dataclass
class LLMResponse:
    status: str
    provider: str
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
            "provider": self.provider,
            "status_code": self.status_code,
            "endpoint": self.endpoint,
            "error": self.error,
            "text": self.text,
            "response": self.response,
        }


class LLMClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        model: str | None = None,
    ) -> LLMResponse:
        provider = self.settings.llm_provider.lower().strip()
        if provider in {"local", "modelharbor"}:
            local = LocalAgentClient(self.settings).chat(messages, max_tokens, temperature, model)
            return LLMResponse(
                status=local.status,
                provider="local",
                response=local.response,
                error=local.error,
                status_code=local.status_code,
                endpoint=local.endpoint,
            )
        return self._openai_compatible_chat(messages, max_tokens, temperature, model)

    def _openai_compatible_chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None,
        temperature: float | None,
        model: str | None,
    ) -> LLMResponse:
        provider = self.settings.llm_provider.lower().strip()
        key_required = provider not in {"gemma_local", "openai_local", "vllm", "sglang"}
        if key_required and not self.settings.llm_api_key:
            return LLMResponse(
                status="config_error",
                provider=self.settings.llm_provider,
                error="FAHMAI_LLM_API_KEY or OPENTYPHOON_API_KEY is not set",
                endpoint=self.settings.llm_chat_url,
            )

        payload = {
            "model": model or self.settings.llm_model,
            "messages": messages,
            "max_tokens": max_tokens or self.settings.llm_max_tokens,
            "temperature": self.settings.llm_temperature if temperature is None else temperature,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"
        request = Request(self.settings.llm_chat_url, data=data, method="POST", headers=headers)
        try:
            with urlopen(request, timeout=self.settings.llm_timeout_sec) as response:
                raw = response.read()
                status_code = response.status
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return LLMResponse(
                status="http_error",
                provider=self.settings.llm_provider,
                error=body or str(exc),
                status_code=exc.code,
                endpoint=self.settings.llm_chat_url,
            )
        except (URLError, TimeoutError, OSError) as exc:
            return LLMResponse(
                status="connection_error",
                provider=self.settings.llm_provider,
                error=str(exc),
                endpoint=self.settings.llm_chat_url,
            )

        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            parsed = {"raw": raw.decode("utf-8", errors="replace")}
        return LLMResponse(
            status="success",
            provider=self.settings.llm_provider,
            response=parsed,
            status_code=status_code,
            endpoint=self.settings.llm_chat_url,
        )
