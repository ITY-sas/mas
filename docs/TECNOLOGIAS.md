# Stack Tecnológico

## ✅ LangGraph: SÍ se usa (en el orquestador)

**Desde la v1.3.0, este proyecto SÍ utiliza LangGraph y LangChain.**

El orquestador (`orchestrator/`) implementa un **sistema multi-agente real** con:

| Componente | Tecnología | Uso |
|-----------|-----------|-----|
| Orquestador | **LangGraph 1.2** | Patrón supervisor que coordina los agentes |
| Agentes | **LangGraph StateGraph** | Subgrafos de ideación y publicación |
| Tools | **LangChain @tool** | 6 tools registradas y disponibles |
| LLM | **langchain-ollama ChatOllama** | Llamadas al LLM vía LangChain |

> **Nota**: Los agentes individuales (`agente_ideacion/`, `agente_publicacion/`)
> siguen usando llamadas HTTP directas a Ollama (sin LangChain) para mantener
> la compatibilidad y simplicidad. El orquestador LangGraph es el sistema
> multi-agente completo.

### ¿Por qué LangGraph AHORA sí?

1. **Sistema multi-agente real**: El patrón supervisor de LangGraph coordina
   ambos agentes con lógica de enrutamiento condicional
2. **Estado compartido**: `SupervisorState` mantiene el estado global entre agentes
3. **Grafos como grafos**: Cada agente es un `StateGraph` con nodos y aristas explícitos
4. **Tools como tools**: Las funciones están registradas como `@tool` de LangChain
5. **Observabilidad**: LangGraph permite inspeccionar la ejecución del grafo

### Arquitectura multi-agente con LangGraph

```
                    ┌─────────────────────────────────────────┐
                    │     SUPERVISOR (LangGraph StateGraph)    │
                    │                                         │
                    │   START → start → [decide_next] → ...   │
                    │                                         │
                    │   decide_next(state):                   │
                    │     if not idea → "ideacion_agent"      │
                    │     if not publication → "publicacion_agent"
                    │     else → END                          │
                    └────────────┬────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                                     ▼
    ┌──────────────────────┐            ┌──────────────────────┐
    │  IDEACIÓN AGENT      │            │  PUBLICACIÓN AGENT   │
    │  (StateGraph)        │            │  (StateGraph)        │
    │                      │            │                      │
    │  load_context        │            │  load_context        │
    │      ↓               │            │      ↓               │
    │  fetch_news          │            │  fetch_trending      │
    │      ↓               │            │      ↓               │
    │  generate_idea       │            │  generate_post       │
    │      ↓               │            │      ↓               │
    │  save_idea           │            │  save_post           │
    └──────────┬───────────┘            └──────────┬───────────┘
               │                                    │
               ▼                                    ▼
    ┌──────────────────────┐            ┌──────────────────────┐
    │ LangChain Tools (6): │            │ LangChain Tools (6): │
    │ • load_client_profile│            │ • load_client_profile│
    │ • search_trends      │            │ • search_trends      │
    │ • search_competitors │            │ • fetch_trending     │
    │ • search_similar_ideas            │ • fetch_news         │
    │ • fetch_news         │            │                      │
    │ • fetch_trending     │            │                      │
    └──────────────────────┘            └──────────────────────┘
```

---

## Stack general del proyecto

### Orquestación y comunicación
| Tecnología | Versión | Uso |
|-----------|---------|-----|
| Docker Compose | v2.40 | Orquestación de contenedores |
| RabbitMQ | 3-management | Colas de mensajería entre agentes |
| pika | 1.4.4 | Cliente Python de RabbitMQ |

### Agentes y API
| Tecnología | Versión | Uso |
|-----------|---------|-----|
| Python | 3.11 | Lenguaje principal |
| FastAPI | 0.141 | Framework web + endpoints |
| Uvicorn | 0.54 | Servidor ASGI |
| Pydantic | 2.13 | Validación de modelos de datos |

### Multi-agente (orquestador)
| Tecnología | Versión | Uso |
|-----------|---------|-----|
| **LangGraph** | 1.2.12 | StateGraph, supervisor pattern, conditional edges |
| **LangChain** | 1.4.2 | Framework base |
| **langchain-core** | 1.6.5 | @tool, tipos base |
| **langchain-ollama** | 1.1.0 | ChatOllama para LLM calls |

### Base de datos y búsqueda semántica
| Tecnología | Versión | Uso |
|-----------|---------|-----|
| PostgreSQL | 16 | Base de datos relacional |
| pgvector | 0.5 | Extensión para vectores + similitud de coseno |
| psycopg2-binary | 2.9 | Cliente PostgreSQL |
| nomic-embed-text | (Ollama) | Modelo de embeddings (768 dimensiones) |

### LLM
| Tecnología | Versión | Uso |
|-----------|---------|-----|
| Ollama | local | Runtime de LLM local |
| gemma3:4b | 3.3 GB | Modelo de generación de texto |
| requests | 2.34 | Cliente HTTP (agentes individuales) |
| ChatOllama | (LangChain) | Cliente LLM (orquestador) |

### Fuentes externas
| Tecnología | Uso |
|-----------|-----|
| Google News RSS | Noticias reales vía RSS (sin API key) |

---

## Comparativa: agentes individuales vs orquestador

| Aspecto | Agentes individuales | Orquestador LangGraph |
|---------|---------------------|----------------------|
| Coordinación | RabbitMQ (colas) | LangGraph supervisor (estado compartido) |
| Tools | Funciones Python directas | LangChain `@tool` registradas |
| LLM | HTTP directo (`requests`) | `ChatOllama` (LangChain) |
| Estado | Se pasa por mensajes JSON | `SupervisorState` (TypedDict) |
| Enrutamiento | Colas separadas | `decide_next()` con edges condicionales |
| Observabilidad | Logs | Logs + estructura de grafo inspeccionable |

### ¿Cuándo usar cada uno?

- **Agentes individuales**: Para pruebas aisladas, integración con sistemas externos
  que consumen una cola específica, o cuando no se necesita coordinación.
- **Orquestador LangGraph**: Para el pipeline completo end-to-end, cuando se
  necesita estado compartido entre agentes, o para inspeccionar el flujo de ejecución.
