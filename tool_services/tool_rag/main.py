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
import hashlib
import json

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
    generation_batch_id: str | None = None
    generation_index: int | None = None


class PublicacionBody(BaseModel):
    brand_id: int
    client_id: int
    content: str
    idea_id: int | None = None
    platform: str | None = None


class DocumentBody(BaseModel):
    title: str
    content: str
    scope: str = "brand"
    organization_id: int | None = None
    brand_id: int | None = None
    source_type: str = "manual"
    source_url: str | None = None
    metadata: dict = {}


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


def op_save_idea(
    brand_id: int,
    client_id: int,
    content: str,
    generation_batch_id: str | None = None,
    generation_index: int | None = None,
) -> dict:
    """Persiste una idea generada (+ embedding vía LLM Gateway)."""
    from shared_tools.db import execute_db
    from shared_tools.embeddings import embedding_to_vector, generate_embedding

    if (generation_batch_id is None) != (generation_index is None):
        raise ValueError("generation_batch_id y generation_index deben enviarse juntos")
    embedding = generate_embedding(content)
    vec = embedding_to_vector(embedding)
    if generation_batch_id is not None:
        columns = "client_id, brand_id, generation_batch_id, generation_index, content"
        values = "%s, %s, %s, %s, %s"
        params = (client_id, brand_id, generation_batch_id, generation_index, content)
        if vec:
            columns += ", embedding"
            values += ", %s::vector"
            params += (vec,)
        new_id = execute_db(
            f"INSERT INTO ideas_generadas ({columns}) VALUES ({values}) "
            "ON CONFLICT (brand_id, generation_batch_id, generation_index) "
            "WHERE generation_batch_id IS NOT NULL DO UPDATE SET "
            "content = EXCLUDED.content, embedding = EXCLUDED.embedding "
            "RETURNING id",
            params,
        )
        return {"id": new_id}

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


def _serialize_idea(row: dict) -> dict:
    raw_content = row.get("content") or ""
    try:
        dossier = json.loads(raw_content)
    except (TypeError, ValueError):
        dossier = {}
    if not isinstance(dossier, dict):
        dossier = {}
    return {
        "id": row.get("id"),
        "brand_id": row.get("brand_id"),
        "client_id": row.get("client_id"),
        "generation_batch_id": row.get("generation_batch_id"),
        "generation_index": row.get("generation_index"),
        "title": dossier.get("title") or raw_content[:120],
        "content": raw_content,
        "dossier": dossier,
        "created_at": row.get("created_at"),
    }


def op_list_ideas(
    brand_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
    query: str | None = None,
    generation_batch_id: str | None = None,
) -> dict:
    """List persisted ideas for one brand, optionally scoped to a batch/search."""
    from shared_tools.db import query_db

    conditions = ["brand_id = %s"]
    params: list = [brand_id]
    if generation_batch_id:
        conditions.append("generation_batch_id = %s")
        params.append(generation_batch_id)
    if query and query.strip():
        conditions.append("content ILIKE %s")
        params.append(f"%{query.strip()}%")
    where = " AND ".join(conditions)
    rows = query_db(
        "SELECT id, brand_id, client_id, generation_batch_id, generation_index, content, created_at "
        f"FROM ideas_generadas WHERE {where} "
        "ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s",
        tuple([*params, limit, offset]),
    )
    count_rows = query_db(
        f"SELECT count(*) AS total FROM ideas_generadas WHERE {where}",
        tuple(params),
    )
    return {
        "brand_id": brand_id,
        "items": [_serialize_idea(row) for row in rows],
        "total": int(count_rows[0]["total"]) if count_rows else 0,
        "limit": limit,
        "offset": offset,
    }


def op_ideas_batch_status(brand_id: int, batch_id: str) -> dict:
    """Return persisted idea rows and counts for one generation batch."""
    from shared_tools.db import query_db

    rows = query_db(
        "SELECT id, brand_id, client_id, generation_batch_id, generation_index, content, created_at "
        "FROM ideas_generadas WHERE brand_id = %s AND generation_batch_id = %s "
        "ORDER BY generation_index, id",
        (brand_id, batch_id),
    )
    return {
        "brand_id": brand_id,
        "generation_batch_id": batch_id,
        "ideas": [_serialize_idea(row) for row in rows],
    }


def op_get_idea(brand_id: int, idea_id: int) -> dict | None:
    """Fetch one idea while enforcing the brand boundary in the SQL query."""
    from shared_tools.db import query_db

    rows = query_db(
        "SELECT id, brand_id, client_id, generation_batch_id, generation_index, content, created_at "
        "FROM ideas_generadas WHERE brand_id = %s AND id = %s LIMIT 1",
        (brand_id, idea_id),
    )
    return _serialize_idea(rows[0]) if rows else None


