"""
Tool service ``rag`` — memoria RAG (ideas/publicaciones) con pgvector.

Microservicio independiente (Tools-as-a-Service):
- **Dueño** de las tablas ``ideas_generadas`` y ``publicaciones_generadas``
  (lectura semántica + escritura con embedding).
- Expone contrato REST + manifiesto de descubrimiento.
- Atiende invocaciones por eventos AMQP (modo asíncrono / larga duración).
- El consumidor (agente) **no ejecuta código de negocio**: sólo consume HTTP/AMQP.
"""
from __future__ import annotations

import logging
import os
import sys
import time

# Permite ejecutar el servicio desde cualquier cwd (repo root)
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from common.contracts import TOOL_MANIFEST_PATH, build_manifest, make_envelope  # noqa: E402
from common.events import tool_rpc_queue  # noqa: E402
from common.rpc import start_rpc_server  # noqa: E402

SERVICE = "tool-rag"
TOOL = "rag"
PORT = int(os.getenv("PORT", "8013"))
AMQP_ENABLED = os.getenv("AMQP_ENABLED", "true").lower() == "true"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(SERVICE)

app = FastAPI(title=SERVICE, version="1.0.0")


# ── Bodies (REST) ──────────────────────────────────────────────
class SimilarBody(BaseModel):
    brand_id: int
    query: str
    limit: int = 3
    min_similarity: float = 0.3


class IdeaBody(BaseModel):
    brand_id: int
    client_id: int
    content: str


class PublicacionBody(BaseModel):
    brand_id: int
    client_id: int
    content: str
    idea_id: int | None = None


# ── Operaciones (lógica compartida REST ⇄ AMQP) ─────────────────
def op_similar(brand_id: int, query: str, limit: int = 3, min_similarity: float = 0.3) -> dict:
    """Búsqueda semántica de ideas previas con texto listo para prompt."""
    from shared_tools.rag import format_ideas_for_prompt, search_similar_ideas

    ideas = search_similar_ideas(brand_id, query, limit, min_similarity)
    return {
        "brand_id": brand_id,
        "query": query,
        "count": len(ideas),
        "ideas": ideas,
        "text": format_ideas_for_prompt(ideas),
    }


def op_save_idea(brand_id: int, client_id: int, content: str) -> dict:
    """Persiste una idea generada (+ embedding vía LLM Gateway)."""
    from shared_tools.db import execute_db
    from shared_tools.embeddings import embedding_to_vector, generate_embedding

    embedding = generate_embedding(content)
    vec = embedding_to_vector(embedding)
    if vec:
        new_id = execute_db(
            "INSERT INTO ideas_generadas (client_id, brand_id, content, embedding) "
            "VALUES (%s, %s, %s, %s::vector) RETURNING id",
            (client_id, brand_id, content, vec),
        )
    else:
        new_id = execute_db(
            "INSERT INTO ideas_generadas (client_id, brand_id, content) VALUES (%s, %s, %s) RETURNING id",
            (client_id, brand_id, content),
        )
    return {"id": new_id}


def op_save_publicacion(brand_id: int, client_id: int, content: str, idea_id: int | None = None) -> dict:
    """Persiste una publicación generada (+ embedding vía LLM Gateway)."""
    from shared_tools.db import execute_db
    from shared_tools.embeddings import embedding_to_vector, generate_embedding

    embedding = generate_embedding(content)
    vec = embedding_to_vector(embedding)
    if vec:
        new_id = execute_db(
            "INSERT INTO publicaciones_generadas (client_id, brand_id, idea_id, content, embedding) "
            "VALUES (%s, %s, %s, %s, %s::vector) RETURNING id",
            (client_id, brand_id, idea_id, content, vec),
        )
    else:
        new_id = execute_db(
            "INSERT INTO publicaciones_generadas (client_id, brand_id, idea_id, content) "
            "VALUES (%s, %s, %s, %s)",
            (client_id, brand_id, idea_id, content),
        )
    return {"id": new_id}


def op_stats() -> dict:
    """Conteo de ideas y publicaciones persistidas."""
    from shared_tools.db import query_db

    ideas = query_db("SELECT count(*) AS n FROM ideas_generadas")[0]["n"]
    publicaciones = query_db("SELECT count(*) AS n FROM publicaciones_generadas")[0]["n"]
    return {"ideas": int(ideas), "publicaciones": int(publicaciones)}


