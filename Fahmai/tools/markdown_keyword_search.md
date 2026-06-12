# Markdown Keyword Search Tool

## Purpose

Search trusted FahMai markdown corpus under `docs/` and `reports/`.

## Quality

- `strong`: direct exact ID or phrase match.
- `medium`: multiple keyword matches.
- `weak`: tangential or low-overlap result.
- `none`: no result.

## Python

```python
from agent.config import Settings
from agent.tools.markdown_search import MarkdownKeywordSearch

search = MarkdownKeywordSearch(Settings.from_env())
results = search.search("MIN-OPS-2025-04 delivery delay")
```
