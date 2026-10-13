# Multi-Agent Studio — Backoffice Ejecutivo & Trazabilidad

Panel web interactivo y BFF (Backend-For-Frontend) diseñado con arquitectura de **Backoffice Ejecutivo**, soporte para React/Vite/Next, menús laterales, métricas en vivo, dashboards ejecutivos, visualización de pipelines LangGraph en tiempo real, biblioteca de dossiers y publicación manual multicanal.

> La guía completa de arquitectura, arranque, variables, API, validación y limitaciones está en [`docs/FRONTEND.md`](../docs/FRONTEND.md). Esta página es un resumen funcional.

---

## 1. Características Principales

### 📊 1. Dashboard General (Centro de Operaciones)
- **KPIs en tiempo real**: Tareas totales en Redis TaskStore, memoria vectorial pgvector (ideas + publicaciones), canales Postiz activos y salud de microservicios en vivo.
- **Ficha corporativa activa**: Producto/servicio, tono de marca, restricciones legales y audiencia.
- **Lote activo**: Seguimiento en vivo de lotes en ejecución con acceso a trazas.
- **Actividad reciente**: Listado de últimas tareas con auditoría directa de traza y resultados.

### 🚀 2. Generador de Lotes (Studio)
- **Generación por lotes**: De una a cinco ideas; brief compartido opcional, briefs individuales por línea, temas/pilares y selector de formato (`auto`, `reel`, `post`). Sin brief, la ideación usa el perfil de marca y señales de mercado.
- **Plantillas rápidas (1-Clic)**: EcoBrand (protector solar), TechStart (pagos QR), FitLife (reto 30 días).
- **Vinculación de canales**: Asocia integraciones Postiz a la marca activa en un clic.

### 📚 3. Biblioteca Persistente de Ideas
- **Explorador Master-Detail**: Búsqueda en vivo en títulos y dossiers, contador de ideas y paginación rápida.
- **Dossier Creativo Completo**: Concepto, objetivo, audiencia, mensaje clave, CTA, razón estratégica (*Why it works*) y visor JSON.
- **Preparación de publicación**: Selección de canales destino, modo (`draft`, `schedule`, `now`) y fecha; el agente prepara variantes editables sin publicar directamente.

### 📤 4. Gestión de Publicaciones Postiz
- **Seguimiento por marca**: Preparaciones y entregas, estado (`awaiting_approval`, `approved_pending`, `sent`, etc.), canal y copy.
- **Revisión y edición**: Edición in-situ de copys por canal antes de despachar a Postiz.
- **Acceso directo**: Apertura de trazabilidad o acceso a la interfaz web de Postiz (:4007).

### 🔍 5. Observabilidad & Trazabilidad (Traceability)
- **Pipeline Interactivo por Nodos (5 Etapas)**:
  - `Ingreso & Supervisor`: LangGraph checkpointeado en Redis (`RedisSaver`).
  - `Agente de Ideación`: Invocación de herramientas (`client.profile`, `trends.search`, `competitors.search`, `rag.similar`, `news.news`) y síntesis en LLM Gateway.
  - `Reanudación Orquestador`: Reanudación tras guardar el dossier en biblioteca.
  - `Agente de Publicación`: Preparación y entrega de copys hacia redes sociales.
  - `Persistencia Durable`: pgvector, `chat_history` en PostgreSQL y eventos RabbitMQ.
- **Nodos clicables**: Inspección de contratos, microservicios y parámetros de cada etapa.
- **Timeline de herramientas**: Contexto extraído en tiempo real (noticias Google News, pgvector, competencia).
- **Historial de chat durable**: Turnos `user` y `assistant` registrados en PostgreSQL.

### 📄 6. Resultados & Preproducción Audiovisual
- **Ficha técnica**: Guión escena por escena, tabla de especificaciones de cámara (plano, ángulo, movimiento, encuadre), dirección de arte, locación, audio y edición.
- **Mockup social**: Vista previa tipo Instagram/Red Social con contador de caracteres (alerta Twitter/X ≤ 280).
- **Exportación**: Descarga en 1-clic a formato Markdown (`.md`) o JSON (`.json`).

### ⚙️ 7. Historial & Monitor del Sistema
- **Historial Redis**: Registro paginado de tareas con filtros de estado y auditoría inmediata.
- **Monitor de microservicios**: Estado en vivo de los 6 servicios principales (Orquestador, Ideación, Publicación, LLM Gateway, Redis, PostgreSQL).
- **Catálogo Tool Discovery**: Herramientas descubiertas en runtime (`/.well-known/tool-manifest`).

---

## 2. Estructura del Frontend

