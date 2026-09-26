# Prueba de Concepto — Sistema Multi-Agente con LangGraph

Sistema multi-agente para generación automatizada de contenido de marketing.
Un **orquestador LangGraph** (patrón *supervisor*) coordina **dos agentes especializados**
—ideación y publicación— que comparten estado y se apoyan en RAG (pgvector),
un LLM local (Ollama) y fuentes externas (Google News RSS).

---

## 1. ¿Qué hace el sistema?

Dado un **brief** de marketing (texto libre + `client_id`), el sistema devuelve:

1. Una **idea de campaña** original (título, descripción, rationale)
2. Una **publicación lista para redes** (hook, hashtags, CTA, ≤280 caracteres)

Ambas quedan guardadas en PostgreSQL **con embedding vectorial**, de modo que
las siguientes consultas RAG puedan usarlas como memoria ("¿qué ideas ya hice?").

---

## 2. Cómo funciona (explicación paso a paso)

### 2.1 Las tres piezas clave de LangGraph

| Concepto | Qué es | Aquí |
|----------|--------|------|
| **State** | Diccionario tipado que viaja por todo el grafo | `SupervisorState` |
| **Node** | Función pura que recibe estado y devuelve *updates* | `load_context`, `generate_idea`… |
| **Edge** | Conexión entre nodos; las *condicionales* deciden el siguiente | `decide_next()` |

**Lo importante**: los nodos *no* se pasan datos por parámetros sueltos.
Cada nodo lee del estado global y escribe de vuelta solo las claves que
produce. LangGraph fusiona esos updates automáticamente.

### 2.2 El estado compartido (`SupervisorState`)

```python
class SupervisorState(TypedDict):
    brief: dict              # entrada: qué pide el cliente
    client_id: int           # entrada: de qué cliente hablamos
    idea: str                # sale del agente de IDEACIÓN
    idea_id: int             # id en PostgreSQL
    publication: str         # sale del agente de PUBLICACIÓN
    publication_id: int      # id en PostgreSQL
    log: Annotated[list[str], operator.add]   # bitácora acumulativa
```

El supervisor **no tiene lógica oculta**: mira este diccionario y decide.
Si `idea` está vacía → falta la ideación. Si `idea` existe pero
`publication` no → falta la publicación. Si ambas existen → fin.

### 2.3 El patrón supervisor (orquestación)

```
                         ┌────────────────────────────────┐
                         │  decide_next(state)            │
                         │                                │
   START ──► start ──────┤  if not idea:      "ideacion"  │
             ▲           │  elif not pub:  "publicacion"  │
             │           │  else:               END       │
             │           └───────────┬────────────────────┘
             │                       │
             │       ┌───────────────┴───────────────┐
             │       ▼                               ▼
             │  ┌──────────────┐              ┌──────────────┐
             └──│ ideacion_    │              │ publicacion_ │
                │ agent        │              │ agent        │
                │ (subgrafo)   │              │ (subgrafo)   │
                └──────────────┘              └──────────────┘
```

Cada agente es un **subgrafo compilado** que se añade como nodo del supervisor.
Al terminar, el flujo vuelve a `decide_next`, que re-evalúa el estado.
Eso hace que el sistema sea **extensible**: añadir un tercer agente
(p. ej. "edición") consiste en añadir una rama más a `decide_next`.

### 2.4 Subgrafo de IDEACIÓN

```
START ─► load_context ─► fetch_news ─► generate_idea ─► save_idea ─► END
```

| Nodo | Qué hace | Servicio |
|------|----------|----------|
| `load_context` | Perfil de marca + tendencias + competencia + ideas similares | PostgreSQL / pgvector |
| `fetch_news` | Noticias reales del tema | Google News RSS |
| `generate_idea` | Construye prompt enriquecido y llama al LLM | Ollama (`gemma3:4b`) |
| `save_idea` | Calcula embedding y persiste | PostgreSQL + pgvector |

