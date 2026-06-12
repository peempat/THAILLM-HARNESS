# Gemma 4 Local Agent

Use `google/gemma-4-31B-it` as the harness chat agent by serving it through an OpenAI-compatible local server.

Reference: the Hugging Face model card shows vLLM serving with:

```powershell
vllm serve "google/gemma-4-31B-it"
```

and calling:

```text
http://localhost:8000/v1/chat/completions
```

## Hardware Note

`google/gemma-4-31B-it` is a large 31B multimodal model. It generally needs a strong GPU setup or quantized/runtime-specific deployment. For local CPU-only machines, use a smaller Gemma model or a quantized build.

## Option A: vLLM

```powershell
cd Fahmai
$env:HF_TOKEN="your_huggingface_token_if_needed"
.\scripts\start_gemma_vllm.ps1 -Install
```

In a second terminal:

```powershell
cd Fahmai
.\scripts\use_gemma_local.ps1
python scripts\test_llm.py
python scripts\run_question.py --question "What did memo MIN-OPS-2025-04 say about delivery delay?" --execute-rag --use-llm
```

## Option B: SGLang

Start server:

```powershell
cd Fahmai
$env:HF_TOKEN="your_huggingface_token_if_needed"
.\scripts\start_gemma_sglang.ps1 -Install -Port 30000
```

Configure current shell:

```powershell
$env:FAHMAI_LLM_PROVIDER="gemma_local"
$env:FAHMAI_LLM_CHAT_URL="http://localhost:30000/v1/chat/completions"
$env:FAHMAI_LLM_MODEL="google/gemma-4-31B-it"
python scripts\test_llm.py
```

## Persistent Config

Copy `.env.gemma.local.example` values into `.env` if you always want the harness to use local Gemma.
