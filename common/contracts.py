"""
Contratos de Tools-as-a-Service.

- **Manifiesto** (``/.well-known/tool-manifest``): contrato autocontenido que
  cada tool service publica. Permite al agente *descubrir* qué operaciones
  existen, sus parámetros y a qué endpoint llamar (Tool Discovery).
- **Envelope**: envoltorio uniforme de toda respuesta de tool service.
"""
from __future__ import annotations

import time
from typing import Any, Iterable, Optional

TOOL_MANIFEST_PATH = "/.well-known/tool-manifest"
MANIFEST_VERSION = "1.0.0"


# ── Manifiesto ─────────────────────────────────────────────────
def build_manifest(
    *,
    name: str,
    service: str,
    description: str,
    operations: Iterable[dict],
    version: str = MANIFEST_VERSION,
    amqp_queue: Optional[str] = None,
    owner: str = "",
) -> dict:
    """Construye el manifiesto de un tool service.

    Cada operación::

        {"id": "search",
         "method": "GET",
         "path": "/search",
         "description": "…",
         "params": [{"name": "query", "in": "query", "type": "string",
                     "required": True, "description": "…"}],
         "returns": "lista de tendencias"}
    """
    transport = ["rest"]
    if amqp_queue:
        transport.append("amqp")
    return {
        "name": name,
        "service": service,
        "version": version,
        "description": description,
        "owner": owner or service,
        "transport": transport,
        "amqp_queue": amqp_queue,
        "operations": list(operations),
    }


def validate_manifest(manifest: dict) -> None:
    """Valida la forma mínima de un manifiesto (lanza ValueError)."""
    for key in ("name", "service", "description", "operations"):
        if not manifest.get(key):
            raise ValueError(f"Manifiesto inválido: falta '{key}'")
    for op in manifest["operations"]:
        for key in ("id", "method", "path", "description"):
            if not op.get(key):
                raise ValueError(f"Operación inválida en manifiesto: falta '{key}'")


# ── Envelope ───────────────────────────────────────────────────
def make_envelope(
    tool: str,
    data: Any,
    duration_ms: float,
    *,
    status: str = "ok",
    error: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> dict:
    """Envoltorio uniforme de respuesta de un tool service."""
    return {
        "tool": tool,
        "status": status,
        "data": data,
        "error": error,
        "duration_ms": round(duration_ms, 2),
        "correlation_id": correlation_id,
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


class EnvelopeError(Exception):
    """Respuesta de tool service con ``status=error`` o malformada."""

    def __init__(self, tool: str, message: str) -> None:
        super().__init__(f"{tool}: {message}")
        self.tool = tool


def parse_envelope(payload: Any, tool: str = "tool") -> Any:
    """Valida un envelope y devuelve ``data``; lanza :class:`EnvelopeError`."""
    if not isinstance(payload, dict) or "status" not in payload:
        raise EnvelopeError(tool, "respuesta sin envelope (falta 'status')")
    if payload.get("status") != "ok":
        raise EnvelopeError(tool, str(payload.get("error") or "error desconocido"))
    return payload.get("data")
