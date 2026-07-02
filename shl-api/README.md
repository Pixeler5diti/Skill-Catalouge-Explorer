# SHL Assessment Recommender API

A conversational RAG system that recommends SHL assessments using hybrid semantic + keyword search (FAISS + BM25) and a Groq LLM, grounded entirely on the catalog file — it cannot hallucinate assessments that aren't in it.

---

## Quick start (local)

### 1. Prerequisites

- Python 3.11+
- A [Groq API key](https://console.groq.com) (free tier works fine)
- The SHL catalog file (the `.txt` file from this repo — it's a JSON array)

### 2. Install dependencies

```bash
cd shl-api
python -m venv venv

# Mac / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in two values:

```env
# Your Groq API key — get one free at https://console.groq.com
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# Path to the catalog JSON file (relative to where you run uvicorn, or absolute)
# If the catalog file is in the shl-api/ folder:
CATALOG_PATH=catalog.json

# If it's one level up (e.g. you cloned the whole repo and kept the structure):
# CATALOG_PATH=../attached_assets/Pasted--entity-id-4302-name-Global-Skills-Development-Report-l_1782925068934.txt
```

> **Tip:** the catalog file has a long name. The simplest thing is to copy it into `shl-api/` and rename it to `catalog.json`, then set `CATALOG_PATH=catalog.json`.

### 4. Run the server

```bash
# Make sure you're inside shl-api/ and your venv is active
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:

```
INFO:     Waiting for application startup.
{"msg": "SHL Recommender starting up…"}
{"msg": "Loaded 377 raw catalog entries from catalog.json"}
{"msg": "No persisted index found — building from scratch (one-time, ~1 min)…"}
...
{"msg": "Ready. Catalog size: 377 assessments."}
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

The first run downloads the embedding model (~130 MB) and builds the FAISS index (~30–60 seconds). Every run after that loads from disk in under 2 seconds.

### 5. Test it

```bash
# Health check
curl http://localhost:8000/health

# Ask for a recommendation
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"I need cognitive tests for a software engineer"}]}'
```

---

## Troubleshooting: "Could not connect to server"

This always means the **server failed to start**, not a networking problem. Check the terminal where you ran `uvicorn` for the real error. Common causes:

| Error in terminal | Fix |
|-------------------|-----|
| `FileNotFoundError: Catalog file not found` | `CATALOG_PATH` in `.env` is wrong — double-check the path |
| `GROQ_API_KEY` missing or invalid | Set it in `.env` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` with your venv active |
| Port already in use | Change `--port 8000` to another port, e.g. `--port 8001` |

---

## API reference

### `GET /health`

```json
{ "status": "ok" }
```

### `POST /chat`

**Request body:**
```json
{
  "messages": [
    { "role": "user",      "content": "I need tests for a sales manager" },
    { "role": "assistant", "content": "..." },
    { "role": "user",      "content": "Keep it under 30 minutes" }
  ]
}
```

Pass the full conversation history on every request — the API is stateless.

**Response (always this shape):**
```json
{
  "reply": "Here are my recommendations...",
  "recommendations": [
    {
      "name": "Occupational Personality Questionnaire OPQ32r",
      "url": "https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/",
      "test_type": "Personality & Behavior"
    }
  ],
  "end_of_conversation": false
}
```

`recommendations` is always present (empty array `[]` when the assistant is asking a clarifying question).

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *(required)* | Groq API key |
| `CATALOG_PATH` | *(required locally)* | Path to the catalog JSON file |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | LLM model |
| `EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model |
| `TOP_K_RETRIEVE` | `20` | Candidates from hybrid search |
| `TOP_K_RETURN` | `10` | Max recommendations returned |
| `FAISS_INDEX_DIR` | `data/faiss_index` | Where to persist the FAISS index |

---

## Running tests

```bash
# Inside shl-api/ with venv active
pytest tests/ -v
```

21 tests covering intent classification, retrieval, validation, and schema compliance.

---

## Project structure

```
shl-api/
├── app/
│   ├── main.py                  # FastAPI app + startup lifecycle
│   ├── api.py                   # Route handlers (/health, /chat)
│   ├── config.py                # Settings (reads from .env)
│   ├── schemas.py               # Pydantic request/response models
│   ├── catalog/
│   │   ├── loader.py            # Load JSON catalog from disk
│   │   └── preprocess.py        # Normalize, deduplicate, build search docs
│   ├── retrieval/
│   │   ├── embeddings.py        # BAAI/bge-small-en-v1.5 encoder
│   │   ├── vectorstore.py       # FAISS index (persisted to disk)
│   │   ├── retriever.py         # Hybrid semantic + BM25 search
│   │   └── reranker.py          # Metadata-boosted reranking
│   ├── conversation/
│   │   ├── intent_classifier.py # 6-class intent classifier
│   │   ├── constraint_extractor.py
│   │   ├── chat_engine.py       # Stateless orchestrator
│   │   ├── comparison.py        # Side-by-side assessment comparison
│   │   └── prompt_builder.py    # Token-efficient prompt construction
│   ├── llm/
│   │   └── groq_client.py       # Groq API client with retry
│   └── utils/
│       ├── validators.py        # Validate recs against catalog
│       └── logger.py            # JSON structured logger
├── data/
│   └── faiss_index/             # Auto-created on first run
├── tests/
│   └── test_chat.py
├── .env.example
├── requirements.txt
├── Dockerfile
└── render.yaml
```

---

## Deployment

### Render (recommended)

1. Push to GitHub
2. Create a **Web Service** on [render.com](https://render.com) pointing to this repo
3. Set `GROQ_API_KEY` and `CATALOG_PATH` in Render's environment variables
4. Render picks up `render.yaml` automatically and deploys

### Docker

```bash
docker build -t shl-recommender .
docker run \
  -e GROQ_API_KEY=your_key \
  -e CATALOG_PATH=/data/catalog.json \
  -v /path/to/your/catalog.json:/data/catalog.json \
  -p 8000:8000 \
  shl-recommender
```
