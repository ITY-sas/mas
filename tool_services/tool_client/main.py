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


class BrandUpdateBody(BaseModel):
    name: str | None = None
    profile_marca: str | None = None
    restricciones_tono: str | None = None
    producto_servicio: str | None = None
    audiencia_objetivo: str | None = None
    objetivo_marketing: str | None = None
    propuesta_valor: str | None = None
    pilares_contenido: str | None = None
    canales_objetivo: str | None = None
    pais: str | None = None
    zona_horaria: str | None = None
    restricciones_legales: str | None = None
    rag_config: dict | None = None
    status: str | None = None


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


def op_get_brand(brand_id: int) -> dict | None:
    from shared_tools.db import query_db

    rows = query_db(
        "SELECT id, organization_id, name, slug, status, profile_marca, "
        "restricciones_tono, producto_servicio, audiencia_objetivo, "
        "objetivo_marketing, propuesta_valor, pilares_contenido, "
        "canales_objetivo, pais, zona_horaria, restricciones_legales, rag_config "
        "FROM brands WHERE id = %s LIMIT 1",
        (brand_id,),
    )
    return rows[0] if rows else None


def op_update_brand(brand_id: int, body: BrandUpdateBody) -> dict:
    import json
    from shared_tools.db import execute_db, query_db

    existing = query_db("SELECT id FROM brands WHERE id = %s", (brand_id,))
    if not existing:
        raise ValueError(f"Marca {brand_id} no encontrada")

    fields = []
    params = []
    if body.name is not None:
        fields.append("name = %s")
        params.append(body.name)
        fields.append("slug = %s")
        params.append(_brand_slug(body.name))
    if body.profile_marca is not None:
        fields.append("profile_marca = %s")
        params.append(body.profile_marca)
    if body.restricciones_tono is not None:
        fields.append("restricciones_tono = %s")
        params.append(body.restricciones_tono)
    if body.producto_servicio is not None:
        fields.append("producto_servicio = %s")
        params.append(body.producto_servicio)
    if body.audiencia_objetivo is not None:
        fields.append("audiencia_objetivo = %s")
        params.append(body.audiencia_objetivo)
    if body.objetivo_marketing is not None:
        fields.append("objetivo_marketing = %s")
        params.append(body.objetivo_marketing)
    if body.propuesta_valor is not None:
        fields.append("propuesta_valor = %s")
        params.append(body.propuesta_valor)
    if body.pilares_contenido is not None:
        fields.append("pilares_contenido = %s")
        params.append(body.pilares_contenido)
    if body.canales_objetivo is not None:
        fields.append("canales_objetivo = %s")
        params.append(body.canales_objetivo)
    if body.pais is not None:
        fields.append("pais = %s")
        params.append(body.pais)
    if body.zona_horaria is not None:
        fields.append("zona_horaria = %s")
        params.append(body.zona_horaria)
    if body.restricciones_legales is not None:
        fields.append("restricciones_legales = %s")
        params.append(body.restricciones_legales)
    if body.rag_config is not None:
        fields.append("rag_config = %s::jsonb")
        params.append(json.dumps(body.rag_config))
    if body.status is not None:
        fields.append("status = %s")
        params.append(body.status)

    if fields:
        params.append(brand_id)
        execute_db(f"UPDATE brands SET {', '.join(fields)} WHERE id = %s", tuple(params))

        c_fields = []
        c_params = []
        if body.name is not None:
            c_fields.append("nombre = %s")
            c_params.append(body.name)
        if body.profile_marca is not None:
            c_fields.append("perfil_marca = %s")
            c_params.append(body.profile_marca)
        if body.restricciones_tono is not None:
            c_fields.append("restricciones_tono = %s")
            c_params.append(body.restricciones_tono)
        if body.producto_servicio is not None:
            c_fields.append("producto_servicio = %s")
            c_params.append(body.producto_servicio)
        if body.audiencia_objetivo is not None:
            c_fields.append("audiencia_objetivo = %s")
            c_params.append(body.audiencia_objetivo)
        if body.objetivo_marketing is not None:
            c_fields.append("objetivo_marketing = %s")
            c_params.append(body.objetivo_marketing)
        if body.propuesta_valor is not None:
            c_fields.append("propuesta_valor = %s")
            c_params.append(body.propuesta_valor)
        if body.pilares_contenido is not None:
            c_fields.append("pilares_contenido = %s")
            c_params.append(body.pilares_contenido)
        if body.canales_objetivo is not None:
            c_fields.append("canales_objetivo = %s")
            c_params.append(body.canales_objetivo)
        if body.pais is not None:
            c_fields.append("pais = %s")
            c_params.append(body.pais)
        if body.zona_horaria is not None:
            c_fields.append("zona_horaria = %s")
            c_params.append(body.zona_horaria)
        if body.restricciones_legales is not None:
            c_fields.append("restricciones_legales = %s")
            c_params.append(body.restricciones_legales)
        if c_fields:
            c_params.append(brand_id)
            execute_db(f"UPDATE clientes SET {', '.join(c_fields)} WHERE id = %s", tuple(c_params))

    return op_get_brand(brand_id) or {"id": brand_id}


