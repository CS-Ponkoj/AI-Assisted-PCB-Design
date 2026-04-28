#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-qwen2.5:3b}"

echo "Installing Python dependencies..."
python -m pip install -r requirements.txt

if ! command -v ollama >/dev/null 2>&1; then
  echo ""
  echo "Ollama was not found on this device."
  echo "Install it from https://ollama.com/download, then run this script again."
  exit 1
fi

echo ""
echo "Pulling Ollama model: ${MODEL}"
ollama pull "${MODEL}"

echo ""
echo "Installed Ollama models:"
ollama list

echo ""
echo "Setup complete."
echo "If Ollama is not already running, open the Ollama app or run: ollama serve"
echo "Then start the prototype with: streamlit run app.py"
