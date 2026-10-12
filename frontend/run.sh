#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "  Iniciando Multi-Agent Studio (Frontend + BFF)          "
echo "=========================================================="

export PORT=${PORT:-3000}
export ORCHESTRATOR_URL=${ORCHESTRATOR_URL:-http://localhost:8002}
export AGENTE_IDEACION_URL=${AGENTE_IDEACION_URL:-http://localhost:8000}
export AGENTE_PUBLICACION_URL=${AGENTE_PUBLICACION_URL:-http://localhost:8001}
export LLM_GATEWAY_URL=${LLM_GATEWAY_URL:-http://localhost:8003}
export TOOL_CLIENT_URL=${TOOL_CLIENT_URL:-http://localhost:8010}
export TOOL_RAG_URL=${TOOL_RAG_URL:-http://localhost:8013}
export REDIS_URL=${REDIS_URL:-redis://localhost:6379}

echo "  URL Local: http://localhost:${PORT}"
echo "  Orquestador conectado: ${ORCHESTRATOR_URL}"
echo "=========================================================="

python -m uvicorn frontend.server:app --host 0.0.0.0 --port ${PORT}
