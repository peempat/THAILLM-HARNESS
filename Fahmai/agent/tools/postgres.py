from __future__ import annotations

from typing import Any
import re

from ..config import Settings
from .sql_safety import validate_sql


class PostgresUnavailable(RuntimeError):
    pass


def _import_driver():
    try:
        import psycopg

        return "psycopg", psycopg
    except Exception:
        try:
            import psycopg2
            import psycopg2.extras

            return "psycopg2", psycopg2
        except Exception as exc:
            raise PostgresUnavailable(
                "Install psycopg with: python -m pip install -r requirements.txt"
            ) from exc


class PostgresClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def execute_select(self, sql: str, params: tuple[Any, ...] | None = None) -> dict:
        ok, warnings = validate_sql(sql)
        if not ok:
            return {
                "status": "blocked",
                "rows": [],
                "row_count": 0,
                "warnings": warnings,
            }

        try:
            driver_name, driver = _import_driver()
        except PostgresUnavailable as exc:
            return {
                "status": "unavailable",
                "error": str(exc),
                "rows": [],
                "row_count": 0,
                "warnings": [str(exc)],
            }

        timeout_ms = self.settings.query_timeout_sec * 1000
        search_path = self._safe_search_path(self.settings.db_search_path)

        try:
            if driver_name == "psycopg":
                with driver.connect(
                    self.settings.database_url,
                    connect_timeout=10,
                    prepare_threshold=None,
                ) as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"SET LOCAL statement_timeout = {int(timeout_ms)}")
                        if search_path:
                            cur.execute(f"SET LOCAL search_path = {search_path}")
                        cur.execute(sql, params)
                        columns = [d.name for d in cur.description] if cur.description else []
                        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
            else:
                with driver.connect(
                    host=self.settings.db_host,
                    port=self.settings.db_port,
                    dbname=self.settings.db_name,
                    user=self.settings.db_user,
                    password=self.settings.db_password,
                    sslmode=self.settings.db_sslmode,
                    connect_timeout=10,
                ) as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"SET LOCAL statement_timeout = {int(timeout_ms)}")
                        if search_path:
                            cur.execute(f"SET LOCAL search_path = {search_path}")
                        cur.execute(sql, params)
                        columns = [d[0] for d in cur.description] if cur.description else []
                        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        except Exception as exc:
            message = str(exc)
            status = "timeout" if "timeout" in message.lower() else "error"
            return {
                "status": status,
                "error": message,
                "rows": [],
                "row_count": 0,
                "warnings": [],
            }

        return {
            "status": "success",
            "rows": rows,
            "row_count": len(rows),
            "warnings": [],
        }

    @staticmethod
    def _safe_search_path(value: str) -> str:
        schemas = []
        for raw_schema in value.split(","):
            schema = raw_schema.strip()
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", schema):
                schemas.append(schema)
        return ", ".join(schemas)
