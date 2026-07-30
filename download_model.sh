#!/bin/bash
# Idempotent downloader for Phi-3 mini 4K Instruct Q4 GGUF
mkdir -p model
MODEL_FILE="model/Phi-3-mini-4k-instruct-q4.gguf"
URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"

if [ -f "$MODEL_FILE" ]; then
    echo "Model file already exists at $MODEL_FILE. Skipping download."
else
    echo "Downloading model weights..."
    curl -L -o "$MODEL_FILE" "$URL"
    if [ $? -eq 0 ]; then
        echo "Download complete."
    else
        echo "Error: Download failed."
        exit 1
    fi
fi
