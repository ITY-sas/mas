"""
Tool service ``trending`` — topics en tendencia de Google News (sin API key).

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

SERVICE = "tool-trending"
TOOL = "trending"
PORT = int(os.getenv("PORT", "8015"))
AMQP_ENABLED = os.getenv("AMQP_ENABLED", "true").lower() == "true"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(SERVICE)

app = FastAPI(title=SERVICE, version="1.0.0")


# ── Operaciones (lógica compartida REST ⇄ AMQP) ─────────────────
def op_trending(query: str = "marketing") -> dict:
    """Topics en tendencia (Google News RSS con fallback a mock)."""
    from shared_tools.fuentes_externas import fetch_trending_topics, format_news_for_prompt

    trending = fetch_trending_topics(query)
    return {
        "query": query,
        "count": len(trending),
        "trending": trending,
        "text": format_news_for_prompt(trending),
    }


OPERATIONS: dict = {
    "trending": {
        "id": "trending",
        "method": "GET",
        "path": "/trending",
        "description": (
            "Topics en tendencia de Google News para un hashtag/categoría, con "
            "formato listo para prompt (sin API key)."
        ),
        "params": [
            {
                "name": "query",
                "in": "query",
                "type": "string",
                "required": False,
                "description": "Hashtag o categoría (default 'marketing')",
            }
        ],
        "returns": "objeto {query, count, trending, text}",
        "handler": op_trending,
    },
}

MANIFEST = build_manifest(
    name=TOOL,
    service=SERVICE,
    description="Topics en tendencia de Google News para hashtags.",
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


@app.get("/trending")
def trending(query: str = Query("marketing", description="Hashtag o categoría")):
    started = time.perf_counter()
    try:
        data = op_trending(query)
        return make_envelope(
            f"{TOOL}.trending", data, (time.perf_counter() - started) * 1000
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("trending falló")
        return JSONResponse(
            status_code=500,
            content=make_envelope(
                f"{TOOL}.trending",
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
