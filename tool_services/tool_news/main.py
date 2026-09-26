"""
Tool service ``news`` — noticias reales de Google News RSS (sin API key).

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

SERVICE = "tool-news"
TOOL = "news"
PORT = int(os.getenv("PORT", "8014"))
AMQP_ENABLED = os.getenv("AMQP_ENABLED", "true").lower() == "true"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(SERVICE)

app = FastAPI(title=SERVICE, version="1.0.0")


# ── Operaciones (lógica compartida REST ⇄ AMQP) ─────────────────
def op_news(query: str, limit: int = 3) -> dict:
    """Noticias de Google News RSS con texto listo para prompt."""
    from shared_tools.fuentes_externas import fetch_google_news, format_news_for_prompt

    news = fetch_google_news(query, limit)
    return {
        "query": query,
        "count": len(news),
        "news": news,
        "text": format_news_for_prompt(news),
    }


OPERATIONS: dict = {
    "news": {
        "id": "news",
        "method": "GET",
        "path": "/news",
        "description": (
            "Noticias reales de Google News RSS para una query, con formato listo "
            "para prompt (sin API key)."
        ),
        "params": [
            {
                "name": "query",
                "in": "query",
                "type": "string",
                "required": True,
                "description": "Tema o texto de búsqueda",
            },
            {
                "name": "limit",
                "in": "query",
                "type": "integer",
                "required": False,
                "description": "Máximo de noticias (default 3)",
            },
        ],
        "returns": "objeto {query, count, news, text}",
        "handler": op_news,
    },
}

MANIFEST = build_manifest(
    name=TOOL,
    service=SERVICE,
    description="Noticias reales de Google News RSS (sin API key).",
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


@app.get("/news")
def news(
    query: str = Query(..., description="Tema o texto de búsqueda"),
    limit: int = Query(3, description="Máximo de noticias"),
):
    started = time.perf_counter()
    try:
        data = op_news(query, limit)
        return make_envelope(
            f"{TOOL}.news", data, (time.perf_counter() - started) * 1000
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("news falló")
        return JSONResponse(
            status_code=500,
            content=make_envelope(
                f"{TOOL}.news",
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
