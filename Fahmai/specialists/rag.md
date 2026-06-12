# RAG Specialist

Use `agent/specialists/rag.py` with `agent/tools/markdown_search.py`.

Must:

- Search exact IDs first.
- Retry with aliases, Thai/English variants, concept terms, and date context.
- Deduplicate chunks.
- Reject weak/tangential evidence.
- Return `no_data` only after `max_retries`.
- Log every attempt.
