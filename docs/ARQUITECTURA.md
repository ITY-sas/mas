# Arquitectura del Sistema Multi-Agente (microservicios)

## Descripción general

Sistema multi-agente para generación automatizada de contenido de marketing,
implementado como **arquitectura de microservicios** con patrones de agentes
sobre infraestructura de servicios:

| # | Requisito | Cómo se cumple |
|---|-----------|----------------|
| 1 | Orquestador **stateless** con estado externo para el ciclo de planificación y el historial de chat | Checkpoints de LangGraph en **Redis** (`RedisSaver`, `thread_id = task_id`) + `TaskStore` en Redis + historial de chat en **PostgreSQL** (`chat_history`). El proceso no retiene nada entre peticiones: puede reiniciarse o escalar horizontalmente |
| 2 | **Tools-as-a-Service** con tool discovery | 6 microservicios de tools, cada uno publica `GET /.well-known/tool-manifest` (contrato operación → método → endpoint). El `ToolRegistry` los descubre, los invoca por REST/AMQP y los expone como `BaseTool` de LangChain |
| 3 | **Resiliencia asíncrona** sobre RabbitMQ con estructuras de evento definidas | Colas durables + `Event` tipado (`agent.task.triggered`, `agent.task.completed`, `tool.task.triggered`, `tool.task.completed`, `task.completed`), consumidores con reconexión, semántica *at-least-once* e idempotencia por checkpoint |
| 4 | **LLM Gateway centralizado** (balanceo, reintentos con backoff, fallback, caché de prompts) | Microservicio `llm-gateway:8003`. Todo LLM (chat y embeddings) pasa por él; ningún componente habla directo con Ollama |

> **Principio rector**: el agente **no ejecuta código de negocio**. Sólo invoca
> contratos de API (REST sobre manifiestos descubiertos) o publica/consume
> eventos. El orquestador **no ejecuta código de negocio** tampoco: sólo
> planifica, despacha y consolida resultados.

---

## 1. Topología (13 contenedores)

```
                              ┌───────────────────────────────────────────┐
   POST /process              │  ORCHESTRATOR  :8002  (stateless)        │
   ideation_queue ───────────►│                                           │
                              │  LangGraph supervisor                     │
                              │  START → decide → dispatch_ideacion       │
                              │            │  interrupt()  ───────────────┼──┐
                              │            ▼                              │  │
                              │  Command(resume=…) ← agent.task.completed│  │
                              │            │                    ▲         │  │
                              │            ▼                    │         │  │
                              │  dispatch_publicacion → END ────┼─────────┼──┤
                              └──────────────────────────────────┼─────────┼──┘
                                                                 │         │
              estado externo:  Redis (checkpoints + TaskStore)   │         │
                              PostgreSQL (chat_history)          │         │
                                                                 │         ▼
        ┌────────────────────────────────────────────────────────┴─── agent.ideacion.tasks
        │  RabbitMQ  (colas durables, eventos tipados)               agent.publicacion.tasks
        │                                                            agent.results
        ▼
┌───────────────────────────┐        ┌────────────────────────────────┐
│ AGENTE IDEACIÓN :8000     │        │ AGENTE PUBLICACIÓN :8001       │
│ LangGraph propio          │        │ LangGraph propio               │
│ load_context → fetch_news │        │ load_context → fetch_trending  │
│ → generate_idea → save_idea│       │ → generate_post → save_post    │
│ checkpoint Redis          │        │ checkpoint Redis               │
│ thread: {agente}:{task}   │        │ thread: {agente}:{task}        │
└──────────┬────────────────┘        └──────────────┬─────────────────┘
           │ ToolRegistry (Tool Discovery)          │
           │ POST /v1/generate (vía gateway)        │
           ▼                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     TOOLS-AS-A-SERVICE (6)                          │
│  tool-client :8010  (clientes)          tool-trends    :8011 (RAG)  │
│  tool-competitors:8012 (competencia)    tool-rag       :8013 (RAG+escritura)│
│  tool-news   :8014  (RSS)               tool-trending  :8015 (RSS)  │
│  cada uno: /health + /.well-known/tool-manifest + ops REST + RPC AMQP│
└──────────┬──────────────────────────────────────┬───────────────────┘
           │ embeddings (siempre vía gateway)     │
           ▼                                      ▼
┌──────────────────────────┐        ┌───────────────────────────────┐
│ LLM GATEWAY :8003        │        │ PostgreSQL 16 + pgvector :5432│
│ balanceo ponderado       │        │ clientes · tendencias ·       │
│ retries + exp. backoff   │        │ referencias_competencia ·     │
│ fallback de proveedor    │        │ ideas_generadas ·             │
│ caché Redis de prompts   │        │ publicaciones_generadas ·     │
└──────────┬───────────────┘        │ chat_history                  │
           │                        └───────────────────────────────┘
           ▼
   Ollama (host, 11434)
   gemma3:4b · mistral-nemo · nomic-embed-text · …
```

