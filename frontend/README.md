# Multi-Agent Studio — Interfaz Web & Trazabilidad

Panel web interactivo y BFF (Backend-For-Frontend) para generar lotes de ideas, revisar dossiers persistidos y solicitar su publicación manual con trazabilidad.

> La guía completa de arquitectura, arranque, variables, API, validación y limitaciones está en [`docs/FRONTEND.md`](../docs/FRONTEND.md). Esta página es un resumen funcional.

---

## 1. Características Principales

### 🚀 1. Centro de Interacción (Studio)
- **Generación por lotes**: De una a cinco ideas; brief compartido opcional, briefs individuales por línea, temas/pilares y formato (`auto`, `reel`, `post`). Sin brief, la ideación usa el perfil de marca y señales de mercado.
- **Biblioteca persistente**: Búsqueda paginada por marca, progreso del lote, dossiers completos y selección explícita de la idea que se desea trabajar.
- **Publicación manual**: Selección de canales/modo/fecha; el agente prepara variantes editables sin publicar. El usuario revisa cada copy y aprueba el envío a Postiz; `now` requiere confirmación.
- **Vinculación de canales**: Consulta integraciones Postiz y las asocia a la marca activa desde Studio.

### 🔍 2. Observabilidad & Trazabilidad (Traceability)
- **Pipeline Interactivo por Nodos**:
  - `Ingreso & Supervisor`: LangGraph checkpointeado en Redis (`RedisSaver`).
  - `Agente de Ideación`: Descubrimiento e invocación de herramientas (`client.profile`, `trends.search`, `competitors.search`, `rag.similar`, `news.news`) y generación en LLM Gateway.
  - `Generación`: Cada tarea de ideación termina después de guardar su dossier; no activa publicación.
  - `Publicación`: Solo una solicitud manual con `idea_id` y canales validados despacha al publicador.
  - `Persistencia`: PostgreSQL conserva ideas y publicaciones; Redis guarda tarea/lote y RabbitMQ transporta eventos.
- **Timeline de Ejecución**: Duraciones en segundos, estados de cada nodo y microservicio.
- **Inspector de Herramientas (Tools-as-a-Service)**: Visualización del contexto extraído por cada herramienta (noticias RSS de Google News, similitud vectorial en pgvector, etc.).
- **Historial de Chat Durable**: Turnos `user` y `assistant` registrados en PostgreSQL.

### 📄 3. Resultados & Dossier Creativo
- **Idea de Campaña**: Título, descripción y justificación estratégica (*Why it works*).
- **Dossier de Preproducción**:
  - Tabla de **Guión Escena por Escena** (tiempo, visual, acción, locución, texto en pantalla).
  - Tabla de **Especificaciones de Cámara** (tiro/shot, ángulo, movimiento, encuadre).
  - Dirección de arte, locación, audio y notas de edición.
- **Mockup de Red Social**: Previsualización tipo tarjeta de red social, contador de caracteres (indicador de límite ≤ 280 para X/Twitter), hashtags y botones de copiado/exportación a Markdown o JSON.

### 📜 4. Historial de Tareas
- Lista completa de tareas en Redis (`TaskStore`) con filtro por estado (`completed`, `running`, `failed`).
- Carga instantánea de cualquier tarea anterior para auditar su trazabilidad y resultados.

### ⚙️ 5. Arquitectura & Estado de Servicios
- Monitor de salud de los microservicios aguas abajo.
- Catálogo de herramientas descubiertas en runtime por **Tool Discovery** (`/.well-known/tool-manifest`).
- Estadísticas de la memoria vectorial RAG (`ideas` y `publicaciones` indexadas con pgvector).

---

## 2. Estructura de la Carpeta

```
frontend/
├── server.py              # BFF FastAPI: endpoints de integración, SSE y servidor estático
├── requirements.txt       # Dependencias Python
├── run.ps1                # Script de inicio rápido en Windows PowerShell
├── run.sh                 # Script de inicio en Linux/macOS
├── Dockerfile             # Dockerfile para desplegar como contenedor independiente
├── README.md              # Documentación técnica
└── static/                # Aplicación Web SPA
    ├── index.html         # Interfaz de usuario (HTML5 + TailwindCSS + FontAwesome)
    ├── css/
    │   └── styles.css     # Estilos de nodos de pipeline, glassmorphism y mockups
    └── js/
        ├── api.js         # Cliente de API REST y SSE
        ├── pipeline.js    # Visualizador dinámico del grafo del pipeline
        ├── trace.js       # Inspector de trazabilidad y eventos
        └── app.js         # Lógica principal y manejo de estado
```

---

## 3. Cómo Ejecutar

### Opción A: Ejecución Local en Windows (Recomendada)
Desde la raíz del repositorio (los comandos de módulo y el script usan `frontend.server`):

```powershell
python -m pip install -r frontend\requirements.txt
.\frontend\run.ps1

# Alternativa manual:
python -m uvicorn frontend.server:app --host 0.0.0.0 --port 3000
```

Abre en tu navegador: **`http://localhost:3000`**

### Opción B: Ejecución en Linux / macOS
Desde la raíz del repositorio:

```bash
python -m pip install -r frontend/requirements.txt
./frontend/run.sh
```

Abre en tu navegador: **`http://localhost:3000`**

### Docker
El `docker-compose.yml` actual no declara el frontend. Para el camino documentado, levanta los servicios con Compose y ejecuta el BFF localmente con uno de los scripts anteriores. El `Dockerfile` del frontend es opcional; al ejecutarlo en un contenedor hay que configurar las URLs hacia los nombres de servicio de la red Compose, ya que `localhost` dentro del contenedor no es el host ni otro servicio.

---

## 4. Endpoints del Backend BFF (`server.py`)

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Sirve la interfaz web estática (`index.html`) |
| `GET` | `/api/health` | Estado de salud de los 5 subsistemas (Orquestador, Agentes, Redis, PG, LLM) |
| `GET` | `/api/overview` | Métricas generales (tareas, memoria RAG, herramientas) |
| `GET` | `/api/clients` | Lista de clientes y perfiles de marca |
| `POST` | `/api/ideas/generate` | Inicia un lote asíncrono de 1–5 ideas |
| `GET` | `/api/idea-batches/{id}?brand_id=` | Consulta progreso/resultados del lote |
| `GET` | `/api/ideas?brand_id=&query=&limit=&offset=` | Busca en la biblioteca de una marca |
| `GET` | `/api/ideas/{id}?brand_id=` | Abre el dossier persistido |
| `POST` | `/api/ideas/{id}/publish` | Prepara variantes para revisar; no llama a Postiz |
| `POST` | `/api/publications/{task_id}/deliver` | Entrega a Postiz los copies revisados y aprobados |
| `POST` | `/api/tasks` | Compatibilidad: genera una idea sin publicar |
| `POST` | `/api/demo` | Genera una idea demo sin publicar |
| `GET` | `/api/tasks` | Historial de tareas almacenadas en Redis |
| `GET` | `/api/tasks/{id}` | Datos brutos de una tarea |
| `GET` | `/api/tasks/{id}/trace` | **Trazabilidad completa**: nodos, duraciones, tools, contexto y salidas |
| `GET` | `/api/tasks/{id}/stream`| **Server-Sent Events (SSE)** para streaming en tiempo real |
| `GET` | `/api/tasks/{id}/history` | Historial de chat persistido en PostgreSQL |
| `GET` | `/api/tools` | Catálogo de herramientas descubiertas por Tool Discovery |
| `GET` | `/api/rag/stats` | Estadísticas de la memoria vectorial pgvector |
