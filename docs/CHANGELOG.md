# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).
Convención de commits: [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/).

## [2.0.0] — 2026-09-26

Reescritura como **arquitectura de microservicios** (13 contenedores) que
cumple los 4 requisitos: orquestador stateless con estado externo, Tools-as-a-
Service con tool discovery, resiliencia de eventos en RabbitMQ y LLM Gateway
centralizado.

### Added
- **feat** (`common/`): kernel compartido que sustituye a `shared_tools` como
  contrato entre servicios
  - `events.py` — dataclass `Event` tipada (`agent.task.triggered`,
    `agent.task.completed`, `tool.task.triggered`, `tool.task.completed`,
    `task.completed`), colas durables, `EventConsumer` con reconexión y ack
    manual, `publish_event`, RPC por eventos y fallback *raw* de `from_body`
  - `contracts.py` — manifiesto `/.well-known/tool-manifest` + envelope
    uniforme `{tool, status, data, error, duration_ms, …}`
  - `tool_client.py` — `ToolRegistry` con Tool Discovery (discover → call →
    `as_langchain_tools`), mapeo operación→endpoint y `TOOL_URLS` por entorno
  - `gateway_client.py` — único cliente LLM (generate/embed/health)
  - `task_store.py` — metadatos/resultados de tarea en Redis (estado externo)
  - `agent_runner.py` — `run_agent_task` idempotente (nueva / retoma /
    reentrega duplicada) con `thread_id = {agente}:{task_id}`
  - `rpc.py` — servidor RPC por eventos para tool services
- **feat** (`tool_services/`): 6 microservicios Tools-as-a-Service
  (`tool-client:8010`, `tool-trends:8011`, `tool-competitors:8012`,
  `tool-rag:8013`, `tool-news:8014`, `tool-trending:8015`)
  - `/health`, manifiesto de descubrimiento, operaciones REST con envelope y
    RPC AMQP (`tool.{nombre}.rpc`)
  - propiedad de datos por servicio (`clientes`, `tendencias`,
    `referencias_competencia`, `ideas_generadas`/`publicaciones_generadas`,
    RSS externo en news/trending)
  - `Dockerfile` parametrizado (`ARG TOOL_DIR`) + `requirements.txt` comunes
- **feat** (`llm_gateway/`): LLM Gateway centralizado (:8003)
  - `providers.py` — registro de proveedores, balanceo ponderado por peso y
    salud en memoria (3 fallos → no sano; éxito → rehabilita)
  - `resilience.py` — reintentos con exponential backoff + jitter y cadena de
    fallback de proveedor (`AllProvidersFailed` con detalle; 4xx sin retry)
  - `cache.py` — caché Redis de prompts/embeddings (`llm:{kind}:sha256`, TTL
    por tipo, fallos de Redis degradan a «sin caché»)
  - API: `GET /health`, `GET /v1/providers`, `POST /v1/generate`,
    `POST /v1/embeddings`
- **feat** (orquestador): reescritura como **orquestador stateless**
  - `multi_agent/supervisor.py` — grafo supervisor con `interrupt()` en
    `dispatch_ideacion`/`dispatch_publicacion` y `Command(resume=…)`
  - `multi_agent/runtime.py` — máquina de estados event-driven **fuera** del
    grafo (start → dispatch → resultado → finalize), guarda anti-duplicados
    (sólo avanza el agente esperado) y `recover_running_tasks()` al arrancar
  - `history.py` — historial de chat durable en PostgreSQL (`chat_history`)
  - `main.py` — `/health` `/metrics` `/graph` `/tools` `/process`
    (`wait`/`timeout`) `/tasks/{id}` `/tasks/{id}/history`, consumidor
    `agent.results` e ingress `ideation_queue` (JSON crudo tolerado)
- **feat** (agentes): `agente_ideacion/` y `agente_publicacion/` como
  **paquetes microservicio** (`python -m agente_x`)
  - `graph.py` — grafo propio de 4 nodos vía `ToolRegistry` + gateway con
    trazabilidad `tool_calls`
  - `prompts.py` — prompts propios de cada agente (persona)
  - `/state/{task_id}` — checkpoint del agente en Redis
  - consumidor `auto_ack=False` con reconexión (reentrega si hay crash)
- **feat**: `docker-compose.yml` con los **13 servicios** (rabbitmq, postgres,
  redis-stack, llm-gateway, 6 tools, 2 agentes, orquestador)
