param(
    [string]$Model = "google/gemma-4-31B-it",
    [int]$Port = 8000,
    [string]$HostName = "127.0.0.1",
    [string]$TensorParallelSize = "1",
    [string]$MaxModelLen = "32768",
    [switch]$Install
)

if ($Install) {
    python -m pip install -U vllm
}

Write-Host "Starting vLLM for $Model on http://$HostName`:$Port"
Write-Host "If the model is gated, set HF_TOKEN in this shell before running."

python -m vllm.entrypoints.openai.api_server `
    --model $Model `
    --host $HostName `
    --port $Port `
    --tensor-parallel-size $TensorParallelSize `
    --max-model-len $MaxModelLen
