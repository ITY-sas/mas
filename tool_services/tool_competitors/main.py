"""
Tool service ``competitors`` — referencias de competencia (RAG con pgvector).

Microservicio independiente (Tools-as-a-Service):
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

from fastapi import FastAPI, Query  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from common.contracts import TOOL_MANIFEST_PATH, build_manifest, make_envelope  # noqa: E402
from common.events import tool_rpc_queue  # noqa: E402
from common.rpc import start_rpc_server  # noqa: E402

SERVICE = "tool-competitors"
TOOL = "competitors"
PORT = int(os.getenv("PORT", "8012"))
AMQP_ENABLED = os.getenv("AMQP_ENABLED", "true").lower() == "true"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(SERVICE)

app = FastAPI(title=SERVICE, version="1.0.0")


# ── Operaciones (lógica compartida REST ⇄ AMQP) ─────────────────
def op_search(query: str, limit: int = 5) -> dict:
    """Búsqueda de referencias de competencia por similitud de coseno."""
    from shared_tools.competencia import format_competitors, get_relevant_competitors

    refs = get_relevant_competitors(query, limit)
    return {
        "query": query,
        "count": len(refs),
        "trends": refs,
        "text": format_competitors(refs),
    }


def op_all(limit: int = 20) -> dict:
    """Referencias de competencia más recientes con texto para prompt."""
    from shared_tools.competencia import format_competitors, get_all_competitors

    refs = get_all_competitors(limit)
    return {
        "count": len(refs),
        "trends": refs,
        "text": format_competitors(refs),
    }


OPERATIONS: dict = {
    "search": {
        "id": "search",
        "method": "GET",
        "path": "/search",
        "description": (
            "Busca referencias de competencia relevantes al texto por similitud de "
            "coseno (pgvector) con formato listo para prompt."
        ),
        "params": [
            {
                "name": "query",
                "in": "query",
                "type": "string",
                "required": True,
                "description": "Texto de búsqueda",
            },
            {
                "name": "limit",
                "in": "query",
                "type": "integer",
                "required": False,
                "description": "Máximo de referencias (default 5)",
            },
        ],
        "returns": "objeto {query, count, trends, text}",
        "handler": op_search,
    },
    "all": {
        "id": "all",
        "method": "GET",
        "path": "/all",
        "description": "Devuelve las referencias de competencia más recientes con formato para prompt.",
        "params": [
            {
                "name": "limit",
                "in": "query",
                "type": "integer",
                "required": False,
                "description": "Máximo de referencias (default 20)",
            }
        ],
        "returns": "objeto {count, trends, text}",
        "handler": op_all,
    },
}

MANIFEST = build_manifest(
    name=TOOL,
    service=SERVICE,
    description="Referencias de competencia por similitud de coseno (pgvector).",
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


@app.get("/search")
def search(
    query: str = Query(..., description="Texto de búsqueda"),
    limit: int = Query(5, description="Máximo de referencias"),
):
    started = time.perf_counter()
    try:
        data = op_search(query, limit)
        return make_envelope(
            f"{TOOL}.search", data, (time.perf_counter() - started) * 1000
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("search falló")
        return JSONResponse(
            status_code=500,
            content=make_envelope(
                f"{TOOL}.search",
                None,
                (time.perf_counter() - started) * 1000,
                status="error",
                error=str(exc),
            ),
        )


@app.get("/all")
def all_competitors(limit: int = Query(20, description="Máximo de referencias")):
    started = time.perf_counter()
    try:
        data = op_all(limit)
        return make_envelope(
            f"{TOOL}.all", data, (time.perf_counter() - started) * 1000
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("all falló")
        return JSONResponse(
            status_code=500,
            content=make_envelope(
                f"{TOOL}.all",
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
