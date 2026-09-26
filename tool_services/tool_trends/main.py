"""
Tool service ``trends`` — tendencias de mercado (RAG con pgvector).

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

SERVICE = "tool-trends"
TOOL = "trends"
PORT = int(os.getenv("PORT", "8011"))
AMQP_ENABLED = os.getenv("AMQP_ENABLED", "true").lower() == "true"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(SERVICE)

app = FastAPI(title=SERVICE, version="1.0.0")


# ── Operaciones (lógica compartida REST ⇄ AMQP) ─────────────────
def _jsonable(rows: list[dict]) -> list[dict]:
    """Normaliza ``date``/``datetime``/``Decimal`` a tipos JSON-safe.

    Necesario para que el mismo ``data`` sirva REST (FastAPI serializa solo)
    y AMQP (``Event.to_json`` usa ``json.dumps`` estricto).
    """
    import datetime as _dt
    from decimal import Decimal

    out = []
    for row in rows:
        item = {}
        for key, value in row.items():
            if isinstance(value, (_dt.date, _dt.datetime)):
                item[key] = value.isoformat()
            elif isinstance(value, Decimal):
                item[key] = float(value)
            else:
                item[key] = value
        out.append(item)
    return out


def op_search(query: str, limit: int = 5) -> dict:
    """Búsqueda de tendencias por similitud de coseno con texto para prompt."""
    from shared_tools.tendencias import format_trends, get_relevant_trends

    trends = _jsonable(get_relevant_trends(query, limit))
    return {
        "query": query,
        "count": len(trends),
        "trends": trends,
        "text": format_trends(trends),
    }


def op_all(limit: int = 20) -> dict:
    """Tendencias más recientes con texto para prompt."""
    from shared_tools.tendencias import format_trends, get_all_trends

    trends = _jsonable(get_all_trends(limit))
    return {
        "count": len(trends),
        "trends": trends,
        "text": format_trends(trends),
    }


OPERATIONS: dict = {
    "search": {
        "id": "search",
        "method": "GET",
        "path": "/search",
        "description": (
            "Busca tendencias relevantes al texto por similitud de coseno (pgvector) "
            "con formato listo para prompt."
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
                "description": "Máximo de tendencias (default 5)",
            },
        ],
        "returns": "objeto {query, count, trends, text}",
        "handler": op_search,
    },
    "all": {
        "id": "all",
        "method": "GET",
        "path": "/all",
        "description": "Devuelve las tendencias más recientes con formato listo para prompt.",
        "params": [
            {
                "name": "limit",
                "in": "query",
                "type": "integer",
                "required": False,
                "description": "Máximo de tendencias (default 20)",
            }
        ],
        "returns": "objeto {count, trends, text}",
        "handler": op_all,
    },
}

MANIFEST = build_manifest(
    name=TOOL,
    service=SERVICE,
    description="Búsqueda RAG de tendencias de mercado por similitud de coseno (pgvector).",
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
    limit: int = Query(5, description="Máximo de tendencias"),
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
def all_trends(limit: int = Query(20, description="Máximo de tendencias")):
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