- **test**: suite reescrita y ampliada a **201 tests** (antes 99)
  - `tests/unit/test_kernel.py` (28) — eventos, envelope/manifiesto,
    discovery, TaskStore y cliente del gateway
  - `tests/unit/test_agentes.py` (15) — estados, grafos, contratos de
    invocación de nodos y semántica idempotente del runner
  - `tests/unit/test_llm_gateway.py` (29) — balanceo, backoff, retries,
    fallback, salud de proveedores y claves de caché
  - `tests/unit/test_orquestador.py` (17) — supervisor, ciclo
    interrupt/resume y runtime completo con dobles
  - `tests/unit/test_prompts.py` (10) — prompts de los agentes
    (sustituye a `test_enrichment.py`)
  - `tests/integration/test_tools_services.py` (20) — contrato completo de
    los 6 tools + RPC AMQP
  - `tests/integration/test_orquestador_integration.py` (12) — discovery,
    nodos contra servicios reales y pipeline HTTP con estado externo
  - `tests/performance/` (9) — P01-P09 con LLM Gateway y tools
  - plan de pruebas movido a `tests/PLAN_DE_PRUEBAS.md` (IDs U-K/U-AG/U-ORQ/
    U-LLM/I-T/I-ORQ/P01-P09)
- **docs**: `docs/ARQUITECTURA.md` reescrito (topología, 4 requisitos,
  secuencia, happy path, caso de uso TechStart, decisiones);
  `docs/TECNOLOGIAS.md` reescrito; `README.md` reescrito

### Changed
- **refactor**: `shared_tools/embeddings.py` llama exclusivamente al LLM
  Gateway (nadie habla directo con Ollama)
- **refactor**: E2E `prueba_e2e.py` reescrito (HTTP + `--eventos` + verificación
  de estado externo en Redis/PostgreSQL) y `prueba_orquestador.py` (modo
  asíncrono + historial)
- **fix**: `Event.from_body` rellena `task_id` en el fallback *raw*
- **fix**: colas declaradas de forma coherente (`durable=True`) en
  `enviar_brief.py`, `prueba_e2e.py` y `test_rabbitmq.py` (un `ideation_queue`
  antiguo no durable provocaba `406 PRECONDITION_FAILED` en el consumidor)
- **fix**: `test_postgres.test_connection` no depende de constantes internas
  de psycopg2 (`SELECT 1`)
- **test**: validación final en verde con el stack completo:
  **201 passed, 0 skipped**; E2E HTTP + eventos + estado externo en 12 s

### Removed
- **remove**: `shared_tools/enrichment.py` (prompts duplicados → ahora viven
  en `agente_ideacion/prompts.py` y `agente_publicacion/prompts.py`)
- **remove**: `orchestrator/multi_agent/{ideacion,publicacion,tools}.py`
  (subgrafos y `@tool` en memoria: los agentes son microservicios y las tools
  son servicios con manifiesto)
- **remove**: `tests/unit/test_enrichment.py` (sustituido por
  `tests/unit/test_prompts.py`)
- **remove**: script temporal `_validar_interrupt.py`

## [1.3.0] — 2026-09-26

### Added
- **feat**: Orquestador multi-agente con **LangGraph** (`orchestrator/`)
  - `multi_agent/state.py` — Esquemas de estado (`SupervisorState`, `IdeacionState`, `PublicacionState`)
  - `multi_agent/tools.py` — 6 tools registradas como `@tool` de LangChain
  - `multi_agent/ideacion.py` — Subgrafo StateGraph del agente de ideación
  - `multi_agent/publicacion.py` — Subgrafo StateGraph del agente de publicación
  - `multi_agent/supervisor.py` — Patrón supervisor con enrutamiento condicional
  - `main.py` — FastAPI + RabbitMQ + LangGraph (puerto 8002)
- **feat**: Endpoints del orquestador: `/health`, `/metrics`, `/tools`, `/graph`, `/process`
- **feat**: Dockerfile y servicio `orchestrator` en docker-compose
- **feat**: Dependencias LangGraph: `langgraph 1.2`, `langchain 1.4`, `langchain-ollama 1.1`
- **test**: 15 tests unitarios del orquestador (`tests/unit/test_orquestador.py`)
  - Esquemas de estado (compatibilidad entre subgrafos y supervisor)
  - Tools LangChain (6 tools con nombre/descripción, tipo `BaseTool`)
  - Lógica de enrutamiento del supervisor (decide_next)
  - Compilación de grafos (StateGraph con nodos correctos)
- **test**: 5 tests de integración (`tests/integration/test_orquestador_integration.py`)
  - Nodos de ideación contra PostgreSQL + Ollama
  - Nodos de publicación contra PostgreSQL + Ollama
  - Pipeline completo E2E del orquestador
