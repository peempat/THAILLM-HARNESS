# sql_safety_hook

## Purpose

Validate SQL before execution.

## Rules

- Allow only `SELECT` or `WITH`.
- Block semicolon chaining.
- Block comments containing suspicious instructions.
- Block write operations.
- Block system/file/network functions.
- Enforce timeout in the PostgreSQL client.

## Python

```python
from agent.tools.sql_safety import validate_sql

ok, warnings = validate_sql("SELECT * FROM dim_product LIMIT 5")
```
