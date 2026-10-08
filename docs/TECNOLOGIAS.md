# Stack Tecnológico

## Mapa tecnológico por capa

```
┌─ API / Orquestación ─────────────────────────────────────────────────┐
│ FastAPI + Uvicorn   (orquestador, agentes, tools, gateway)           │
│ LangGraph 1.2       (grafos del supervisor y de cada agente)         │
│ langgraph-checkpoint-redis  (RedisSaver: checkpoints externos)       │
│ Pydantic            (esquemas de API del gateway)                    │
├─ Mensajería ─────────────────────────────────────────────────────────┤
│ RabbitMQ (AMQP 0-9-1) + pika   (eventos durables + RPC)             │
├─ Datos / Estado ─────────────────────────────────────────────────────┤
│ PostgreSQL 16 + pgvector  (datos de negocio + historial de chat)     │
│ Redis Stack 7.4           (checkpoints LangGraph, TaskStore,         │
│                            caché de prompts, pub/sub de tareas)      │
├─ LLM ────────────────────────────────────────────────────────────────┤
│ LLM Gateway propio       (balanceo, backoff, fallback, caché)        │
│ Ollama (host)             (gemma3:4b, mistral-nemo,                  │
│                            nomic-embed-text, …)                      │
│ httpx / requests          (transporte HTTP)                          │
├─ Infraestructura ────────────────────────────────────────────────────┤
│ Docker + docker compose   (14 servicios)                             │
│ rss vía requests + xml.etree  (noticias y trending Google News)       │
└──────────────────────────────────────────────────────────────────────┘
```

## Papel de cada tecnología

### LangGraph 1.2 — el patrón de agentes, NO la coordinación

LangGraph se usa en **dos niveles** y sólo para lo que aporta:

| Dónde | Qué modela | Por qué |
|-------|-----------|---------|
| `orchestrator/multi_agent/supervisor.py` | Grafo supervisor: `decide → dispatch_ideacion → dispatch_publicacion → END` | El ciclo de planificación queda como **grafo checkpointeable**: `interrupt()` suspende y `Command(resume=…)` retoma desde Redis sin memoria en el proceso |
| `agente_ideacion/graph.py`, `agente_publicacion/graph.py` | Grafo de 4 nodos por agente | Cada agente microservicio posee su flujo (carga contexto → enriquece → genera → persiste) con su propio checkpointer |

Lo que **no** se hace con LangGraph (y es deliberado):

- La coordinación entre orquestador y agentes **no** son subgrafos en memoria:
  son **eventos `agent.task.triggered` / `agent.task.completed`** por RabbitMQ.
- El estado del ciclo **no** vive en el `State` del proceso: vive en Redis
  (`RedisSaver`, `thread_id = task_id`).
- Los agentes **no** usan `@tool` de LangChain para la lógica de negocio:
  usan `ToolRegistry` (Tool Discovery → contratos REST). Sí existe un puente
  `as_langchain_tools()` que materializa los manifiestos como `BaseTool`
  cuando un grafo quiera usarlos formalmente.

### Patrones de agentes cubiertos (requisitos del proyecto)

| Requisito | Tecnología / módulo |
|-----------|---------------------|
| 1. Estado externo del ciclo (ReAct/plan) + historial de chat | `langgraph-checkpoint-redis` (`RedisSaver`) + `common/task_store.py` (Redis) + `orchestrator/history.py` (PostgreSQL `chat_history`) |
| 2. Tools-as-a-Service + tool discovery | `common/contracts.py` (manifiesto `/.well-known/tool-manifest`, envelope) + `common/tool_client.py` (`ToolRegistry`: discover → call → `as_langchain_tools`) + FastAPI en cada tool |
| 3. Resiliencia del bucle asíncrono en RabbitMQ | `common/events.py` (dataclass `Event`, colas durables, `EventConsumer` con reconexión y ack manual) + `common/rpc.py` (RPC sobre eventos) + `common/agent_runner.py` (idempotencia at-least-once) |
| 4. LLM Gateway centralizado | `llm_gateway/` (`providers.py` balanceo ponderado + salud, `resilience.py` backoff exponencial + cadena de fallback, `cache.py` caché Redis) + `common/gateway_client.py` (único cliente) |

### RabbitMQ vs Kafka

Se usa **RabbitMQ** (colas durables, acks, reentrega, RPC por eventos) porque
ya estaba en la infraestructura y cubre el patrón requerido. **Kafka** sería
la alternativa en producción si se necesita re-consumo histórico, retención
larga de eventos o streaming de alto throughput — el contrato de `Event` es
JSON plano, portable a un topic de Kafka sin cambiar los consumidores.

### Redis Stack (no Redis simple)

`langgraph-checkpoint-redis` exige **RedisJSON + RediSearch**, así que la
imagen es `redis/redis-stack-server:7.4.0-v3`. Redis sostiene:

- checkpoints del supervisor (`thread_id = task_id`) y de cada agente
  (`thread_id = {agente}:{task_id}`),
- `TaskStore` (metadatos/resultados de tarea) + canales pub/sub de espera,
- caché de prompts y embeddings del gateway (`llm:{kind}:{sha256}`),
- `agent.state:*` (serialización de estado de agente para su endpoint).

### PostgreSQL + pgvector — datos de negocio y memoria multi-tenant

| Tabla | Dueña | Rol |
|-------|-------|-----|
| `organizations`, `users`, `organization_members` | tool-client | Tenancy y membresías |
| `brands`, `brand_members` | tool-client | Marca, perfil, audiencia y permisos |
| `clientes`, `legacy_client_brand` | Compatibilidad | Migración de clientes existentes |
| `tendencias` | tool-trends | Embeddings de tendencias (RAG) |
| `referencias_competencia` | tool-competitors | Enfoques de competencia |
| `ideas_generadas` | tool-rag | Memoria RAG de ideas filtrada por `brand_id` |
| `publicaciones_generadas` | tool-rag | Publicaciones filtradas por `brand_id` |
| `brand_sources`, `brand_documents`, `brand_chunks` | tool-rag | Ingesta y memoria documental con scopes |
| `brand_evidence` | tool-rag | Procedencia y evidencias |
| `brand_channels` | tool-postiz | Canales de publicación por marca |
| `chat_history` | orquestador | Historial durable de la conversación |

### Ollama (LLM local)

Modelos por defecto (`.env`):

- `OLLAMA_MODEL=gemma3:4b` — generación de ideas y posts
- `LLM_FALLBACK_MODEL=mistral-nemo` — cadena de fallback del gateway
- `EMBEDDING_MODEL=nomic-embed-text` — embeddings (768 dimensiones)

Acceso **exclusivamente** a través del LLM Gateway: ningún otro componente
abre conexión con `:11434`.

## Versiones mínimas verificadas

| Paquete | Versión | Nota |
|---------|---------|------|
| Python | 3.10 (host) / 3.11 (imágenes) | LangGraph requiere ≥3.10 |
| langgraph | 1.2.12 | `interrupt()` / `Command(resume=…)` |
| langgraph-checkpoint-redis | 0.5.2 | RedisSaver |
| fastapi / uvicorn | latest | APIs HTTP |
| pika | latest | AMQP 0-9-1 |
| psycopg2-binary | latest | PostgreSQL |
| requests | latest | Cliente HTTP de tools y gateway |
| redis (Stack) | 7.4.0-v3 | RedisJSON + RediSearch |
| PostgreSQL | 16 + pgvector | Búsqueda vectorial |
