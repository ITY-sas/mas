# Plan de Pruebas — Sistema Multi-Agente

## 1. Alcance de las pruebas

### 1.1 Niveles de prueba

| Nivel | Carpeta | Objetivo | Herramienta |
|-------|---------|----------|-------------|
| **Unitarias** | `tests/unit/` | Verificar cada función individualmente | pytest |
| **Integración** | `tests/integration/` | Verificar interacción entre componentes | pytest |
| **E2E** | `prueba_e2e.py` | Flujo completo de punta a punta | Script standalone |
| **Rendimiento** | `tests/performance/` | Tiempos de respuesta y throughput | pytest + time |

### 1.2 Cobertura objetivo

```
Módulo                      Unitarias  Integración  Rendimiento
─────────────────────────────────────────────────────────────────
shared_tools/db.py             ✅          ✅            —
shared_tools/embeddings.py     ✅          ✅            ✅
shared_tools/cliente.py        ✅          ✅            —
shared_tools/tendencias.py     ✅          ✅            ✅
shared_tools/competencia.py    ✅          ✅            —
shared_tools/rag.py            ✅          ✅            ✅
shared_tools/enrichment.py     ✅          ✅            ✅
shared_tools/fuentes_externas  ✅          ✅            —
agente_ideacion/main.py        ✅          ✅            ✅
agente_publicacion/main.py     ✅          ✅            ✅
─────────────────────────────────────────────────────────────────
TOTAL                          10 tests    6 tests       4 tests
```

---

## 2. Pruebas Unitarias (`tests/unit/`)

### 2.1 `test_embeddings.py`

| # | Test | Entrada esperada | Criterio de aceptación |
|---|------|-----------------|----------------------|
| U01 | `generate_embedding` devuelve lista de floats | `"texto de prueba"` | `isinstance(result, list)` y `len > 0` |
| U02 | `embedding_to_vector` formatea correctamente | `[0.1, 0.2]` | `"== '[0.1,0.2]'"` |
| U03 | `embedding_to_vector(None)` devuelve None | `None` | `result is None` |
| U04 | URL de Ollama con host `0.0.0.0:11434` | env var `OLLAMA_HOST=0.0.0.0:11434` | URL = `http://127.0.0.1:11434` |
| U05 | URL de Ollama con host normal | env var `OLLAMA_HOST=ollama` | URL = `http://ollama:11434` |

### 2.2 `test_enrichment.py`

| # | Test | Entrada esperada | Criterio de aceptación |
|---|------|-----------------|----------------------|
| U06 | `build_ideacion_prompt` incluye perfil del cliente | context con `client_profile` | `"Client Profile" in prompt` |
| U07 | `build_ideacion_prompt` incluye tendencias | context con `trends` | `"Market Trends" in prompt` |
| U08 | `build_ideacion_prompt` incluye competencia | context con `competitors` | `"Competitor" in prompt` |
| U09 | `build_publicacion_prompt` incluye tono | context con `client_profile` | `"Tone Rules" in prompt` |
| U10 | `enrich_brief_context` devuelve stats | `client_id=1` | `stats` tiene `trends_found` etc. |

### 2.3 `test_tools_cliente.py`

| # | Test | Entrada esperada | Criterio de aceptación |
|---|------|-----------------|----------------------|
| U11 | `get_client_profile` existe en DB | `client_id=1` | Retorna dict con `perfil_marca` |
| U12 | `get_client_profile` con ID inexistente | `client_id=999` | Retorna `None` |
| U13 | `format_client_profile(None)` | `None` | `"No hay información"` |
| U14 | `list_all_clients` retorna ≥1 | — | `len >= 1` |

### 2.4 `test_tools_tendencias.py`

| # | Test | Entrada esperada | Criterio de aceptación |
|---|------|-----------------|----------------------|
| U15 | `get_all_trends` retorna ≥10 | `limit=20` | `len >= 10` |
| U16 | `get_relevant_trends` con embedding | `"moda sostenible"` | Retorna ≥1 con `similarity > 0` |
| U17 | `format_trends` con lista vacía | `[]` | `"No hay tendencias"` |
| U18 | `get_trends_by_categoria` filtra | `"marketing"` | Solo returns de esa categoría |

### 2.5 `test_rag.py`

| # | Test | Entrada esperada | Criterio de aceptación |
|---|------|-----------------|----------------------|
| U19 | `search_similar_ideas` con query relevante | `"campaña ropa sostenible"` | Retorna lista (puede ser vacía) |
| U20 | `search_similar_content` con tabla inválida | `tabla="hack"` | `raises ValueError` |
| U21 | `store_embedding` con tabla válida | `ideas_generadas, id=1` | `True` o `False` sin excepción |

---

## 3. Pruebas de Integración (`tests/integration/`)

### 3.1 `test_rabbitmq.py`

