# SHL Assessment Recommender

A full-stack AI tool that recommends SHL psychometric assessments through a conversational chat interface. Ask in plain English — get back specific assessments with links directly to the SHL catalog.

```
[React frontend]  →  /shl-api/*  →  [Python FastAPI]  →  Groq LLM + FAISS
```

---

## What's in this repo

```
shl-api/                  ← Python FastAPI backend (the brains)
artifacts/shl-chat/       ← React + Vite frontend (the chat UI)
attached_assets/          ← SHL catalog JSON file (source of truth)
```

---

## Running locally

You need two terminal windows — one for each service.

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| pnpm | 8+ | `npm install -g pnpm` |

---

### Terminal 1 — Python API

```bash
cd shl-api

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
```

Open `shl-api/.env` and set your values:

```env
GROQ_API_KEY=gsk_your_key_here          # get free at console.groq.com
CATALOG_PATH=catalog.json               # see note below
```

> **Catalog file:** copy the long `.txt` file from `attached_assets/` into `shl-api/` and rename it:
> ```bash
> cp attached_assets/Pasted--entity-id-4302-name-Global-Skills-Development-Report-l_1782925068934.txt shl-api/catalog.json
> ```

```bash
# Start the API (from inside shl-api/)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

First run takes ~60 seconds to download the embedding model and build the FAISS index. You'll see:

```
Ready. Catalog size: 377 assessments.
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

Every run after that starts in under 2 seconds.

---

### Terminal 2 — React frontend

```bash
# From the project root
pnpm install

# Start the frontend
pnpm --filter @workspace/shl-chat run dev
```

Then open **http://localhost:23098** in your browser.

The frontend automatically proxies `/shl-api/*` → `http://localhost:8000` so the two services talk to each other with no extra config.

---

### Verify everything works

```bash
# API health
curl http://localhost:8000/health
# → {"status":"ok"}

# Test a chat request
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Cognitive tests for a software engineer"}]}'
# → {"reply":"...","recommendations":[...],"end_of_conversation":false}
```

---

## Environment variables

### `shl-api/.env`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ | — | Get free at [console.groq.com](https://console.groq.com) |
| `CATALOG_PATH` | ✅ | — | Path to the SHL catalog JSON file |
| `GROQ_MODEL` | | `llama-3.3-70b-versatile` | LLM model |
| `EMBED_MODEL` | | `BAAI/bge-small-en-v1.5` | Embedding model |
| `TOP_K_RETRIEVE` | | `20` | Candidates from hybrid search |
| `TOP_K_RETURN` | | `10` | Max recommendations returned |

### Frontend (optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_SHL_API_URL` | `/shl-api` | Where the frontend sends API requests. In dev this is proxied by Vite. In production set this to your deployed API URL. |

---

## Pushing to GitHub

### First time

```bash
# Make sure you're in the project root
git init                                    # skip if already a git repo
git add .
git commit -m "Initial commit"

# Create a repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

### After making changes

```bash
git add .
git commit -m "describe what you changed"
git push
```

### What gets committed / what doesn't

| Committed | Not committed |
|-----------|--------------|
| All source code | `node_modules/` |
| `shl-api/requirements.txt` | `shl-api/venv/` |
| `attached_assets/` catalog file | `shl-api/data/faiss_index/` (rebuilt automatically) |
| `.env.example` | `shl-api/.env` (contains your secret key) |

> The `.env` file is already in `.gitignore` — your `GROQ_API_KEY` will not be pushed.

---

## Deploying

The two services deploy independently because one is Python and one is Node/static.

### Python API → Render (recommended)

1. Push to GitHub
2. Go to [render.com](https://render.com) → **New Web Service** → connect your repo
3. Set **Root Directory** to `shl-api`
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables in Render's dashboard:
   - `GROQ_API_KEY` = your key
   - `CATALOG_PATH` = `/opt/render/project/src/catalog.json` *(after uploading catalog)*
7. Upload the catalog file to your repo or use Render's persistent disk

### Python API → Docker (anywhere)

```bash
cd shl-api
docker build -t shl-api .
docker run -e GROQ_API_KEY=your_key -e CATALOG_PATH=/data/catalog.json \
  -v $(pwd)/catalog.json:/data/catalog.json \
  -p 8000:8000 shl-api
```

### Frontend → any static host (Vercel, Netlify, GitHub Pages)

```bash
# Build the frontend
VITE_SHL_API_URL=https://your-deployed-api.com pnpm --filter @workspace/shl-chat run build
# Output is in artifacts/shl-chat/dist/public/
```

Point your host at `artifacts/shl-chat/dist/public/` and configure all routes to serve `index.html`.

> Set `VITE_SHL_API_URL` to your deployed Python API URL so the frontend knows where to send requests.

---

## Running tests

```bash
cd shl-api
source venv/bin/activate
pytest tests/ -v
# 21 tests, all passing
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Could not connect to server` | API not running | Start `uvicorn` in Terminal 1 first |
| `{"detail":"Internal error"}` | Missing `GROQ_API_KEY` | Check `shl-api/.env` has the real key, restart uvicorn |
| `FileNotFoundError: Catalog file not found` | Wrong `CATALOG_PATH` | Check path in `.env` is correct relative to where you run uvicorn |
| Frontend shows "Disconnected" | API on wrong port | Make sure uvicorn is on port 8000 |
| First startup slow (~60s) | Downloading embedding model | Normal — subsequent starts are instant |
| `red` colors everywhere in UI | Theme CSS not loaded | Hard-refresh the browser (Ctrl+Shift+R) |
