<<<<<<< HEAD
"""
SafeVoice Backend — v2.0
Real backend improvements applied:
  1. JWT Authentication      — /api/token issues a short-lived JWT; /api/chat requires it
  2. Rate Limiting           — slowapi: 20 req/min per IP on /api/chat
  3. Redis Response Caching  — identical (message+lang) queries cached 10 min, saves Gemini quota
  4. Background Health Jobs  — APScheduler pings helplines every hour, exposes freshness via /api/helplines
  5. Proper REST structure    — all routes on /api prefix, versioned responses, structured error bodies
"""

import os
import re
import hashlib
import json
import httpx
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# ── Third-party: JWT
import jwt as pyjwt

# ── Third-party: Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ── Third-party: Background scheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ── Third-party: Redis (optional — graceful fallback if Redis not running)
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

import google.generativeai as genai

load_dotenv()

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
JWT_SECRET = os.getenv("JWT_SECRET", "safevoice-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_TTL_SECONDS = 600  # 10 minutes

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini API key loaded")
else:
    print("⚠️  WARNING: GEMINI_API_KEY not set — fallback responses will be used")

# ─────────────────────────────────────────────
# Rate Limiter
# ─────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/day"])

# ─────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────
app = FastAPI(
    title="SafeVoice API",
    version="2.0.0",
    description="AI-powered legal guidance for women in Karnataka. JWT-authenticated, rate-limited, cached.",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS (tightened — no wildcard in production)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Mount static frontend
=======
import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
from dotenv import load_dotenv, set_key

load_dotenv()

# ── Configure Gemini ──
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY not set in .env file")
    print("   Either set it in backend/.env OR enter it in the web UI")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini API key loaded from .env")

app = FastAPI(title="SafeVoice API", version="1.0.0")

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount static frontend ──
>>>>>>> 0f0c55ea77934618953a7fa1307a70011ab93e77
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
static_path = os.path.join(frontend_path, "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# ─────────────────────────────────────────────
<<<<<<< HEAD
# Redis client (lazy — won't crash if Redis is absent)
# ─────────────────────────────────────────────
redis_client = None

async def get_redis():
    global redis_client
    if not REDIS_AVAILABLE:
        return None
    if redis_client is None:
        try:
            redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
            await redis_client.ping()
            print("✅ Redis connected")
        except Exception as e:
            print(f"⚠️  Redis unavailable ({e}) — caching disabled")
            redis_client = None
    return redis_client

# ─────────────────────────────────────────────
# JWT helpers
# ─────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)

def create_access_token() -> str:
    """Issue an anonymous session token (no user identity — privacy by design)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
    payload = {"sub": "anonymous_session", "exp": expire, "iat": datetime.now(timezone.utc)}
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Dependency: validate Bearer JWT on protected routes."""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "missing_token", "message": "Authorization header required"},
        )
    try:
        pyjwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"error": "token_expired", "message": "Token expired — request a new one from /api/token"},
        )
    except pyjwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "Invalid token"},
        )

# ─────────────────────────────────────────────
# Helpline registry + background health checker
# ─────────────────────────────────────────────
HELPLINES = [
    {"id": "181",  "name": "National Women Helpline", "number": "181",        "desc": "24/7 support for women in distress",                      "tag": "PAN INDIA · 24/7",  "icon": "👩‍⚖️", "url": None},
    {"id": "1091", "name": "Vanitha Sahayavani",       "number": "1091",       "desc": "Karnataka state women's helpline. Counselling, legal aid.", "tag": "KARNATAKA · 24/7",  "icon": "🏠",  "url": None},
    {"id": "100",  "name": "Police Emergency",          "number": "100",        "desc": "Immediate danger. FIR for 498A, assault.",                 "tag": "EMERGENCY · 24/7",  "icon": "🚔",  "url": None},
    {"id": "osc",  "name": "One Stop Centre",           "number": "7827170170", "desc": "Medical, police, legal aid, shelter under one roof.",      "tag": "KARNATAKA · FREE",  "icon": "🏥",  "url": "https://wcd.nic.in/schemes/one-stop-centre-scheme"},
    {"id": "1098", "name": "Childline (POCSO)",         "number": "1098",       "desc": "Child abuse and POCSO emergencies. Free, 24/7.",           "tag": "CHILDREN · 24/7",   "icon": "👶",  "url": None},
    {"id": "icall","name": "iCall Mental Health",       "number": "9152987821", "desc": "Free counselling for trauma and emotional distress.",      "tag": "COUNSELLING · FREE", "icon": "🧠",  "url": "https://icallhelpline.org"},
]