OPERATIONS: dict = {
    "similar": {
        "id": "similar",
        "method": "POST",
        "path": "/similar",
        "description": (
            "Búsqueda semántica (pgvector) de ideas previas del cliente, con "
            "similitud mínima y texto listo para prompt."
        ),
        "params": [
            {
                "name": "brand_id",
                "in": "body",
                "type": "integer",
                "required": True,
                "description": "Marca cuyo cerebro RAG se puede consultar",
            },
            {
                "name": "query",
                "in": "body",
                "type": "string",
                "required": True,
                "description": "Texto de búsqueda",
            },
            {
                "name": "limit",
                "in": "body",
                "type": "integer",
                "required": False,
                "description": "Máximo de ideas (default 3)",
            },
            {
                "name": "min_similarity",
                "in": "body",
                "type": "number",
                "required": False,
                "description": "Similitud mínima 0..1 (default 0.3)",
            },
        ],
        "returns": "objeto {query, count, ideas, text}",
        "handler": op_similar,
    },
    "save_idea": {
        "id": "save_idea",
        "method": "POST",
        "path": "/ideas",
        "description": "Persiste una idea generada con su embedding (tabla ideas_generadas).",
        "params": [
            {
                "name": "client_id",
                "in": "body",
                "type": "integer",
                "required": True,
                "description": "Identificador del cliente",
            },
            {
                "name": "content",
                "in": "body",
                "type": "string",
                "required": True,
                "description": "Contenido de la idea",
            },
        ],
        "returns": "objeto {id}",
        "handler": op_save_idea,
    },
    "save_publicacion": {
        "id": "save_publicacion",
        "method": "POST",
        "path": "/publicaciones",
        "description": (
            "Persiste una publicación generada con su embedding "
            "(tabla publicaciones_generadas, opcionalmente ligada a la idea)."
        ),
        "params": [
            {
                "name": "client_id",
                "in": "body",
                "type": "integer",
                "required": True,
                "description": "Identificador del cliente",
            },
            {
                "name": "content",
                "in": "body",
                "type": "string",
                "required": True,
                "description": "Contenido de la publicación",
            },
            {
                "name": "idea_id",
                "in": "body",
                "type": "integer",
                "required": False,
                "description": "Id de la idea de la que deriva (opcional)",
            },
        ],
        "returns": "objeto {id}",
        "handler": op_save_publicacion,
    },
    "stats": {
        "id": "stats",
        "method": "GET",
        "path": "/stats",
        "description": "Conteo de ideas y publicaciones persistidas.",
        "params": [],
        "returns": "objeto {ideas, publicaciones}",
        "handler": op_stats,
    },
}

MANIFEST = build_manifest(
    name=TOOL,
    service=SERVICE,
    description=(
        "Memoria RAG: ideas/publicaciones previas (búsqueda semántica) y "
        "persistencia con embedding."
    ),
    amqp_queue=tool_rpc_queue(TOOL),
    operations=[{k: v for k, v in op.items() if k != "handler"} for op in OPERATIONS.values()],
)


# ── REST ────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": SERVICE, "tool": TOOL, "amqp": AMQP_ENABLED}


@app.get(TOOL_MANIFEST_PATH)
def manifest() -> dict:
    return MANIFEST


@app.post("/similar")
def similar(body: SimilarBody):
    started = time.perf_counter()
    try:
        data = op_similar(body.brand_id, body.query, body.limit, body.min_similarity)
        return make_envelope(
            f"{TOOL}.similar", data, (time.perf_counter() - started) * 1000
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("similar falló")
        return JSONResponse(
            status_code=500,
            content=make_envelope(
                f"{TOOL}.similar",
                None,
                (time.perf_counter() - started) * 1000,
                status="error",
                error=str(exc),
            ),
        )


@app.post("/ideas")
def save_idea(body: IdeaBody):
    started = time.perf_counter()
    try:
        data = op_save_idea(body.brand_id, body.client_id, body.content)
        return make_envelope(
            f"{TOOL}.save_idea", data, (time.perf_counter() - started) * 1000
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("save_idea falló")
        return JSONResponse(
            status_code=500,
            content=make_envelope(
                f"{TOOL}.save_idea",
                None,
                (time.perf_counter() - started) * 1000,
                status="error",
                error=str(exc),
            ),
        )


@app.post("/publicaciones")
def save_publicacion(body: PublicacionBody):
    started = time.perf_counter()
    try:
        data = op_save_publicacion(body.brand_id, body.client_id, body.content, body.idea_id)
        return make_envelope(
            f"{TOOL}.save_publicacion", data, (time.perf_counter() - started) * 1000
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("save_publicacion falló")
        return JSONResponse(
            status_code=500,
            content=make_envelope(
                f"{TOOL}.save_publicacion",
                None,
                (time.perf_counter() - started) * 1000,
                status="error",
                error=str(exc),
            ),
        )


@app.get("/stats")
def stats():
    started = time.perf_counter()
    try:
        data = op_stats()
        return make_envelope(
            f"{TOOL}.stats", data, (time.perf_counter() - started) * 1000
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("stats falló")
        return JSONResponse(
            status_code=500,
            content=make_envelope(
                f"{TOOL}.stats",
                None,
                (time.perf_counter() - started) * 1000,
                status="error",
                error=str(exc),
            ),
        )


# ── AMQP RPC (modo asíncrono) ──────────────────────────────────
def _rpc_handler(event) -> dict:
    op_id = event.operation or ""
    if op_id not in OPERATIONS:
        raise ValueError(f"operación desconocida: {op_id}")
    return OPERATIONS[op_id]["handler"](**dict(event.payload or {}))


if AMQP_ENABLED:
    start_rpc_server(tool_rpc_queue(TOOL), _rpc_handler, source=SERVICE)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
