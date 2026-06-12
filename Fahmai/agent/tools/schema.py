from __future__ import annotations

import csv
from pathlib import Path

from ..config import Settings
from .postgres import PostgresClient


def _local_csv_schema(settings: Settings, table_or_view_name: str | None = None) -> dict:
    tables_dir = settings.corpus_root / "tables"
    tables = []
    if not tables_dir.exists():
        return {"tables": [], "views": [], "materialized_views": [], "warnings": ["tables directory not found"]}

    for csv_path in sorted(tables_dir.glob("*.csv")):
        name = csv_path.stem
        if table_or_view_name and name.lower() != table_or_view_name.lower():
            continue
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                headers = next(reader)
        except Exception as exc:
            tables.append({"name": name, "columns": [], "join_keys": [], "date_columns": [], "warning": str(exc)})
            continue

        columns = [{"name": header, "type": "unknown", "description": ""} for header in headers]
        date_columns = [h for h in headers if "date" in h.lower()]
        join_keys = []
        for header in headers:
            lower = header.lower()
            if lower.endswith("_id"):
                join_keys.append({"column": header, "references": "inspect matching DIM/FACT table"})
        tables.append(
            {
                "name": name,
                "columns": columns,
                "join_keys": join_keys,
                "date_columns": date_columns,
            }
        )

    return {"tables": tables, "views": [], "materialized_views": [], "warnings": ["schema loaded from local CSV files"]}


def get_schema_info(settings: Settings, table_or_view_name: str | None = None) -> dict:
    table_filter = ""
    if table_or_view_name:
        table_filter = f"AND lower(t.table_name) = lower('{table_or_view_name.replace(chr(39), chr(39) + chr(39))}')"
        if "." in table_or_view_name:
            table_filter = (
                "AND lower(t.table_schema || '.' || t.table_name) = "
                f"lower('{table_or_view_name.replace(chr(39), chr(39) + chr(39))}')"
            )

    sql = f"""
SELECT
  t.table_schema,
  t.table_name,
  t.table_type,
  c.column_name,
  c.data_type
FROM information_schema.tables t
JOIN information_schema.columns c
  ON c.table_schema = t.table_schema
 AND c.table_name = t.table_name
WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
  {table_filter}
ORDER BY t.table_schema, t.table_name, c.ordinal_position
""".strip()

    client = PostgresClient(settings)
    result = client.execute_select(sql)
    if result.get("status") != "success":
        fallback = _local_csv_schema(settings, table_or_view_name)
        fallback["warnings"].append(f"database schema inspection failed: {result.get('error') or result.get('warnings')}")
        return fallback

    tables_by_name: dict[str, dict] = {}
    views_by_name: dict[str, dict] = {}
    for row in result.get("rows", []):
        schema_name = row["table_schema"]
        relation_name = row["table_name"]
        name = f"{schema_name}.{relation_name}"
        target = views_by_name if row.get("table_type") == "VIEW" else tables_by_name
        entry = target.setdefault(
            name,
            {
                "name": name,
                "schema": schema_name,
                "relation": relation_name,
                "columns": [],
                "join_keys": [],
                "date_columns": [],
            },
        )
        column_name = row["column_name"]
        entry["columns"].append(
            {
                "name": column_name,
                "type": row["data_type"],
                "description": "",
            }
        )
        if "date" in column_name.lower():
            entry["date_columns"].append(column_name)
        if column_name.lower().endswith("_id"):
            entry["join_keys"].append({"column": column_name, "references": "inspect matching DIM/FACT table"})

    return {
        "tables": list(tables_by_name.values()),
        "views": list(views_by_name.values()),
        "materialized_views": [],
        "warnings": [],
    }


def write_schema_cache(settings: Settings, output_path: Path, table: str | None = None) -> dict:
    schema = get_schema_info(settings, table)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    import json

    output_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    return schema