def op_delete_brand(brand_id: int) -> dict:
    from shared_tools.db import execute_db, query_db

    existing = query_db("SELECT id FROM brands WHERE id = %s", (brand_id,))
    if not existing:
        raise ValueError(f"Marca {brand_id} no encontrada")

    execute_db("UPDATE brands SET status = 'archived' WHERE id = %s", (brand_id,))
    return {"id": brand_id, "status": "archived"}


def op_list_brands(organization_id: int) -> list[dict]:
    from shared_tools.db import query_db

    return query_db(
        "SELECT id, organization_id, name, slug, status, pais, zona_horaria "
        "FROM brands WHERE organization_id = %s AND status != 'archived' ORDER BY id",
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
    "get_brand": {
        "id": "get_brand",
        "method": "GET",
        "path": "/brands/{brand_id}",
        "description": "Obtiene la información y perfil de una marca.",
        "params": [],
        "returns": "objeto de marca",
        "handler": op_get_brand,
    },
    "update_brand": {
        "id": "update_brand",
        "method": "PUT",
        "path": "/brands/{brand_id}",
        "description": "Actualiza los datos, tono o configuración RAG de una marca.",
        "params": [],
        "returns": "objeto de marca actualizado",
        "handler": op_update_brand,
    },
    "delete_brand": {
        "id": "delete_brand",
        "method": "DELETE",
        "path": "/brands/{brand_id}",
        "description": "Archiva una marca (soft delete).",
        "params": [],
        "returns": "objeto {id, status}",
        "handler": op_delete_brand,
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
@app.get("/brands/{brand_id}")
def get_brand(brand_id: int):
    started = time.perf_counter()
    try:
        data = op_get_brand(brand_id)
        if data is None:
            return JSONResponse(status_code=404, content=make_envelope(
                f"{TOOL}.get_brand", None, (time.perf_counter() - started) * 1000,
                status="error", error="marca no encontrada"))
        return make_envelope(f"{TOOL}.get_brand", data, (time.perf_counter() - started) * 1000)
    except Exception as exc:  # noqa: BLE001
        logger.exception("get_brand falló")
        return JSONResponse(status_code=500, content=make_envelope(
            f"{TOOL}.get_brand", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))


@app.put("/brands/{brand_id}")
def update_brand(brand_id: int, body: BrandUpdateBody):
    started = time.perf_counter()
    try:
        data = op_update_brand(brand_id, body)
        return make_envelope(f"{TOOL}.update_brand", data, (time.perf_counter() - started) * 1000)
    except ValueError as exc:
        return JSONResponse(status_code=404, content=make_envelope(
            f"{TOOL}.update_brand", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))
    except Exception as exc:  # noqa: BLE001
        logger.exception("update_brand falló")
        return JSONResponse(status_code=500, content=make_envelope(
            f"{TOOL}.update_brand", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))


@app.delete("/brands/{brand_id}")
def delete_brand(brand_id: int):
    started = time.perf_counter()
    try:
        data = op_delete_brand(brand_id)
        return make_envelope(f"{TOOL}.delete_brand", data, (time.perf_counter() - started) * 1000)
    except ValueError as exc:
        return JSONResponse(status_code=404, content=make_envelope(
            f"{TOOL}.delete_brand", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))
    except Exception as exc:  # noqa: BLE001
        logger.exception("delete_brand falló")
        return JSONResponse(status_code=500, content=make_envelope(
            f"{TOOL}.delete_brand", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))


# ── AMQP RPC (modo asíncrono) ──────────────────────────────────
def _rpc_handler(event) -> dict:
    op_id = event.operation or ""
    if op_id not in OPERATIONS:
        raise ValueError(f"operación desconocida: {op_id}")
    if op_id == "create_brand":
        return op_create_brand(BrandBody(**dict(event.payload or {})))
    if op_id == "update_brand":
        payload = dict(event.payload or {})
        b_id = payload.pop("brand_id", 0)
        return op_update_brand(b_id, BrandUpdateBody(**payload))
    return OPERATIONS[op_id]["handler"](**dict(event.payload or {}))


if AMQP_ENABLED:
    start_rpc_server(tool_rpc_queue(TOOL), _rpc_handler, source=SERVICE)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
