# Prueba de Concepto — Sistema Multi-Agente de Microservicios

Sistema multi-agente para generación automatizada de contenido de marketing,
implementado como **arquitectura de microservicios** (13 contenedores) con
patrones de agentes sobre infraestructura de servicios:

- **Orquestador stateless** — un supervisor LangGraph que se suspende con
  `interrupt()` y guarda todo su estado fuera del proceso (Redis + PostgreSQL).
- **2 agentes microservicio** — ideación y publicación, cada uno con su propio
  grafo LangGraph, su contenedor y su cola de eventos.
- **6 tool microservicios** (Tools-as-a-Service) — descubiertos en runtime por
  manifiestos (`/.well-known/tool-manifest`); el agente nunca ejecuta código
  de negocio, sólo invoca contratos REST/AMQP.
- **LLM Gateway centralizado** — balanceo ponderado, reintentos con backoff
  exponencial, fallback entre proveedores y caché de prompts en Redis.
- **RabbitMQ** — bucle asíncrono resiliente con eventos tipados
  (`agent.task.triggered` / `agent.task.completed`), acks y reentrega.

---

## 1. ¿Qué hace el sistema?

Dado un **brief** de marketing (texto libre + `client_id`), el sistema devuelve:

1. Una **idea de campaña** original (título, descripción, rationale)
2. Una **publicación lista para redes** (hook, hashtags, CTA, ≤280 caracteres)

Ambas quedan guardadas en PostgreSQL **con embedding vectorial**, de modo que
las siguientes consultas RAG las usen como memoria («¿qué ideas ya hice?»), y
el **historial de la conversación** queda durable en `chat_history`.

---

## 2. Los 4 requisitos y dónde están

| # | Requisito | Implementación | Pruebas |
|---|-----------|----------------|---------|
| 1 | Orquestador **stateless** con estado externo (ciclo ReAct/plan + historial de chat) | `interrupt()`/`Command(resume=…)` + `RedisSaver` (`thread_id=task_id`), `TaskStore` en Redis, `chat_history` en PostgreSQL; `runtime.py` fuera del grafo; `recover_running_tasks()` al arrancar | U-ORQ-03/04/05, U-AG-04/05, I-ORQ-05 |
| 2 | **Tools-as-a-Service** con tool discovery | 6 servicios con manifiesto `/.well-known/tool-manifest`; `ToolRegistry.discover/call/as_langchain_tools` en `common/tool_client.py` | U-K-07…10, I-T-*, I-ORQ-01/02 |
| 3 | **Resiliencia asíncrona** en RabbitMQ con eventos definidos | `common/events.py` (dataclass `Event`, colas durables, reconexión, ack manual), idempotencia por checkpoint, filtrado de duplicados | U-K-01…03, U-ORQ-05, I-T-05, I14-I16 |
| 4 | **LLM Gateway** (balanceo, backoff, fallback, caché de prompts) | `llm_gateway/` + `common/gateway_client.py` (único cliente; todo LLM pasa por `:8003`) | U-LLM-01…18, P01/P04 |

> **Principio rector**: *lo que no sirva, no está*. El agente no ejecuta
> código de negocio; el orquestador sólo planifica, despacha y consolida.

---

## 3. Arquitectura en un vistazo