| Servicio | Puerto | Rol |
|----------|--------|-----|
| orchestrator | 8002 | Supervisor stateless (LangGraph `interrupt` + eventos) |
| agente-ideacion | 8000 | Microservicio de ideación (grafo propio, event-driven) |
| agente-publicacion | 8001 | Microservicio de publicación (grafo propio, event-driven) |
| llm-gateway | 8003 | Punto único de llamadas a LLM |
| tool-client | 8010 | Perfil de cliente |
| tool-trends | 8011 | Búsqueda RAG de tendencias |
| tool-competitors | 8012 | Referencias de competencia |
| tool-rag | 8013 | Memoria RAG + escritura de ideas/publicaciones |
| tool-news | 8014 | Noticias Google News RSS |
| tool-trending | 8015 | Topics en tendencia (hashtags) |
| rabbitmq | 5672/15672 | Bus de eventos + RPC |
| postgres | 5432 | Datos de negocio + historial de chat |
| redis (redis-stack) | 6379 | Checkpoints LangGraph, TaskStore, caché de prompts |

---

## 2. Patrones de agentes implementados

### 2.1 Estado del ciclo de planificación fuera del proceso (requisito 1)

El supervisor de LangGraph **no mantiene estado en memoria**. Cada ciclo se
checkpointea en Redis y el proceso se suspende con `interrupt()`:

```python
# orchestrator/multi_agent/supervisor.py
def dispatch_ideacion(state) -> dict:
    result = interrupt({                 # ← suspende el grafo aquí
        "agent": "ideacion",
        "queue": "agent.ideacion.tasks",
        "payload": {"brief": state["brief"], "client_id": state["client_id"]},
    })                                   # ← al reanudar: resultado del agente
    ...
```

El **runtime event-driven** (`multi_agent/runtime.py`) vive fuera del grafo:

```
start_task()
  → TaskStore.create(task_id)                         (Redis)
  → graph.invoke(initial, thread_id=task_id)          hasta el 1er interrupt()
  → publica agent.task.triggered                      (RabbitMQ)
        ⇠ consumidor recibe agent.task.completed
  → graph.invoke(Command(resume=result), thread_id)   (desde el checkpoint)
  → siguiente interrupt() … o END
  → guarda historial de chat                           (PostgreSQL)
  → publica task.completed                            (RabbitMQ)
```

Si el contenedor del orquestador muere en cualquier punto, al arrancar
`recover_running_tasks()` re-publica el despacho pendiente de las tareas
`running` que quedaron en TaskStore: **la memoria está en Redis, no en el
proceso** (escalado horizontal + recuperación ante caídas).

El historial de chat es durable en PostgreSQL (`chat_history`): una fila por
turno (`user` = brief recibido, `assistant` = idea + publicación generadas),
consultable con `GET /tasks/{id}/history`.

### 2.2 Tools-as-a-Service + Tool Discovery (requisito 2)

Cada tool es un microservicio con su propio despliegue, propiedad de sus
datos y un **manifiesto autocontenido**:

```json
GET http://tool-trends:8011/.well-known/tool-manifest
{
  "name": "trends", "service": "tool-trends", "version": "1.0.0",
  "transport": ["rest", "amqp"], "amqp_queue": "tool.trends.rpc",
  "operations": [
    {"id": "search", "method": "GET", "path": "/search",
     "description": "Búsqueda RAG de tendencias…",
     "params": [{"name": "query", "in": "query", "type": "string", "required": true}],
     "returns": "…"}
  ]
}
```