- **test**: Script `prueba_orquestador.py` para prueba E2E directa
- **docs**: `docs/TECNOLOGIAS.md` — Actualizado: LangGraph SÍ se usa en orquestador
- **docs**: `docs/ARQUITECTURA.md` — Diagrama del patrón supervisor y subgrafos
- **docs**: `docs/PLAN_DE_PRUEBAS.md` — Tests U-ORQ-01..04, I-ORQ-01..03, criterios G11..G14
- **docs**: `docs/CHANGELOG.md` — Este archivo

### Changed
- **refactor**: `docker-compose.yml` añade servicio `orchestrator` (puerto 8002)
- **refactor**: Suite completa: **99 passed, 1 skipped** (antes: 79 passed)
- **docs**: `README.md` reescrito completo — explicación de LangGraph (State,
  Node, Edge, patrón supervisor), arquitectura, 3 formas de uso, happy path
  y caso de uso real documentado con salida obtenida

## [1.2.0] — 2026-09-26

### Added
- **feat**: Paquete `shared_tools/` con tools compartidas para ambos agentes
  - `cliente.py` — Perfiles de cliente desde PostgreSQL
  - `tendencias.py` — Tendencias + búsqueda RAG con pgvector
  - `competencia.py` — Referencias de competencia + RAG
  - `rag.py` — Búsqueda semántica con pgvector (cosine similarity)
  - `enrichment.py` — Construcción de prompts enriquecidos
  - `fuentes_externas.py` — Google News RSS (sin API key)
  - `embeddings.py` — Generación de embeddings con nomic-embed-text
  - `db.py` — Utilidades de conexión PostgreSQL
- **feat**: Endpoint `GET /tools` en ambos agentes (lista tools disponibles)
- **feat**: Pipeline de enriquecimiento de contexto en ambos agentes
- **feat**: Seed data con 3 clientes, 17 tendencias, 13 competidores
- **feat**: Script `seed_data.py` para poblar datos de ejemplo
- **feat**: Script `backfill_embeddings.py` para generar embeddings faltantes
- **feat**: Script `enviar_brief.py` para enviar briefs personalizados
- **test**: Arquitectura de pruebas en `tests/`
  - `tests/unit/` — 54 tests unitarios (embeddings, enrichment, tools, RAG)
  - `tests/integration/` — 17 tests de integración (RabbitMQ, PostgreSQL, pipeline)
  - `tests/performance/` — 9 tests de rendimiento con umbrales
- **docs**: `docs/TECNOLOGIAS.md` — Stack tecnológico documentado
- **docs**: `docs/PLAN_DE_PRUEBAS.md` — Plan de pruebas completo
- **docs**: `docs/ARQUITECTURA.md` — Documentación de arquitectura
- **docs**: `docs/CHANGELOG.md` — Este archivo
- **chore**: `pytest.ini` con markers (unit, integration, performance, slow)
- **chore**: `.gitignore` actualizado

### Changed
- **fix**: URL de Ollama maneja host `0.0.0.0:11434` → `127.0.0.1:11434`
- **fix**: Credenciales RabbitMQ en agentes (`user`/`password`)
- **fix**: Dockerfile usa Python 3.11 (soporta `int | None` syntax)
- **fix**: `docker-compose.yml` build context en raíz del proyecto (para shared_tools)
- **fix**: `init.sql` — Eliminadas columnas duplicadas y comas trailing
- **refactor**: Ambos agentes usan pipeline de 5 pasos/4 pasos con tools
- **refactor**: `prueba_e2e.py` con JSON válido, credenciales y UTF-8

### Removed
- **chore**: Contenedor Ollama de docker-compose (usa instancia local)

## [1.1.0] — 2026-09-25

### Added
- **feat**: Pipeline E2E funcional (brief → idea → publicación → DB)
- **feat**: Integración con Ollama (gemma3:4b) para generación de texto
- **feat**: Integración con PostgreSQL para persistencia
- **feat**: Comunicación RabbitMQ entre agentes
- **feat**: Scripts de setup (`setup.ps1`, `setup.sh`)
- **feat**: Healthchecks en docker-compose
- **test**: `prueba_e2e.py` con verificación en base de datos

### Fixed
- **fix**: Autenticación RabbitMQ (credenciales user/password)
- **fix**: Encoding UTF-8 en Windows (emojis, tildes)
- **fix**: Puerto 11434 en conflicto (Ollama local vs contenedor)

## [1.0.0] — 2026-09-25

### Added
- **feat**: Estructura inicial del proyecto
- **feat**: Docker Compose con RabbitMQ, PostgreSQL, Ollama, 2 agentes
- **feat**: Esqueleto de agentes (FastAPI + RabbitMQ consumer)
- **feat**: Esquema de base de datos con pgvector
