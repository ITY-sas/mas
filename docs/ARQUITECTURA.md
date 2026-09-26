# Arquitectura del Sistema Multi-Agente

## Descripción general

Sistema multi-agente para generación automatizada de contenido de marketing. Utiliza **LangGraph** como orquestador con el patrón **supervisor** para coordinar dos agentes especializados, complementado con microservicios comunicados por mensajería asíncrona (RabbitMQ) y enriquecimiento de contexto mediante Retrieval Augmented Generation (RAG).

## Arquitectura LangGraph (orquestador)

```
                         ┌─────────────────────────────────────┐
                         │   ORCHESTRATOR (LangGraph) :8002    │
                         │                                     │
                         │   ┌─────────────────────────────┐   │
  POST /process ────────►│   │  SupervisorState            │   │
  RabbitMQ ideation_queue│   │  (brief, idea, publication) │   │
                         │   └──────────┬──────────────────┘   │
                         │              │                      │
                         │     ┌────────▼────────┐             │
                         │     │  decide_next()  │             │
                         │     │  (conditional   │             │
                         │     │   edge)         │             │
                         │     └───┬─────────┬───┘             │
                         │         │         │                 │
                         │    ┌────▼───┐ ┌───▼──────┐          │
                         │    │IDEACIÓN│ │PUBLICACIÓN│          │
                         │    │agent   │ │agent      │          │
                         │    │(graph) │ │(graph)    │          │
                         │    └────┬───┘ └───┬──────┘          │
                         │         │         │                 │
                         └─────────┼─────────┼─────────────────┘
                                   │         │
                    ┌──────────────┘         └──────────────┐
                    ▼                                       ▼
           ┌────────────────┐                     ┌────────────────┐
           │ LangChain @tool│                     │ LangChain @tool│
           │ (6 tools)      │                     │ (4 tools)      │
           └───────┬────────┘                     └───────┬────────┘
                   │                                      │
        ┌──────────┼──────────┐                ┌──────────┼──────────┐
        ▼          ▼          ▼                ▼          ▼          ▼
   PostgreSQL   Ollama   Google News      PostgreSQL   Ollama   Google News
   + pgvector   (LLM)    RSS              + pgvector   (LLM)    RSS
```

### Flujo del supervisor

```python
def decide_next(state: SupervisorState) -> str:
    if not state.get("idea"):
        return "ideacion_agent"      # ← Primero: generar idea
    if not state.get("publication"):
        return "publicacion_agent"   # ← Después: generar publicación
    return END                       # ← Pipeline completo
```

### Estructura del grafo

```
START → start → decide_next → ideacion_agent → decide_next → publicacion_agent → decide_next → END
              ↑______________________________|_____________________________↑
```

---

## Agentes

### 1. Agente de Ideación (LangGraph subgraph)

**Nodos**: `load_context` → `fetch_news` → `generate_idea` → `save_idea`

```
Brief (JSON)
  │
  ├─► [Node] load_context()
  │         ├─► get_client_profile() → PostgreSQL
  │         ├─► get_relevant_trends() → pgvector similarity
  │         ├─► get_relevant_competitors() → pgvector similarity
  │         └─► search_similar_ideas() → pgvector RAG
  │
  ├─► [Node] fetch_news()
  │         └─► fetch_google_news() → Google News RSS
  │
  ├─► [Node] generate_idea()
  │         └─► ChatOllama (gemma3:4b) → Genera idea
  │
  └─► [Node] save_idea()
            └─► PostgreSQL + embedding (nomic-embed-text)
```

### 2. Agente de Publicación (LangGraph subgraph)

**Nodos**: `load_context` → `fetch_trending` → `generate_post` → `save_post`

```
Idea (del estado del supervisor)
  │
  ├─► [Node] load_context()
  │         ├─► get_client_profile() → Restricciones de tono
  │         └─► get_relevant_trends() → Tendencias para hashtags
  │
  ├─► [Node] fetch_trending()
  │         └─► fetch_trending_topics() → Google News RSS
  │
  ├─► [Node] generate_post()
  │         └─► ChatOllama (gemma3:4b) → Genera post
  │
  └─► [Node] save_post()
            └─► PostgreSQL + embedding
```

### 3. Agentes individuales (compatibilidad)

Los agentes individuales (`agente_ideacion/`, `agente_publicacion/`) siguen
disponibles como microservicios independientes con FastAPI + RabbitMQ.

---

## Stack tecnológico

