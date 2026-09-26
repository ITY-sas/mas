"""
Registro de proveedores LLM, selección ponderada por peso y salud.

- Proveedores desde ``LLM_PROVIDERS`` (JSON array) o, si no existe, a partir
  de ``OLLAMA_HOST``/``OLLAMA_PORT`` (+ ``OLLAMA_MODEL``/``EMBEDDING_MODEL``).
- Selección ponderada (``weight``) sólo entre proveedores sanos.
- Salud en memoria: ``healthy = consecutive_failures < 3``.
"""
from __future__ import annotations

import json
import logging
import os
import random
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

logger = logging.getLogger("llm_gateway.providers")

#: Fallas consecutivas necesarias para marcar un proveedor como no sano.
FAILURE_THRESHOLD = 3

DEFAULT_OLLAMA_HOST = "localhost"
DEFAULT_OLLAMA_PORT = "11434"
DEFAULT_CHAT_MODEL = "gemma3:4b"
DEFAULT_EMBED_MODEL = "nomic-embed-text"


def _env(env: Optional[Mapping[str, str]], key: str, default: Optional[str] = None) -> Optional[str]:
    """Lee de ``env`` (dict) si se pasa, si no de ``os.environ``."""
    source = os.environ if env is None else env
    value = source.get(key, default)
    return value if value not in (None, "") else default


def _normalize_base_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if url and "://" not in url:
        url = f"http://{url}"
    return url


@dataclass
class Provider:
    """Un proveedor LLM (Ollama u otro) con su peso y su salud en memoria."""

    name: str
    base_url: str
    chat_model: str
    embed_model: str
    weight: int = 100
    region: str = "local"
    consecutive_failures: int = field(default=0)

    @property
    def healthy(self) -> bool:
        return self.consecutive_failures < FAILURE_THRESHOLD

    @property
    def is_healthy(self) -> bool:  # alias explícito para el contrato de API
        return self.healthy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "chat_model": self.chat_model,
            "embed_model": self.embed_model,
            "weight": self.weight,
            "region": self.region,
            "healthy": self.healthy,
        }


# ── Construcción de la lista de proveedores ──────────────────────────────
def resolve_ollama_base_url(env: Optional[Mapping[str, str]] = None) -> str:
    """Mapea ``OLLAMA_HOST``/``OLLAMA_PORT`` a una URL base usable.

    Reglas:
    - ``0.0.0.0...`` → ``127.0.0.0`` → ``127.0.0.1`` (conservando el puerto si venía).
    - Si el host ya trae ``:puerto`` se usa tal cual.
    - Si no, se le añade ``OLLAMA_PORT`` (default ``11434``).
    """
    host = (_env(env, "OLLAMA_HOST", DEFAULT_OLLAMA_HOST) or DEFAULT_OLLAMA_HOST).strip()
    port = str(_env(env, "OLLAMA_PORT", DEFAULT_OLLAMA_PORT) or DEFAULT_OLLAMA_PORT).strip()

    if host.startswith("0.0.0.0"):
        host = "127.0.0.1" + host[len("0.0.0.0"):]
    if ":" not in host:
        host = f"{host}:{port}"
    return f"http://{host}"


def build_default_providers(env: Optional[Mapping[str, str]] = None) -> List[Provider]:
    """Lista por defecto (Ollama local) + fallback opcional (``LLM_FALLBACK_MODEL``)."""
    base_url = _normalize_base_url(resolve_ollama_base_url(env))
    chat_model = _env(env, "OLLAMA_MODEL", DEFAULT_CHAT_MODEL) or DEFAULT_CHAT_MODEL
    embed_model = _env(env, "EMBEDDING_MODEL", DEFAULT_EMBED_MODEL) or DEFAULT_EMBED_MODEL

    primary = Provider(
        name="ollama",
        base_url=base_url,
        chat_model=chat_model,
        embed_model=embed_model,
        weight=100,
        region="local",
    )
    return _append_fallback([primary], env)


def _append_fallback(providers: List[Provider], env: Optional[Mapping[str, str]] = None) -> List[Provider]:
    """Añade un 2.º proveedor (mismo ``base_url``) si ``LLM_FALLBACK_MODEL`` está definido."""
    fallback_model = _env(env, "LLM_FALLBACK_MODEL")
    if not fallback_model or not providers:
        return providers
    if any(p.chat_model == fallback_model for p in providers):
        return providers
    primary = providers[0]
    fallback = Provider(
        name=f"{primary.name}-fallback",
        base_url=primary.base_url,
        chat_model=fallback_model,
        embed_model=primary.embed_model,
        weight=50,
        region="local-fallback",
    )
    logger.info("fallback configurado: %s (%s)", fallback.name, fallback_model)
    return list(providers) + [fallback]