# In-memory health status (updated by background job)
helpline_health: dict = {h["id"]: {"status": "unknown", "checked_at": None} for h in HELPLINES}

async def check_helpline_urls():
    """Background job: HTTP-ping any helplines that have a URL. Runs every hour."""
    async with httpx.AsyncClient(timeout=8.0) as client:
        for h in HELPLINES:
            if h.get("url"):
                try:
                    resp = await client.head(h["url"])
                    status = "ok" if resp.status_code < 500 else "degraded"
                except Exception:
                    status = "unreachable"
                helpline_health[h["id"]] = {
                    "status": status,
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                # Phone-only lines — mark as not_checked (we can't HTTP-ping a number)
                helpline_health[h["id"]] = {
                    "status": "phone_only",
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                }
    print(f"[scheduler] Helpline health check completed at {datetime.now(timezone.utc).isoformat()}")

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup():
    # Warm Redis connection
    await get_redis()
    # Run first health check immediately, then every hour
    await check_helpline_urls()
    scheduler.add_job(check_helpline_urls, "interval", hours=1, id="helpline_health")
    scheduler.start()
    print("✅ Background scheduler started (helpline health checks every 1h)")

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown(wait=False)
    if redis_client:
        await redis_client.close()

# ─────────────────────────────────────────────
# System prompts
=======
# System prompts per language
>>>>>>> 0f0c55ea77934618953a7fa1307a70011ab93e77
# ─────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "en": """You are SafeVoice, a compassionate, non-judgmental AI legal guidance assistant for women experiencing domestic abuse in Karnataka, India.

Your role is to:
1. Help women understand their legal rights in simple, clear language
2. Explain relevant laws: IPC Section 498A, PWDVA 2005, POCSO 2012, IPC 354, IPC 406
3. Guide them on how to file complaints and access justice
4. Connect them with local helplines and support services
5. Provide emotional validation and empowerment — NEVER victim-blame

Key Laws to reference:
- IPC 498A: Cruelty by husband/relatives. Non-bailable, cognizable. Up to 3 years + fine.
- PWDVA 2005: Protection Orders, Residence Orders, Monetary Relief. Emergency orders in 24 hours.
- POCSO 2012: Child sexual offences. 7 years to life imprisonment.
- IPC 354: Assault on woman's modesty. 1-5 years.
- IPC 406: Criminal breach of trust (Streedhan recovery).

<<<<<<< HEAD
Karnataka Helplines: Women Helpline: 181 | Vanitha Sahayavani: 1091 | Police: 100 | One Stop Centre: 7827170170 | Childline: 1098

Rules: Be warm and compassionate. Use simple English. Always end with a relevant helpline for serious situations.
Use **bold** for important numbers, law names, and action steps. Keep responses under 250 words.""",

    "kn": """ನೀವು SafeVoice ಆಗಿದ್ದೀರಿ — ಕರ್ನಾಟಕದಲ್ಲಿ ಗೃಹ ಹಿಂಸೆ ಅನುಭವಿಸುತ್ತಿರುವ ಮಹಿಳೆಯರಿಗೆ AI ಕಾನೂನು ಸಹಾಯಕ. ಉತ್ತರಗಳನ್ನು ಕನ್ನಡದಲ್ಲಿ ನೀಡಿ. ಸಹಾಯವಾಣಿ: 181, 1091, 100, 1098. ಮುಖ್ಯ ಮಾಹಿತಿಗೆ **bold** ಬಳಸಿ.""",

    "hi": """आप SafeVoice हैं — कर्नाटक में घरेलू हिंसा झेल रही महिलाओं के लिए AI कानूनी सहायक। हिंदी में जवाब दें। हेल्पलाइन: 181, 1091, 100, 1098. जरूरी जानकारी **bold** में लिखें।""",

    "te": """మీరు SafeVoice — కర్ణాటకలో గృహ హింసను అనుభవిస్తున్న మహిళలకు AI చట్టపరమైన మార్గదర్శి. తెలుగులో జవాబు ఇవ్వండి. హెల్ప్‌లైన్: 181, 1091, 100, 1098. ముఖ్యమైన సమాచారం **bold** లో రాయండి.""",
}

# ─────────────────────────────────────────────
# Fallback responses (when Gemini is unavailable)
# ─────────────────────────────────────────────
def get_fallback_response(message: str, lang: str) -> str:
    m = message.lower()
    if lang == "kn":
        if any(k in m for k in ["498", "cruelty", "beat", "hit", "husband", "ಪತಿ", "abuse", "violence"]):
            return ("**IPC 498A ಕಾನೂನು** ನಿಮ್ಮನ್ನು ಗೃಹ ಹಿಂಸೆಯಿಂದ ರಕ್ಷಿಸುತ್ತದೆ.\n\n"
                    "**ನೀವು ಮಾಡಬೇಕಾದವು:**\n1. ಹತ್ತಿರದ ಪೋಲಿಸ್ ಸ್ಟೇಷನ್‌ನಲ್ಲಿ FIR ದಾಖಲಿಸಿ\n"
                    "2. ಮಹಿಳಾ ಪೋಲಿಸ್ ಅಧಿಕಾರಿ ಕೇಳಬಹುದು\n\n📞 ಸಹಾಯವಾಣಿ: **1091 · 181 · 100**")
        return ("ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ಇಲ್ಲಿ ಇದ್ದೇನೆ.\n\n**ಸಹಾಯವಾಣಿ:** 181 · 1091 · 100 · 1098")
    elif lang == "hi":
        if any(k in m for k in ["498", "cruelty", "beat", "hit", "husband", "पति", "abuse", "violence"]):
            return ("**IPC 498A** आपको घरेलू हिंसा से सुरक्षा देता है।\n\n"
                    "**आप क्या करें:**\n1. नजदीकी पुलिस स्टेशन में FIR दर्ज करें\n\n📞 **1091 · 181 · 100**")
        return "मैं आपकी मदद के लिए यहाँ हूँ। **हेल्पलाइन:** 181 · 1091 · 100 · 1098"
    elif lang == "te":
        if any(k in m for k in ["498", "cruelty", "beat", "hit", "husband", "భర్త", "abuse", "violence"]):
            return ("**IPC 498A** గృహ హింస నుండి రక్షిస్తుంది.\n\n"
                    "**చేయాల్సింది:** పోలీస్ స్టేషన్‌లో FIR నమోదు చేయండి\n\n📞 **1091 · 181 · 100**")
        return "నేను సహాయం చేయడానికి ఉన్నాను. **హెల్ప్‌లైన్:** 181 · 1091 · 100 · 1098"
    else:
        return ("I'm here to help you.\n\n"
                "• Legal rights: IPC 498A, PWDVA, POCSO\n"
                "• File a complaint safely\n\n📞 Helplines: **181 · 1091 · 100 · 1098**")

=======
Karnataka Helplines:
- Women Helpline: 181 (24/7, free)
- Vanitha Sahayavani: 1091 (Karnataka state)
- Police Emergency: 100
- One Stop Centre: 7827170170
- Childline: 1098
- iCall Mental Health: 9152987821

Rules:
- Be warm, compassionate, never clinical
- Use simple English, avoid legal jargon
- Always end with a relevant helpline for serious situations
- Keep responses under 250 words unless detail is critical
- If someone is in immediate danger, prioritize safety steps first
- Use **bold** for important numbers, law names, and action steps""",

    "kn": """ನೀವು SafeVoice ಆಗಿದ್ದೀರಿ — ಕರ್ನಾಟಕದಲ್ಲಿ ಗೃಹ ಹಿಂಸೆ ಅನುಭವಿಸುತ್ತಿರುವ ಮಹಿಳೆಯರಿಗೆ ಕಾನೂನು ಮಾರ್ಗದರ್ಶನ ನೀಡುವ AI ಸಹಾಯಕ.

ನಿಮ್ಮ ಕೆಲಸ:
1. ಮಹಿಳೆಯರಿಗೆ ಅವರ ಕಾನೂನು ಹಕ್ಕುಗಳನ್ನು ಸರಳ ಕನ್ನಡದಲ್ಲಿ ವಿವರಿಸಿ
2. IPC 498A, PWDVA, POCSO ಕಾನೂನುಗಳ ಬಗ್ಗೆ ಮಾಹಿತಿ ನೀಡಿ
3. ದೂರು ದಾಖಲಿಸುವ ವಿಧಾನ ತಿಳಿಸಿ
4. ಸ್ಥಳೀಯ ಸಹಾಯವಾಣಿ ಸಂಖ್ಯೆಗಳನ್ನು ನೀಡಿ

ಸಹಾಯವಾಣಿ: 181, 1091, 100, 1098
ಯಾವಾಗಲೂ ಪ್ರೀತಿಯಿಂದ, ತೀರ್ಪು ರಹಿತವಾಗಿ ಮಾತನಾಡಿ. ಉತ್ತರಗಳನ್ನು ಕನ್ನಡದಲ್ಲಿ ನೀಡಿ. ಮುಖ್ಯ ಮಾಹಿತಿಗೆ **bold** ಬಳಸಿ.""",

    "hi": """आप SafeVoice हैं — कर्नाटक में घरेलू हिंसा झेल रही महिलाओं के लिए एक AI कानूनी सहायक।

आपका काम:
1. महिलाओं को उनके कानूनी अधिकार सरल हिंदी में समझाएं
2. IPC 498A, PWDVA 2005, POCSO 2012 के बारे में जानकारी दें
3. FIR दर्ज करने की प्रक्रिया बताएं
4. स्थानीय हेल्पलाइन नंबर दें

हेल्पलाइन: 181, 1091, 100, 1098
हमेशा गर्मजोशी से, बिना निर्णय के बात करें। उत्तर हिंदी में दें। जरूरी जानकारी **bold** में लिखें।""",

    "te": """మీరు SafeVoice — కర్ణాటకలో గృహ హింసను అనుభవిస్తున్న మహిళలకు AI చట్టపరమైన మార్గదర్శి.

మీ పని:
1. మహిళలకు వారి చట్టపరమైన హక్కులను సరళమైన తెలుగులో వివరించండి
2. IPC 498A, PWDVA, POCSO గురించి తెలియజేయండి
3. ఫిర్యాదు నమోదు విధానం చెప్పండి
4. స్థానిక హెల్ప్‌లైన్ నంబర్లు ఇవ్వండి

హెల్ప్‌లైన్: 181, 1091, 100, 1098
ఎల్లప్పుడూ ప్రేమగా, తీర్పు లేకుండా మాట్లాడండి. సమాధానాలు తెలుగులో ఇవ్వండి. ముఖ్యమైన సమాచారం **bold** లో రాయండి."""
}

