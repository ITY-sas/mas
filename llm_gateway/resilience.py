"""
Resiliencia del gateway: exponential backoff + cadena de fallback.

Todas las funciones ``*_delay``/``weighted``/puras aceptan ``rng`` inyectable
para poder testearlas con una semilla fija.
"""
from __future__ import annotations

import inspect
import logging
import os
import random
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import requests

logger = logging.getLogger("llm_gateway.resilience")

DEFAULT_MAX_RETRIES = 3


def _resolve_max_retries(value: Optional[int] = None) -> int:
    if value is not None:
        return max(int(value), 1)
    try:
        return max(int(os.getenv("LLM_MAX_RETRIES", str(DEFAULT_MAX_RETRIES))), 1)
    except ValueError:
        return DEFAULT_MAX_RETRIES


# ── Excepciones ──────────────────────────────────────────────────────────
class ProviderError(Exception):
    """Error de proveedor; ``retryable`` decide si se reintenta."""

    retryable: bool = True

    def __init__(
        self,
        message: str,
        *,
        provider: Optional[str] = None,
        status_code: Optional[int] = None,
        retryable: Optional[bool] = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        if retryable is not None:
            self.retryable = retryable
        self.provider_errors: List[Dict[str, str]] = []


class ProviderHTTPError(ProviderError):
    """Respuesta HTTP >= 500 (o inesperada) del proveedor → reintentable."""


class ProviderClientError(ProviderError):
    """HTTP 4xx: error del cliente → NO se reintenta ni se salta de proveedor."""

    retryable = False


class ProviderParseError(ProviderError):
    """Respuesta con estructura inesperada → reintentable."""

    retryable = True


class AllProvidersFailed(Exception):
    """Se agotaron todos los proveedores (y sus reintentos)."""

    def __init__(self, message: str, provider_errors: Sequence[Dict[str, str]], attempts: int = 0) -> None:
        super().__init__(message)
        self.provider_errors: List[Dict[str, str]] = list(provider_errors)
        self.attempts = attempts


# ── Clasificación de errores ─────────────────────────────────────────────
_RETRYABLE_EXC = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.RequestException,
    ConnectionError,
    TimeoutError,
    OSError,
)


def is_retryable(exc: BaseException) -> bool:
    """¿Conviene reintentar este error? (conexión/timeout/5xx → sí; 4xx → no)."""
    if isinstance(exc, ProviderError):
        return bool(exc.retryable)
    if isinstance(exc, _RETRYABLE_EXC):
        return True
    return False


# ── Backoff exponencial con jitter (función pura) ────────────────────────
def backoff_delay(
    attempt: int,
    base: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 8.0,
    jitter: float = 0.2,
    rng: Any = None,
) -> float:
    """Delay del reintento ``attempt`` (0-based).

    ``delay = min(base * factor**attempt, max_delay)`` con jitter aleatorio
    proporcional (±``jitter``) y tope final en ``max_delay``.

    Con los defaults (factor 2, jitter 0.2) la secuencia es estrictamente
    creciente para cualquier semilla y siempre ≤ ``max_delay``.
    """
    if attempt < 0:
        attempt = 0
    rng = rng or random
    delay = min(float(base) * (float(factor) ** attempt), float(max_delay))
    if jitter:
        spread = delay * float(jitter)
        delay += rng.uniform(-spread, spread)
    return max(0.0, min(delay, float(max_delay)))


def _fn_takes_attempt(fn: Callable[..., Any]) -> bool:
    """¿Podemos llamar ``fn(attempt)`` o hay que llamar ``fn()``?"""
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):  # builtins sin firma
        return False
    for param in sig.parameters.values():
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        ):
            return True
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default is inspect.Parameter.empty:
            return True
    return False


