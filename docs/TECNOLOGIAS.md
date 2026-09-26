# Stack Tecnológico

## ⚠️ Aclaración importante: ¿Usamos LangChain?

**NO.** Este proyecto **no utiliza LangChain, LangGraph, CrewAI ni AutoGen.**

Existía un archivo esqueleto `` `agente_ideacion/grafo.py `` con una clase dummy:

```python
class LangGraph:  # ← ESTO NUNCA SE USÓ
    def deliberate(self, brief):
        return {"content": f"Idea generated for {brief.content}"}
```

Esa clase **nunca fue importada** por el código real y fue ignorada.

---

## Tecnologías SÍ utilizadas

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
| FastAPI | 0.141 | Framework web + endpoints /health, /metrics, /tools |
| Uvicorn | 0.54 | Servidor ASGI |
| Pydantic | 2.13 | Validación de modelos de datos |

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
| requests | 2.34 | Cliente HTTP para API de Ollama |

### Fuentes externas
| Tecnología | Uso |
|-----------|-----|
| Google News RSS | Noticias reales vía RSS (sin API key) |

---

## ¿Por qué NO LangChain?

1. **Simplicidad**: Para esta PoC, llamadas HTTP directas a Ollama son suficientes
2. **Sin dependencias pesadas**: LangChain añade ~50 dependencias
3. **Transparencia**: El pipeline es explícito y fácil de depurar
4. **Control total**: Sin abstracciones que oculten lo que ocurre

### ¿Cuándo SÍ convendría LangChain?

- Cuando se necesiten **cadenas de prompts complejos** con memoria conversacional
- Cuando se quiera **tool-calling automático** (ReAct loop donde el LLM decide qué tool usar)
- Cuando se necesiten **múltiples proveedores LLM** con fallback
- Cuando se quiera **agentes con reasoning loops** (el LLM decide sus propios pasos)

### ¿Cómo se agregaría?

```bash
pip install langchain langchain-ollama
```

Y reemplazar las llamadas directas por:

```python
from langchain_ollama import OllamaLLM
from langchain.agents import initialize_agent, Tool

llm = OllamaLLM(model="gemma3:4b")
tools = [
    Tool(name="get_client_profile", func=get_client_profile, description="..."),
    Tool(name="get_relevant_trends", func=get_relevant_trends, description="..."),
]
agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
```

---

## Arquitectura actual (sin LangChain)

```
                    ┌─────────────────────────────────────┐
                    │           RabbitMQ                  │
  Brief ──────────► │  ┌─────────────┐ ┌──────────────┐  │
  (JSON)            │  │ideation_    │ │publication_  │  │
                    │  │queue        │ │queue         │  │
                    │  └──────┬──────┘ └──────▲───────┘  │
                    └─────────┼───────────────┼──────────┘
                              │               │
                   ┌──────────▼──┐   ┌────────┴──────────┐
                   │   AGENTE    │   │   AGENTE           │
                   │ IDEACIÓN    │──►│ PUBLICACIÓN         │
                   │  (8000)     │   │   (8001)           │
                   └──┬───┬───┬──┘   └──┬───┬───┬────────┘
                      │   │   │         │   │   │
            ┌─────────┘   │   └────┐    │   │   └────────┐
            ▼             ▼        ▼    ▼   ▼            ▼
       ┌────────┐   ┌──────────┐ ┌──┐┌────┐┌──────┐ ┌─────────┐
       │Ollama  │   │PostgreSQL│ │G.││Oll.││Postg│ │Google   │
       │(LLM)   │   │+pgvector │ │N.││LLM ││SQL  │ │News RSS │
       └────────┘   └──────────┘ └──┘└────┘└─────┘ └─────────┘
```

**Pipeline de cada brief:**

1. Brief llega por RabbitMQ
2. `enrich_brief_context()` ejecuta 4 tools:
   - `get_client_profile()` → PostgreSQL
   - `get_relevant_trends()` → pgvector similarity search
   - `get_relevant_competitors()` → pgvector similarity search
   - `search_similar_ideas()` → pgvector RAG
3. `fetch_google_news()` → Google News RSS
4. Prompt enriquecido se envía a Ollama (gemma3:4b)
5. Idea guardada en PostgreSQL + embedding
6. Publicada a `publication_queue`
7. Agente de publicación repite proceso similar