El flujo de descubrimiento del agente:

```
ToolRegistry.discover()  →  GET /.well-known/tool-manifest  (por servicio)
       │                     valida la forma (validate_manifest)
       ▼
ToolRegistry.call("trends", "search", params=…)  →  mapea op → GET /search
       │                                          →  envelope {tool,status,data,…}
       ▼
ToolRegistry.as_langchain_tools()  →  BaseTool "trends_search" con nombre,
                                     descripción y esquema del manifiesto
```

Respuesta uniforme (**envelope**): `{tool, status: ok|error, data, error,
duration_ms, correlation_id, server_time}`. Los errores de dominio se
devuelven como envelope `status=error` (HTTP 500) y el cliente lanza
`EnvelopeError` — nunca se filtra stacktrace ni shape ad-hoc.

También existe invocación **asíncrona** (tareas largas / decoupling total):
`tool.task.triggered` en `tool.{nombre}.rpc` → `tool.task.completed` en la
cola `reply_to` (RPC sobre eventos, `common/rpc.py`). Es el transporte
`amqp` declarado en cada manifiesto.

**Propiedad de datos por tool** (sin solapamientos):

| Tool | Dueña de tablas | Fuente externa |
|------|-----------------|----------------|
| tool-client | `clientes` | — |
| tool-trends | `tendencias` | — |
| tool-competitors | `referencias_competencia` | — |
| tool-rag | `ideas_generadas`, `publicaciones_generadas` (lectura + escritura) | — |
| tool-news | — | Google News RSS |
| tool-trending | — | Google News RSS |

### 2.3 Resiliencia del bucle asíncrono (requisito 3)

**Estructura de evento** (`common/events.py`, dataclass serializada a JSON):

| Campo | Significado |
|-------|-------------|
| `event_type` | `agent.task.triggered` · `agent.task.completed` · `tool.task.triggered` · `tool.task.completed` · `task.completed` |
| `task_id` | Identidad de la tarea (igual al `thread_id` del checkpoint) |
| `correlation_id` | Trazabilidad extremo a extremo (hereda de `task_id`) |
| `event_id`, `timestamp`, `source` | Identificador único, hora y emisor |
| `reply_to` | Cola de respuesta (RPC) |
| `agent`, `tool`, `operation` | Destino/consumible de la operación |
| `payload` | Datos del despacho o `{"result": …}` |
| `status`, `error`, `duration_ms` | `completed`/`failed` + motivo + duración |

Colas durables (`delivery_mode=2`):

```
agent.ideacion.tasks    orchestrator → agente de ideación
agent.publicacion.tasks orchestrator → agente de publicación
agent.results           agentes     → orquestador (agent.task.completed)
task.results            orquestador → mundo (task.completed)
tool.{nombre}.rpc       invocación RPC/async de tools
ideation_queue          ingreso de briefs por eventos (compatibilidad)
```

Garantías implementadas:

1. **Reconexión**: `EventConsumer` reintenta cada 5 s si RabbitMQ cae.
2. **Procesamiento justo**: agentes consumen con `auto_ack=False`; si el
   proceso muere a mitad, RabbitMQ reentrega el mensaje.
3. **Idempotencia**: el agente corre su grafo con
   `thread_id = {agente}:{task_id}` (`common/agent_runner.py`):
   - checkpoint **completo** → reentrega duplicada → devuelve el mismo
     resultado sin re-ejecutar nada;
   - checkpoint **con nodos pendientes** → `invoke(None, config)` retoma
     desde el último nodo persistido;
   - sin checkpoint → ejecución nueva.
4. **Filtros en el orquestador**: resultados de agentes no esperados
   (duplicados, obsoletos) se ignoran; una tarea desconocida o ya
   finalizada se descarta con log.
5. **Fallos**: un agente publica `agent.task.completed` con
   `status=failed, error=…` → el runtime marca la tarea `failed` en
   TaskStore y registra el error en el historial. Un error al publicar un
   despacho marca la tarea como fallida (visible vía `GET /tasks/{id}`).
