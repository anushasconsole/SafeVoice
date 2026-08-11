#!/bin/bash
echo "🛡️  Starting SafeVoice..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+"
    exit 1
fi

cd backend

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "📦 Installing dependencies..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Check API key
if grep -q "your_gemini_api_key_here" .env 2>/dev/null; then
    echo "⚠️  WARNING: Please set your GEMINI_API_KEY in backend/.env"
    echo "   Get a free key at: https://aistudio.google.com/apikey"
    echo ""
fi

echo "🚀 Server starting at http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
