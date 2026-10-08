"""
LLM Gateway — microservicio de centralización de LLM (requisito arquitectura #4).

Todos los agentes hablan con este servicio; nunca con Ollama/otros proveedores.

- Balanceo de carga ponderado por ``weight`` (sólo entre proveedores sanos).
- Reintentos con exponential backoff + jitter y cadena de fallback de proveedor.
- Caché Redis de prompts/embeddings frecuentes (SHA-256 + TTL).
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Union

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - pragma: no cover
        pass

import requests
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

try:  # ejecución como script: `python main.py` (directorio del gateway en sys.path)
    import cache as gateway_cache
    import providers as providers_mod
    from resilience import (
        AllProvidersFailed,
        ProviderClientError,
        ProviderError,
        ProviderHTTPError,
        ProviderParseError,
        execute_with_fallback,
    )
except ImportError:  # importado como paquete: `llm_gateway.main`
    from llm_gateway import cache as gateway_cache
    from llm_gateway import providers as providers_mod
    from llm_gateway.resilience import (
        AllProvidersFailed,
        ProviderClientError,
        ProviderError,
        ProviderHTTPError,
        ProviderParseError,
        execute_with_fallback,
    )

PORT = int(os.getenv("PORT", "8003"))
EMBEDDINGS_TIMEOUT = float(os.getenv("EMBEDDINGS_TIMEOUT", "60"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("llm_gateway")

app = FastAPI(title="LLM Gateway", description="Balanceo, reintentos, fallback y caché de LLMs")

_registry: Optional[providers_mod.ProviderRegistry] = None


def get_registry() -> providers_mod.ProviderRegistry:
    """Registro de proveedores (singleton, construido bajo demanda)."""
    global _registry
    if _registry is None:
        _registry = providers_mod.ProviderRegistry.from_env()
        logger.info("proveedores cargados: %s", [p.to_dict() for p in _registry.providers])
    return _registry


# ── Modelos ──────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    prompt: str
    system: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: float = 180.0
    cache: bool = True
    format: Any = None


class EmbeddingsRequest(BaseModel):
    input: Union[str, List[str]] = Field(..., alias="input")
    cache: bool = True


# ── Transporte a proveedores (Ollama por defecto) ────────────────────────
def _http_error(resp: "requests.Response", provider: providers_mod.Provider, action: str) -> ProviderError:
    body = (resp.text or "").replace("\n", " ")[:300]
    message = f"{provider.name}: HTTP {resp.status_code} en {action}: {body}"
    if 400 <= resp.status_code < 500:
        return ProviderClientError(message, provider=provider.name, status_code=resp.status_code)
    return ProviderHTTPError(message, provider=provider.name, status_code=resp.status_code, retryable=True)


def _post_json(url: str, payload: Dict[str, Any], timeout: float, provider: providers_mod.Provider, action: str):
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.exceptions.Timeout as exc:
        raise ProviderHTTPError(
            f"{provider.name}: timeout en {action} ({timeout}s)", provider=provider.name, retryable=True
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise ProviderHTTPError(
            f"{provider.name}: error de conexión en {action}: {exc}", provider=provider.name, retryable=True
        ) from exc
    if resp.status_code >= 400:
        raise _http_error(resp, provider, action)
    try:
        return resp.json()
    except ValueError as exc:
        raise ProviderParseError(
            f"{provider.name}: respuesta no-JSON en {action}: {(resp.text or '')[:200]}",
            provider=provider.name,
        ) from exc


def chat_completion(
    provider: providers_mod.Provider,
    *,
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: float = 180.0,
    response_format: Any = None,
) -> str:
    """POST {base_url}/api/chat (Ollama) → contenido del mensaje."""
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload: Dict[str, Any] = {
        "model": model or provider.chat_model,
        "messages": messages,
        "stream": False,
    }
    options: Dict[str, Any] = {}
    if temperature is not None:
        options["temperature"] = temperature
    if max_tokens is not None:
        options["num_predict"] = max_tokens
    if options:
        payload["options"] = options
    if response_format is not None:
        payload["format"] = response_format

    data = _post_json(f"{provider.base_url}/api/chat", payload, timeout, provider, "chat")
    content = ((data or {}).get("message") or {}).get("content")
    if not isinstance(content, str):
        raise ProviderParseError(f"{provider.name}: respuesta sin message.content: {str(data)[:200]}", provider=provider.name)
    return content


def _normalize_vectors(vectors: Any, provider: providers_mod.Provider) -> List[List[float]]:
    """Normaliza la respuesta a una lista de vectores de floats."""
    if not isinstance(vectors, list) or not vectors:
        raise ProviderParseError(f"{provider.name}: embeddings ilegibles: {str(vectors)[:200]}", provider=provider.name)
    if isinstance(vectors[0], (int, float)):  # un único vector plano
        return [[float(x) for x in vectors]]
    normalized: List[List[float]] = []
    for vector in vectors:
        if not isinstance(vector, (list, tuple)):
            raise ProviderParseError(f"{provider.name}: vector inválido: {str(vector)[:100]}", provider=provider.name)
        normalized.append([float(x) for x in vector])
    return normalized


def _embed_legacy(provider: providers_mod.Provider, inputs: List[str], timeout: float) -> List[List[float]]:
    """Fallback 404 → POST /api/embeddings (un texto a la vez) → ``{"embedding": [...]}``."""
    vectors: List[List[float]] = []
    for text in inputs:
        data = _post_json(
            f"{provider.base_url}/api/embeddings",
            {"model": provider.embed_model, "prompt": text},
            timeout,
            provider,
            "embeddings",
        )
        vector = (data or {}).get("embedding")
        if isinstance(vector, (int, float)):
            vector = [vector]
        if not isinstance(vector, list) or not vector:
            raise ProviderParseError(
                f"{provider.name}: respuesta sin embedding: {str(data)[:200]}", provider=provider.name
            )
        vectors.append([float(x) for x in vector])
    return vectors


def embed_texts(
    provider: providers_mod.Provider,
    inputs: List[str],
    *,
    timeout: float = EMBEDDINGS_TIMEOUT,
) -> List[List[float]]:
    """POST {base_url}/api/embed → lista de vectores (con fallback a /api/embeddings)."""
    try:
        data = _post_json(
            f"{provider.base_url}/api/embed",
            {"model": provider.embed_model, "input": inputs},
            timeout,
            provider,
            "embed",
        )
    except ProviderClientError as exc:
        if exc.status_code != 404:
            raise
        logger.info("%s: /api/embed no disponible (404); usando /api/embeddings", provider.name)
        return _embed_legacy(provider, inputs, timeout)
    return _normalize_vectors((data or {}).get("embeddings"), provider)


# ── Orquestación compartida (caché → LB → fallback) ─────────────────────
def _ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _error_response(exc: Exception, fallback_provider: Optional[str] = None) -> JSONResponse:
    errors = getattr(exc, "provider_errors", None) or []
    if not errors:
        errors = [{"provider": fallback_provider or "desconocido", "error": str(exc) or exc.__class__.__name__}]
    logger.error("fallo total del gateway: %s", errors)
    return JSONResponse(status_code=502, content={"error": str(exc) or exc.__class__.__name__, "provider_errors": errors})


def _cached_payload(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    payload = gateway_cache.loads(raw)
    if isinstance(payload, dict):
        return payload
    return None


# ── Endpoints ────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "healthy", "service": "llm-gateway", "providers": get_registry().names()}


@app.get("/v1/providers")
def list_providers() -> Dict[str, Any]:
    return {"providers": get_registry().snapshot()}


@app.post("/v1/generate")
def generate(body: GenerateRequest) -> Any:
    started = time.perf_counter()
    registry = get_registry()

    # 1) Caché (clave calculada antes del balanceo)
    model_key = body.model or registry.default_chat_model
    key = None
    if body.cache:
        key = gateway_cache.cache_key(
            "generate",
            [model_key, body.system or "", body.prompt, str(body.temperature), str(body.format)],
        )
        cached = _cached_payload(gateway_cache.cache_get(key))
        if cached is not None and "content" in cached:
            return {
                "content": cached["content"],
                "provider": cached.get("provider", "cache"),
                "model": cached.get("model", model_key),
                "cached": True,
                "attempts": 0,
                "duration_ms": _ms(started),
            }

    # 2) Balanceo de carga + 3) cadena de fallback
    chosen = registry.pick()
    order = registry.order_starting_at(chosen)

    def call(provider: providers_mod.Provider, attempt: int) -> str:
        try:
            content = chat_completion(
                provider,
                prompt=body.prompt,
                system=body.system,
                model=body.model,
                temperature=body.temperature,
                max_tokens=body.max_tokens,
                timeout=body.timeout,
                response_format=body.format,
            )
        except Exception:
            registry.record_failure(provider.name)
            raise
        registry.record_success(provider.name)
        return content

    try:
        content, attempts, provider = execute_with_fallback(order, call)
    except (AllProvidersFailed, ProviderError) as exc:
        return _error_response(exc)
    except Exception as exc:  # noqa: BLE001 - último recurso: nunca 500 sin cuerpo
        return _error_response(exc)

    model_used = body.model or provider.chat_model

    # 4) Sólo se cachean respuestas OK
    if key:
        gateway_cache.cache_set(
            key,
            gateway_cache.dumps({"content": content, "provider": provider.name, "model": model_used}),
            gateway_cache.ttl_for("generate"),
        )

    return {
        "content": content,
        "provider": provider.name,
        "model": model_used,
        "cached": False,
        "attempts": attempts,
        "duration_ms": _ms(started),
    }


@app.post("/v1/embeddings")
def embeddings(body: EmbeddingsRequest) -> Any:
    started = time.perf_counter()
    registry = get_registry()

    inputs = [body.input] if isinstance(body.input, str) else list(body.input)

    # 1) Caché
    model_key = registry.default_embed_model
    key = None
    if body.cache:
        key = gateway_cache.cache_key("embeddings", [model_key, json.dumps(body.input, sort_keys=True)])
        cached = _cached_payload(gateway_cache.cache_get(key))
        if cached is not None and isinstance(cached.get("embeddings"), list):
            return {
                "embeddings": cached["embeddings"],
                "model": cached.get("model", model_key),
                "provider": cached.get("provider", "cache"),
                "cached": True,
                "duration_ms": _ms(started),
            }

    # 2) Balanceo + 3) fallback
    chosen = registry.pick()
    order = registry.order_starting_at(chosen)

    def call(provider: providers_mod.Provider, attempt: int) -> List[List[float]]:
        try:
            vectors = embed_texts(provider, inputs, timeout=EMBEDDINGS_TIMEOUT)
        except Exception:
            registry.record_failure(provider.name)
            raise
        registry.record_success(provider.name)
        return vectors

    try:
        vectors, _attempts, provider = execute_with_fallback(order, call)
    except (AllProvidersFailed, ProviderError) as exc:
        return _error_response(exc)
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)

    if key:
        gateway_cache.cache_set(
            key,
            gateway_cache.dumps({"embeddings": vectors, "model": provider.embed_model, "provider": provider.name}),
            gateway_cache.ttl_for("embeddings"),
        )

    return {
        "embeddings": vectors,
        "model": provider.embed_model,
        "provider": provider.name,
        "cached": False,
        "duration_ms": _ms(started),
    }


if __name__ == "__main__":
    logger.info("LLM Gateway escuchando en 0.0.0.0:%d", PORT)
    uvicorn.run(app, host="0.0.0.0", port=PORT)