6. **Recuperación al arranque**: `recover_running_tasks()` re-publica los
   despachos pendientes (semántica *at-least-once* + idempotencia).

> Kafka es una alternativa válida para producción (retenimiento más largo y
> re-consumo); este PoC usa RabbitMQ, que ya estaba en la infraestructura y
> cubre el patrón con colas durables + acks.

### 2.4 LLM Gateway centralizado (requisito 4)

Ningún componente habla con Ollama directamente: `common/gateway_client.py`
es el único cliente y apunta a `LLM_GATEWAY_URL` (por defecto
`http://localhost:8003`).

API del gateway:

| Método | Ruta | Uso |
|--------|------|-----|
| GET | `/health` | Estado + proveedores configurados |
| GET | `/v1/providers` | Proveedor, modelo, peso, región, salud |
| POST | `/v1/generate` | `{prompt, system?, model?, temperature?, max_tokens?, cache?}` → `{content, provider, model, cached, attempts, duration_ms}` |
| POST | `/v1/embeddings` | `{input: str\|[str], cache?}` → `{embeddings, model, provider, cached, duration_ms}` |

Comportamiento interno:

- **Balanceo de carga ponderado** por `weight` entre proveedores sanos
  (`weighted_choice`, función pura testeable).
- **Reintentos con exponential backoff + jitter** (`backoff_delay(attempt)`:
  `min(base·factor^attempt, max_delay)` ± jitter), sólo ante errores de
  conexión, timeout y HTTP 5xx (nunca ante 4xx).
- **Fallback automático de proveedor**: cadena rotativa — p. ej. si
  `gemma3:4b` agota sus reintentos, se prueba `mistral-nemo`
  (`LLM_FALLBACK_MODEL`). La respuesta expone `attempts` y
  `provider_errors` acumulados; 502 sólo si fallan todos.
- **Caché de prompts/embeddings en Redis**: clave
  `llm:{kind}:sha256(parts)` con TTL (`CACHE_TTL` 1 h para generación,
  `EMB_CACHE_TTL` 24 h para embeddings). `cache=false` la desactiva por
  petición. Un Redis caído degrada a "sin caché", no tumbar la petición.
- **Salud por proveedor**: 3 fallos consecutivos lo marcan `healthy=false`
  (se excluye del balanceo) y un éxito lo rehabilita.

---

## 3. Cómo funciona (secuencia completa)

```
 cliente                      orchestrator            rabbitmq          agente-x           tools / gateway
   │  POST /process               │                     │                 │                    │
   │  {client_id, content}        │                     │                 │                    │
   ├─────────────────────────────►│ TaskStore.create()  │                 │                    │
   │                              │ historial user ──── PostgreSQL         │                    │
   │                              │ graph.invoke()      │                 │                    │
   │                              │  …decide → ideacion │                 │                    │
   │                              │  interrupt() ⏸      │                 │                    │
   │                              │ checkpoint ──────── Redis             │                    │
   │                              │ publish agent.task.triggered          │                    │
   │                              ├────────────────────►│                 │                    │
   │                              │                     ├────────────────►│                    │
   │                              │                     │                 │ discover manifests │
   │                              │                     │                 ├───────────────────►│
   │                              │                     │                 │ REST: profile,     │
   │                              │                     │                 │ trends, competitors│
   │                              │                     │                 ├───────────────────►│
   │                              │                     │                 │ POST /v1/generate  │
   │                              │                     │                 │ (LB+retries+cache) │
   │                              │                     │                 ├───────────────────►│
   │                              │                     │                 │ save_idea (embedding│
   │                              │                     │                 │  vía gateway)      │
   │                              │                     │◄────────────────┤                    │
   │                              │◄────────────────────┤ agent.task.completed                 │
   │                              │ Command(resume) ⏵   │                 │                    │
   │                              │  …decide → publicacion → interrupt() ⏸ │                    │
   │                              │ publish agent.task.triggered          │                    │
   │                              ├────────────────────►├────────────────►│ …misma cadena …    │
   │                              │◄────────────────────┤◄────────────────┤                    │
   │                              │ Command(resume) ⏵ → END               │                    │
   │                              │ historial assistant PostgreSQL         │                    │
   │                              │ publish task.completed                 │                    │
   ◄──────────────────────────────┤ status=completed                      │                    │
```