def op_save_publicacion(
    brand_id: int,
    client_id: int,
    content: str,
    idea_id: int | None = None,
    platform: str | None = None,
) -> dict:
    """Persiste una publicación generada (+ embedding vía LLM Gateway)."""
    from shared_tools.db import execute_db
    from shared_tools.embeddings import embedding_to_vector, generate_embedding

    embedding = generate_embedding(content)
    vec = embedding_to_vector(embedding)
    if vec:
        new_id = execute_db(
            "INSERT INTO publicaciones_generadas (client_id, brand_id, idea_id, platform, content, embedding) "
            "VALUES (%s, %s, %s, %s, %s, %s::vector) RETURNING id",
            (client_id, brand_id, idea_id, platform, content, vec),
        )
    else:
        new_id = execute_db(
            "INSERT INTO publicaciones_generadas (client_id, brand_id, idea_id, platform, content) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (client_id, brand_id, idea_id, platform, content),
        )
    return {"id": new_id}


def op_stats() -> dict:
    """Conteo de ideas y publicaciones persistidas."""
    from shared_tools.db import query_db

    ideas = query_db("SELECT count(*) AS n FROM ideas_generadas")[0]["n"]
    publicaciones = query_db("SELECT count(*) AS n FROM publicaciones_generadas")[0]["n"]
    return {"ideas": int(ideas), "publicaciones": int(publicaciones)}


