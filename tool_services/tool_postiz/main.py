"""
Tool service ``postiz`` — crea borradores o publicaciones en Postiz.

Postiz es opcional: el servicio expone el manifiesto aunque no tenga credenciales,
pero las operaciones devuelven un envelope de error hasta configurar
POSTIZ_API_KEY. La API sigue el contrato publico de Postiz:
GET /public/v1/integrations y POST /public/v1/posts.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any

import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from common.contracts import TOOL_MANIFEST_PATH, build_manifest, make_envelope  # noqa: E402
from common.events import tool_rpc_queue  # noqa: E402
from common.rpc import start_rpc_server  # noqa: E402

SERVICE = "tool-postiz"
TOOL = "postiz"
PORT = int(os.getenv("PORT", "8016"))
AMQP_ENABLED = os.getenv("AMQP_ENABLED", "true").lower() == "true"
POSTIZ_API_URL = os.getenv("POSTIZ_API_URL", "https://api.postiz.com/public/v1").rstrip("/")
POSTIZ_API_KEY = os.getenv("POSTIZ_API_KEY", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(SERVICE)
app = FastAPI(title=SERVICE, version="1.0.0")


class CreatePostBody(BaseModel):
    content: str
    integration_ids: list[str] = Field(default_factory=list)
    mode: str = "draft"
    publish_at: str | None = None
    settings: dict[str, dict[str, Any]] = Field(default_factory=dict)
    tags: list[dict[str, str]] = Field(default_factory=list)


def _headers() -> dict[str, str]:
    if not POSTIZ_API_KEY:
        raise RuntimeError("POSTIZ_API_KEY no configurada")
    return {"Authorization": POSTIZ_API_KEY, "Content-Type": "application/json"}


def _request(method: str, path: str, **kwargs: Any) -> Any:
    response = requests.request(
        method,
        f"{POSTIZ_API_URL}{path}",
        headers=_headers(),
        timeout=float(os.getenv("POSTIZ_TIMEOUT", "20")),
        **kwargs,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Postiz HTTP {response.status_code}: {response.text[:500]}")
    return response.json()


def op_integrations(group: str | None = None) -> Any:
    params = {"group": group} if group else None
    return _request("GET", "/integrations", params=params)


def op_create_post(body: CreatePostBody) -> Any:
    if body.mode not in {"draft", "schedule", "now"}:
        raise ValueError("mode debe ser draft, schedule o now")
    if not body.integration_ids:
        raise ValueError("integration_ids no puede estar vacío")
    if body.mode == "schedule" and not body.publish_at:
        raise ValueError("publish_at es obligatorio con mode=schedule")

    posts = []
    for integration_id in body.integration_ids:
        platform_settings = dict(body.settings.get(integration_id) or {})
        if "__type" not in platform_settings:
            raise ValueError(
                f"falta settings[{integration_id}].__type; consulta /integrations"
            )
        posts.append(
            {
                "integration": {"id": integration_id},
                "value": [{"content": body.content, "image": []}],
                "settings": platform_settings,
            }
        )

    payload = {
        "type": body.mode,
        "date": body.publish_at,
        "shortLink": False,
        "tags": body.tags,
        "posts": posts,
    }
    return _request("POST", "/posts", json=payload)


OPERATIONS = {
    "integrations": {
        "id": "integrations",
        "method": "GET",
        "path": "/integrations",
        "description": "Lista los canales sociales conectados en Postiz.",
        "params": [{"name": "group", "in": "query", "type": "string", "required": False}],
        "returns": "lista de integraciones Postiz",
        "handler": op_integrations,
    },
    "create_post": {
        "id": "create_post",
        "method": "POST",
        "path": "/posts",
        "description": "Crea un borrador, publica ahora o programa un post en varios canales Postiz.",
        "params": [],
        "returns": "lista de {postId, integration}",
        "handler": op_create_post,
    },
}

MANIFEST = build_manifest(
    name=TOOL,
    service=SERVICE,
    description="Integracion opcional con Postiz para borradores, publicaciones y programacion multicanal.",
    amqp_queue=tool_rpc_queue(TOOL),
    operations=[{k: v for k, v in op.items() if k != "handler"} for op in OPERATIONS.values()],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy" if POSTIZ_API_KEY else "degraded",
        "service": SERVICE,
        "tool": TOOL,
        "configured": bool(POSTIZ_API_KEY),
        "api_url": POSTIZ_API_URL,
        "amqp": AMQP_ENABLED,
    }


@app.get(TOOL_MANIFEST_PATH)
def manifest() -> dict:
    return MANIFEST


@app.get("/integrations")
def integrations(group: str | None = None):
    started = time.perf_counter()
    try:
        data = op_integrations(group)
        return make_envelope(TOOL + ".integrations", data, (time.perf_counter() - started) * 1000)
    except Exception as exc:
        return JSONResponse(status_code=502, content=make_envelope(
            TOOL + ".integrations", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))


@app.post("/posts")
def create_post(body: CreatePostBody):
    started = time.perf_counter()
    try:
        data = op_create_post(body)
        return make_envelope(TOOL + ".create_post", data, (time.perf_counter() - started) * 1000)
    except Exception as exc:
        return JSONResponse(status_code=502, content=make_envelope(
            TOOL + ".create_post", None, (time.perf_counter() - started) * 1000,
            status="error", error=str(exc)))


def _rpc_handler(event) -> dict:
    if event.operation == "integrations":
        return op_integrations((event.payload or {}).get("group"))
    if event.operation == "create_post":
        return op_create_post(CreatePostBody(**(event.payload or {})))
    raise ValueError(f"operación desconocida: {event.operation}")


if AMQP_ENABLED:
    start_rpc_server(tool_rpc_queue(TOOL), _rpc_handler, source=SERVICE)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
