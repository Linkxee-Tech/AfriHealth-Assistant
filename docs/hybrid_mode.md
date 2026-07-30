# Hybrid and offline mode

Core chat, the local SQLite database, the Chroma knowledge base, deterministic vital checks, and local clinical references work without internet when the compatible GGUF and embedding model are present.

The hybrid orchestrator checks connectivity, handles simple questions offline, combines local retrieval with web results for complex/current questions, caches repeated context lookups for five minutes, and limits online searches to 30 requests per minute. Search failure falls back to local context.

Gemini is an optional cloud fallback. It is marked unavailable unless the SDK and API key are configured and a request succeeds. Usage is counted from returned text tokens as an estimate; provider billing remains authoritative. No cloud synchronization or telemedicine provider is claimed until one is configured.
