# Schema Inspection Tool

## Purpose

Ground SQL retries in confirmed schema.

## Output

```json
{
  "tables": [
    {
      "name": "fact_sales",
      "columns": [{"name": "sku_id", "type": "text", "description": ""}],
      "join_keys": [{"column": "sku_id", "references": "dim_product.sku_id"}],
      "date_columns": ["business_event_date", "posting_date"]
    }
  ],
  "views": [],
  "materialized_views": []
}
```

## Python

```python
from agent.config import Settings
from agent.tools.schema import get_schema_info

schema = get_schema_info(Settings.from_env(), "dim_product")
```
