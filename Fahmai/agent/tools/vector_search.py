from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math
import re

from ..config import Settings
from .embedding_client import EmbeddingClient


@dataclass
class VectorDocument:
    source: str
    title: str
    snippet: str
    embedding: list[float]


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 160) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    chunks = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + max_chars)
        chunks.append(normalized[start:end])
        if end >= len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def iter_markdown_chunks(settings: Settings, limit: int | None = None):
    roots = [settings.corpus_root / "docs", settings.corpus_root / "reports"]
    count = 0
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            title = text.splitlines()[0].strip("# ").strip() if text.splitlines() else path.stem
            for idx, chunk in enumerate(chunk_text(text)):
                count += 1
                yield {
                    "id": hashlib.sha1(f"{path}:{idx}:{chunk[:80]}".encode("utf-8")).hexdigest(),
                    "source": str(path),
                    "title": title,
                    "chunk_index": idx,
                    "snippet": chunk,
                }
                if limit and count >= limit:
                    return


def build_vector_index(settings: Settings, output_path: Path | None = None, limit: int | None = None) -> dict:
    output_path = output_path or settings.vector_index_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    client = EmbeddingClient(settings)
    batch_size = max(1, settings.embedding_batch_size)
    written = 0
    errors: list[str] = []
    batch: list[dict] = []

    with output_path.open("w", encoding="utf-8") as handle:
        for chunk in iter_markdown_chunks(settings, limit=limit):
            batch.append(chunk)
            if len(batch) < batch_size:
                continue
            count, batch_errors = _write_batch(handle, client, batch)
            written += count
            errors.extend(batch_errors)
            batch = []
            if batch_errors:
                break
        if batch and not errors:
            count, batch_errors = _write_batch(handle, client, batch)
            written += count
            errors.extend(batch_errors)

    return {
        "status": "success" if written and not errors else "error",
        "model": settings.embedding_model,
        "index_path": str(output_path),
        "written": written,
        "errors": errors,
    }


def _write_batch(handle, client: EmbeddingClient, batch: list[dict]) -> tuple[int, list[str]]:
    response = client.embed([item["snippet"] for item in batch])
    if response.status != "success":
        return 0, [response.error or response.status]
    written = 0
    for item, embedding in zip(batch, response.embeddings):
        record = dict(item)
        record["embedding"] = embedding
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        written += 1
    return written, []


class VectorSearch:
    def __init__(self, settings: Settings, index_path: Path | None = None):
        self.settings = settings
        self.index_path = index_path or settings.vector_index_path
        self.client = EmbeddingClient(settings)

    def available(self) -> bool:
        return self.index_path.exists() and self.index_path.stat().st_size > 0

    def search(self, query: str, top_k: int | None = None) -> tuple[list[dict], list[str]]:
        top_k = top_k or self.settings.vector_top_k
        if not self.available():
            return [], [f"vector index not found: {self.index_path}"]
        query_response = self.client.embed(query)
        if query_response.status != "success" or not query_response.embeddings:
            return [], [query_response.error or query_response.status]
        query_vector = query_response.embeddings[0]
        scored = []
        with self.index_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                embedding = record.get("embedding")
                if not isinstance(embedding, list):
                    continue
                score = cosine_similarity(query_vector, embedding)
                scored.append(
                    {
                        "source": record.get("source", ""),
                        "title": record.get("title", ""),
                        "snippet": record.get("snippet", ""),
                        "score": score,
                        "search_type": "vector",
                        "model": self.settings.embedding_model,
                    }
                )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k], []


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
