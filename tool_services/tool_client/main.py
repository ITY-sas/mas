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
from pydantic import BaseModel, Field  # noqa: E402

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


class BrandBody(BaseModel):
    organization_id: int
    name: str
    profile_marca: str = ""
    restricciones_tono: str = ""
    producto_servicio: str = ""
    audiencia_objetivo: str = ""
    objetivo_marketing: str = ""
    propuesta_valor: str = ""
    pilares_contenido: str = ""
    canales_objetivo: str = ""
    pais: str = "Colombia"
    zona_horaria: str = "America/Bogota"
    restricciones_legales: str = ""


def _brand_slug(name: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


@app.on_event("startup")
async def startup_event():
    from shared_tools.cliente import ensure_client_profile_fields

    ensure_client_profile_fields()


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


def op_create_brand(body: BrandBody) -> dict:
    from shared_tools.db import execute_db

    brand_id = execute_db(
        "INSERT INTO brands (organization_id, name, slug, profile_marca, "
        "restricciones_tono, producto_servicio, audiencia_objetivo, "
        "objetivo_marketing, propuesta_valor, pilares_contenido, "
        "canales_objetivo, pais, zona_horaria, restricciones_legales) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "RETURNING id",
        (
            body.organization_id, body.name, _brand_slug(body.name), body.profile_marca,
            body.restricciones_tono, body.producto_servicio, body.audiencia_objetivo,
            body.objetivo_marketing, body.propuesta_valor, body.pilares_contenido,
            body.canales_objetivo, body.pais, body.zona_horaria,
            body.restricciones_legales,
        ),
    )
    return {"brand_id": brand_id, "organization_id": body.organization_id, "name": body.name}


def op_list_brands(organization_id: int) -> list[dict]:
    from shared_tools.db import query_db

    return query_db(
        "SELECT id, organization_id, name, slug, status, pais, zona_horaria "
        "FROM brands WHERE organization_id = %s ORDER BY id",
        (organization_id,),
    )


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
    "create_brand": {
        "id": "create_brand",
        "method": "POST",
        "path": "/brands",
        "description": "Crea una marca y su perfil inicial dentro de una organización.",
        "params": [],
        "returns": "objeto {brand_id, organization_id, name}",
        "handler": op_create_brand,
    },
    "list_brands": {
        "id": "list_brands",
        "method": "GET",
        "path": "/brands",
        "description": "Lista las marcas de una organización.",
        "params": [{"name": "organization_id", "in": "query", "type": "integer", "required": True}],
        "returns": "lista de marcas",
        "handler": op_list_brands,
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


@app.post("/brands")
def create_brand(body: BrandBody):
    started = time.perf_counter()
    try:
        data = op_create_brand(body)
        return make_envelope(f"{TOOL}.create_brand", data, (time.perf_counter() - started) * 1000)
    except Exception as exc:  # noqa: BLE001
        logger.exception("create_brand falló")
        return JSONResponse(status_code=500, content=make_envelope(
            f"{TOOL}.create_brand", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))


@app.get("/brands")
def list_brands(organization_id: int = Query(...)):
    started = time.perf_counter()
    try:
        data = op_list_brands(organization_id)
        return make_envelope(f"{TOOL}.list_brands", data, (time.perf_counter() - started) * 1000)
    except Exception as exc:  # noqa: BLE001
        logger.exception("list_brands falló")
        return JSONResponse(status_code=500, content=make_envelope(
            f"{TOOL}.list_brands", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))
# ── AMQP RPC (modo asíncrono) ──────────────────────────────────
def _rpc_handler(event) -> dict:
    op_id = event.operation or ""
    if op_id not in OPERATIONS:
        raise ValueError(f"operación desconocida: {op_id}")
    if op_id == "create_brand":
        return op_create_brand(BrandBody(**dict(event.payload or {})))
    return OPERATIONS[op_id]["handler"](**dict(event.payload or {}))


if AMQP_ENABLED:
    start_rpc_server(tool_rpc_queue(TOOL), _rpc_handler, source=SERVICE)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
