# API Reference

Base URL: `http://localhost:8000/api/v1`
Interactive docs: `http://localhost:8000/docs`

---

## System

### GET `/system/health`
Basic health check. Returns 200 if server is running.

### GET `/system/status`
Returns model load status, memory, CPU, and knowledge base info.

---

## Chat

### POST `/chat`
Blocking chat. Returns full response after generation completes.

**Request:**
```json
{"query": "What is malaria?", "language": "English", "top_k": 3}
```
**Response:** `{"answer": "...", "sources": ["WHO guidelines"], "elapsed_ms": 1200}`

### POST `/chat/stream`
Streaming chat. Returns `text/plain` stream of tokens.
First chunk: `__SOURCES__:["WHO guidelines"]`
Subsequent chunks: plain text tokens.

### POST `/chat/save`
Save a conversation to SQLite history.

---

## Chat History

### GET `/chat/history`
List all saved conversations. Query param: `limit` (default 100).

### GET `/chat/history/{session_id}`
Get all messages in a conversation.

### POST `/chat/history`
Save a conversation: `{"messages": [...], "session_id": "optional"}`

### DELETE `/chat/history/{session_id}`
Delete a conversation and all its messages.

---

## Health Metrics

### POST `/metrics`
Save a health metric entry.
```json
{"metric_type": "Heart Rate", "value": "78", "unit": "bpm", "notes": "at rest"}
```

### GET `/metrics`
Get entries. Query params: `metric_type`, `start_date`, `end_date`, `limit`.

### GET `/metrics/export`
Download all entries as CSV.

### DELETE `/metrics/{entry_id}`
Delete a metric entry.

### POST `/metrics/check-vitals`
Check a vital sign against clinical normal ranges.
```json
{"metric_type": "Heart Rate", "value": "160"}
```
Returns: `{"status": "critical_high", "urgency": "Emergency", "message": "..."}`

### POST `/metrics/analyze-symptoms`
Triage a list of symptom strings.
```json
{"symptoms": ["fever", "headache", "cough"]}
```
Returns: `{"urgency": "Medium", "advice": "...", "do_not": [...]}`

---

## Documents

### POST `/documents/upload`
Upload a PDF, DOCX, TXT, or image file.
Extracts text, chunks it, adds to RAG knowledge base, returns analysis.

### POST `/documents/analyze`
Re-analyze an uploaded document by filename.

### GET `/documents`
List all uploaded documents.
