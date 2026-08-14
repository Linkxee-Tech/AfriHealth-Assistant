# Online Deployment Guide — Using Remote LLM APIs

## Overview

The AfriHealth Assistant now supports **both local and remote LLM models**. For online deployment, you don't need to download or host large GGUF files locally. Instead, use free or affordable cloud APIs.

## Quick Setup for Online Deployment

### Option 1: Hugging Face Inference API (Recommended)

**Advantages:**
- Free tier available
- No local model required
- Easy to scale
- Supports multiple Llama models

**Setup:**

1. **Get API Key:**
   - Go to [huggingface.co](https://huggingface.co)
   - Create a free account
   - Navigate to Settings → Access Tokens
   - Create a new token (read permission is sufficient)
2. **Update `.env`:**
   ```env
   LLM_PROVIDER=huggingface
   HUGGINGFACE_API_KEY=hf_YOUR_API_KEY_HERE
   HUGGINGFACE_MODEL_ID=meta-llama/Llama-2-7b-chat-hf
   MODEL_PATH=
   ```

3. **Install dependencies:**
   ```bash
   pip install huggingface-hub
   ```

4. **Test:**
   ```bash
   python -c "from backend.config import settings; from backend.core.llm_engine import llm_engine; llm_engine.load_model(); print('✓ Connected to Hugging Face API')"
   ```

---

### Option 2: Groq API (Free, Very Fast)

**Advantages:**
- **Completely free** for reasonable usage
- Very fast inference
- Simple API
- Perfect for LLaMA models

**Setup:**

1. **Get API Key:**
   - Go to [groq.com](https://groq.com)
   - Sign up for free (no credit card needed)
   - Get your API key from the dashboard

2. **Update `.env`:**
   ```env
   LLM_PROVIDER=groq
   GROQ_API_KEY=gsk_YOUR_KEY_HERE
   MODEL_PATH=
   ```

3. **Install dependencies:**
   ```bash
   pip install groq
   ```

4. **Test:**
   ```bash
   python -c "from backend.config import settings; from backend.core.llm_engine import llm_engine; llm_engine.load_model(); print('✓ Connected to Groq API')"
   ```

---

### Option 3: Google Gemini API

**Advantages:**
- Integrated with Google Cloud
- Multimodal capabilities
- Free tier with rate limits
- Already partially configured in the project

**Setup:**

1. **Get API Key:**
   - Go to [aistudio.google.com](https://aistudio.google.com)
   - Click "Get API Key"
   - Create new API key for free

2. **Update `.env`:**
   ```env
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=YOUR_KEY_HERE
   MODEL_PATH=
   ```

3. **Install dependencies:**
   ```bash
   pip install google-generativeai
   ```

4. **Test:**
   ```bash
   python -c "from backend.config import settings; from backend.core.llm_engine import llm_engine; llm_engine.load_model(); print('✓ Connected to Gemini API')"
   ```

---

### Option 4: Local Model (Offline Deployment)

If you need offline capability or have a local GGUF file:

```env
LLM_PROVIDER=local
MODEL_PATH=backend/models/llm/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf
```

---

## Configuration Reference

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `LLM_PROVIDER` | Which LLM backend to use | `local` |
| `MODEL_PATH` | Path to local GGUF (leave empty for remote) | `` |
| `HUGGINGFACE_API_KEY` | Hugging Face API token | `` |
| `HUGGINGFACE_MODEL_ID` | Hugging Face model to use | `meta-llama/Llama-2-7b-chat-hf` |
| `GROQ_API_KEY` | Groq API key | `` |
| `GEMINI_API_KEY` | Google Gemini API key | `` |

### Supported Providers

| Provider | Config Value | Free Tier | Speed | Use Case |
|----------|-------------|-----------|-------|----------|
| Local | `local` | Yes* | Fast | Offline, Privacy |
| Hugging Face | `huggingface` | Yes | Medium | Development, Testing |
| Groq | `groq` | **Yes** | **Very Fast** | Production* |
| Gemini | `gemini` | Limited | Good | Multimodal needs |

*Local requires downloading GGUF (not free). **Groq is best for cost-free production.**

---

## Deployment Checklist

- [ ] Remove or clear `MODEL_PATH` in `.env`
- [ ] Set `LLM_PROVIDER` to your chosen provider
- [ ] Set the appropriate API key (HUGGINGFACE_API_KEY, GROQ_API_KEY, or GEMINI_API_KEY)
- [ ] Install provider dependencies: `pip install huggingface-hub groq google-generativeai`
- [ ] Test API connection: `python -m backend.tests.test_api`
- [ ] Run backend: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- [ ] Test frontend chat: Open http://localhost:8501 and try a chat message

---

## Testing Connection

```python
from backend.core.llm_engine import llm_engine
from backend.config import settings

# Check which provider is active
print(f"Provider: {llm_engine.provider}")

# Load the model
llm_engine.load_model()

# Check status
status = llm_engine.get_status()
print(f"Loaded: {status['model_loaded']}")
print(f"Error: {status['load_error']}")

# Test generation
if status['model_loaded']:
    response = llm_engine.generate("What is malaria?", max_tokens=100)
    print(f"Response: {response}")
```

---

## Cost Estimates (Approximate)

### Groq
- **Free tier**: Unlimited (with rate limits)
- **Paid**: Very affordable ($0.10–$1 per million tokens)

### Hugging Face
- **Free tier**: Limited requests
- **Pro**: $9/month (unlimited)

### Gemini
- **Free tier**: 60 requests/minute
- **Paid**: $0.000075–$0.0003 per 1000 tokens

### Local (GGUF)
- **Download**: ~10–30 GB one-time
- **Runtime**: Free but requires CPU/GPU

---

## Troubleshooting

### "API key not set in .env"
- Ensure `.env` file exists in the project root
- Copy from `.env.example` if missing
- Verify the key is correctly pasted

### "Model connection failed"
- Check internet connection
- Verify API key is valid
- Check API rate limits (especially Gemini free tier)
- View logs: `tail -f backend/logs/app.log`

### Slow responses
- **Gemini free tier**: Limited concurrency. Use Groq instead.
- **Hugging Face**: Free tier may be slow. Upgrade to Pro.
- **Groq**: Already optimized. May be network latency.

### Module not found errors
- Reinstall dependencies: `pip install -r requirements.txt`
- Or install specific provider: `pip install groq` or `pip install huggingface-hub`

---

## Performance Notes

### Comparison Table

| Metric | Local | Hugging Face | Groq | Gemini |
|--------|-------|--------------|------|--------|
| **Latency** | ~2–5s | ~3–10s | ~1–2s | ~2–5s |
| **Setup Time** | 30 min | 2 min | 1 min | 1 min |
| **Free Tier** | No* | Yes | **Yes** | Limited |
| **Scalability** | None | Good | Excellent | Good |

*Local requires downloading ~20GB GGUF

---

## Production Recommendations

For **production online deployment**:

1. **Use Groq** — Fastest, free, no credit card
2. **Set up monitoring** — Track API usage and costs
3. **Add rate limiting** — Protect against abuse
4. **Use async/streaming** — For better responsiveness
5. **Cache responses** — Reduce redundant API calls

---

## Next Steps

1. Choose your provider above
2. Get API credentials
3. Update `.env`
4. Test with: `python -m pytest backend/tests/test_api.py`
5. Deploy with Docker or your cloud platform

---

## Additional Resources

- [Groq Docs](https://console.groq.com/docs)
- [Hugging Face Inference API](https://huggingface.co/docs/api-inference)
- [Google Gemini Docs](https://ai.google.dev)
- [Project Setup Guide](docs/setup.md)
- [Architecture](docs/architecture.md)
