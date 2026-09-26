# setup.ps1 — Levanta todo el sistema multi-agente en Windows
# Uso:  powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Continue"
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Sistema Multi-Agente – Setup Completo" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan

# 1. Levantar contenedores
Write-Host "`n[1/6] Levantando contenedores Docker …" -ForegroundColor Yellow
docker compose down -v 2>$null
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al levantar Docker. ¿Docker Desktop está corriendo?" -ForegroundColor Red
    exit 1
}

# 2. Esperar servicios
Write-Host "`n[2/6] Esperando RabbitMQ + PostgreSQL …" -ForegroundColor Yellow
Start-Sleep -Seconds 15

# 3. Verificar/crear modelo de Ollama para embeddings
Write-Host "`n[3/6] Verificando modelo de embeddings (nomic-embed-text) …" -ForegroundColor Yellow
$embModel = "nomic-embed-text"
$exists = ollama list 2>$null | Select-String $embModel
if (-not $exists) {
    Write-Host "  Descargando $embModel (~275MB) …" -ForegroundColor Yellow
    ollama pull $embModel
} else {
    Write-Host "  ✓ $embModel ya disponible" -ForegroundColor Green
}

# 4. Verificar modelo de generación
Write-Host "`n[4/6] Verificando modelo de generación …" -ForegroundColor Yellow
$genModel = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "gemma3:4b" }
$exists = ollama list 2>$null | Select-String $genModel
if (-not $exists) {
    Write-Host "  Descargando $genModel …" -ForegroundColor Yellow
    ollama pull $genModel
} else {
    Write-Host "  ✓ $genModel ya disponible" -ForegroundColor Green
}

# 5. Poblar datos de ejemplo (tendencias, competencia)
Write-Host "`n[5/6] Poblando datos de ejemplo en PostgreSQL …" -ForegroundColor Yellow
python seed_data.py

# 6. Verificar agentes
Write-Host "`n[6/6] Verificando agentes …" -ForegroundColor Yellow
Start-Sleep -Seconds 3

try {
    $h1 = Invoke-RestMethod -Uri http://localhost:8000/health -TimeoutSec 5
    Write-Host "  ✓ Agente Ideación:   $($h1.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Agente Ideación:   NO RESPONDE" -ForegroundColor Red
}
try {
    $h2 = Invoke-RestMethod -Uri http://localhost:8001/health -TimeoutSec 5
    Write-Host "  ✓ Agente Publicación: $($h2.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Agente Publicación: NO RESPONDE" -ForegroundColor Red
}
try {
    $tools = Invoke-RestMethod -Uri http://localhost:8000/tools -TimeoutSec 5
    Write-Host "  ✓ Tools disponibles: $($tools.tools.Count)" -ForegroundColor Green
} catch {}

Write-Host "`n═══════════════════════════════════════" -ForegroundColor Green
Write-Host " Setup completado" -ForegroundColor Green
Write-Host "═══════════════════════════════════════" -ForegroundColor Green
Write-Host @"

URLs:
  RabbitMQ UI:   http://localhost:15672 (user/password)
  Ideación:      http://localhost:8000/health | /tools
  Publicación:   http://localhost:8001/health | /tools

Comandos:
  Enviar brief:  python enviar_brief.py "Tu brief aquí"
  Prueba E2E:    python prueba_e2e.py
  Ver logs:      docker compose logs -f agente-ideacion agente-publicacion
  Seed data:     python seed_data.py
"@