| # | Test | Condición previa | Criterio de aceptación |
|---|------|-----------------|----------------------|
| I01 | Conexión a RabbitMQ | Container corriendo | `connection.is_open == True` |
| I02 | Declarar cola `ideation_queue` | Conexión OK | Cola existe |
| I03 | Publicar y consumir mensaje | Cola existe | Mensaje recibido == enviado |
| I04 | Credenciales correctas | user/password | No lanza `ProbableAuthenticationError` |

### 3.2 `test_postgres.py`

| # | Test | Condición previa | Criterio de aceptación |
|---|------|-----------------|----------------------|
| I05 | Conexión a PostgreSQL | Container corriendo | `conn.status == 2` |
| I06 | Tablas existen | init.sql ejecutado | 5 tablas presentes |
| I07 | Insert + Select de idea | Tablas OK | Roundtrip completo |
| I08 | Búsqueda vectorial pgvector | Datos con embedding | Retorna resultado ordenado por similitud |
| I09 | Seed data ejecutado | — | ≥17 tendencias, ≥13 competidores |

### 3.3 `test_pipeline.py`

| # | Test | Condición previa | Criterio de aceptación |
|---|------|-----------------|----------------------|
| I10 | Agente Ideación `/health` | Container corriendo | `status == healthy` |
| I11 | Agente Publicación `/health` | Container corriendo | `status == healthy` |
| I12 | Endpoint `/tools` lista tools | Container corriendo | `len(tools) >= 6` |
| I13 | `enrich_brief_context` completo | DB con seed | Retorna contexto con stats |
| I14 | Brief completo → idea en DB | Todos los servicios | ≥1 nueva fila en `ideas_generadas` |

---

## 4. Pruebas de Rendimiento (`tests/performance/`)

### 4.1 Métricas a medir

| # | Métrica | Umbral aceptable | Umbral óptimo |
|---|---------|-----------------|--------------|
| P01 | `generate_embedding()` | < 2 seg | < 0.5 seg |
| P02 | `get_relevant_trends()` (RAG) | < 3 seg | < 1 seg |
| P03 | `enrich_brief_context()` completo | < 10 seg | < 5 seg |
| P04 | Generación LLM (gemma3:4b) | < 60 seg | < 30 seg |
| P05 | Pipeline completo (brief → publicación) | < 120 seg | < 60 seg |
| P06 | Health endpoint `/health` | < 500 ms | < 100 ms |
| P07 | Búsqueda vectorial pgvector | < 500 ms | < 100 ms |
| P08 | Conexión a RabbitMQ | < 2 seg | < 500 ms |

### 4.2 Escenarios de carga

| Escenario | Descripción | Métrica clave |
|-----------|-------------|---------------|
| C1 | 5 briefs consecutivos | Tiempo promedio por brief |
| C2 | 10 briefs concurrentes (threads) | Throughput briefs/minuto |
| P09 | Memoria de agentes tras 10 procesos | < 500 MB por agente |

### 4.3 Comando para ejecutar

```bash
# Todas las pruebas de rendimiento
pytest tests/performance/ -v --durations=10

# Con reporte de tiempos
pytest tests/performance/ -v --tb=short --durations=0
```

---

## 5. Ejecución de pruebas

### 5.1 Instalar dependencias de testing

```bash
pip install pytest pytest-asyncio pytest-timeout requests pika psycopg2-binary
```

### 5.2 Ejecutar todos los niveles

```bash
# Solo unitarias (rápidas, sin servicios externos)
pytest tests/unit/ -v

# Integración (requiere Docker corriendo)
pytest tests/integration/ -v

# Rendimiento (requiere Docker + Ollama)
pytest tests/performance/ -v --durations=10

# Todas
pytest tests/ -v --durations=10

# Con cobertura
pip install pytest-cov
pytest tests/unit/ --cov=shared_tools --cov-report=html
```

### 5.3 Prueba E2E (fuera de pytest)

```bash
python prueba_e2e.py
```

---

## 6. Criterios de aceptación globales

| # | Criterio | Verificado por |
|---|---------|---------------|
| G01 | Todos los tests unitarios pasan | `pytest tests/unit/` |
| G02 | Todos los tests de integración pasan | `pytest tests/integration/` |
| G03 | No test de rendimiento excede umbral | `pytest tests/performance/` |
| G04 | E2E completo pasa | `python prueba_e2e.py` |
| G05 | `/health` responde en ambos agentes | `curl localhost:8000/health` |
| G06 | `/tools` lista las tools disponibles | `curl localhost:8000/tools` |
| G07 | Datos seed cargados | ≥17 tendencias, ≥13 competidores |
| G08 | Embeddings generados | 0 registros con `embedding IS NULL` |
| G09 | Documentación actualizada | `docs/` completo |
| G10 | Commits con convención | `git log` con `feat:`, `fix:`, etc. |