```
                        ┌────────────────────────────────────┐
 POST /process          │ ORCHESTRATOR :8002 (stateless)     │
 ideation_queue ───────►│  supervisor LangGraph              │
                        │  interrupt() ⇄ Command(resume=…)   │◄── estado en
                        └───────┬────────────────────────────┘    Redis + PG
                                │ agent.task.triggered / completed
                        ┌───────▼────────────────────────────┐
                        │ RabbitMQ (colas durables + RPC)    │
                        └───┬────────────────────────┬───────┘
                            │                        │
              ┌─────────────▼──────────┐  ┌──────────▼─────────────┐
              │ AGENTE IDEACIÓN :8000  │  │ AGENTE PUBLICACIÓN:8001│
              │ 4 nodos + prompts      │  │ 4 nodos + prompts      │
              └──────┬─────────────────┘  └──────────┬─────────────┘
                     │ ToolRegistry (discover→call)  │
        ┌────────────▼───────────────────────────────▼────────────┐
        │ TOOLS-AS-A-SERVICE: tool-client:8010  tool-trends:8011  │
        │  tool-competitors:8012  tool-rag:8013                   │
        │  tool-news:8014  tool-trending:8015                     │
        └────────────┬────────────────────────────────────────────┘
                     │ embeddings / generación
        ┌────────────▼──────────────┐   ┌────────────────────────┐
        │ LLM GATEWAY :8003        │   │ PostgreSQL + pgvector  │
        │ LB · backoff · fallback  │   │ Redis Stack (ciclo)     │
        └────────────┬──────────────┘   └────────────────────────┘
                     ▼
              Ollama (host :11434)
```