---

## 4. Happy Path (camino feliz)

Escenario: el cliente **EcoBrand** (`client_id=1`) pide una campaña de verano.

```bash
curl -X POST http://localhost:8002/process \
  -H "Content-Type: application/json" \
  -d '{"client_id": 1, "content": "Campana de verano para nuestra linea de cuidado personal organico"}'
```

Lo que ocurre por dentro (secuencia de eventos y logs):

```
orchestrator  tarea <uuid> creada (client_id=1)
orchestrator  tarea <uuid> → agent.task.triggered [ideacion]

agente_ideacion  agent.task.triggered task=<uuid>
  load_context    ✓ REST tool-client.profile + tool-trends.search(5)
                  ✓ REST tool-competitors.search(5) + tool-rag.similar(3)
  fetch_news      ✓ REST tool-news.news(3)
  generate_idea   ✓ llm-gateway /v1/generate (provider=gemma3:4b, cached=false)
  save_idea       ✓ REST tool-rag.save_idea → idea_id=13
agente_ideacion  fin tarea <uuid> (completed)

orchestrator  tarea <uuid> ← agent.task.completed [ideacion]
orchestrator  tarea <uuid> → agent.task.triggered [publicacion]

agente_publicacion  load_context  ✓ profile + trends.search(3)
                    fetch_trending ✓ tool-trending.trending
                    generate_post ✓ llm-gateway /v1/generate
                    save_post     ✓ tool-rag.save_publicacion → publication_id=9

orchestrator  tarea <uuid> COMPLETADA idea_id=13 publication_id=9
orchestrator  task.completed publicado en task.results
```

Respuesta HTTP (esperada, `wait=true`):

```json
{
  "task_id": "…", "status": "completed",
  "idea": "**Title:** …", "idea_id": 13,
  "publication": "☀️ … #EcoBrand", "publication_id": 9,
  "agents": {"ideacion": {"status": "completed"}, "publicacion": {"status": "completed"}}
}
```

Verificación del estado externo (otro proceso, sin compartir memoria):

```bash
curl localhost:8002/tasks/<task_id>              # TaskStore en Redis: completed
curl localhost:8002/tasks/<task_id>/history      # PostgreSQL: turnos user/assistant
curl localhost:8000/state/<task_id>              # checkpoint Redis del agente
```

**Criterios de éxito:**
- ✅ `POST /process` responde 200 y `status=completed`
- ✅ `idea_id > 0` y `publication_id > 0` en PostgreSQL (con embedding)
- ✅ `GET /tasks/{id}` → `status=completed` con `result` (estado externo)
- ✅ `GET /tasks/{id}/history` → `[user, assistant]` (historial durable)
- ✅ `GET /state/{task_id}` en el agente → valores del checkpoint en Redis
- ✅ `GET /tools` del orquestador → 6 tools descubiertas por manifiesto

---

## 5. Caso de uso completo

**TechStart** es una fintech latinoamericana (`client_id=2`) que simplifica
pagos para pequeñas empresas. Quiere lanzar una app que automatice cobros para
**panaderías y cafeterías independientes de México**.

```bash
curl -X POST http://localhost:8002/process \
  -H "Content-Type: application/json" \
  -d '{"client_id": 2, "content": "Lanzamiento de una app movil que automatiza cobros para pequenas panaderias y cafeterias independientes en Mexico"}'
```

**Atribución del resultado a los microservicios** (cada pieza del texto viene
de un servicio concreto, verificable por `tool_calls` en el checkpoint):

| Elemento del resultado | Servicio que lo aportó |
|------------------------|------------------------|
| Valores de velocidad/seguridad, tono | `tool-client` (`perfil_marca`, `restricciones_tono`) |
| Tendencia QR / pagos móviles | `tool-trends` (búsqueda por similitud coseno) |
| Enfoque de la competencia (gamification) | `tool-competitors` |
| Memoria: no repetir campañas previas | `tool-rag` (`similar` sobre `ideas_generadas`) |
| Noticias del sector | `tool-news` (Google News RSS) |
| Hashtags en tendencia | `tool-trending` |
| Texto generado (idea y post) | `llm-gateway` → Ollama (con caché/backoff/fallback) |
| Persistencia con embedding | `tool-rag` (`save_idea`, `save_publicacion`) |
| Secuenciación y consolidación | `orchestrator` (eventos + checkpoints Redis) |

