@echo off
echo Starting Private LLM Stack...

echo [1/3] Restarting Cloudflare Tunnel service...
sc stop cloudflared >nul 2>&1
timeout /t 2 /nobreak >nul
sc start cloudflared
timeout /t 3 /nobreak >nul

echo [2/3] Checking Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo Ollama not running - starting...
    start "" "C:\Users\Moonga Dev\AppData\Local\Programs\Ollama\ollama.exe" serve
    timeout /t 5 /nobreak >nul
) else (
    echo Ollama is already running.
)

echo [3/3] Starting FastAPI proxy...
set LLM_API_KEY=PN30ZENng6XE09CJ_n5VUnIBcBfbKWPkO0XGJaLvfUo
start "LLM Proxy" cmd /k "cd /d "C:\Moonga_agent\Dev Projects\privateLLM" && uvicorn server:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul
echo.
echo Checking health...
curl -s https://llm.minnal.io/health
echo.
echo Done. Keep this window open or close it - proxy runs in its own window.
pause