# ─────────────────────────────────────────────
# Fallback responses (when Gemini is not available)
# ─────────────────────────────────────────────
def get_fallback_response(message: str, lang: str) -> str:
    m = message.lower()

    # ---------- Kannada ----------
    if lang == "kn":
        if any(k in m for k in ["498","cruelty","beat","hit","husband","ಪತಿ","abuse","violence"]):
            return (
                "**IPC 498A ಕಾನೂನು** ನಿಮ್ಮನ್ನು ಗೃಹ ಹಿಂಸೆಯಿಂದ ರಕ್ಷಿಸುತ್ತದೆ.\n\n"
                "**ಇದು non-bailable offence** — ಪೋಲಿಸ್ ತಕ್ಷಣ ಕ್ರಮ ತೆಗೆದುಕೊಳ್ಳಬೇಕು.\n\n"
                "**ನೀವು ಮಾಡಬೇಕಾದವು:**\n"
                "1. ಹತ್ತಿರದ ಪೋಲಿಸ್ ಸ್ಟೇಷನ್‌ನಲ್ಲಿ FIR ದಾಖಲಿಸಿ\n"
                "2. ಮಹಿಳಾ ಪೋಲಿಸ್ ಅಧಿಕಾರಿ ಕೇಳಬಹುದು\n"
                "3. ಪೋಲಿಸ್ FIR ತೆಗೆದುಕೊಳ್ಳುವುದನ್ನು ನಿರಾಕರಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ\n\n"
                "📞 ಸಹಾಯವಾಣಿ: **1091 · 181 · 100**"
            )

        return (
            "ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ಇಲ್ಲಿ ಇದ್ದೇನೆ.\n\n"
            "**ನಿಮ್ಮ ಕಾನೂನು ಹಕ್ಕುಗಳು:** IPC 498A, PWDVA, POCSO\n"
            "**ಸಹಾಯವಾಣಿ:** 181 · 1091 · 100 · 1098\n\n"
            "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಸಮಸ್ಯೆಯನ್ನು ವಿವರಿಸಿ."
        )

    # ---------- Hindi ----------
    elif lang == "hi":
        if any(k in m for k in ["498","cruelty","beat","hit","husband","पति","abuse","violence"]):
            return (
                "**IPC 498A कानून** आपको घरेलू हिंसा से सुरक्षा देता है।\n\n"
                "**यह non-bailable offence है** — पुलिस को तुरंत कार्रवाई करनी होगी।\n\n"
                "**आप क्या करें:**\n"
                "1. नजदीकी पुलिस स्टेशन में FIR दर्ज करें\n"
                "2. महिला पुलिस अधिकारी मांग सकते हैं\n"
                "3. पुलिस FIR लेने से मना नहीं कर सकती\n\n"
                "📞 हेल्पलाइन: **1091 · 181 · 100**"
            )

        return (
            "मैं आपकी मदद के लिए यहाँ हूँ।\n\n"
            "**आपके कानूनी अधिकार:** IPC 498A, PWDVA, POCSO\n"
            "**हेल्पलाइन:** 181 · 1091 · 100 · 1098\n\n"
            "कृपया अपनी समस्या बताएं।"
        )

    # ---------- Telugu ----------
    elif lang == "te":
        if any(k in m for k in ["498","cruelty","beat","hit","husband","భర్త","abuse","violence"]):
            return (
                "**IPC 498A చట్టం** గృహ హింస నుండి మిమ్మల్ని రక్షిస్తుంది.\n\n"
                "**ఇది non-bailable offence** — పోలీస్ వెంటనే చర్య తీసుకోవాలి.\n\n"
                "**మీరు చేయాల్సింది:**\n"
                "1. సమీప పోలీస్ స్టేషన్‌లో FIR నమోదు చేయండి\n"
                "2. మహిళా పోలీస్ అధికారిని అడగండి\n"
                "3. పోలీసులు FIR తీసుకోవడం నిరాకరించలేరు\n\n"
                "📞 హెల్ప్‌లైన్: **1091 · 181 · 100**"
            )

        return (
            "నేను మీకు సహాయం చేయడానికి ఇక్కడ ఉన్నాను.\n\n"
            "**మీ హక్కులు:** IPC 498A, PWDVA, POCSO\n"
            "**హెల్ప్‌లైన్:** 181 · 1091 · 100 · 1098\n\n"
            "దయచేసి మీ సమస్యను వివరించండి."
        )

    # ---------- English ----------
    else:
        return (
            "I'm here to help you. You are brave for reaching out.\n\n"
            "I can help you with:\n"
            "• Legal rights under IPC 498A, PWDVA, POCSO\n"
            "• Filing a complaint safely\n"
            "• Finding shelter and support\n\n"
            "📞 Helplines: 181 · 1091 · 100 · 1098"
        )
