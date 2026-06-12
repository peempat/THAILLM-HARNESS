# Local Agent Tool

## Purpose

Call the ModelHarbor local LLM endpoint.

## Config

Loaded from `Fahmai/.env`:

- `FAHMAI_LOCAL_HEALTH_URL`
- `FAHMAI_LOCAL_AGENT_URL`
- `FAHMAI_LOCAL_OCR_URL`
- `FAHMAI_LOCAL_MODEL`
- `FAHMAI_LOCAL_MAX_TOKENS`
- `FAHMAI_LOCAL_TEMPERATURE`
- `FAHMAI_LOCAL_TIMEOUT_SEC`

## Primary Contract

POST `/agent/local`

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Can you summarize the benefits of local LLMs?"}
  ],
  "max_tokens": 2048,
  "temperature": 0.7
}
```

The client falls back to `/v1/chat/completions` if `/agent/local` returns 404.

For OpenTyphoon or another OpenAI-compatible chat API, use `tools/llm_client.py` and `scripts/test_llm.py`.

## Test

```powershell
python scripts/test_local_agent.py
```
