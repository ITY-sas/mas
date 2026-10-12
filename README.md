# Prueba de Concepto — Sistema Multi-Agente de Microservicios

Sistema multi-agente para generación automatizada de contenido de marketing,
implementado como **arquitectura de microservicios** (14 contenedores) con
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

Studio genera de una a cinco ideas por lote, con brief opcional o briefs
individuales. Cada dossier se guarda en PostgreSQL dentro de su marca y puede
revisarse en una biblioteca. La generación no publica: el usuario selecciona
una idea, canales Postiz y modo; solo entonces se despacha el agente publicador.
El progreso operativo vive en Redis y el historial durable en `chat_history`.

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
 POST /ideas/generate   │ ORCHESTRATOR :8002 (stateless)     │
 POST /ideas/{id}/publish│ generación / publicación manual   │
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
Guía de arranque local: **[`GUIA_LEVANTAR_SERVICIOS.md`](GUIA_LEVANTAR_SERVICIOS.md)** ·
Interfaz & Trazabilidad: **[`frontend/README.md`](frontend/README.md)** ·
Plan de pruebas: **[`tests/PLAN_DE_PRUEBAS.md`](tests/PLAN_DE_PRUEBAS.md)** ·
Demo multi-tenant: **[`docs/DEMO_MULTI_TENANT.md`](docs/DEMO_MULTI_TENANT.md)** ·
Modelo de datos: **[`docs/DATOS.md`](docs/DATOS.md)**

---

## 4. Cómo funciona (explicación corta)

1. **`POST /ideas/generate`** crea un lote en Redis y hasta cinco tareas hijas;
  cada una dispara ideación por RabbitMQ. Un brief vacío se deriva del perfil,
  los pilares y los temas de la marca.
2. El agente genera y valida un dossier completo, lo guarda en
  `ideas_generadas` con `brand_id`, lote e índice, y termina. El supervisor no
  infiere que una idea deba publicarse.
3. Studio consulta `GET /ideas/batches/{id}` para el avance y usa
  `GET /ideas` / `GET /ideas/{id}` para buscar y revisar dossiers.
4. Tras seleccionar canales y modo, **`POST /ideas/{id}/publish`** carga el
  dossier y le pide al publicador preparar variantes; aún no llama a Postiz.
5. El usuario revisa/edita cada copy en Resultados y pulsa aprobar. Solo
  entonces **`POST /publications/{prepare_task_id}/deliver`** valida la marca,
  los canales y fecha, y despacha al publicador para enviar/programar en Postiz.

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

## 6. Formas de usarlo

### A) Interfaz Web Interactiva & Trazabilidad (Frontend Studio)

Inicia el servidor web y abre la interfaz en tu navegador:

```bash
# Windows
.\frontend\run.ps1

# Linux / macOS
./frontend/run.sh
```

Abre en tu navegador: **`http://localhost:3000`**

Incluye:
- Lotes de 1–5 ideas, briefs opcionales o individuales, temas y formato.
- Biblioteca persistente paginada con búsqueda, progreso y dossier completo.
- Selección de canales/modo y acción manual de publicación; `now` requiere confirmación.
- Trazabilidad SSE e historial de tareas, herramientas y checkpoints.

### B) Generar un lote por HTTP

```bash
curl -X POST http://localhost:8002/ideas/generate \
  -H "Content-Type: application/json" \
  -d '{"client_id": 1, "brand_id": 1, "count": 3, "content": "", "topics": ["verano", "sostenibilidad"]}'
```

```json
{
  "generation_batch_id": "…", "status": "running", "count": 3,
  "task_ids": ["…", "…", "…"]
}
```

Consulta `GET /ideas/batches/{generation_batch_id}?brand_id=1` para el avance y
`GET /ideas?brand_id=1&limit=50&offset=0` para la biblioteca. También se puede
enviar `briefs` como lista de briefs individuales; no puede superar `count`.

El brief acepta `content_format` con los valores `auto`, `reel` o `post`:

```json
{
  "client_id": 1,
  "content": "Presentar una crema solar natural para el verano colombiano",
  "content_format": "reel"
}
```

Un dossier `reel` exige escenas, guion, cámara, actuación, arte, audio y
edición. Un dossier `post` no exige guion ni cámara: entrega concepto visual,
composición, dirección de imagen, texto sobre la pieza, slides de carrusel,
caption direction, alt text y adaptaciones por plataforma. `auto` permite al
modelo elegir el formato más adecuado.

### C) Publicar manualmente una idea guardada

```bash
curl -X POST http://localhost:8002/ideas/13/publish \
  -H "Content-Type: application/json" \
  -d '{"brand_id": 1, "publish_mode": "draft", "integration_ids": ["integration-id"]}'
```

Esta primera operación valida la idea/canales y devuelve una tarea de
preparación. Cuando termina, abre Resultados, donde se revisa/edita el copy de
cada plataforma. La operación no crea todavía un post en Postiz.

Después de revisar, Studio solicita `POST /publications/{prepare_task_id}/deliver`
con `brand_id`, `publish_mode`, fecha, canales y las variantes aprobadas. Esa
segunda tarea llama a Postiz; su resultado registra modo, canales, respuesta o
error para inspeccionarlo en Trazabilidad.

### D) Por eventos RabbitMQ (compatibilidad)

```bash
python enviar_brief.py      # publica {client_id, content} en ideation_queue
```

### E) Configurar Postiz

Postiz es opcional y se configura mediante variables de entorno antes de
levantar Compose:

```powershell
$env:POSTIZ_API_URL = "https://api.postiz.com/public/v1"
$env:POSTIZ_API_KEY = "tu-api-key"
docker compose up -d --build
```

Primero se consultan los canales conectados:

```powershell
curl.exe http://localhost:8016/integrations
```

Vincula los canales a una marca desde Studio. Los modos `draft`, `schedule` y
`now` se eligen al publicar una idea desde la biblioteca; `now` requiere
confirmación explícita del usuario.

### E) Onboarding e ingesta de marca

Crear una marca dentro de una organización:

```powershell
$brand = @{ organization_id = 1; name = "Cafe Andino"; producto_servicio = "Cafe especial colombiano"; audiencia_objetivo = "Adultos cafeteros de Colombia"; objetivo_marketing = "Aumentar ventas online"; pais = "Colombia" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8010/brands -ContentType "application/json" -Body $brand | ConvertTo-Json -Depth 8
```

Ingerir un documento autorizado en la memoria de una marca:

```powershell
$document = @{ brand_id = 4; title = "Manual de marca"; content = "..."; scope = "brand"; source_type = "brand_manual" } | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri http://localhost:8013/documents -ContentType "application/json" -Body $document | ConvertTo-Json -Depth 8
```

Las migraciones están en `migrations/`. En volúmenes existentes, aplica 004 y
005 manualmente con `psql`; no hace falta borrar ni recrear datos.

---

## 7. Endpoints

| Servicio | Método · Ruta | Descripción |
|----------|---------------|-------------|
| orchestrator | GET `/health` `/metrics` `/graph` `/tools` | Salud, métricas, grafo, catálogo descubierto |
| orchestrator | POST `/ideas/generate` · GET `/ideas/batches/{id}` | Genera lote y consulta progreso |
| orchestrator | POST `/ideas/{id}/publish` | Prepara variantes por canal; no llama a Postiz |
| orchestrator | POST `/publications/{task_id}/deliver` | Envía a Postiz los copies aprobados |
| orchestrator | POST `/process` | Compatibilidad: generación individual, sin publicación |
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
tool_services/         6 tools (:8010-8015) + tool-postiz (:8016) + Dockerfile parametrizado
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