Cadena de eventos del caso:

```
POST /process
 → agent.task.triggered [ideacion]
     → REST: client.profile, trends.search, competitors.search, rag.similar
     → REST: news.news
     → gateway: /v1/generate  →  REST: rag.save_idea      (idea_id=…)
 → agent.task.completed [ideacion]
 → agent.task.triggered [publicacion]
     → REST: client.profile, trends.search
     → REST: trending.trending
     → gateway: /v1/generate  →  REST: rag.save_publicacion (publication_id=…)
 → agent.task.completed [publicacion]
 → task.completed (task.results)
```

Impacto acumulado: cada ejecución crece `ideas_generadas`, de modo que
`tool-rag.similar` devuelve cada vez más contexto — el sistema **aprende del
histórico** y evita repetir ideas (RAG de memoria).

---

## 6. Cómo usarlo

### 6.1 Arrancar

```bash
# requisitos: Docker Compose + Ollama en el host con:
ollama pull gemma3:4b
ollama pull nomic-embed-text
ollama pull mistral-nemo          # modelo de fallback del gateway

docker compose up -d --build
```

### 6.2 Tres formas de entrada

**A) HTTP síncrono** (espera el resultado):

```bash
curl -X POST http://localhost:8002/process \
  -H "Content-Type: application/json" \
  -d '{"client_id": 1, "content": "…", "wait": true, "timeout": 300}'
```

**B) HTTP asíncrono** (devuelve `task_id` al instante):

```bash
curl -X POST http://localhost:8002/process \
  -d '{"client_id": 1, "content": "…", "wait": false}'
# → {"task_id": "…", "status": "running", "mode": "async"}
curl localhost:8002/tasks/<task_id>
```

**C) Por eventos** (RabbitMQ, el emisor no espera nada):

```bash
python enviar_brief.py        # publica {client_id, content} en ideation_queue
```

### 6.3 Endpoints

| Servicio | Método | Ruta | Descripción |
|----------|--------|------|-------------|
| orchestrator | GET | `/health` | Salud + subsistemas (redis/rabbitmq/postgres/gateway) |
| orchestrator | GET | `/metrics` | Patrón, capa de estado, agentes, eventos |
| orchestrator | GET | `/tools` | Catálogo agregado vía Tool Discovery |
| orchestrator | GET | `/graph` | Nodos/arestas + mecanismo de suspensión |
| orchestrator | POST | `/process` | Lanza el pipeline (`wait`, `timeout`) |
| orchestrator | GET | `/tasks/{id}` | Metadatos + resultados (TaskStore/Redis) |
| orchestrator | GET | `/tasks/{id}/history` | Historial de chat (PostgreSQL) |
| agente-x | GET | `/health` `/metrics` `/tools` | Identidad, colas y tools descubiertas |
| agente-x | GET | `/state/{task_id}` | Checkpoint del agente en Redis |
| tool-x | GET | `/health` | Salud + transporte |
| tool-x | GET | `/.well-known/tool-manifest` | Contrato de descubrimiento |
| tool-x | … | operaciones del manifiesto | Endpoints REST de dominio |
| llm-gateway | GET | `/health` `/v1/providers` | Salud y proveedores |
| llm-gateway | POST | `/v1/generate` `/v1/embeddings` | Invocaciones LLM |

### 6.4 Pruebas

```bash
pytest tests/unit/ -v            # rápidas, sin servicios externos
pytest tests/ -v                 # completa (integración se salta si el stack baja)
python prueba_orquestador.py     # API del orquestador (modo asíncrono)
python prueba_e2e.py --eventos   # E2E: HTTP + ingreso por eventos + estado externo
```

---

## 7. Estructura del proyecto

