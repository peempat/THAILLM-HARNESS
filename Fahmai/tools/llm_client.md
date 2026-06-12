# LLM Client

## Purpose

Call the configured chat LLM. Default provider is OpenTyphoon.

## Config

```env
FAHMAI_LLM_PROVIDER=opentyphoon
FAHMAI_LLM_BASE_URL=https://api.opentyphoon.ai/v1
FAHMAI_LLM_CHAT_URL=https://api.opentyphoon.ai/v1/chat/completions
FAHMAI_LLM_API_KEY=replace-me
FAHMAI_LLM_MODEL=typhoon-v2.5-30b-a3b-instruct
FAHMAI_LLM_MAX_TOKENS=2048
FAHMAI_LLM_TEMPERATURE=0.2
FAHMAI_LLM_TIMEOUT_SEC=90
```

The key can also be provided as `OPENTYPHOON_API_KEY`.

## Test

```powershell
python scripts/test_llm.py
python scripts/run_question.py --question "..." --execute-rag --use-llm
```
