# Prueba de Concepto de Sistema Multi-Agente Basado en Microservicios

## Arquitectura

```
                         ┌─────────────────────────────────────┐
                         │           RabbitMQ                  │
                         │  ┌─────────────┐ ┌──────────────┐  │
  Brief ──────────────►  │  │ideation_    │ │publication_  │  │
  (prueba_e2e.py)        │  │queue        │ │queue         │  │
                         │  └──────┬──────┘ └──────▲───────┘  │
                         └─────────┼───────────────┼──────────┘
                                   │               │
                    ┌──────────────▼──┐   ┌────────┴───────────┐
                    │ Agente Ideación │──►│ Agente Publicación  │
                    │   (Puerto 8000) │   │    (Puerto 8001)    │
                    └───────┬─────────┘   └────────┬───────────┘
                            │    ┌─────────┐       │
                            ├───►│ Ollama  │◄──────┤
                            │    │  (LLM)  │       │
                            │    └─────────┘       │
                            │                      │
                    ┌───────▼──────────────────────▼───┐
                    │     PostgreSQL + pgvector         │
                    │  (ideas_generadas,                │
                    │   publicaciones_generadas)        │
                    └──────────────────────────────────┘
```

## Flujo de datos

1. Se publica un **brief** en `ideation_queue`
2. **Agente de Ideación** recibe el brief → llama a **Ollama** para generar una idea → guarda en **PostgreSQL** → publica la idea en `publication_queue`
3. **Agente de Publicación** recibe la idea → llama a **Ollama** para generar una publicación → guarda en **PostgreSQL**

## Implementación y No Implementación

- **Implementado**:
  - Agente de Ideación (Ollama + PostgreSQL + RabbitMQ + FastAPI)
  - Agente de Publicación (Ollama + PostgreSQL + RabbitMQ + FastAPI)
  - RabbitMQ con healthchecks
  - PostgreSQL con extensión pgvector
  - Un único proveedor LLM local (Ollama)
  - Prueba end-to-end (`prueba_e2e.py`)
  - Scripts de setup (`setup.ps1` / `setup.sh`)

- **No Implementado**:
  - Agente de Edición
  - API Gateway, Vault, MinIO, Prometheus/Grafana, ELK, Jaeger
  - Fuentes de datos externas reales
  - Cadena de fallback multi-proveedor de LLM
  - Embeddings vectoriales (columnas VECTOR(1536) disponibles pero sin poblar)

## Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) con Docker Compose
- Python 3.9+ (para la prueba E2E)
- ~2 GB de espacio para el modelo de Ollama

## Levantamiento del Sistema

### Opción A: Script automático (recomendado)

**Windows:**
```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

### Opción B: Manual

```bash
# 1. Levantar todos los servicios
docker compose up -d --build

# 2. Esperar a que estén listos (~15 segundos)

# 3. Descargar el modelo de Ollama (solo primera vez)
docker exec ollama ollama pull llama3.2:1b

# 4. Verificar agentes
curl http://localhost:8000/health   # Ideación
curl http://localhost:8001/health   # Publicación
```

## Ejecutar la prueba E2E

```bash
pip install pika psycopg2-binary
python prueba_e2e.py
```

La prueba:
1. Publica un brief de ejemplo en `ideation_queue`
2. Espera a que ambos agentes procesen (hasta 60 s)
3. Consulta PostgreSQL para verificar ideas y publicaciones
4. Muestra un informe con los resultados

## Endpoints disponibles

| Servicio | URL | Descripción |
|----------|-----|-------------|
| RabbitMQ UI | http://localhost:15672 | user / password |
| Agente Ideación | http://localhost:8000/health | Health check |
| Agente Ideación | http://localhost:8000/metrics | Métricas |
| Agente Publicación | http://localhost:8001/health | Health check |
| Agente Publicación | http://localhost:8001/metrics | Métricas |
| PostgreSQL | localhost:5432 | ideation_db / postgres / password |
| Ollama API | http://localhost:11434 | API del LLM |

## Estructura del proyecto

```
proyecto multiagente/
├── agente_ideacion/
│   ├── main.py              # Agente de ideación (FastAPI + RabbitMQ + Ollama)
│   ├── Dockerfile
│   └── requirements.txt
├── agente_publicacion/
│   ├── main.py              # Agente de publicación (FastAPI + RabbitMQ + Ollama)
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml       # Orquestación de servicios
├── init.sql                 # Esquema de base de datos
├── prueba_e2e.py            # Prueba end-to-end
├── setup.ps1                # Setup automático (Windows)
├── setup.sh                 # Setup automático (Linux/macOS)
└── README.md
```

## Solución de problemas

| Problema | Solución |
|----------|----------|
| Agentes no arrancan | `docker compose logs agente-ideacion` |
| Ollama sin modelo | `docker exec ollama ollama pull llama3.2:1b` |
| RabbitMQ no responde | `docker compose restart rabbitmq` |
| PostgreSQL no listo | `docker compose logs postgres` |
| Prueba falla | Revisa logs de ambos agentes y verifica que Ollama tenga el modelo |
| Cambiar modelo | Exporta `OLLAMA_MODEL=llama3.2` antes de `docker compose up` |
