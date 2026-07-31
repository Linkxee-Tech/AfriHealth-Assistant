#!/bin/bash
# Idempotent downloader for Phi-3 mini 4K Instruct Q4 GGUF
set -eu

mkdir -p backend/models/llm
MODEL_FILE="backend/models/llm/Phi-3-mini-4k-instruct-q4.gguf"
TEMP_FILE="${MODEL_FILE}.download"
URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"

if [ -f "$MODEL_FILE" ]; then
    echo "Model file already exists at $MODEL_FILE. Skipping download."
else
    echo "Downloading model weights..."
    trap 'rm -f "$TEMP_FILE"' EXIT
    curl --fail --location --retry 3 --output "$TEMP_FILE" "$URL"
    [ "$(head -c 4 "$TEMP_FILE")" = "GGUF" ] || { echo "Error: downloaded file is not GGUF."; exit 1; }
    mv "$TEMP_FILE" "$MODEL_FILE"
    trap - EXIT
    echo "Download complete."
fi
