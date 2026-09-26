# Plan de Pruebas — Sistema Multi-Agente de Microservicios

> Ubicación: `tests/PLAN_DE_PRUEBAS.md` (el plan vive junto a las pruebas).

## 1. Alcance de las pruebas

### 1.1 Niveles y marcadores

| Nivel | Carpeta | Marcador | Objetivo | Requisitos |
|-------|---------|----------|----------|------------|
| **Unitarias** | `tests/unit/` | `unit` | Contratos, nodos y runtime con dobles falsos | Ninguno (sin red) |
| **Integración** | `tests/integration/` | `integration` | Servicios reales: tools, agentes, orquestador | `docker compose up -d --build` |
| **Rendimiento** | `tests/performance/` | `performance` | Umbrales de latencia | Stack + Ollama |
| **E2E (script)** | `prueba_e2e.py`, `prueba_orquestador.py` | — | Flujo completo punta a punta | Stack completo |

Marcador auxiliar: `slow` (> 5 s: generaciones LLM, pipelines completos).

### 1.2 Cómo ejecutar

```bash
pytest tests/ -v                      # toda la suite
pytest tests/ -v -m unit              # sólo unitarias (sin servicios)
pytest tests/ -v -m integration       # sólo integración (requiere stack)
pytest tests/ -v -m performance       # sólo rendimiento
pytest tests/ -v -m "integration and not slow"   # integración rápida
```

> Las pruebas de integración **se saltan** (skip) si el servicio requerido no
> está disponible; esto permite ejecutar `pytest tests/ -v` en cualquier estado
> sin fallos espurios.

### 1.3 Cobertura objetivo

```
Módulo / servicio                      Unitarias  Integración  Rendimiento
──────────────────────────────────────────────────────────────────────────
common/events.py (Event, colas, RPC)      ✅           —            —
common/contracts.py (envelope/manifiesto) ✅           —            —
common/tool_client.py (discovery/call)    ✅           ✅            ✅
common/task_store.py (Redis)              ✅           —            —
common/gateway_client.py                  ✅           —            ✅
common/agent_runner.py (idempotencia)     ✅           —            —
agente_ideacion (estado, grafo, nodos)    ✅           ✅            ✅
agente_publicacion (estado, grafo, nodos) ✅           ✅            —
prompts de los agentes                    ✅           —            —
orquestador: SupervisorState/decide       ✅           —            —
orquestador: interrupt/Command(resume)    ✅           —            —
orquestador: runtime event-driven         ✅           —            —
orquestador: API HTTP + estado externo    —            ✅            ✅
6 tool services (health/manifest/ops)     ✅*          ✅            —
llm_gateway (backoff/fallback/balanceo)   ✅**         ✅            ✅
shared_tools (cliente/tendencias/…)       ✅           ✅            ✅
shared_tools/embeddings (vía gateway)     ✅           —            ✅
fuentes externas (RSS)                    ✅           ✅            —
PostgreSQL / RabbitMQ                     —            ✅            ✅

*  tests/unit/test_tools_*.py (lógica de dominio, BD simulada/real según fixture)
** tests/unit/test_llm_gateway.py (funciones puras del gateway)
```

## 2. Estructura de la suite

```
tests/
├── PLAN_DE_PRUEBAS.md          ← este documento
├── conftest.py                 # fixtures compartidos (brief, contexto, embedding)
├── unit/
│   ├── test_kernel.py          # eventos, contratos, TaskStore, discovery, gateway client
│   ├── test_agentes.py         # estados/grafo/nodos de los agentes + runner idempotente
│   ├── test_orquestador.py     # supervisor, interrupt/resume, runtime event-driven
│   ├── test_prompts.py         # prompts de ideación y publicación (U06-U10)
│   ├── test_embeddings.py      # embeddings centralizados en el gateway
│   ├── test_rag.py             # lógica RAG
│   ├── test_tools_cliente.py   # dominio de tool-client
│   ├── test_tools_tendencias.py# dominio de tool-trends
│   ├── test_tools_competencia.py # dominio de tool-competitors
│   └── test_fuentes_externas.py# RSS / tendencias
├── integration/
│   ├── test_tools_services.py  # contrato completo de los 6 tools + RPC AMQP
│   ├── test_orquestador_integration.py # discovery, nodos vs servicios, pipeline HTTP
│   ├── test_pipeline.py        # agentes vivos, endpoints, contexto vía contratos
│   ├── test_postgres.py        # esquema + queries
│   └── test_rabbitmq.py        # colas/producción/consumo
└── performance/
    └── test_performance.py     # P01-P09
```

## 3. IDs de prueba

### 3.1 Unitarias

