# SQL Specialist

Use `agent/specialists/sql.py` with `agent/tools/sql_safety.py`, `agent/tools/postgres.py`, and `agent/tools/schema.py`.

Must:

- Validate every query before execution.
- Execute only `SELECT` or `WITH`.
- Use `business_event_date` for business-event timing.
- Use `posting_date` for accounting/ledger timing.
- Inspect schema instead of guessing table/column names.
- Log all attempts.
- Refuse only after retries or confirmed schema absence.
