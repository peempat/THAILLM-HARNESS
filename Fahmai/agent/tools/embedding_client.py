from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json

from ..config import Settings


@dataclass
class EmbeddingResponse:
    status: str
    embeddings: list[list[float]]
    model: str
    error: str | None = None
    status_code: int | None = None
    endpoint: str | None = None
    response: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "model": self.model,
            "embedding_count": len(self.embeddings),
            "dimension": len(self.embeddings[0]) if self.embeddings else 0,
            "status_code": self.status_code,
            "endpoint": self.endpoint,
            "error": self.error,
        }


class EmbeddingClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def embed(self, texts: str | list[str]) -> EmbeddingResponse:
        is_single = isinstance(texts, str)
        inputs = [texts] if is_single else list(texts)
        payload = {
            "model": self.settings.embedding_model,
            "input": inputs[0] if is_single else inputs,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            self.settings.embedding_url,
            data=data,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.settings.embedding_timeout_sec) as response:
                raw = response.read()
                status_code = response.status
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return EmbeddingResponse(
                status="http_error",
                embeddings=[],
                model=self.settings.embedding_model,
                error=body or str(exc),
                status_code=exc.code,
                endpoint=self.settings.embedding_url,
            )
        except (URLError, TimeoutError, OSError) as exc:
            return EmbeddingResponse(
                status="connection_error",
                embeddings=[],
                model=self.settings.embedding_model,
                error=str(exc),
                endpoint=self.settings.embedding_url,
            )

        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return EmbeddingResponse(
                status="parse_error",
                embeddings=[],
                model=self.settings.embedding_model,
                error=raw.decode("utf-8", errors="replace")[:500],
                status_code=status_code,
                endpoint=self.settings.embedding_url,
            )

        embeddings = []
        for item in parsed.get("data", []):
            embedding = item.get("embedding")
            if isinstance(embedding, list):
                embeddings.append([float(value) for value in embedding])
        return EmbeddingResponse(
            status="success" if embeddings else "empty",
            embeddings=embeddings,
            model=parsed.get("model") or self.settings.embedding_model,
            status_code=status_code,
            endpoint=self.settings.embedding_url,
            response=parsed,
        )
