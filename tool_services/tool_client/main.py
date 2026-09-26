"""
Tool service ``client`` — perfil de marca del cliente (PostgreSQL).

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

SERVICE = "tool-client"
TOOL = "client"
PORT = int(os.getenv("PORT", "8010"))
AMQP_ENABLED = os.getenv("AMQP_ENABLED", "true").lower() == "true"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(SERVICE)

app = FastAPI(title=SERVICE, version="1.0.0")


# ── Operaciones (lógica compartida REST ⇄ AMQP) ─────────────────
def op_profile(client_id: int) -> dict:
    """Perfil de marca + tono + histórico, con texto listo para prompt."""
    from shared_tools.cliente import format_client_profile, get_client_profile

    profile = get_client_profile(client_id)
    return {
        "client_id": client_id,
        "found": profile is not None,
        "profile": profile,
        "text": format_client_profile(profile),
    }


OPERATIONS: dict = {
    "profile": {
        "id": "profile",
        "method": "GET",
        "path": "/profile",
        "description": (
            "Devuelve el perfil de marca del cliente (tono, restricciones e histórico) "
            "con formato listo para prompt."
        ),
        "params": [
            {
                "name": "client_id",
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "Identificador del cliente",
            }
        ],
        "returns": "objeto {client_id, found, profile, text}",
        "handler": op_profile,
    },
}

MANIFEST = build_manifest(
    name=TOOL,
    service=SERVICE,
    description="Perfil de marca del cliente (tono, restricciones, histórico) desde PostgreSQL.",
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


@app.get("/profile")
def profile(client_id: int = Query(..., description="Identificador del cliente")):
    started = time.perf_counter()
    try:
        data = op_profile(client_id)
        return make_envelope(
            f"{TOOL}.profile", data, (time.perf_counter() - started) * 1000
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("profile falló")
        return JSONResponse(
            status_code=500,
            content=make_envelope(
                f"{TOOL}.profile",
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
