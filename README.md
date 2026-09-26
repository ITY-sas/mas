# Prueba de Concepto de Sistema Multi-Agente Basado en Microservicios

## Arquitectura

```
                         ┌──────────────────────────────────────┐
                         │    ORQUESTADOR LangGraph (8002)      │
                         │                                      │
   Brief ──────────────► │    Supervisor → Ideación → Publicación│
   (POST /process        │    (estado compartido SupervisorState)│
    o RabbitMQ)          └──────────┬───────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
             ┌────────────┐  ┌───────────┐  ┌──────────────┐
             │  LangChain  │  │  Ollama   │  │ PostgreSQL   │
             │  @tool (6)  │  │  (LLM)    │  │ + pgvector   │
             └──────┬─────┘  └───────────┘  └──────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   PostgreSQL   Google News   Ollama
   (RAG)        RSS           (embeddings)
```

### También disponible: agentes individuales (RabbitMQ)

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

### Vía orquestador LangGraph (recomendado)

1. Brief llega por `POST /process` o RabbitMQ `ideation_queue`
2. **Supervisor** (LangGraph) evalúa el estado → enruta a agente de **Ideación**
3. **Agente Ideación** (StateGraph): `load_context` → `fetch_news` → `generate_idea` → `save_idea`
4. **Supervisor** evalúa → enruta a agente de **Publicación**
5. **Agente Publicación** (StateGraph): `load_context` → `fetch_trending` → `generate_post` → `save_post`
6. **Supervisor** evalúa → ambos completados → `END`

### Vía RabbitMQ (agentes individuales)

1. Se publica un **brief** en `ideation_queue`
2. **Agente de Ideación** recibe el brief → llama a **Ollama** → guarda en **PostgreSQL** → publica en `publication_queue`
3. **Agente de Publicación** recibe la idea → llama a **Ollama** → guarda en **PostgreSQL**

## Implementación y No Implementación

- **Implementado**:
  - ✅ **Orquestador multi-agente con LangGraph** (patrón supervisor, 8002)
  - ✅ **6 LangChain tools** registradas como `@tool`
  - ✅ **Agentes como StateGraph** (ideación + publicación como subgrafos)
  - Agente de Ideación (Ollama + PostgreSQL + RabbitMQ + FastAPI)
  - Agente de Publicación (Ollama + PostgreSQL + RabbitMQ + FastAPI)
  - RabbitMQ con healthchecks
  - PostgreSQL con extensión pgvector
  - Un único proveedor LLM local (Ollama)
  - Prueba end-to-end (`prueba_e2e.py` + `prueba_orquestador.py`)
  - Scripts de setup (`setup.ps1` / `setup.sh`)
  - Suite de tests: 99+ tests (unit + integration + performance)

- **No Implementado**:
  - Agente de Edición
  - API Gateway, Vault, MinIO, Prometheus/Grafana, ELK, Jaeger
  - Cadena de fallback multi-proveedor de LLM

## Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) con Docker Compose
- Python 3.10+ (para pruebas y scripts)
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
# 1. Levantar todos los servicios (incluye orquestador LangGraph)
docker compose up -d --build

# 2. Esperar a que estén listos (~15 segundos)

# 3. Verificar servicios
curl http://localhost:8000/health   # Agente Ideación
curl http://localhost:8001/health   # Agente Publicación
curl http://localhost:8002/health   # Orquestador LangGraph
```

## Ejecutar las pruebas E2E

```bash
# Prueba clásica (agentes individuales vía RabbitMQ)
pip install pika psycopg2-binary
python prueba_e2e.py

# Prueba del orquestador LangGraph (directo, sin RabbitMQ)
pip install langgraph langchain langchain-ollama
python prueba_orquestador.py
```

## Ejecutar tests

```bash
# Suite completa
pytest tests/ -v

# Solo unitarios (sin servicios externos)
pytest tests/unit/ -v

# Solo integración (requiere Docker + Ollama)
pytest tests/integration/ -v
```

## Endpoints disponibles

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Orquestador LangGraph** | **http://localhost:8002/health** | **Health check** |
| **Orquestador LangGraph** | **http://localhost:8002/tools** | **Tools LangChain** |
| **Orquestador LangGraph** | **http://localhost:8002/graph** | **Estructura del grafo** |
| **Orquestador LangGraph** | **http://localhost:8002/process** | **Ejecutar pipeline (POST)** |
| RabbitMQ UI | http://localhost:15672 | user / password |
| Agente Ideación | http://localhost:8000/health | Health check |
| Agente Ideación | http://localhost:8000/tools | Tools disponibles |
| Agente Publicación | http://localhost:8001/health | Health check |
| Agente Publicación | http://localhost:8001/tools | Tools disponibles |
| PostgreSQL | localhost:5432 | ideation_db / postgres / password |
| Ollama API | http://localhost:11434 | API del LLM |

## Estructura del proyecto

```
proyecto multiagente/
├── orchestrator/               # Orquestador multi-agente con LangGraph
│   ├── multi_agent/
│   │   ├── __init__.py         # Exports del paquete
│   │   ├── state.py            # SupervisorState, IdeacionState, PublicacionState
│   │   ├── tools.py            # 6 LangChain @tool
│   │   ├── ideacion.py         # StateGraph del agente de ideación
│   │   ├── publicacion.py      # StateGraph del agente de publicación
│   │   └── supervisor.py       # Patrón supervisor (decide_next)
│   ├── main.py                 # FastAPI + RabbitMQ + LangGraph (8002)
│   ├── Dockerfile
│   └── requirements.txt        # langgraph, langchain, langchain-ollama
├── agente_ideacion/
│   ├── main.py                 # Agente de ideación (FastAPI + RabbitMQ + Ollama)
│   ├── Dockerfile
│   └── requirements.txt
├── agente_publicacion/
│   ├── main.py                 # Agente de publicación (FastAPI + RabbitMQ + Ollama)
│   ├── Dockerfile
│   └── requirements.txt
├── shared_tools/               # Tools compartidas (cliente, tendencias, competencia, RAG)
├── tests/
│   ├── unit/                   # Tests unitarios (incluye orquestador)
│   ├── integration/            # Tests de integración (incluye pipeline LangGraph)
│   └── performance/            # Tests de rendimiento
├── docs/
│   ├── TECNOLOGIAS.md          # Stack tecnológico (LangGraph incluido)
│   ├── ARQUITECTURA.md         # Arquitectura detallada
│   ├── PLAN_DE_PRUEBAS.md      # Plan de pruebas
│   └── CHANGELOG.md            # Historial de cambios
├── docker-compose.yml          # Orquestación de servicios
├── init.sql                    # Esquema de base de datos
├── prueba_e2e.py               # Prueba E2E (agentes individuales)
├── prueba_orquestador.py       # Prueba E2E (orquestador LangGraph)
├── setup.ps1                   # Setup automático (Windows)
├── setup.sh                    # Setup automático (Linux/macOS)
└── README.md
```

## Solución de problemas

| Problema | Solución |
|----------|----------|
| Orquestador no arranca | `docker compose logs orchestrator` |
| Agentes no arrancan | `docker compose logs agente-ideacion` |
| Ollama sin modelo | Asegúrate de que Ollama local tenga `gemma3:4b` y `nomic-embed-text` |
| RabbitMQ no responde | `docker compose restart rabbitmq` |
| PostgreSQL no listo | `docker compose logs postgres` |
| Prueba falla | Revisa logs y verifica que Ollama esté corriendo en `localhost:11434` |
| Cambiar modelo | Exporta `OLLAMA_MODEL=gemma3:4b` antes de `docker compose up` |