### 2.5 Subgrafo de PUBLICACIÓN

```
START ─► load_context ─► fetch_trending ─► generate_post ─► save_post ─► END
```

| Nodo | Qué hace | Servicio |
|------|----------|----------|
| `load_context` | Tono del cliente + tendencias para hashtags | PostgreSQL / pgvector |
| `fetch_trending` | Topics en tendencia (para hashtags) | Google News RSS |
| `generate_post` | Genera el post (hook, hashtags, CTA) | Ollama |
| `save_post` | Persiste con embedding, ligado a la idea | PostgreSQL |

### 2.6 Las tools (LangChain `@tool`)

Están registradas en `orchestrator/multi_agent/tools.py` con decorador `@tool`,
lo que les da **nombre, descripción y esquema de argumentos** — exactamente lo
que un LLM necesita para invocarlas (patrón *tool calling*):

| Tool | Fuente |
|------|--------|
| `load_client_profile` | PostgreSQL |
| `search_trends` | pgvector (búsqueda por similitud coseno) |
| `search_competitors` | pgvector |
| `search_similar_ideas_tool` | pgvector (RAG de memoria) |
| `fetch_news` | Google News RSS |
| `fetch_trending` | Google News RSS |

> **Nota de honestidad**: hoy los nodos llaman a las funciones base de
> `shared_tools/` de forma determinista (más predecible y rápido). Las `@tool`
> están registradas y expuestas en `GET /tools` para uso del LLM y para
> futuras versiones con bucle ReAct, donde el modelo *decide* qué tool usar.

---

## 3. Arquitectura

### 3.1 Diagrama general

```
                    entrada
        ┌──────────────┴──────────────┐
        │  POST /process              │  RabbitMQ ideation_queue
        ▼                             ▼
┌───────────────────────────────────────────────────┐
│        ORCHESTRATOR LangGraph   (puerto 8002)     │
│                                                   │
│   SupervisorState  ──►  decide_next()             │
│                              │                    │
│            ┌─────────────────┴──────────────┐     │
│            ▼                                ▼     │
│   ┌─────────────────┐             ┌─────────────────┐
│   │ AGENTE IDEACIÓN │             │AGENTE PUBLICACIÓN│
│   │  (StateGraph)   │             │   (StateGraph)   │
│   └────────┬────────┘             └────────┬────────┘
└────────────┼───────────────────────────────┼────────┘
             │                               │
   ┌─────────┼───────────┬───────────────────┼──────────┐
   ▼         ▼           ▼                   ▼          ▼
┌───────┐ ┌────────┐ ┌─────────┐      ┌──────────┐ ┌─────────┐
│Ollama │ │PostgreS│ │Google   │      │PostgreSQL│ │ Google  │
│  LLM  │ │QL+pgvec│ │News RSS │      │ + pgvec  │ │News RSS │
└───────┘ └────────┘ └─────────┘      └──────────┘ └─────────┘
```

### 3.2 Servicios

| Servicio | Puerto | Tecnología | Rol |
|----------|--------|-----------|-----|
| **orchestrator** | **8002** | **LangGraph + FastAPI** | **Coordina los 2 agentes** |
| agente-ideacion | 8000 | FastAPI + RabbitMQ | Agente independiente (compat.) |
| agente-publicacion | 8001 | FastAPI + RabbitMQ | Agente independiente (compat.) |
| rabbitmq | 5672 / 15672 | RabbitMQ 3-management | Colas + UI |
| postgres | 5432 | PostgreSQL 16 + pgvector | Datos + vectores (768d) |
| Ollama (host) | 11434 | Ollama local | LLM `gemma3:4b` + `nomic-embed-text` |

### 3.3 Modelo de datos

```sql
clientes                -- perfil_marca, restricciones_tono, historico, embedding
tendencias              -- 17 tendencias + embeddings
referencias_competencia -- 13 referencias + embeddings
ideas_generadas         -- ideas generadas + embeddings  (memoria RAG)
publicaciones_generadas -- posts generados + embeddings
```