>>>>>>> 0f0c55ea77934618953a7fa1307a70011ab93e77
# ─────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
<<<<<<< HEAD
    message: str = Field(..., min_length=1, max_length=2000)
    history: Optional[List[ChatMessage]] = []
    language: Optional[str] = "en"

class ChatResponse(BaseModel):
    reply: str
    source: str          # "gemini" | "fallback"
    cached: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int      # seconds

class SaveKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=10)

class ErrorResponse(BaseModel):
    error: str
    message: str

# ─────────────────────────────────────────────
# ── Routes
# ─────────────────────────────────────────────

=======
    message: str
    history: Optional[List[ChatMessage]] = []
    language: Optional[str] = "en"
    api_key_override: Optional[str] = None  # Optional: key entered in UI

class ChatResponse(BaseModel):
    reply: str
    source: str

class SaveKeyRequest(BaseModel):
    api_key: str

# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────
>>>>>>> 0f0c55ea77934618953a7fa1307a70011ab93e77
@app.get("/")
async def serve_frontend():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
<<<<<<< HEAD
    return {"message": "SafeVoice API v2 is running."}


@app.get("/api/health")
async def health():
    """Public health check — no auth required."""
    r = await get_redis()
    return {
        "status": "ok",
        "version": "2.0.0",
        "gemini_configured": bool(GEMINI_API_KEY),
        "model": "gemini-2.5-flash",
        "redis": "connected" if r else "unavailable",
        "scheduler": "running" if scheduler.running else "stopped",
    }