# ── Reintentos de una sola llamada ───────────────────────────────────────
def call_with_retries(
    fn: Callable[..., Any],
    *,
    max_retries: Optional[int] = None,
    base: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 8.0,
    jitter: float = 0.2,
    rng: Any = None,
    sleep: Optional[Callable[[float], None]] = None,
    on_attempt: Optional[Callable[[int], None]] = None,
    on_retry: Optional[Callable[[BaseException, int, float], None]] = None,
) -> Any:
    """Ejecuta ``fn`` con hasta ``max_retries`` intentos y backoff exponencial.

    - ``on_attempt(attempt)`` se llama antes de cada intento (0-based).
    - ``on_retry(exc, attempt, delay)`` justo antes de dormir.
    - No reintenta ante errores no reintentables (4xx).
    """
    retries = _resolve_max_retries(max_retries)
    rng = rng or random
    sleep = sleep or time.sleep
    takes_attempt = _fn_takes_attempt(fn)

    last_error: Optional[BaseException] = None
    for attempt in range(retries):
        if on_attempt is not None:
            on_attempt(attempt)
        try:
            return fn(attempt) if takes_attempt else fn()
        except BaseException as exc:  # noqa: BLE001 - se reclasifica abajo
            if not is_retryable(exc):
                raise
            last_error = exc
            if attempt + 1 >= retries:
                break
            delay = backoff_delay(attempt, base=base, factor=factor, max_delay=max_delay, jitter=jitter, rng=rng)
            if on_retry is not None:
                on_retry(exc, attempt, delay)
            logger.debug("reintento %d/%d tras %.2fs (%s)", attempt + 1, retries, delay, exc)
            sleep(delay)

    if last_error is None:  # pragma: no cover - defensivo
        raise RuntimeError("call_with_retries: sin errores y sin resultado")
    raise last_error


# ── Cadena de fallback entre proveedores ─────────────────────────────────
def execute_with_fallback(
    providers: Sequence[Any],
    call: Callable[..., Any],
    *,
    max_retries: Optional[int] = None,
    base: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 8.0,
    jitter: float = 0.2,
    rng: Any = None,
    sleep: Optional[Callable[[float], None]] = None,
    attempt_hook: Optional[Callable[..., None]] = None,
) -> Tuple[Any, int, Any]:
    """Recorre ``providers`` en orden; por cada uno hasta ``max_retries`` intentos.

    ``call(provider, attempt)`` es la llamada real.
    ``attempt_hook(provider, attempt, total)`` se invoca antes de cada intento
    (para contabilizar métricas).

    Devuelve ``(resultado, intentos_totales, provider)``.
    Lanza ``AllProvidersFailed`` con ``provider_errors`` si se agotan todos,
    o re-lanza el error no reintentable (4xx) con sus ``provider_errors``.
    """
    ordered = list(providers)
    if not ordered:
        raise AllProvidersFailed("no hay proveedores configurados", [], 0)

    retries = _resolve_max_retries(max_retries)
    rng = rng or random
    sleep = sleep or time.sleep
    counter = {"attempts": 0}
    errors: List[Dict[str, str]] = []

    for provider in ordered:

        def _on_attempt(attempt: int, p: Any = provider) -> None:
            counter["attempts"] += 1
            if attempt_hook is not None:
                attempt_hook(p, attempt, counter["attempts"])

        def _call(attempt: int, p: Any = provider) -> Any:
            return call(p, attempt)

        try:
            result = call_with_retries(
                _call,
                max_retries=retries,
                base=base,
                factor=factor,
                max_delay=max_delay,
                jitter=jitter,
                rng=rng,
                sleep=sleep,
                on_attempt=_on_attempt,
            )
        except BaseException as exc:  # noqa: BLE001
            name = getattr(provider, "name", str(provider))
            message = str(exc) or exc.__class__.__name__
            errors.append({"provider": name, "error": message})
            logger.warning("proveedor %s agotado: %s", name, message)
            if not is_retryable(exc):
                # Error del cliente (4xx): no se reintenta ni se prueba otro proveedor.
                wrapped = exc if isinstance(exc, ProviderError) else ProviderError(message, provider=name)
                wrapped.provider_errors = errors
                raise wrapped from exc
            continue

        return result, counter["attempts"], provider

    detail = "; ".join(f"{e['provider']}: {e['error']}" for e in errors)
    raise AllProvidersFailed(f"todos los proveedores fallaron: {detail}", errors, counter["attempts"])


__all__ = [
    "AllProvidersFailed",
    "ProviderClientError",
    "ProviderError",
    "ProviderHTTPError",
    "ProviderParseError",
    "backoff_delay",
    "call_with_retries",
    "execute_with_fallback",
    "is_retryable",
]
