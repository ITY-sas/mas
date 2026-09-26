# Arquitectura del Sistema Multi-Agente

## Descripción general

Sistema multi-agente para generación automatizada de contenido de marketing, basado en microservicios comunicados por mensajería asíncrona (RabbitMQ) con enriquecimiento de contexto mediante Retrieval Augmented Generation (RAG).

## Agentes

### 1. Agente de Ideación (Puerto 8000)

**Responsabilidad**: Recibir briefs de clientes y generar ideas de contenido personalizadas.

**Pipeline**:
```
Brief (JSON)
  │
  ├─► [Tool] get_client_profile(client_id)
  │         → PostgreSQL: perfil de marca, tono, histórico
  │
  ├─► [Tool] get_relevant_trends(brief)
  │         → pgvector: búsqueda de similitud de coseno
  │
  ├─► [Tool] get_relevant_competitors(brief)
  │         → pgvector: referencias de competencia
  │
  ├─► [Tool] search_similar_ideas(brief)
  │         → pgvector RAG: ideas previas similares
  │
  ├─► [Tool] fetch_google_news(brief)
  │         → Google News RSS: noticias reales
  │
  ├─► build_ideacion_prompt() → Prompt enriquecido
  │
  ├─► Ollama (gemma3:4b) → Genera idea
  │
  ├─► save_idea() → PostgreSQL + embedding (nomic-embed-text)
  │
  └─► publish_idea() → RabbitMQ (publication_queue)
```

### 2. Agente de Publicación (Puerto 8001)

**Responsabilidad**: Recibir ideas y generar publicaciones listas para redes sociales.

**Pipeline**:
```
Idea (JSON)
  │
  ├─► [Tool] get_client_profile(client_id)
  │         → Restricciones de tono
  │
  ├─► [Tool] get_relevant_trends(idea)
  │         → Tendencias para hashtags
  │
  ├─► [Tool] fetch_trending_topics()
  │         → Google News RSS: topics trending
  │
  ├─► build_publicacion_prompt() → Prompt enriquecido
  │
  ├─► Ollama (gemma3:4b) → Genera post
  │
  └─► save_publicacion() → PostgreSQL + embedding
```

## Stack tecnológico

| Componente | Tecnología | Puerto |
|-----------|-----------|--------|
| Mensajería | RabbitMQ 3-management | 5672, 15672 |
| Base de datos | PostgreSQL 16 + pgvector | 5432 |
| LLM | Ollama (gemma3:4b) | 11434 |
| Embeddings | Ollama (nomic-embed-text, 768d) | 11434 |
| Agente Ideación | FastAPI + Python 3.11 | 8000 |
| Agente Publicación | FastAPI + Python 3.11 | 8001 |

## Modelo de datos

```sql
clientes                -- Perfiles de marca (perfil_marca, tono, histórico)
tendencias              -- Tendencias de mercado + embeddings
referencias_competencia -- Competidores + embeddings
ideas_generadas         -- Ideas generadas + embeddings
publicaciones_generadas -- Publicaciones finales + embeddings
```

Todas las tablas tienen columna `embedding VECTOR(768)` para búsqueda semántica.

## Comunicación

```
prueba_e2e.py / enviar_brief.py
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

## Tools disponibles

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

## Decisiones de diseño

1. **Sin LangChain**: Llamadas HTTP directas a Ollama para simplicidad y transparencia
2. **Ollama local**: Los agentes usan `host.docker.internal:11434` (instancia local, ahorra RAM)
3. **Embeddings con nomic-embed-text**: 768 dimensiones, modelo ligero y rápido
4. **pgvector con IVFFlat**: Índice para búsqueda vectorial eficiente
5. **Reconexión automática**: Los agentes reconectan RabbitMQ si se cae
6. **Fallback en tools**: Si Ollama falla, se usa contenido mock
