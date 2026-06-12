param(
    [string]$Model = "google/gemma-4-31B-it",
    [int]$Port = 30000,
    [string]$HostName = "127.0.0.1",
    [switch]$Install
)

if ($Install) {
    python -m pip install -U "sglang[all]"
}

Write-Host "Starting SGLang for $Model on http://$HostName`:$Port"
Write-Host "If the model is gated, set HF_TOKEN in this shell before running."

python -m sglang.launch_server `
    --model-path $Model `
    --host $HostName `
    --port $Port