| Componente | Tecnología | Puerto |
|-----------|-----------|--------|
| Mensajería | RabbitMQ 3-management | 5672, 15672 |
| Base de datos | PostgreSQL 16 + pgvector | 5432 |
| LLM | Ollama (gemma3:4b) | 11434 |
| Embeddings | Ollama (nomic-embed-text, 768d) | 11434 |
| **Orquestador** | **LangGraph + FastAPI** | **8002** |
| Agente Ideación | FastAPI + Python 3.11 | 8000 |
| Agente Publicación | FastAPI + Python 3.11 | 8001 |

---

## Modelo de datos

```sql
clientes                -- Perfiles de marca (perfil_marca, tono, histórico)
tendencias              -- Tendencias de mercado + embeddings
referencias_competencia -- Competidores + embeddings
ideas_generadas         -- Ideas generadas + embeddings
publicaciones_generadas -- Publicaciones finales + embeddings
```

Todas las tablas tienen columna `embedding VECTOR(768)` para búsqueda semántica.

---

## Comunicación

### Vía orquestador LangGraph (recomendado)

```
prueba_orquestador.py / POST /process
         │
         ▼
┌────────────────────────────────────────┐
│  Orquestador LangGraph (8002)          │
│                                        │
│  Supervisor → Ideación → Publicación   │
│  (estado compartido en SupervisorState)│
└────────────────┬───────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
 PostgreSQL    Ollama    Google News
```

### Vía RabbitMQ (agentes individuales)

```
enviar_brief.py
        │
        ▼ (JSON)
   ┌────────────────┐
   │ ideation_queue  │ ◄── RabbitMQ
   └───────┬────────┘
           │
    ┌──────▼───────┐
    │  IDEACIÓN    │──► Ollama + PostgreSQL
    └──────┬───────┘
           │
   ┌───────▼────────┐
   │publication_queue│ ◄── RabbitMQ
   └───────┬────────┘
           │
    ┌──────▼────────┐
    │ PUBLICACIÓN    │──► Ollama + PostgreSQL
    └───────────────┘
```

---

## Tools disponibles

### Orquestador LangGraph (`GET /tools`)

Registradas como `@tool` de LangChain:

| Tool | Descripción |
|------|-------------|
| `load_client_profile` | Perfil de marca del cliente |
| `search_trends` | Búsqueda RAG de tendencias |
| `search_competitors` | Referencias de competencia |
| `search_similar_ideas_tool` | RAG sobre ideas previas |
| `fetch_news` | Noticias de Google News RSS |
| `fetch_trending` | Topics en tendencia |

### Agente de Ideación (`GET /tools`)
- `get_client_profile` — Perfil de marca del cliente
- `get_relevant_trends` — Búsqueda RAG de tendencias
- `get_relevant_competitors` — Referencias de competencia
- `search_similar_ideas` — RAG sobre ideas previas
- `fetch_google_news` — Noticias de Google News RSS
- `enrich_brief_context` — Combina todas las tools
- `generate_idea_with_ollama` — Genera idea con LLM
- `save_idea` — Guarda idea + embedding

### Agente de Publicación (`GET /tools`)
- `get_client_profile` — Perfil y tono del cliente
- `get_relevant_trends` — Tendencias para hashtags
- `fetch_trending_topics` — Topics en tendencia
- `enrich_idea_context` — Combina tools
- `generate_publicacion_with_ollama` — Genera post
- `save_publicacion` — Guarda post + embedding

---

## Endpoints del orquestador

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/metrics` | GET | Métricas del orquestador |
| `/tools` | GET | Lista tools LangChain registradas |
| `/graph` | GET | Estructura del grafo supervisor |
| `/process` | POST | Ejecuta el pipeline completo directamente |

---

## Decisiones de diseño

1. **LangGraph para orquestación**: Patrón supervisor con estado compartido y enrutamiento condicional
2. **LangChain @tool**: Tools registradas como objetos `BaseTool` con nombre y descripción
3. **ChatOllama**: Integración nativa LangChain ↔ Ollama para el orquestador
4. **Agentes individuales sin LangChain**: HTTP directo para simplicidad y retrocompatibilidad
5. **Ollama local**: Los agentes usan `host.docker.internal:11434` (instancia local, ahorra RAM)
6. **Embeddings con nomic-embed-text**: 768 dimensiones, modelo ligero y rápido
7. **pgvector con IVFFlat**: Índice para búsqueda vectorial eficiente
8. **Reconexión automática**: Los agentes reconectan RabbitMQ si se cae
9. **Fallback en tools**: Si Ollama falla, se usa contenido mock