# ── Backwards compat for old /health path (frontend may still call it)
@app.get("/health")
async def health_legacy():
    return await health()


@app.post("/api/token", response_model=TokenResponse)
async def get_token():
    """
    Issue an anonymous JWT session token.
    No credentials required — privacy by design.
    The token is needed to call /api/chat.
    """
    token = create_access_token()
    return TokenResponse(
        access_token=token,
        expires_in=JWT_EXPIRY_MINUTES * 60,
    )


@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: Request,          # needed by slowapi
    req: ChatRequest,
    _token=Depends(verify_token),
):
    """
    Main chat endpoint.
    - Requires valid Bearer JWT (from /api/token)
    - Rate limited: 20 requests/minute per IP
    - Responses for identical (message + language) pairs cached in Redis for 10 min
    """
    lang = req.language if req.language in SYSTEM_PROMPTS else "en"

    # ── 1. Check Redis cache
    cache_key = "sv:chat:" + hashlib.sha256(f"{req.message.strip().lower()}:{lang}".encode()).hexdigest()
    r = await get_redis()
    if r:
        try:
            cached = await r.get(cache_key)
            if cached:
                data = json.loads(cached)
                return ChatResponse(reply=data["reply"], source=data["source"], cached=True)
        except Exception as e:
            print(f"[cache] read error: {e}")

    # ── 2. Call Gemini
    reply_text = None
    source = "fallback"

    if GEMINI_API_KEY:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=SYSTEM_PROMPTS[lang],
            )