Todas las tablas usan `embedding VECTOR(768)` y búsqueda por similitud coseno.

---

## 4. Cómo usarlo

### 4.1 Requisitos

- Docker Desktop con Compose
- Python 3.10+
- Ollama corriendo en el host con los modelos:
  ```bash
  ollama pull gemma3:4b
  ollama pull nomic-embed-text
  ```
- Dependencias Python:
  ```bash
  pip install langgraph langchain langchain-ollama fastapi pika psycopg2-binary requests
  ```

### 4.2 Arrancar todo

```bash
docker compose up -d --build
```

Verificar:

```bash
curl http://localhost:8002/health    # Orquestador LangGraph
curl http://localhost:8002/graph     # Estructura del grafo
curl http://localhost:8002/tools     # 6 tools LangChain
```

### 4.3 Las 3 formas de usarlo

#### A) HTTP directo (la más sencilla)

```bash
curl -X POST http://localhost:8002/process \
  -H "Content-Type: application/json" \
  -d '{"client_id": 1, "content": "Campaña de verano para cosmética natural"}'
```

Respuesta (estructura real, salida abreviada):

```json
{
  "idea": "**Title:** ... **Description:** ... **Why it works:** ...",
  "idea_id": 12,
  "publication": "☀️ ¿Aún le das pan con calculadora? ... #TechStart #FintechLatam",
  "publication_id": 8,
  "log": ["supervisor: pipeline iniciado"]
}
```

#### B) RabbitMQ (asíncrono, orientado a eventos)

```bash
python enviar_brief.py
```

El orquestador consume `ideation_queue` en un hilo en segundo plano y ejecuta
el mismo grafo. Útil cuando el emisor no debe esperar la respuesta.

#### C) Desde código (librería)

```python
import sys
sys.path.insert(0, "orchestrator")

from multi_agent.supervisor import run_pipeline

resultado = run_pipeline(
    brief={"client_id": 1, "content": "Campaña de verano"},
    client_id=1,
)
print(resultado["idea"])
print(resultado["publication"])
```

### 4.4 Endpoints del orquestador

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado del servicio |
| GET | `/metrics` | Modelo, agentes, patrón usado |
| GET | `/tools` | Las 6 tools LangChain con descripción |
| GET | `/graph` | Nodos, aristas y subgrafos |
| POST | `/process` | Ejecuta el pipeline completo y devuelve resultado |

### 4.5 Ejecutar las pruebas

```bash
pytest tests/ -v                 # 99 passed, 1 skipped
pytest tests/unit/ -v            # rápidas, sin servicios
pytest tests/integration/ -v     # requiere Docker + Ollama
python prueba_orquestador.py     # E2E directo del orquestador
python prueba_e2e.py             # E2E vía RabbitMQ (agentes individuales)
```

---

## 5. Happy Path (camino feliz)

Escenario: el cliente **EcoBrand** (`client_id=1`) pide una campaña de verano.

```bash
curl -X POST http://localhost:8002/process \
  -H "Content-Type: application/json" \
  -d '{"client_id": 1, "content": "Campana de verano para nuestra linea de cuidado personal organico dirigida a jovenes profesionales"}'
```

**Lo que ocurre por dentro (log real):**

```
supervisor  [supervisor] Iniciando pipeline para client_id=1
supervisor  → Enrutando a AGENTE DE IDEACIÓN

  ┌─ AGENTE IDEACIÓN ────────────────────────────────────────
  │ load_context   ✓ perfil de cliente + 5 tendencias
  │                ✓ 5 competidores + 0 ideas similares
  │ fetch_news     ✓ Google News RSS
  │ generate_idea  ✓ LLM (prompt 2443 chars) → idea
  │ save_idea      ✓ guardada con id=5 + embedding
  └──────────────────────────────────────────────────────────

supervisor  → Enrutando a AGENTE DE PUBLICACIÓN

  ┌─ AGENTE PUBLICACIÓN ─────────────────────────────────────
  │ load_context    ✓ tono del cliente + 3 tendencias
  │ fetch_trending  ✓ 5 trending topics
  │ generate_post   ✓ LLM → post
  │ save_post       ✓ guardada con id=3 + embedding
  └──────────────────────────────────────────────────────────

supervisor  → Pipeline completo. END
```

