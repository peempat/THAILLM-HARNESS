from __future__ import annotations

from ..config import Settings
from ..tools.markdown_search import MarkdownKeywordSearch, evaluate_result_quality
from ..tools.vector_search import VectorSearch


class RAGSpecialist:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.searcher = MarkdownKeywordSearch(settings)
        self.vector_searcher = VectorSearch(settings)

    @staticmethod
    def _queries(question: str, hints: dict) -> list[str]:
        stopwords = {
            "what",
            "did",
            "say",
            "about",
            "the",
            "and",
            "for",
            "with",
            "มี",
            "คือ",
            "อะไร",
        }
        queries: list[str] = []
        for value in hints.get("exact_ids", []) or []:
            if value and value not in queries:
                queries.append(str(value))

        primary_terms = [
            str(value)
            for value in (hints.get("primary_terms", []) or [])
            if str(value).lower() not in stopwords and len(str(value)) >= 3
        ]
        if primary_terms:
            compound = " ".join(primary_terms[:6])
            if compound not in queries:
                queries.append(compound)

        for key in ("aliases",):
            for value in hints.get(key, []) or []:
                if value and value not in queries:
                    queries.append(str(value))
        if question not in queries:
            queries.append(question)
        for exact_id in hints.get("exact_ids", []) or []:
            spaced = str(exact_id).replace("-", " ")
            if spaced not in queries:
                queries.append(spaced)
        return queries

    def run(self, subtask: dict, normalized: dict) -> dict:
        hints = subtask.get("retrieval_hints", {})
        question = normalized.get("normalized_question", "")
        max_retries = int(hints.get("max_retries") or self.settings.max_retries)
        queries = self._queries(question, hints)
        attempts = []
        best_results: list[dict] = []

        for attempt in range(1, max_retries + 1):
            query = queries[attempt - 1] if attempt - 1 < len(queries) else question
            keyword_results = self.searcher.search(query, top_k=self.settings.keyword_top_k)
            vector_results, vector_warnings = self.vector_searcher.search(query, top_k=self.settings.vector_top_k)
            results = self._merge_results(keyword_results, vector_results)
            quality, reason = evaluate_result_quality(
                query,
                results,
                exact_ids=hints.get("exact_ids", []),
                date_range=hints.get("date_range"),
            )
            if vector_warnings and not vector_results:
                reason = f"{reason}; vector: {vector_warnings[0]}"
            attempts.append(
                {
                    "attempt": attempt,
                    "query": query,
                    "search_type": "hybrid_vector_keyword",
                    "result_count": len(results),
                    "keyword_count": len(keyword_results),
                    "vector_count": len(vector_results),
                    "quality": quality,
                    "reason": reason,
                }
            )
            if results and (not best_results or results[0].get("score", 0) > best_results[0].get("score", 0)):
                best_results = results
            if quality in {"strong", "medium"}:
                evidence = [
                    {
                        "source": result["source"],
                        "claim": result["snippet"],
                        "value": None,
                        "score": result["score"],
                    }
                    for result in results
                ]
                return {
                    "specialist": "rag",
                    "status": "success",
                    "max_retries": max_retries,
                    "attempts": attempts,
                    "evidence": evidence,
                    "summary": results[0]["snippet"] if results else "",
                    "refusal_topic": None,
                    "warnings": [],
                }

        return {
            "specialist": "rag",
            "status": "no_data",
            "max_retries": max_retries,
            "attempts": attempts,
            "evidence": [],
            "summary": "",
            "refusal_topic": question,
            "warnings": ["retrieval exhausted after max_retries"],
            "debug_best_results": best_results[:3],
        }

    @staticmethod
    def _merge_results(keyword_results: list[dict], vector_results: list[dict]) -> list[dict]:
        by_source: dict[str, dict] = {}
        for result in vector_results:
            key = f"{result.get('source')}::{result.get('snippet', '')[:120]}"
            item = dict(result)
            item["score"] = float(item.get("score", 0)) * 10
            by_source[key] = item
        for result in keyword_results:
            key = f"{result.get('source')}::{result.get('snippet', '')[:120]}"
            if key in by_source:
                by_source[key]["score"] = float(by_source[key].get("score", 0)) + float(result.get("score", 0))
                by_source[key]["search_type"] = "hybrid"
            else:
                item = dict(result)
                item["search_type"] = "keyword"
                by_source[key] = item
        merged = list(by_source.values())
        merged.sort(key=lambda item: float(item.get("score", 0)), reverse=True)
        return merged