```
frontend/
├── server.py              # BFF FastAPI: endpoints de integración, SSE y servidor estático
├── requirements.txt       # Dependencias Python
├── package.json           # Dependencias React 19, Lucide Icons, Vite y Tailwind CSS v4
├── vite.config.js         # Configuración Vite: compilación directa a static/ y proxy /api
├── test-backoffice.mjs    # Pruebas automatizadas E2E en navegador Edge headless
├── run.ps1                # Script de inicio rápido en Windows PowerShell
├── run.sh                 # Script de inicio en Linux/macOS
├── src/                   # Código Fuente React (Modern Backoffice)
│   ├── main.jsx           # Entrypoint React
│   ├── App.jsx            # Layout principal del Backoffice
│   ├── index.css          # Estilos Tailwind v4 y variables de diseño
│   ├── api/client.js      # Cliente HTTP REST y SSE
│   ├── context/AppContext.jsx # Estado global y lógica de negocio unificada
│   └── components/
│       ├── layout/        # Sidebar, Header y Toasts
│       ├── dashboard/     # Dashboard General y métricas KPI
│       ├── studio/        # Generador de lotes y plantillas
│       ├── library/       # Explorador Master-Detail de ideas
│       ├── publications/  # Gestión y aprobación de publicaciones
│       ├── traceability/  # Grafo interactivo de 5 etapas y timeline
│       ├── results/       # Dossiers, guiones de cámara y mockup social
│       ├── history/       # Registro de tareas en Redis
│       └── system/        # Monitor de servicios y catálogo Tool Discovery
└── static/                # Bundle compilado de producción servido por FastAPI
    ├── index.html
    └── assets/            # CSS y JS optimizados
```

---

## 3. Cómo Ejecutar

### Opción A: Modo Producción Local (Recomendado)
Desde la raíz del repositorio, ejecuta el BFF FastAPI. El servidor compila y entrega tanto la API como la interfaz web en el puerto 3000:

```powershell
python -m pip install -r frontend\requirements.txt
.\frontend\run.ps1

# Alternativa manual:
python -m uvicorn frontend.server:app --host 0.0.0.0 --port 3000
```

Abre en tu navegador: **`http://localhost:3000`**

### Opción B: Modo Desarrollo Frontend (React + Vite)
Para desarrollar la interfaz con recarga en caliente (Hot Module Replacement) conectada al BFF en puerto 3000:

```bash
cd frontend
npm install
npm run dev
```

Abre en tu navegador: **`http://localhost:5173`** (las llamadas `/api` se redirigen automáticamente a `:3000`).

### Compilar el Frontend:
Para generar un nuevo bundle de producción en `frontend/static/`:

```bash
cd frontend
npm run build
```

### Ejecutar Pruebas Automatizadas E2E:
Para verificar que todas las vistas, navegaciones y llamadas API respondan sin errores en un navegador real:

```bash
node frontend/test-backoffice.mjs
```

---

## 4. Endpoints del Backend BFF (`server.py`)

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Sirve el Backoffice web (`index.html`) |
| `GET` | `/api/health` | Estado de salud de los microservicios aguas abajo |
| `GET` | `/api/overview` | Métricas generales (tareas, memoria RAG, herramientas) |
| `GET` | `/api/clients` | Lista de clientes y perfiles de marca |
| `POST` | `/api/ideas/generate` | Inicia un lote asíncrono de 1–5 ideas |
| `GET` | `/api/idea-batches/{id}?brand_id=` | Consulta progreso y resultados del lote |
| `GET` | `/api/ideas?brand_id=&query=&limit=&offset=` | Consulta y busca en la biblioteca de una marca |
| `GET` | `/api/ideas/{id}?brand_id=` | Abre el dossier persistido completo |
| `GET` | `/api/publications?brand_id=&limit=` | Lista entregas con estado y copies por canal |
| `POST` | `/api/publications/{task_id}/approve` | Guarda copys editados como aprobados pendientes |
| `POST` | `/api/ideas/{id}/publish` | Prepara variantes para revisar sin llamar a Postiz |
| `POST` | `/api/publications/{task_id}/deliver` | Entrega a Postiz los copies revisados y aprobados |
| `POST` | `/api/tasks` | Genera una idea sin publicar (compatibilidad) |
| `POST` | `/api/demo` | Genera una idea demo con EcoBrand (1-clic) |
| `GET` | `/api/tasks` | Historial de tareas almacenadas en Redis TaskStore |
| `GET` | `/api/tasks/{id}` | Datos brutos de una tarea |
| `GET` | `/api/tasks/{id}/trace` | **Trazabilidad completa**: nodos, duraciones, tools, contexto y salidas |
| `GET` | `/api/tasks/{id}/stream`| **Server-Sent Events (SSE)** para streaming en tiempo real |
| `GET` | `/api/tasks/{id}/history` | Historial de chat persistido en PostgreSQL |
| `GET` | `/api/tools` | Catálogo de herramientas descubiertas por Tool Discovery |
| `GET` | `/api/rag/stats` | Estadísticas de la memoria vectorial pgvector |
