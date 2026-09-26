# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).
Convención de commits: [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/).

## [1.2.0] — 2026-09-26

### Added
- **feat**: Paquete `shared_tools/` con tools compartidas para ambos agentes
  - `cliente.py` — Perfiles de cliente desde PostgreSQL
  - `tendencias.py` — Tendencias + búsqueda RAG con pgvector
  - `competencia.py` — Referencias de competencia + RAG
  - `rag.py` — Búsqueda semántica con pgvector (cosine similarity)
  - `enrichment.py` — Construcción de prompts enriquecidos
  - `fuentes_externas.py` — Google News RSS (sin API key)
  - `embeddings.py` — Generación de embeddings con nomic-embed-text
  - `db.py` — Utilidades de conexión PostgreSQL
- **feat**: Endpoint `GET /tools` en ambos agentes (lista tools disponibles)
- **feat**: Pipeline de enriquecimiento de contexto en ambos agentes
- **feat**: Seed data con 3 clientes, 17 tendencias, 13 competidores
- **feat**: Script `seed_data.py` para poblar datos de ejemplo
- **feat**: Script `backfill_embeddings.py` para generar embeddings faltantes
- **feat**: Script `enviar_brief.py` para enviar briefs personalizados
- **test**: Arquitectura de pruebas en `tests/`
  - `tests/unit/` — 54 tests unitarios (embeddings, enrichment, tools, RAG)
  - `tests/integration/` — 17 tests de integración (RabbitMQ, PostgreSQL, pipeline)
  - `tests/performance/` — 9 tests de rendimiento con umbrales
- **docs**: `docs/TECNOLOGIAS.md` — Stack tecnológico documentado
- **docs**: `docs/PLAN_DE_PRUEBAS.md` — Plan de pruebas completo
- **docs**: `docs/ARQUITECTURA.md` — Documentación de arquitectura
- **docs**: `docs/CHANGELOG.md` — Este archivo
- **chore**: `pytest.ini` con markers (unit, integration, performance, slow)
- **chore**: `.gitignore` actualizado

### Changed
- **fix**: URL de Ollama maneja host `0.0.0.0:11434` → `127.0.0.1:11434`
- **fix**: Credenciales RabbitMQ en agentes (`user`/`password`)
- **fix**: Dockerfile usa Python 3.11 (soporta `int | None` syntax)
- **fix**: `docker-compose.yml` build context en raíz del proyecto (para shared_tools)
- **fix**: `init.sql` — Eliminadas columnas duplicadas y comas trailing
- **refactor**: Ambos agentes usan pipeline de 5 pasos/4 pasos con tools
- **refactor**: `prueba_e2e.py` con JSON válido, credenciales y UTF-8

### Removed
- **chore**: Contenedor Ollama de docker-compose (usa instancia local)

## [1.1.0] — 2026-09-25

### Added
- **feat**: Pipeline E2E funcional (brief → idea → publicación → DB)
- **feat**: Integración con Ollama (gemma3:4b) para generación de texto
- **feat**: Integración con PostgreSQL para persistencia
- **feat**: Comunicación RabbitMQ entre agentes
- **feat**: Scripts de setup (`setup.ps1`, `setup.sh`)
- **feat**: Healthchecks en docker-compose
- **test**: `prueba_e2e.py` con verificación en base de datos

### Fixed
- **fix**: Autenticación RabbitMQ (credenciales user/password)
- **fix**: Encoding UTF-8 en Windows (emojis, tildes)
- **fix**: Puerto 11434 en conflicto (Ollama local vs contenedor)

## [1.0.0] — 2026-09-25

### Added
- **feat**: Estructura inicial del proyecto
- **feat**: Docker Compose con RabbitMQ, PostgreSQL, Ollama, 2 agentes
- **feat**: Esqueleto de agentes (FastAPI + RabbitMQ consumer)
- **feat**: Esquema de base de datos con pgvector
