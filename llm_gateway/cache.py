"""
Caché Redis de prompts/embeddings frecuentes.

- Claves: ``llm:{kind}:{sha256("|".join(parts))}`` (función pura testeable).
- TTL por tipo: ``CACHE_TTL`` (generate) y ``EMB_CACHE_TTL`` (embeddings).
- Cualquier fallo de Redis se ignora con un warning: la petición sigue
  adelante sin caché (Redis nunca tumbará una llamada).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Optional, Sequence

logger = logging.getLogger("llm_gateway.cache")

REDIS_URL_DEFAULT = "redis://localhost:6379"
DEFAULT_GENERATE_TTL = 3600
DEFAULT_EMBEDDINGS_TTL = 86400

_client: Any = None


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        logger.warning("valor inválido para %s; usando %d", name, default)
        return default


# ── Función pura ─────────────────────────────────────────────────────────
def cache_key(kind: str, payload_parts: Sequence[Any]) -> str:
    """Clave determinista: hash SHA-256 de las partes unidas por ``|``."""
    parts = ["" if part is None else str(part) for part in payload_parts]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"llm:{kind}:{digest}"


# ── Cliente (lazy) ───────────────────────────────────────────────────────
def get_redis() -> Any:
    """Cliente ``redis.Redis`` (``decode_responses=True``), creado bajo demanda."""
    global _client
    if _client is None:
        import redis  # import local: `cache_key` sigue usable sin paquete redis

        url = os.getenv("REDIS_URL", REDIS_URL_DEFAULT)
        _client = redis.Redis.from_url(url, decode_responses=True)
    return _client


def reset_client() -> None:
    """Invalida el cliente (útil en tests)."""
    global _client
    _client = None


# ── Operaciones (best-effort) ────────────────────────────────────────────
def cache_get(key: str) -> Optional[str]:
    """Devuelve el valor o ``None`` (fallo Redis → warning + ``None``)."""
    try:
        value = get_redis().get(key)
        return value if isinstance(value, str) else None
    except Exception as exc:  # noqa: BLE001 - Redis nunca debe tumbar la petición
        logger.warning("Redis GET falló (se sigue sin caché): %s", exc)
        return None


def cache_set(key: str, value: str, ttl: int = DEFAULT_GENERATE_TTL) -> bool:
    """Escribe con TTL; devuelve False si Redis falla (sin propagar el error)."""
    try:
        get_redis().setex(key, max(int(ttl), 1), value)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis SET falló (se sigue sin caché): %s", exc)
        return False


def cache_delete(key: str) -> bool:
    try:
        get_redis().delete(key)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis DEL falló: %s", exc)
        return False


def ttl_for(kind: str) -> int:
    """TTL por tipo de entrada (``generate`` | ``embeddings``)."""
    if kind == "embeddings":
        return _env_int("EMB_CACHE_TTL", DEFAULT_EMBEDDINGS_TTL)
    return _env_int("CACHE_TTL", DEFAULT_GENERATE_TTL)


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def loads(raw: Optional[str]) -> Optional[Any]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


__all__ = [
    "cache_delete",
    "cache_get",
    "cache_key",
    "cache_set",
    "dumps",
    "get_redis",
    "loads",
    "reset_client",
    "ttl_for",
]
