# Start the private LLM proxy server
# Prerequisites: Ollama must be running with gemma4:e2b pulled

$ErrorActionPreference = "Stop"

Write-Host "Checking Ollama..." -ForegroundColor Cyan
try {
    $r = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3
    Write-Host "Ollama is up. Models: $($r.models.name -join ', ')" -ForegroundColor Green
} catch {
    Write-Host "Ollama is not running. Start it with: ollama serve" -ForegroundColor Red
    Write-Host "Then pull the model: ollama pull gemma4:e2b" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting FastAPI proxy on http://localhost:8000 ..." -ForegroundColor Cyan
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