def _provider_from_item(item: Mapping[str, Any], index: int, env: Optional[Mapping[str, str]]) -> Provider:
    name = str(item.get("name") or f"provider-{index + 1}")
    base_url = _normalize_base_url(str(item.get("base_url") or resolve_ollama_base_url(env)))
    chat_model = str(item.get("chat_model") or _env(env, "OLLAMA_MODEL", DEFAULT_CHAT_MODEL) or DEFAULT_CHAT_MODEL)
    embed_model = str(item.get("embed_model") or _env(env, "EMBEDDING_MODEL", DEFAULT_EMBED_MODEL) or DEFAULT_EMBED_MODEL)
    try:
        weight = int(item.get("weight", 100))
    except (TypeError, ValueError):
        weight = 100
    region = str(item.get("region", "local"))
    return Provider(
        name=name,
        base_url=base_url,
        chat_model=chat_model,
        embed_model=embed_model,
        weight=weight,
        region=region,
    )


def build_providers(env: Optional[Mapping[str, str]] = None) -> List[Provider]:
    """Construye la lista completa de proveedores desde la configuración."""
    raw = _env(env, "LLM_PROVIDERS")
    if not raw:
        return build_default_providers(env)
    try:
        items = json.loads(raw)
    except (TypeError, ValueError) as exc:
        logger.warning("LLM_PROVIDERS no es JSON válido (%s); usando proveedores por defecto", exc)
        return build_default_providers(env)
    if not isinstance(items, list) or not items:
        logger.warning("LLM_PROVIDERS vacío; usando proveedores por defecto")
        return build_default_providers(env)

    providers = [_provider_from_item(item, i, env) for i, item in enumerate(items) if isinstance(item, dict)]
    if not providers:
        return build_default_providers(env)
    return _append_fallback(providers, env)


# ── Selección ponderada (función pura) ───────────────────────────────────
def weighted_choice(providers: Sequence[Provider], rng: Any = None) -> Provider:
    """Elige un proveedor al azar ponderado por ``weight``.

    Sólo considera proveedores ``healthy``; si ninguno lo está se elige
    entre la lista completa (para no quedarnos sin intento).
    ``rng`` admite ``random.Random(seed)``.
    """
    if not providers:
        raise ValueError("weighted_choice: no hay proveedores")
    rng = rng or random
    candidates = [p for p in providers if p.healthy] or list(providers)
    weights = [float(p.weight) for p in candidates]
    if sum(weights) <= 0:
        weights = [1.0] * len(candidates)
    return rng.choices(candidates, weights=weights, k=1)[0]


# ── Registro con salud en memoria ────────────────────────────────────────
class ProviderRegistry:
    """Lista de proveedores + contadores de fallos consecutivos (thread-safe)."""

    def __init__(self, providers: Sequence[Provider]):
        if not providers:
            raise ValueError("ProviderRegistry: se requiere al menos un proveedor")
        self._providers: List[Provider] = list(providers)
        self._lock = threading.RLock()

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "ProviderRegistry":
        return cls(build_providers(env))

    # -- lectura --
    @property
    def providers(self) -> List[Provider]:
        with self._lock:
            return list(self._providers)

    def names(self) -> List[str]:
        return [p.name for p in self.providers]

    def get(self, name: str) -> Optional[Provider]:
        with self._lock:
            for p in self._providers:
                if p.name == name:
                    return p
        return None

    def healthy_providers(self) -> List[Provider]:
        return [p for p in self.providers if p.healthy]

    def snapshot(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.providers]

    @property
    def default_chat_model(self) -> str:
        return self.providers[0].chat_model

    @property
    def default_embed_model(self) -> str:
        return self.providers[0].embed_model

    # -- salud --
    def record_success(self, name: str) -> None:
        with self._lock:
            provider = self._find(name)
            if provider is not None:
                if provider.consecutive_failures:
                    logger.info("proveedor %s recuperado (fallo consecutivo reseteado)", name)
                provider.consecutive_failures = 0

    def record_failure(self, name: str) -> int:
        with self._lock:
            provider = self._find(name)
            if provider is None:
                return 0
            provider.consecutive_failures += 1
            failures = provider.consecutive_failures
            if failures == FAILURE_THRESHOLD:
                logger.warning("proveedor %s marcado como NO sano (%d fallos consecutivos)", name, failures)
            return failures

    # -- selección --
    def pick(self, rng: Any = None) -> Provider:
        return weighted_choice(self.providers, rng=rng)

    def order_starting_at(self, provider: Provider) -> List[Provider]:
        """Rota la lista para empezar por ``provider`` (orden de fallback)."""
        with self._lock:
            names = [p.name for p in self._providers]
            try:
                idx = names.index(provider.name)
            except ValueError:
                return list(self._providers)
            ordered = self._providers[idx:] + self._providers[:idx]
            return list(ordered)

    def _find(self, name: str) -> Optional[Provider]:
        for p in self._providers:
            if p.name == name:
                return p
        return None


__all__ = [
    "Provider",
    "ProviderRegistry",
    "FAILURE_THRESHOLD",
    "build_default_providers",
    "build_providers",
    "resolve_ollama_base_url",
    "weighted_choice",
]
