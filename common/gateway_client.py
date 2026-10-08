"""
Cliente del LLM Gateway.

Los agentes **nunca** hablan directamente con Ollama/otros proveedores:
toda llamada a LLM pasa por el gateway (balanceo, reintentos, fallback,
caché de prompts) — requisito de centralización de LLM.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional, Union

import requests

logger = logging.getLogger(__name__)


class GatewayError(Exception):
    """El LLM Gateway devolvió error o no es alcanzable."""


def gateway_base() -> str:
    """URL base del gateway (``LLM_GATEWAY_URL``)."""
    base = os.getenv("LLM_GATEWAY_URL", "http://localhost:8003").rstrip("/")
    return base


def generate(
    prompt: str,
    *,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: float = 180.0,
    cache: bool = True,
    format: Any = None,
) -> dict:
    """Generación de texto vía gateway.

    Devuelve ``{content, provider, model, cached, attempts, duration_ms}``.
    """
    body: dict[str, Any] = {"prompt": prompt, "cache": cache}
    if system:
        body["system"] = system
    if model:
        body["model"] = model
    if temperature is not None:
        body["temperature"] = temperature
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if format is not None:
        body["format"] = format
    try:
        resp = requests.post(f"{gateway_base()}/v1/generate", json=body, timeout=timeout)
    except requests.RequestException as exc:
        raise GatewayError(f"gateway inaccesible: {exc}") from exc
    if resp.status_code != 200:
        raise GatewayError(f"gateway {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    if "content" not in data:
        raise GatewayError(f"respuesta inesperada del gateway: {data}")
    return data


def embed(
    inputs: Union[str, list[str]],
    *,
    timeout: float = 60.0,
    cache: bool = True,
) -> list[list[float]]:
    """Embeddings vía gateway. Devuelve lista de vectores."""
    body = {"input": inputs, "cache": cache}
    try:
        resp = requests.post(f"{gateway_base()}/v1/embeddings", json=body, timeout=timeout)
    except requests.RequestException as exc:
        raise GatewayError(f"gateway inaccesible: {exc}") from exc
    if resp.status_code != 200:
        raise GatewayError(f"gateway {resp.status_code}: {resp.text[:300]}")
    embeddings = resp.json().get("embeddings")
    if not isinstance(embeddings, list):
        raise GatewayError(f"respuesta inesperada: {resp.json()}")
    return embeddings


def embed_text(text: str, **kwargs: Any) -> list[float]:
    """Conveniencia: embedding de un solo texto."""
    vectors = embed([text], **kwargs)
    return vectors[0] if vectors else []


def health() -> dict:
    """Health del gateway (best-effort)."""
    try:
        resp = requests.get(f"{gateway_base()}/health", timeout=3)
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        return {"status": "unreachable", "error": str(exc)}


__all__ = ["GatewayError", "gateway_base", "generate", "embed", "embed_text", "health"]