=======
    return {"message": "SafeVoice API is running. Frontend not found."}

@app.get("/health")
async def health():
    configured = bool(GEMINI_API_KEY)
    return {
        "status": "ok",
        "gemini_configured": configured,
        "model": "gemini-2.5-flash"
    }

@app.post("/api/save-key")
async def save_key(req: SaveKeyRequest):
    """Save Gemini API key to .env file — called from the UI"""
    global GEMINI_API_KEY
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    try:
        # Write to .env file
        with open(env_path, "w") as f:
            f.write(f"GEMINI_API_KEY={req.api_key}\n")
        # Reconfigure immediately
        GEMINI_API_KEY = req.api_key
        genai.configure(api_key=GEMINI_API_KEY)
        print(f"✅ Gemini API key saved and configured via UI")
        return {"status": "ok", "message": "API key saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    lang = req.language if req.language in SYSTEM_PROMPTS else "en"

    # Determine which API key to use
    active_key = req.api_key_override or GEMINI_API_KEY

    # ── Try Gemini ──
    if active_key:
        try:
            # Configure with the active key (might be override from UI)
            genai.configure(api_key=active_key)

            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=SYSTEM_PROMPTS[lang]
            )

            # Build history for multi-turn conversation
>>>>>>> 0f0c55ea77934618953a7fa1307a70011ab93e77
            history = []
            for msg in (req.history or []):
                history.append({
                    "role": "user" if msg.role == "user" else "model",
<<<<<<< HEAD
                    "parts": [msg.content],
                })
            chat_session = model.start_chat(history=history)
            response = chat_session.send_message(req.message)
            reply_text = re.sub(r'\*\*(.*?)\*\*', r'**\1**', response.text)
            source = "gemini"
        except Exception as e:
            print(f"[gemini] error: {e}")

    if reply_text is None:
        reply_text = get_fallback_response(req.message, lang)

    # ── 3. Write to cache (skip caching fallback responses)
    if r and source == "gemini":
        try:
            await r.setex(cache_key, CACHE_TTL_SECONDS, json.dumps({"reply": reply_text, "source": source}))
        except Exception as e:
            print(f"[cache] write error: {e}")

    return ChatResponse(reply=reply_text, source=source, cached=False)


