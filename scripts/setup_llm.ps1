param(
    [string]$Model = "qwen2.5:3b"
)

$ErrorActionPreference = "Stop"

Write-Host "Installing Python dependencies..."
python -m pip install -r requirements.txt

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host ""
    Write-Host "Ollama was not found on this device."
    Write-Host "Install it from https://ollama.com/download, then run this script again."
    exit 1
}

Write-Host ""
Write-Host "Pulling Ollama model: $Model"
ollama pull $Model

Write-Host ""
Write-Host "Installed Ollama models:"
ollama list

Write-Host ""
Write-Host "Setup complete."
Write-Host "If Ollama is not already running, open the Ollama app or run: ollama serve"
Write-Host "Then start the prototype with: streamlit run app.py"
