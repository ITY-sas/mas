# Script de arranque para el Frontend BFF (Windows PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Iniciando Multi-Agent Studio (Frontend + BFF)          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Definir puerto (por defecto 3000)
$env:PORT = if ($env:PORT) { $env:PORT } else { "3000" }
$env:ORCHESTRATOR_URL = if ($env:ORCHESTRATOR_URL) { $env:ORCHESTRATOR_URL } else { "http://localhost:8002" }
$env:AGENTE_IDEACION_URL = if ($env:AGENTE_IDEACION_URL) { $env:AGENTE_IDEACION_URL } else { "http://localhost:8000" }
$env:AGENTE_PUBLICACION_URL = if ($env:AGENTE_PUBLICACION_URL) { $env:AGENTE_PUBLICACION_URL } else { "http://localhost:8001" }
$env:LLM_GATEWAY_URL = if ($env:LLM_GATEWAY_URL) { $env:LLM_GATEWAY_URL } else { "http://localhost:8003" }
$env:TOOL_CLIENT_URL = if ($env:TOOL_CLIENT_URL) { $env:TOOL_CLIENT_URL } else { "http://localhost:8010" }
$env:TOOL_RAG_URL = if ($env:TOOL_RAG_URL) { $env:TOOL_RAG_URL } else { "http://localhost:8013" }
$env:REDIS_URL = if ($env:REDIS_URL) { $env:REDIS_URL } else { "redis://localhost:6379" }

Write-Host "  URL Local: http://localhost:$env:PORT" -ForegroundColor Green
Write-Host "  Orquestador conectado: $env:ORCHESTRATOR_URL" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# Ejecutar el servidor Python
python -m uvicorn frontend.server:app --host 0.0.0.0 --port $env:PORT
