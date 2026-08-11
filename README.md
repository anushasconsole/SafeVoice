# SafeVoice 🛡️
**AI-Powered Legal Guidance for Women — Karnataka, India**

Built by Team Nova | PES University CSE (AIML) | Hackfinity 2025

---

## Backend Improvements (v2.0)

**JWT Authentication**
Added `/api/token` that issues an anonymous short-lived JWT (60 min). Every `/api/chat` request now requires a valid `Authorization: Bearer <token>` header. The key insight: privacy by design — the token has no user identity, it just prevents unauthenticated abuse of the Gemini quota. The old version had zero authentication; anyone with the URL could burn the API key.

**Rate Limiting (slowapi)**
`/api/chat` is limited to 20 requests/minute per IP using `slowapi`. This is the direct practical fix for a single malicious user exhausting the 250 free daily Gemini requests in one burst. Returns HTTP 429 with a readable error instead of silently failing.

**Redis Response Caching**
Identical `(message + language)` pairs are SHA-256 hashed and cached in Redis for 10 minutes. Common questions like "What is IPC 498A?" will be served from cache on repeated hits — the response includes a `cached: true` flag. Falls back gracefully if Redis is not running, so the app still works without it.

**Background Helpline Health Checker (APScheduler)**
An `AsyncIOScheduler` job runs `check_helpline_urls()` on startup and every hour. It HTTP-pings any helpline URLs that have a web presence and stores `{status, checked_at}` per helpline. The `/api/helplines` endpoint returns this metadata so a future frontend badge like "✅ verified 2h ago" is possible.

**API Key Moved Server-Side**
The original `index.html` had a hardcoded `GEMINI_API_KEY` in the JavaScript — visible to anyone who opened DevTools. The key is now stored only in `backend/.env`. The frontend calls `/api/chat` (JWT-protected) and never sees the key.

---

## Quick Start

### Option A — Local (no Docker)

```bash
# 1. Copy and fill in your environment variables
cp backend/.env.example backend/.env
# Edit backend/.env — paste your GEMINI_API_KEY

# 2. Install dependencies
cd backend
pip install -r requirements.txt

# 3. (Optional) Start Redis for caching
# Windows: download from https://github.com/tporadowski/redis/releases
# Or skip — the app works without Redis, caching just won't be active

# 4. Start the server
uvicorn main:app --reload --port 8000
```

Open: **http://localhost:8000**

### Option B — Docker Compose (includes Redis)

```bash
# Set your API key first
echo "GEMINI_API_KEY=your_key_here" > backend/.env

docker-compose up --build
```

Open: **http://localhost:8000**

---

## Project Structure

```
safevoice/
├── backend/
│   ├── main.py              # FastAPI — JWT auth, rate limiting, Redis cache, scheduler
│   ├── requirements.txt     # Python dependencies
│   ├── .env                 # API keys (NEVER commit this!)
│   └── .env.example         # Template for environment variables
├── frontend/
│   └── index.html           # Single-page app — calls backend API, no key exposed
├── Dockerfile               # Production container image
├── docker-compose.yml       # App + Redis
├── .gitignore
├── start.sh / start.bat     # Local quick-start scripts
└── README.md
```

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | None | Health check: Redis, scheduler, Gemini status |
| POST | `/api/token` | None | Issue anonymous JWT session token |
| POST | `/api/chat` | JWT | Send message, get AI reply (rate limited, cached) |
| GET | `/api/helplines` | None | Helpline list with health check timestamps |
| POST | `/api/save-key` | JWT | Save Gemini API key to .env |

### Chat request

```json
POST /api/chat
Authorization: Bearer <token>

{
  "message": "What is IPC 498A?",
  "language": "en",
  "history": []
}
```

### Chat response

```json
{
  "reply": "**IPC 498A** protects women from...",
  "source": "gemini",
  "cached": false
}
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | — | Free key from https://aistudio.google.com/apikey |
| `JWT_SECRET` | No | dev-secret | Random string — change in production |
| `JWT_EXPIRY_MINUTES` | No | 60 | Token lifetime |
| `REDIS_URL` | No | redis://localhost:6379 | Redis connection string |
| `ALLOWED_ORIGINS` | No | localhost:8000 | Comma-separated CORS origins |

---

## Emergency Numbers

| Number | Service |
|--------|---------|
| 100 | Police Emergency |
| 181 | National Women Helpline |
| 1091 | Vanitha Sahayavani (Karnataka) |
| 1098 | Childline |
| 7827170170 | One Stop Centre |

---

## Team Nova — Hackfinity 2025

Adithi B Prabhu · Ananya J C · Anusha  
PES University, Department of Computer Science & Engineering (AIML)
