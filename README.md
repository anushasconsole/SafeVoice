# SafeVoice 🛡️
**AI-Powered Legal Guidance for Women — Karnataka, India**

Built by Team Nova | PES University CSE (AIML) | Hackfinity 2025

---

<<<<<<< HEAD
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
=======
## 🚀 Quick Start (5 minutes)

### Step 1 — Get a FREE Gemini API Key
1. Go to: https://aistudio.google.com/apikey
2. Sign in with your Google account (no credit card required)
3. Click "Create API Key"
4. Copy the key

### Step 2 — Add your API Key
Open `backend/.env` and paste your key:
```
GEMINI_API_KEY=paste_your_key_here
```

### Step 3 — Install & Run
```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000
```

### Step 4 — Open the App
Open your browser at: **http://localhost:8000**

That's it! 🎉

---

## 📁 Project Structure
>>>>>>> 0f0c55ea77934618953a7fa1307a70011ab93e77

```
safevoice/
├── backend/
<<<<<<< HEAD
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
=======
│   ├── main.py              # FastAPI app — AI logic, API routes
│   ├── requirements.txt     # Python dependencies
│   └── .env                 # API keys (NEVER commit this!)
├── frontend/
│   └── index.html           # Complete single-page app (served by backend)
├── .gitignore               # Protects .env from being committed
├── start.sh                 # Linux/Mac one-click start
├── start.bat                # Windows one-click start
>>>>>>> 0f0c55ea77934618953a7fa1307a70011ab93e77
└── README.md
```

---

<<<<<<< HEAD
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
=======
## 🔑 Why Gemini? (Free Alternative to Anthropic)

| | Gemini 2.5 Flash (FREE) | Anthropic Claude |
|---|---|---|
| Price | **FREE** (no credit card) | $3–15 per 1M tokens |
| Daily limit | 250 requests/day | Paid only |
| Setup | Google account | Credit card required |
| Quality | Excellent | Excellent |

Gemini 2.5 Flash gives you **250 free requests per day** — more than enough for a hackathon demo!

---

## 🛡️ Security Architecture

```
User Browser  →  FastAPI Backend  →  Gemini API
                 (holds API key)
```

- API key is stored ONLY in `backend/.env`
- Frontend never sees the key
- All requests are stateless (no data stored)
- CORS configured for local development

---

## ✨ Features

- 🤖 **AI Legal Guidance** — Powered by Gemini 2.5 Flash
- 🌐 **4 Languages** — Kannada, Hindi, Telugu, English
- 👁️ **Disguise Mode** — Instant calculator overlay
- ⚡ **Quick Exit** — One click to Google
- 🔒 **Zero Data Storage** — Privacy by architecture
- 🎤 **Voice Input** — Web Speech API
- 📞 **Karnataka Helplines** — Verified, curated
- 📜 **Know Your Rights** — IPC 498A, PWDVA, POCSO

---

## 📞 Emergency Numbers
>>>>>>> 0f0c55ea77934618953a7fa1307a70011ab93e77

| Number | Service |
|--------|---------|
| 100 | Police Emergency |
| 181 | National Women Helpline |
| 1091 | Vanitha Sahayavani (Karnataka) |
| 1098 | Childline |
| 7827170170 | One Stop Centre |

---

<<<<<<< HEAD
## Team Nova — Hackfinity 2025

Adithi B Prabhu · Ananya J C · Anusha  
=======
## 🏆 Hackfinity 2025 — Team Nova

- Adithi B Prabhu
- Ananya J C  
- Anusha

>>>>>>> 0f0c55ea77934618953a7fa1307a70011ab93e77
PES University, Department of Computer Science & Engineering (AIML)
