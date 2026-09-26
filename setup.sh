#!/usr/bin/env bash
# setup.sh — Levanta todo el sistema en Linux/macOS
# Uso:  chmod +x setup.sh && ./setup.sh

set -e

echo "======================================"
echo " Sistema Multi-Agente – Setup"
echo "======================================"

# 1. Levantar contenedores
echo -e "\n[1/4] Levantando contenedores …"
docker compose up -d --build

# 2. Esperar servicios
echo -e "\n[2/4] Esperando servicios (RabbitMQ + PostgreSQL) …"
sleep 15

# 3. Modelo Ollama
echo -e "\n[3/4] Verificando modelo de Ollama …"
MODEL="llama3.2:1b"
if docker exec ollama ollama list 2>/dev/null | grep -q "$MODEL"; then
    echo "  Modelo $MODEL ya disponible."
else
    echo "  Descargando $MODEL (puede tardar) …"
    docker exec ollama ollama pull "$MODEL"
fi

# 4. Verificar agentes
echo -e "\n[4/4] Verificando agentes …"
sleep 3

if curl -sf http://localhost:8000/health > /dev/null; then
    echo "  Agente Ideación:    healthy"
else
    echo "  Agente Ideación:    NO RESPONDE"
fi

if curl -sf http://localhost:8001/health > /dev/null; then
    echo "  Agente Publicación: healthy"
else
    echo "  Agente Publicación: NO RESPONDE"
fi

echo ""
echo "======================================"
echo " Setup completado"
echo "======================================"
echo ""
echo "Enlaces útiles:"
echo "  RabbitMQ UI:  http://localhost:15672  (user / password)"
echo "  Ideación:     http://localhost:8000/health"
echo "  Publicación:  http://localhost:8001/health"
echo ""
echo "Para ejecutar la prueba E2E:"
echo "  pip install pika psycopg2-binary"
echo "  python prueba_e2e.py"
echo ""
echo "Para ver logs:"
echo "  docker compose logs -f agente-ideacion"
echo "  docker compose logs -f agente-publicacion"
