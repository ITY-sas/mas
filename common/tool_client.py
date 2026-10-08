"""
Cliente de tools con **Tool Discovery** (Tools-as-a-Service).

Flujo de descubrimiento::

    1. ``ToolRegistry.discover()``  → GET /.well-known/tool-manifest de cada servicio
    2. El registro cachea ``name → Manifest`` (operaciones + parámetros)
    3. ``call(tool, op)`` mapea la operación a su endpoint REST concreto
    4. ``as_langchain_tools()`` genera objetos ``BaseTool`` de LangChain a
       partir de los manifiestos (nombre/descripción/esquema → endpoint)

El agente **nunca** importa código de negocio: solo consume contratos HTTP/AMQP.
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Iterable, Optional

import requests

from .contracts import TOOL_MANIFEST_PATH, EnvelopeError, parse_envelope, validate_manifest
from .events import TOOL_TASK_COMPLETED, TOOL_TASK_TRIGGERED, Event, rpc_call, tool_rpc_queue

logger = logging.getLogger(__name__)

# Endpoints por defecto (modo local / tests). En Docker se sobrescribe con
# TOOL_URLS (JSON) en docker-compose.
DEFAULT_TOOL_URLS = {
    "client": "http://localhost:8010",
    "trends": "http://localhost:8011",
    "competitors": "http://localhost:8012",
    "rag": "http://localhost:8013",
    "news": "http://localhost:8014",
    "trending": "http://localhost:8015",
    "postiz": "http://localhost:8016",
}

_TYPE_MAP = {"string": str, "integer": int, "number": float, "boolean": bool}


class ToolServiceError(Exception):
    """Fallo invocando un tool service (HTTP, envelope o timeout)."""


def load_tool_urls() -> dict[str, str]:
    """Lee ``TOOL_URLS`` (JSON) del entorno; si no existe usa los defaults."""
    raw = os.getenv("TOOL_URLS")
    if raw:
        try:
            urls = json.loads(raw)
            if isinstance(urls, dict):
                return {**DEFAULT_TOOL_URLS, **urls}
        except json.JSONDecodeError:
            logger.warning("TOOL_URLS no es JSON válido; usando defaults")
    return dict(DEFAULT_TOOL_URLS)


class ToolRegistry:
    """Registro de tools con descubrimiento por manifiesto."""

    def __init__(
        self,
        base_urls: Optional[dict[str, str]] = None,
        *,
        timeout: float = 30.0,
        discover_on_init: bool = False,
    ) -> None:
        self.base_urls = {**DEFAULT_TOOL_URLS, **(base_urls or load_tool_urls())}
        self.timeout = timeout
        self._manifests: dict[str, dict] = {}
        if discover_on_init:
            self.discover()

    # ── Descubrimiento ─────────────────────────────────────────
    def discover(self, *, refresh: bool = False, timeout: float = 4.0) -> dict[str, dict]:
        """Obtiene y cachea los manifiestos de todos los servicios configurados."""
        if self._manifests and not refresh:
            return self._manifests
        found: dict[str, dict] = {}
        for name, base in self.base_urls.items():
            try:
                resp = requests.get(f"{base}{TOOL_MANIFEST_PATH}", timeout=timeout)
                resp.raise_for_status()
                manifest = resp.json()
                validate_manifest(manifest)
                found[manifest["name"]] = manifest
                logger.info("descubierto '%s' → %s (%d ops)", manifest["name"], base,
                            len(manifest["operations"]))
            except Exception as exc:  # noqa: BLE001
                logger.warning("no se pudo descubrir '%s' en %s: %s", name, base, exc)
        self._manifests = found
        return found

    @property
    def manifests(self) -> dict[str, dict]:
        return self._manifests or self.discover()

    def manifest(self, tool: str) -> dict:
        manifests = self.manifests
        if tool not in manifests:
            raise ToolServiceError(
                f"tool '{tool}' no descubierto (disponibles: {sorted(manifests)})"
            )
        return manifests[tool]

    def operation(self, tool: str, operation: str) -> dict:
        for op in self.manifest(tool)["operations"]:
            if op["id"] == operation:
                return op
        raise ToolServiceError(f"operación '{operation}' no existe en tool '{tool}'")

    def endpoint(self, tool: str, operation: str) -> tuple[str, str]:
        """Mapea (tool, operación) → (METHOD, URL completa con base)."""
        op = self.operation(tool, operation)
        base = self.base_urls.get(tool) or self.base_urls.get(
            self.manifest(tool)["service"].replace("-", "_"), ""
        )
        if not base:
            raise ToolServiceError(f"sin URL base para tool '{tool}'")
        return op["method"], f"{base}{op['path']}"

    # ── Invocación síncrona (REST) ─────────────────────────────
    def call(
        self,
        tool: str,
        operation: str,
        *,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
        timeout: Optional[float] = None,
        task_id: str = "",
    ) -> Any:
        """Invoca una operación vía REST y devuelve ``data`` del envelope."""
        method, url = self.endpoint(tool, operation)
        params = params or {}
        correlation_id = str(uuid.uuid4())
        started = time.perf_counter()
        try:
            if method.upper() == "GET":
                resp = requests.get(url, params=params, timeout=timeout or self.timeout)
            else:
                resp = requests.post(
                    url,
                    params=params,
                    json=json_body if json_body is not None else params,
                    timeout=timeout or self.timeout,
                )
            resp.raise_for_status()
            data = parse_envelope(resp.json(), tool=f"{tool}.{operation}")
        except EnvelopeError:
            raise
        except requests.RequestException as exc:
            raise ToolServiceError(f"{tool}.{operation} → {exc}") from exc
        except ValueError as exc:
            raise ToolServiceError(f"{tool}.{operation} respuesta no JSON: {exc}") from exc
        elapsed = (time.perf_counter() - started) * 1000
        logger.debug("%s.%s → %.0f ms", tool, operation, elapsed)
        _ = correlation_id, task_id  # reservado para trazas
        return data

    # ── Invocación asíncrona (eventos AMQP) ────────────────────
    def call_async(
        self,
        tool: str,
        operation: str,
        *,
        payload: Optional[dict] = None,
        timeout: float = 30.0,
        task_id: str = "",
        correlation_id: str = "",
    ) -> Any:
        """Invoca una operación vía eventos ``tool.task.triggered`` →
        ``tool.task.completed`` (para tareas de larga duración)."""
        manifest = self.manifest(tool)
        if "amqp" not in manifest.get("transport", []):
            raise ToolServiceError(f"tool '{tool}' no soporta invocación AMQP")
        event = Event(
            event_type=TOOL_TASK_TRIGGERED,
            task_id=task_id or str(uuid.uuid4()),
            correlation_id=correlation_id,
            source="agent",
            tool=tool,
            operation=operation,
            payload=payload or {},
        )
        reply = rpc_call(tool_rpc_queue(tool), event, timeout=timeout)
        if not reply.ok:
            raise EnvelopeError(f"{tool}.{operation}", reply.error or "error en tool")
        return reply.payload.get("result")

    # ── Adaptador LangChain ────────────────────────────────────
    def as_langchain_tools(self, tools: Optional[Iterable[str]] = None) -> list:
        """Construye objetos ``BaseTool`` de LangChain desde los manifiestos.

        Es el puente formal **definición → endpoint**: cada operación del
        manifiesto se convierte en una tool invocable por el LLM.
        """
        from langchain_core.tools import StructuredTool
        from pydantic import create_model

        selected = set(tools) if tools else set(self.manifests)
        built: list = []
        for tool_name, manifest in sorted(self.manifests.items()):
            if tool_name not in selected:
                continue
            for op in manifest["operations"]:
                fields = {}
                for p in op.get("params", []):
                    py_type = _TYPE_MAP.get(p.get("type", "string"), str)
                    default = ... if p.get("required") else p.get("default", None)
                    if not p.get("required") and default is None:
                        py_type = Optional[py_type]  # type: ignore[assignment]
                    fields[p["name"]] = (py_type, default)
                args_model = create_model(
                    f"{tool_name}_{op['id']}_args", **fields  # type: ignore[arg-type]
                )

                def _make(t=tool_name, o=op["id"]):
                    def _fn(**kwargs):
                        return self.call(t, o, params=kwargs)

                    return _fn

                built.append(
                    StructuredTool.from_function(
                        _make(),
                        name=f"{tool_name}_{op['id']}",
                        description=op["description"],
                        args_schema=args_model,
                    )
                )
        return built

    def catalog(self) -> list[dict]:
        """Catálogo legible de tools descubiertas (para GET /tools)."""
        out = []
        for name, m in sorted(self.manifests.items()):
            out.append(
                {
                    "tool": name,
                    "service": m["service"],
                    "description": m["description"],
                    "transport": m.get("transport", ["rest"]),
                    "operations": [
                        {"id": o["id"], "method": o["method"], "path": o["path"],
                         "description": o["description"]}
                        for o in m["operations"]
                    ],
                }
            )
        return out


__all__ = ["ToolRegistry", "ToolServiceError", "load_tool_urls", "DEFAULT_TOOL_URLS",
           "TOOL_TASK_COMPLETED"]
