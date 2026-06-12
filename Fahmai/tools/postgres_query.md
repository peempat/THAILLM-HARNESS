# PostgreSQL Query Tool

## Purpose

Execute safe read-only SQL against FahMai PostgreSQL.

## Config

Loaded from `Fahmai/.env`:

- host: `0.tcp.ap.ngrok.io`
- port: `26551`
- database: `fahmai`
- user: `fahmai_app`
- sslmode: `disable`

## Python

```python
from agent.config import Settings
from agent.tools.postgres import PostgresClient

settings = Settings.from_env()
client = PostgresClient(settings)
result = client.execute_select("SELECT * FROM dim_product LIMIT 5")
```