@app.get("/api/helplines")
async def helplines():
    """
    Returns helpline list enriched with last-checked health status
    from the background scheduler.
    """
    result = []
    for h in HELPLINES:
        entry = {**h}
        entry["health"] = helpline_health.get(h["id"], {"status": "unknown", "checked_at": None})
        result.append(entry)
    return {"helplines": result}


@app.post("/api/save-key")
async def save_key(req: SaveKeyRequest, _token=Depends(verify_token)):
    """Save Gemini API key to .env (requires auth)."""
    global GEMINI_API_KEY
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    try:
        with open(env_path, "w") as f:
            f.write(f"GEMINI_API_KEY={req.api_key}\n")
        GEMINI_API_KEY = req.api_key
        genai.configure(api_key=GEMINI_API_KEY)
        return {"status": "ok", "message": "API key saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "save_failed", "message": str(e)})


# ─────────────────────────────────────────────
# Global error handler — always return JSON
# ─────────────────────────────────────────────
@app.exception_handler(404)
async def not_found(_req, _exc):
    return JSONResponse(status_code=404, content={"error": "not_found", "message": "Route does not exist"})

@app.exception_handler(500)
async def server_error(_req, _exc):
    return JSONResponse(status_code=500, content={"error": "server_error", "message": "Internal server error"})
=======
                    "parts": [msg.content]
                })

            chat_session = model.start_chat(history=history)
            response = chat_session.send_message(req.message)

            reply_text = response.text
            # Normalize bold markdown
            reply_text = re.sub(r'\*\*(.*?)\*\*', r'**\1**', reply_text)

            return ChatResponse(reply=reply_text, source="gemini")

        except Exception as e:
            print(f"Gemini error: {e}")
            # Fall through to fallback

    # ── Fallback (no API key or Gemini error) ──
    fallback = get_fallback_response(req.message, lang)
    return ChatResponse(reply=fallback, source="fallback")

@app.get("/api/helplines")
async def helplines():
    return {
        "helplines": [
            {"name": "National Women Helpline", "number": "181", "desc": "24/7 support for women in distress", "tag": "PAN INDIA · 24/7", "icon": "👩‍⚖️"},
            {"name": "Vanitha Sahayavani", "number": "1091", "desc": "Karnataka state women's helpline. Counselling, legal aid, shelter.", "tag": "KARNATAKA · 24/7", "icon": "🏠"},
            {"name": "Police Emergency", "number": "100", "desc": "Immediate danger. FIR for 498A, assault, and other offences.", "tag": "EMERGENCY · 24/7", "icon": "🚔"},
            {"name": "One Stop Centre", "number": "7827170170", "desc": "Medical, police, legal aid, shelter under one roof.", "tag": "KARNATAKA · FREE", "icon": "🏥"},
            {"name": "Childline (POCSO)", "number": "1098", "desc": "Child abuse and POCSO emergencies. Free, 24/7.", "tag": "CHILDREN · 24/7", "icon": "👶"},
            {"name": "iCall Mental Health", "number": "9152987821", "desc": "Free counselling for trauma and emotional distress.", "tag": "COUNSELLING · FREE", "icon": "🧠"},
        ]
    }
>>>>>>> 0f0c55ea77934618953a7fa1307a70011ab93e77