Detalle completo (secuencia, happy path, caso de uso, decisiones):
**[`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)** ·
Stack: **[`docs/TECNOLOGIAS.md`](docs/TECNOLOGIAS.md)** ·
Plan de pruebas: **[`tests/PLAN_DE_PRUEBAS.md`](tests/PLAN_DE_PRUEBAS.md)**

---

## 4. Cómo funciona (explicación corta)

1. **`POST /process`** crea la tarea en Redis (`TaskStore`), guarda el turno
   `user` en `chat_history` y ejecuta el supervisor hasta el primer
   `interrupt()`: el grafo queda **checkpointeado en Redis** y publica
   `agent.task.triggered` en `agent.ideacion.tasks`.
2. El **agente de ideación** consume su cola (`auto_ack=False`), descubre los
   manifiestos de los tools, invoca por REST el perfil, las tendencias, la
   competencia y las ideas similares, añade noticias RSS, genera la idea vía
   **LLM Gateway**, la persiste con `tool-rag` y publica
   `agent.task.completed` en `agent.results`.
3. El orquestador recibe el resultado (filtrando duplicados o agentes
   inesperados), **reanuda** el grafo con `Command(resume=…)` desde el
   checkpoint, decide `dispatch_publicacion` y repite el ciclo.
4. Al llegar a `END`: guarda el turno `assistant` en el historial, marca la
   tarea `completed` en Redis y publica `task.completed`.

Cada paso es **recuperable**: si un contenedor muere, el estado está en Redis
y los mensajes en RabbitMQ (semántica *at-least-once* + idempotencia por
`thread_id = {agente}:{task_id}`).

---

## 5. Arranque rápido

### Requisitos

- Docker Desktop con Compose
- Python 3.10+ (sólo para tests/scripts locales)
- Ollama en el host:

```bash
ollama pull gemma3:4b
ollama pull nomic-embed-text
ollama pull mistral-nemo        # fallback del gateway
```

### Levantar las 13 piezas

```bash
docker compose up -d --build
```

### Verificar

```bash
curl http://localhost:8002/health      # subsistemas: redis/rabbitmq/postgres/gateway
curl http://localhost:8002/graph       # grafo supervisor + mecanismo de suspensión
curl http://localhost:8002/tools       # catálogo vía Tool Discovery (6 tools)
curl http://localhost:8003/health      # LLM Gateway + proveedores
curl http://localhost:8010/.well-known/tool-manifest   # contrato de un tool
```

---

## 6. Las 3 formas de usarlo

### A) HTTP síncrono (espera el resultado)

```bash
curl -X POST http://localhost:8002/process \
  -H "Content-Type: application/json" \
  -d '{"client_id": 1, "content": "Campaña de verano para cosmética natural"}'
```

```json
{
  "task_id": "…", "status": "completed",
  "idea": "**Title:** …", "idea_id": 13,
  "publication": "☀️ … #EcoBrand", "publication_id": 9,
  "agents": {"ideacion": {"status": "completed"},
             "publicacion": {"status": "completed"}}
}
```

### B) HTTP asíncrono (devuelve `task_id` al instante)

```bash
curl -X POST http://localhost:8002/process \
  -H "Content-Type: application/json" \
  -d '{"client_id": 1, "content": "…", "wait": false}'
# → {"task_id": "…", "status": "running", "mode": "async"}

curl http://localhost:8002/tasks/<task_id>            # estado en Redis
curl http://localhost:8002/tasks/<task_id>/history    # historial en PostgreSQL
```

### C) Por eventos RabbitMQ (el emisor no espera nada)

```bash
python enviar_brief.py      # publica {client_id, content} en ideation_queue
```

---

## 7. Endpoints

| Servicio | Método · Ruta | Descripción |
|----------|---------------|-------------|
| orchestrator | GET `/health` `/metrics` `/graph` `/tools` | Salud, métricas, grafo, catálogo descubierto |
| orchestrator | POST `/process` | Lanza el pipeline (`wait`, `timeout`) |
| orchestrator | GET `/tasks/{id}` · `/tasks/{id}/history` | Metadatos+resultados (Redis) · historial (PostgreSQL) |
| agente-x | GET `/health` `/metrics` `/tools` `/state/{task_id}` | Identidad, colas, tools, checkpoint en Redis |
| tool-x | GET `/health` `/.well-known/tool-manifest` + ops | Contrato y operaciones de dominio |
| llm-gateway | GET `/health` `/v1/providers` | Salud y proveedores |
| llm-gateway | POST `/v1/generate` `/v1/embeddings` | Invocaciones LLM (cacheables) |

---

## 8. Pruebas

```bash
pytest tests/ -v                # toda la suite (integración se salta si falta el stack)
pytest tests/ -v -m unit        # sólo unitarias: sin ningún servicio
python prueba_orquestador.py    # API del orquestador (modo asíncrono + estado externo)
python prueba_e2e.py --eventos  # E2E: HTTP + eventos + verificación en Redis/PG
```

Plan completo (IDs, cobertura, criterios de aceptación):
[`tests/PLAN_DE_PRUEBAS.md`](tests/PLAN_DE_PRUEBAS.md)

---

## 9. Estructura del repositorio

```
common/                kernel compartido: events · contracts · tool_client ·
                       gateway_client · task_store · agent_runner · rpc
orchestrator/          supervisor LangGraph + runtime event-driven + API (:8002)
agente_ideacion/       microservicio de ideación (:8000): graph · prompts · main
agente_publicacion/    microservicio de publicación (:8001)
llm_gateway/           gateway LLM (:8003): providers · resilience · cache · main
tool_services/         6 tools (:8010-8015) + Dockerfile parametrizado
shared_tools/          librería de dominio (la usan SÓLO los tool services)
tests/                 unit · integration · performance + PLAN_DE_PRUEBAS.md
docs/                  ARQUITECTURA · TECNOLOGIAS · CHANGELOG
docker-compose.yml     13 servicios
init.sql               esquema + seed
prueba_e2e.py          E2E punta a punta
prueba_orquestador.py  demo de la API del orquestador
enviar_brief.py        ingreso de briefs por eventos
```

---

## 10. Caso de uso resumido

**TechStart** (`client_id=2`), fintech que lanza una app de cobros para
panaderías y cafeterías independientes de México:

```bash
curl -X POST http://localhost:8002/process \
  -H "Content-Type: application/json" \
  -d '{"client_id": 2, "content": "Lanzamiento de una app movil que automatiza cobros para pequenas panaderias y cafeterias independientes en Mexico"}'
```

Cada fragmento del resultado es atribuible a un servicio concreto (perfil →
`tool-client`, tendencias → `tool-trends`, competencia → `tool-competitors`,
memoria → `tool-rag`, noticias → `tool-news`, hashtags → `tool-trending`,
texto → `llm-gateway`), y la trazabilidad `tool_calls` queda en el checkpoint
de cada agente. Desglose completo en [`docs/ARQUITECTURA.md` §5](docs/ARQUITECTURA.md).
