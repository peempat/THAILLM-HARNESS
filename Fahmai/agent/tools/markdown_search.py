from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import shutil
import subprocess

from ..config import Settings
from ..hooks import retrieval_dedup_hook


TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+|[\u0E00-\u0E7F]+")


@dataclass
class SearchResult:
    source: str
    score: float
    snippet: str
    title: str

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "score": self.score,
            "snippet": self.snippet,
            "title": self.title,
        }


class MarkdownKeywordSearch:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.roots = [
            settings.corpus_root / "docs",
            settings.corpus_root / "reports",
        ]

    def _files(self):
        for root in self.roots:
            if not root.exists():
                continue
            yield from root.rglob("*.md")

    @staticmethod
    def _tokens(query: str) -> list[str]:
        return [t.lower() for t in TOKEN_RE.findall(query) if len(t.strip()) >= 2]

    @staticmethod
    def _snippet(text: str, query: str, tokens: list[str], width: int = 360) -> str:
        lowered = text.lower()
        candidates = [query.lower()] + tokens
        positions = [lowered.find(c) for c in candidates if c and lowered.find(c) >= 0]
        pos = min(positions) if positions else 0
        start = max(0, pos - width // 2)
        end = min(len(text), start + width)
        return " ".join(text[start:end].split())

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        top_k = top_k or self.settings.keyword_top_k
        query = query.strip()
        if not query:
            return []

        tokens = self._tokens(query)
        phrase = query.lower()
        scored: list[SearchResult] = []

        # Fast path: exact IDs commonly appear in filenames or source paths.
        for path in self._files():
            filename = path.name.lower()
            source = str(path).lower()
            path_score = 0.0
            if phrase and phrase in filename:
                path_score += 12.0
            elif phrase and phrase in source:
                path_score += 10.0
            for token in tokens:
                if token in filename:
                    path_score += 1.5
            if path_score <= 0:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            title = text.splitlines()[0].strip("# ").strip() if text.splitlines() else path.stem
            scored.append(
                SearchResult(
                    source=str(path),
                    score=path_score,
                    snippet=self._snippet(text, query, tokens),
                    title=title,
                )
            )

        if scored:
            scored.sort(key=lambda item: item.score, reverse=True)
            return retrieval_dedup_hook([item.to_dict() for item in scored[:top_k]])

        rg_results = self._ripgrep_search(query, tokens, top_k)
        if rg_results:
            return retrieval_dedup_hook([item.to_dict() for item in rg_results[:top_k]])

        # Fallback for machines without ripgrep. This is intentionally last
        # because the corpus contains tens of thousands of markdown files.
        for path in self._files():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            lowered = text.lower()
            filename = path.name.lower()
            score = 0.0
            if phrase and phrase in lowered:
                score += 10.0
            if phrase and phrase in filename:
                score += 8.0
            for token in tokens:
                if token in lowered:
                    score += 2.0
                if token in filename:
                    score += 1.5
            if score <= 0:
                continue
            title = text.splitlines()[0].strip("# ").strip() if text.splitlines() else path.stem
            scored.append(
                SearchResult(
                    source=str(path),
                    score=score,
                    snippet=self._snippet(text, query, tokens),
                    title=title,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return retrieval_dedup_hook([item.to_dict() for item in scored[:top_k]])

    def _ripgrep_search(self, query: str, tokens: list[str], top_k: int) -> list[SearchResult]:
        if not shutil.which("rg"):
            return []
        roots = [str(root) for root in self.roots if root.exists()]
        if not roots:
            return []
        cmd = [
            "rg",
            "--json",
            "--ignore-case",
            "--fixed-strings",
            "--max-count",
            "3",
            query,
            *roots,
        ]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
        except Exception:
            return []

        by_path: dict[str, SearchResult] = {}
        for line in completed.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "match":
                continue
            data = event.get("data", {})
            path = data.get("path", {}).get("text")
            lines = data.get("lines", {}).get("text", "")
            if not path:
                continue
            source_lower = path.lower()
            score = 10.0 if query.lower() in lines.lower() else 5.0
            for token in tokens:
                if token in source_lower:
                    score += 1.5
            current = by_path.get(path)
            snippet = " ".join(lines.split())
            if current:
                current.score += score
                if snippet and snippet not in current.snippet:
                    current.snippet = f"{current.snippet} {snippet}"[:720]
            else:
                by_path[path] = SearchResult(
                    source=path,
                    score=score,
                    snippet=snippet,
                    title=Path(path).stem,
                )
        results = list(by_path.values())
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]


def evaluate_result_quality(
    query: str,
    results: list[dict],
    exact_ids: list[str] | None = None,
    date_range: dict | None = None,
) -> tuple[str, str]:
    if not results:
        return "none", "no results"

    exact_ids = [x.lower() for x in (exact_ids or [])]
    combined = "\n".join((r.get("source", "") + "\n" + r.get("snippet", "")).lower() for r in results)
    has_exact_id = bool(exact_ids and any(x in combined for x in exact_ids))
    has_query = query.lower() in combined
    score = max(float(r.get("score", 0)) for r in results)

    if date_range:
        start = date_range.get("start")
        end = date_range.get("end")
        if start and start[:4] not in combined and end and end[:4] not in combined:
            if not has_exact_id:
                return "weak", "results do not show requested date window"

    if has_exact_id:
        return "strong", "direct exact ID match"
    if has_query and score >= 10:
        return "strong", "direct query phrase match"
    if score >= 6:
        return "medium", "multiple keyword matches"
    return "weak", "low keyword overlap"