**Resultado:**

| Campo | Valor |
|-------|-------|
| `idea_id` | 5 (guardada en `ideas_generadas` con vector 768d) |
| `publication_id` | 3 (guardada en `publicaciones_generadas`) |
| `log` | `["supervisor: pipeline iniciado"]` |

**Verificación:**

```bash
# La idea y la publicación son consultables por RAG después
python -c "import psycopg2; ..."
```

**Criterios de éxito del happy path:**
- ✅ `POST /process` responde 200 en < 120 s
- ✅ `idea_id > 0` y `publication_id > 0`
- ✅ Ambas filas tienen `embedding IS NOT NULL`
- ✅ El log muestra el enrutamiento supervisor → ideación → publicación → END

---

## 6. Caso de uso completo

### Contexto

**TechStart** es una fintech latinoamericana (`client_id=2`) que simplifica
pagos para pequeñas empresas. Quiere lanzar una app que automatice cobros
para **panaderías y cafeterías independientes de México**.

### Ejecución

```bash
curl -X POST http://localhost:8002/process \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 2,
    "content": "Lanzamiento de una app movil que automatiza cobros para pequenas panaderias y cafeterias independientes en Mexico"
  }'
```

### Respuesta real obtenida

**IDEA (idea_id = 12):**

> **Title:** "El Pan que Vende Online: Cobra en un Click"
>
> **Description:** This Instagram carousel will visually showcase how
> TechStart's app streamlines payments for small bakeries and cafes, using
> real-life examples. We'll demonstrate the speed and ease with which they
> can accept payments via QR code (leveraging the 300% growth trend) and
> highlight the security features for peace of mind.
>
> **Why it works:** Leverages the carousel trend (higher engagement), taps
> into the burgeoning QR code payment market, directly addresses the
> client's values of speed and security...

**PUBLICACIÓN (publication_id = 8):**

> ¿Aún le das el pan con calculadora? 🍞 TechStart simplifica pagos para tu
> negocio. ⚡ 300% más rápido con QR y súper seguro. 👉 Descarga la app y
> empieza a recibir pagos sin complicaciones!
> `#TechStart #FintechLatam #PagosRapidos #Emprendedores #Marketing2026 #SmallBusiness`

### Por qué el resultado es bueno (atribución a las tools)

| Elemento del resultado | Tool que lo aportó |
|------------------------|--------------------|
| "valores de velocidad y seguridad" | `load_client_profile` (perfil TechStart) |
| "300% growth trend" / QR payments | `search_trends` (pgvector, 5 tendencias) |
| "gamification trend (Noom)" | `search_competitors` (referencias competencia) |
| Tono joven, directo, fiable | `restricciones_tono` del cliente |
| Hashtags `#FintechLatam #PagosRapidos` | `search_trends` + `fetch_trending` |
| Enfoque en panaderías (contexto del brief) | `brief.content` |

### Cadena de eventos

```
POST /process
   │
   ├─ Supervisor: idea vacía ──► IDEACIÓN
   │     ├─ load_context   → perfil + 5 tendencias + 5 competidores
   │     ├─ fetch_news     → noticias RSS
   │     ├─ generate_idea  → LLM genera "El Pan que Vende Online"
   │     └─ save_idea      → id=12 + embedding 768d
   │
   ├─ Supervisor: idea ✓, publication ✕ ──► PUBLICACIÓN
   │     ├─ load_context    → tono + 3 tendencias
   │     ├─ fetch_trending  → 5 topics trending
   │     ├─ generate_post   → LLM genera el post con hashtags
   │     └─ save_post       → id=8 + embedding 768d
   │
   └─ Supervisor: ambos ✓ ──► END
```

