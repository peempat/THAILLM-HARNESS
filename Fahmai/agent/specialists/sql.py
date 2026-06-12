from __future__ import annotations

from ..config import Settings
from ..tools.postgres import PostgresClient
from ..tools.sql_safety import validate_sql


class SQLSpecialist:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = PostgresClient(settings)

    def run(
        self,
        subtask: dict,
        normalized: dict,
        candidate_sqls: list[str] | None = None,
    ) -> dict:
        attempts = []
        candidate_sqls = candidate_sqls or []
        if not candidate_sqls:
            return {
                "specialist": "sql",
                "status": "needs_sql",
                "attempts": [],
                "queries": [],
                "rows": [],
                "summary": "SQL specialist is ready; provide candidate SQL from planner/LLM to execute.",
                "evidence": [],
                "refusal_topic": None,
                "warnings": ["no candidate_sqls provided"],
            }

        rows = []
        queries = []
        tool_errors = []
        for index, sql in enumerate(candidate_sqls[: self.settings.max_sql_retries], start=1):
            ok, safety_warnings = validate_sql(sql)
            if not ok:
                attempts.append(
                    {
                        "attempt": index,
                        "sql": sql,
                        "purpose": "Validate read-only SQL before execution",
                        "result_status": "blocked",
                        "row_count": 0,
                        "quality": "none",
                        "reason": "; ".join(safety_warnings),
                    }
                )
                continue

            result = self.client.execute_select(sql)
            result_status = result.get("status", "error")
            row_count = result.get("row_count", 0)
            quality = "strong" if result_status == "success" and row_count > 0 else "none"
            reason = "query returned rows" if quality == "strong" else result.get("error") or "query returned no rows"
            if result_status in {"unavailable", "error", "timeout"}:
                tool_errors.append(reason)
            attempts.append(
                {
                    "attempt": index,
                    "sql": sql,
                    "purpose": "Execute read-only SQL candidate",
                    "result_status": "success" if quality == "strong" else result_status,
                    "row_count": row_count,
                    "quality": quality,
                    "reason": reason,
                }
            )
            queries.append(sql)
            if quality == "strong":
                rows = result.get("rows", [])
                break

        if rows:
            return {
                "specialist": "sql",
                "status": "success",
                "attempts": attempts,
                "queries": queries,
                "rows": rows,
                "summary": f"SQL returned {len(rows)} row(s).",
                "evidence": [
                    {
                        "source": "postgres",
                        "table_or_view": ",".join(subtask.get("sql_hints", {}).get("primary_tables_or_views", [])),
                        "claim": "query result",
                        "value": rows,
                    }
                ],
                "refusal_topic": None,
                "warnings": [],
            }

        if tool_errors:
            return {
                "specialist": "sql",
                "status": "error",
                "attempts": attempts,
                "queries": queries,
                "rows": [],
                "summary": "",
                "evidence": [],
                "refusal_topic": None,
                "warnings": tool_errors,
            }

        return {
            "specialist": "sql",
            "status": "no_data",
            "attempts": attempts,
            "queries": queries,
            "rows": [],
            "summary": "",
            "evidence": [],
            "refusal_topic": normalized.get("normalized_question"),
            "warnings": ["SQL exhausted or returned no usable rows"],
        }
