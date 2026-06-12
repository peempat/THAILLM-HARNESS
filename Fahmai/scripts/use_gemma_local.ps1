$env:FAHMAI_LLM_PROVIDER = "gemma_local"
$env:FAHMAI_LLM_BASE_URL = "http://localhost:8000/v1"
$env:FAHMAI_LLM_CHAT_URL = "http://localhost:8000/v1/chat/completions"
$env:FAHMAI_LLM_API_KEY = ""
$env:FAHMAI_LLM_MODEL = "google/gemma-4-31B-it"
$env:FAHMAI_LLM_TIMEOUT_SEC = "180"

Write-Host "Configured current shell for local Gemma via vLLM localhost:8000"
Write-Host "Test with: python scripts\test_llm.py --message `"ตอบว่า Gemma local พร้อมใช้งาน`""