### Impacto acumulado

Tras varias ejecuciones, la tabla `ideas_generadas` crece y la tool
`search_similar_ideas_tool` empieza a devolver resultados: el sistema
**aprende del histórico** y evita repetir ideas (RAG de memoria).

---

## 7. Estructura del proyecto

```
proyecto multiagente/
├── orchestrator/                 # Orquestador multi-agente (LangGraph)
│   ├── multi_agent/
│   │   ├── state.py              # SupervisorState / IdeacionState / PublicacionState
│   │   ├── tools.py              # 6 LangChain @tool
│   │   ├── ideacion.py           # StateGraph de ideación (4 nodos)
│   │   ├── publicacion.py        # StateGraph de publicación (4 nodos)
│   │   └── supervisor.py         # decide_next() + create_orchestrator()
│   ├── main.py                   # FastAPI + RabbitMQ + LangGraph (8002)
│   ├── Dockerfile
│   └── requirements.txt
├── agente_ideacion/              # Agente independiente (8000, compat.)
├── agente_publicacion/           # Agente independiente (8001, compat.)
├── shared_tools/                 # Tools compartidas (cliente, tendencias, RAG…)
├── tests/
│   ├── unit/                     # 54+ tests (incluye orquestador)
│   ├── integration/              # 17+ tests (incluye pipeline LangGraph)
│   └── performance/              # 9 tests con umbrales
├── docs/
│   ├── ARQUITECTURA.md           # Arquitectura detallada
│   ├── TECNOLOGIAS.md            # Stack y por qué LangGraph
│   ├── PLAN_DE_PRUEBAS.md        # Plan de pruebas
│   └── CHANGELOG.md              # Historial (v1.0.0 → v1.3.0)
├── docker-compose.yml
├── init.sql                      # Esquema + seed
├── prueba_orquestador.py         # E2E del orquestador
├── prueba_e2e.py                 # E2E vía RabbitMQ
├── enviar_brief.py               # Envía briefs por RabbitMQ
├── seed_data.py                  # Pobla datos de ejemplo
└── README.md
```

---

## 8. Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Orquestación multi-agente | **LangGraph 1.2** (StateGraph, conditional edges) |
| Framework de tools | **LangChain 1.4** (`@tool`) |
| Cliente LLM | **langchain-ollama** (`ChatOllama`) |
| API | FastAPI + Uvicorn |
| Mensajería | RabbitMQ + pika |
| Base de datos | PostgreSQL 16 + pgvector |
| Embeddings | `nomic-embed-text` (768 dimensiones) |
| LLM | Ollama local — `gemma3:4b` |
| Fuentes externas | Google News RSS (sin API key) |
| Tests | pytest (unit / integration / performance) |

---

## 9. Solución de problemas

| Problema | Solución |
|----------|----------|
| Orquestador no arranca | `docker compose logs orchestrator` |
| Ollama no responde | Verifica `ollama list` y que esté en `localhost:11434` |
| Modelos no instalados | `ollama pull gemma3:4b && ollama pull nomic-embed-text` |
| Puerto 8002 ocupado | Cambia el mapeo en `docker-compose.yml` |
| RabbitMQ no responde | `docker compose restart rabbitmq` |
| Tests de integración fallan | Asegura `docker compose up -d` + Ollama activo |
| Cambiar modelo | `OLLAMA_MODEL=gemma3:4b docker compose up -d` |

---

## 10. Roadmap / No implementado

- **Agente de Edición** (tercera rama del supervisor)
- Bucle **ReAct** donde el LLM decide qué `@tool` invocar
- **Human-in-the-loop** (aprobación antes de publicar)
- API Gateway, Prometheus/Grafana, observabilidad distribuida
- Fallback multi-proveedor de LLM