def op_ingest_document(body: DocumentBody) -> dict:
    """Ingesta texto autorizado con chunks, embeddings y procedencia."""
    from shared_tools.db import execute_db
    from shared_tools.embeddings import embedding_to_vector, generate_embeddings_batch

    if body.scope not in {"global", "organization", "brand"}:
        raise ValueError("scope debe ser global, organization o brand")
    if body.scope == "brand" and body.brand_id is None:
        raise ValueError("brand_id es obligatorio para scope=brand")
    if body.scope == "organization" and body.organization_id is None:
        raise ValueError("organization_id es obligatorio para scope=organization")
    if body.scope == "global" and (body.organization_id is not None or body.brand_id is not None):
        raise ValueError("scope=global no admite organization_id ni brand_id")
    if not body.content.strip():
        raise ValueError("content no puede estar vacío")

    content_hash = hashlib.sha256(body.content.encode("utf-8")).hexdigest()
    source_id = execute_db(
        "INSERT INTO brand_sources (organization_id, brand_id, scope, source_type, title, url, content_hash, metadata, fetched_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, now()) RETURNING id",
        (body.organization_id, body.brand_id, body.scope, body.source_type, body.title,
         body.source_url, content_hash, json.dumps(body.metadata)),
    )
    document_id = execute_db(
        "INSERT INTO brand_documents (source_id, organization_id, brand_id, scope, title, content, content_hash, metadata) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb) RETURNING id",
        (source_id, body.organization_id, body.brand_id, body.scope, body.title,
         body.content, content_hash, json.dumps(body.metadata)),
    )
    chunk_size = 1200
    chunks = [body.content[index:index + chunk_size] for index in range(0, len(body.content), chunk_size)]
    embeddings = generate_embeddings_batch(chunks)
    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        vector = embedding_to_vector(embedding) if embedding else None
        if vector:
            execute_db(
                "INSERT INTO brand_chunks (document_id, organization_id, brand_id, scope, chunk_index, content, embedding) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s::vector)",
                (document_id, body.organization_id, body.brand_id, body.scope, index, chunk, vector),
            )
        else:
            execute_db(
                "INSERT INTO brand_chunks (document_id, organization_id, brand_id, scope, chunk_index, content) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (document_id, body.organization_id, body.brand_id, body.scope, index, chunk),
            )
    return {"source_id": source_id, "document_id": document_id, "chunks": len(chunks), "content_hash": content_hash}


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
            {
                "name": "generation_batch_id",
                "in": "body",
                "type": "string",
                "required": False,
                "description": "UUID del lote para deduplicar reentregas",
            },
            {
                "name": "generation_index",
                "in": "body",
                "type": "integer",
                "required": False,
                "description": "Posición de la idea dentro del lote",
            },
        ],
        "returns": "objeto {id}",
        "handler": op_save_idea,
    },
    "list_ideas": {
        "id": "list_ideas",
        "method": "GET",
        "path": "/ideas",
        "description": "Lista ideas persistidas de una marca, con filtro de texto/lote y paginación.",
        "params": [
            {"name": "brand_id", "in": "query", "type": "integer", "required": True},
            {"name": "limit", "in": "query", "type": "integer", "required": False},
            {"name": "offset", "in": "query", "type": "integer", "required": False},
            {"name": "query", "in": "query", "type": "string", "required": False},
            {"name": "generation_batch_id", "in": "query", "type": "string", "required": False},
        ],
        "returns": "objeto {brand_id, items, total, limit, offset}",
        "handler": op_list_ideas,
    },
    "get_idea": {
        "id": "get_idea",
        "method": "GET",
        "path": "/ideas/detail",
        "description": "Obtiene el dossier de una idea dentro de la marca solicitada.",
        "params": [
            {"name": "brand_id", "in": "query", "type": "integer", "required": True},
            {"name": "idea_id", "in": "query", "type": "integer", "required": True},
        ],
        "returns": "objeto dossier; 404 si idea no pertenece a brand_id",
        "handler": op_get_idea,
    },
    "batch_status": {
        "id": "batch_status",
        "method": "GET",
        "path": "/ideas/batch-status",
        "description": "Lista las ideas persistidas para un lote de generación.",
        "params": [
            {"name": "brand_id", "in": "query", "type": "integer", "required": True},
            {"name": "generation_batch_id", "in": "query", "type": "string", "required": True},
        ],
        "returns": "objeto {brand_id, generation_batch_id, ideas}",
        "handler": op_ideas_batch_status,
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
            {
                "name": "platform",
                "in": "body",
                "type": "string",
                "required": False,
                "description": "Plataforma destino de la variante (instagram, linkedin, x, etc.)",
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
    "ingest_document": {
        "id": "ingest_document",
        "method": "POST",
        "path": "/documents",
        "description": "Ingesta un documento autorizado con chunks, embeddings y procedencia.",
        "params": [],
        "returns": "objeto {source_id, document_id, chunks, content_hash}",
        "handler": op_ingest_document,
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
        data = op_save_idea(
            body.brand_id,
            body.client_id,
            body.content,
            body.generation_batch_id,
            body.generation_index,
        )
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


@app.get("/ideas")
def list_ideas(
    brand_id: int,
    limit: int = 50,
    offset: int = 0,
    query: str | None = None,
    generation_batch_id: str | None = None,
):
    started = time.perf_counter()
    if not 1 <= limit <= 100 or offset < 0:
        return JSONResponse(status_code=422, content=make_envelope(
            "rag.list_ideas", None, (time.perf_counter() - started) * 1000,
            status="error", error="limit debe estar entre 1 y 100 y offset no puede ser negativo"))
    try:
        data = op_list_ideas(
            brand_id, limit=limit, offset=offset, query=query,
            generation_batch_id=generation_batch_id,
        )
        return make_envelope("rag.list_ideas", data, (time.perf_counter() - started) * 1000)
    except Exception as exc:  # noqa: BLE001
        logger.exception("list_ideas falló")
        return JSONResponse(status_code=500, content=make_envelope(
            "rag.list_ideas", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))


@app.get("/ideas/batch-status")
def ideas_batch_status(brand_id: int, generation_batch_id: str):
    started = time.perf_counter()
    try:
        data = op_ideas_batch_status(brand_id, generation_batch_id)
        return make_envelope("rag.batch_status", data, (time.perf_counter() - started) * 1000)
    except Exception as exc:  # noqa: BLE001
        logger.exception("batch_status falló")
        return JSONResponse(status_code=500, content=make_envelope(
            "rag.batch_status", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))


@app.get("/ideas/detail")
def get_idea_detail(idea_id: int, brand_id: int):
    started = time.perf_counter()
    try:
        data = op_get_idea(brand_id, idea_id)
        if data is None:
            return JSONResponse(status_code=404, content=make_envelope(
                "rag.get_idea", None, (time.perf_counter() - started) * 1000,
                status="error", error="idea no encontrada para la marca solicitada"))
        return make_envelope("rag.get_idea", data, (time.perf_counter() - started) * 1000)
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_idea falló")
        return JSONResponse(status_code=500, content=make_envelope(
            "rag.get_idea", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))


@app.get("/ideas/{idea_id}")
def get_idea(idea_id: int, brand_id: int):
    return get_idea_detail(idea_id, brand_id)


@app.post("/publicaciones")
def save_publicacion(body: PublicacionBody):
    started = time.perf_counter()
    try:
        data = op_save_publicacion(
            body.brand_id, body.client_id, body.content, body.idea_id, body.platform
        )
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


@app.post("/documents")
def ingest_document(body: DocumentBody):
    started = time.perf_counter()
    try:
        data = op_ingest_document(body)
        return make_envelope(TOOL + ".ingest_document", data, (time.perf_counter() - started) * 1000)
    except Exception as exc:  # noqa: BLE001
        logger.exception("ingest_document falló")
        return JSONResponse(status_code=500, content=make_envelope(
            TOOL + ".ingest_document", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))
# ── AMQP RPC (modo asíncrono) ──────────────────────────────────
def _rpc_handler(event) -> dict:
    op_id = event.operation or ""
    if op_id not in OPERATIONS:
        raise ValueError(f"operación desconocida: {op_id}")
    if op_id == "ingest_document":
        return op_ingest_document(DocumentBody(**dict(event.payload or {})))
    return OPERATIONS[op_id]["handler"](**dict(event.payload or {}))


if AMQP_ENABLED:
    start_rpc_server(tool_rpc_queue(TOOL), _rpc_handler, source=SERVICE)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
