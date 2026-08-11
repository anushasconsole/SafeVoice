@echo off
echo 🛡️  Starting SafeVoice...
echo.

cd backend

if not exist ".venv" (
    echo 📦 Installing dependencies...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate
)

echo 🚀 Server starting at http://localhost:8000
echo    Press Ctrl+C to stop
echo.
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