```
proyecto multiagente/
├── common/                       # KERNEL compartido (contratos entre servicios)
│   ├── events.py                 # Event tipado, colas, publish/consumer, RPC
│   ├── contracts.py              # manifiesto + envelope (Tool Discovery)
│   ├── tool_client.py            # ToolRegistry: discover/call/as_langchain_tools
│   ├── gateway_client.py         # único cliente LLM (→ llm-gateway)
│   ├── task_store.py             # metadatos de tarea en Redis
│   ├── agent_runner.py           # ejecución idempotente del grafo del agente
│   └── rpc.py                    # servidor RPC por eventos para tools
├── orchestrator/                 # ORQUESTADOR STATELESS (:8002)
│   ├── multi_agent/
│   │   ├── state.py              # SupervisorState + initial_state()
│   │   ├── supervisor.py         # grafo con dispatch_* + interrupt()
│   │   └── runtime.py            # máquina de estados event-driven externa
│   ├── history.py                # historial de chat (PostgreSQL)
│   └── main.py                   # FastAPI + consumidores + recuperación
├── agente_ideacion/              # MICROSERVICIO de ideación (:8000)
│   ├── graph.py                  # 4 nodos vía ToolRegistry + gateway
│   ├── prompts.py                # persona/prompt del agente
│   └── main.py                   # consumidor agent.ideacion.tasks
├── agente_publicacion/           # MICROSERVICIO de publicación (:8001)
│   ├── graph.py · prompts.py · main.py
├── llm_gateway/                  # LLM GATEWAY (:8003)
│   ├── main.py                   # /v1/generate · /v1/embeddings
│   ├── providers.py              # registro + balanceo ponderado + salud
│   ├── resilience.py             # backoff exponencial + cadena de fallback
│   └── cache.py                  # caché Redis de prompts/embeddings
├── tool_services/                # TOOLS-AS-A-SERVICE (6, :8010-8015)
│   ├── Dockerfile                # build parametrizado (ARG TOOL_DIR)
│   └── tool_client|trends|competitors|rag|news|trending/main.py
├── shared_tools/                 # librería de dominio (SÓLO la usan los tools)
├── tests/
│   ├── PLAN_DE_PRUEBAS.md        # plan de pruebas (IDs, cobertura, criterios)
│   ├── unit/ integration/ performance/
├── docs/                         # ARQUITECTURA · TECNOLOGIAS · CHANGELOG
├── docker-compose.yml            # 13 servicios
├── init.sql                      # esquema + seed
├── prueba_e2e.py                 # E2E (HTTP + eventos + estado externo)
├── prueba_orquestador.py         # demo de la API del orquestador
└── enviar_brief.py               # ingress de briefs por eventos
```

---

## 8. Decisiones y trade-offs

| Decisión | Alternativa descartada | Motivo |
|----------|------------------------|--------|
| Agentes = microservicios separados con eventos | subgrafos en memoria del supervisor | Requisito: estado externo + despliegue independiente por agente |
| 6 tool services (1 por herramienta) | 1 servicio monolítico de tools | Máxima independencia: despliegue, escalado y propiedad de datos por tool |
| RabbitMQ con colas durables | Kafka | RabbitMQ ya estaba en la infraestructura; cubre el patrón con acks + reentrega. Kafka es la vía si se necesita re-consumo histórico |
| `interrupt()` + `Command(resume=…)` | hilos/colas ad-hoc esperando | El ciclo de planificación queda como checkpoint consultable y recuperable en Redis |
| Redis Stack (`redis/redis-stack-server`) | Redis alpine | `langgraph-checkpoint-redis` requiere RedisJSON + RediSearch |
| Idempotencia por checkpoint (`{agente}:{task_id}`) | deduplicación por message-id | La clave de idempotencia es el negocio (tarea), no el sobre (mensaje); cubre también reentrega tras crash |
| LLM vía gateway único | ChatOllama directo en cada agente | Requisito: balanceo, backoff, fallback y caché centralizados; los agentes no dependen del runtime de Ollama |
| Historial de chat en PostgreSQL | Redis | Durabilidad: el historial sobrevive a reinicios de caché; los checkpoints de ciclo (volátiles/recientes) van a Redis |