| ID | Archivo | Qué verifica |
|----|---------|--------------|
| U-K-01…03 | `test_kernel.py` | Evento: serialización roundtrip, fallback *raw*, constantes de tipos/colas |
| U-K-04…06 | `test_kernel.py` | Envelope (ok/error/no-envelope) y manifiesto (build/validate) |
| U-K-07…10 | `test_kernel.py` | Tool Discovery: URLs por entorno, mapeo op→endpoint, descubrimiento tolerante a fallos, `call()` sobre contrato, `as_langchain_tools()` |
| U-K-11…12 | `test_kernel.py` | TaskStore: crear/leer, estados, resultados por agente, listado |
| U-K-13…15 | `test_kernel.py` | Cliente del gateway: URL por entorno, `/v1/generate`, errores 502, embeddings, health |
| U-AG-01 | `test_agentes.py` | Esquemas `IdeacionState` / `PublicacionState` |
| U-AG-02 | `test_agentes.py` | Compilación de ambos grafos y sus nodos |
| U-AG-03 | `test_agentes.py` | Nodos invocan sólo contratos (ToolRegistry) y el gateway; trazabilidad `tool_calls` |
| U-AG-04…05 | `test_agentes.py` | `run_agent_task`: nueva / retoma desde checkpoint / reentrega duplicada idempotente |
| U-ORQ-01 | `test_orquestador.py` | `SupervisorState` e `initial_state()` |
| U-ORQ-02 | `test_orquestador.py` | `decide_next`: enruta a ideación → publicación → END y detecta fallos |
| U-ORQ-03 | `test_orquestador.py` | Ciclo `interrupt()` → `Command(resume=…)` con MemorySaver |
| U-ORQ-04 | `test_orquestador.py` | Runtime completo con dobles: start → dispatch → resultado → finalize |
| U-ORQ-05 | `test_orquestador.py` | Fallo de agente → tarea `failed`; resultado duplicado/obsoleto ignorado |
| U06-U10 | `test_prompts.py` | Prompts de los agentes (perfil, tendencias, competencia, RAG, 280 chars) |
| U-EMB | `test_embeddings.py` | Embeddings vía gateway (normalización, lote, None en fallo) |
| U-LLM-01… | `test_llm_gateway.py` | Balanceo ponderado, `backoff_delay`, cadena de fallback, claves de caché |
| U-T-… | `test_tools_*.py` | Lógica de dominio de cada tool service |

### 3.2 Integración

| ID | Archivo | Qué verifica |
|----|---------|--------------|
| I-T-01…03 | `test_tools_services.py` | Cada tool: `/health`, manifiesto válido, operación principal con envelope ok |
| I-T-04 | `test_tools_services.py` | `tool-rag` es dueño de sus tablas (`/stats`) |
| I-T-05 | `test_tools_services.py` | Invocación RPC por eventos (`tool.trends.rpc`) |
| I-ORQ-01 | `test_orquestador_integration.py` | Tool Discovery descubre los 6 manifiestos y son válidos |
| I-ORQ-02 | `test_orquestador_integration.py` | `call()` REST de perfil y tendencias |
| I-ORQ-03 | `test_orquestador_integration.py` | Nodos de los agentes contra servicios reales + generación vía gateway |
| I-ORQ-05 | `test_orquestador_integration.py` | Pipeline HTTP completo: resultado + TaskStore + historial de chat |
| I-ORQ-06 | `test_orquestador_integration.py` | `/health`, `/graph`, `/tools` del orquestador |
| I01-I06 | `test_pipeline.py` | Salud y endpoints de los agentes (health/metrics/tools/state) |
| I07-I11 | `test_postgres.py` | Esquema, tablas y queries de negocio |
| I12-I12b | `test_pipeline.py` | `/tools` de los agentes: catálogo descubierto con operaciones |
| I13-I13b | `test_pipeline.py` | Contexto completo armado con contratos REST de los tools |
| I14-I16 | `test_rabbitmq.py` | Colas durables, publicación y consumo |

### 3.3 Rendimiento

| ID | Umbral | Qué mide |
|----|--------|----------|
| P01 | < 2 s | `generate_embedding` vía LLM Gateway |
| P02 | < 3 s | `get_relevant_trends` |
| P03 | < 10 s | Contexto completo vía 4 contratos REST (tool services) |
| P04 | < 60 s | Generación LLM vía `/v1/generate` |
| P05 | < 120 s | Pipeline completo (`POST /process wait=true`) |
| P06 | < 500 ms | Endpoints `/health` |
| P07 | < 500 ms | Búsqueda vectorial pgvector (sin incluir embedding) |
| P08 | < 2 s | Conexión y roundtrip a RabbitMQ |
| P09 | < 200 ms | Latencia de la caché de prompts del gateway |

## 4. Criterios de aceptación de la suite

1. `pytest tests/ -v` en verde: **todo aprobado o saltado por falta de
   servicios**, cero errores.
2. `pytest tests/ -v -m unit` en verde **sin ningún servicio levantado**.
3. Con el stack completo (`docker compose up -d --build`): los tests de
   integración **no se saltan** y `prueba_e2e.py` termina con código 0.
4. Cubre los 4 requisitos arquitectónicos:
   - **Estado externo**: U-ORQ-03/05, U-AG-04/05, I-ORQ-05 (TaskStore,
     checkpoints, historial de chat).
   - **Tools-as-a-Service + discovery**: U-K-07…10, I-T-*, I-ORQ-01/02.
   - **Resiliencia de eventos**: U-K-01…03, U-ORQ-05 (duplicados),
     I-T-05 (RPC), I14-I16.
   - **LLM Gateway**: U-K-13…15, U-LLM-*, I-ORQ-03, P01/P04/P09.
