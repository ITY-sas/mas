"""
Tests unitarios del LLM Gateway (requisito 4: centralización de LLM).

Cubre las funciones puras del gateway —sin red, sin Redis, sin Ollama:

- Balanceo ponderado entre proveedores sanos              [U-LLM-01…03]
- Backoff exponencial con jitter (función pura)           [U-LLM-04…06]
- Reintentos de una llamada (`call_with_retries`)         [U-LLM-07…09]
- Cadena de fallback entre proveedores                    [U-LLM-10…12]
- Registro de proveedores y salud en memoria              [U-LLM-13…15]
- Caché de prompts: claves deterministas y TTL            [U-LLM-16…18]

Los tests de integración del gateway (POST /v1/generate con proveedores
reales) viven en `tests/performance/test_performance.py` (P04/P09).
"""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest

pytestmark = pytest.mark.unit


# ── Dobles falsos ──────────────────────────────────────────────
class FakeProvider:
    """Sustituye a Provider para las funciones de resilience (sólo .name)."""

    def __init__(self, name: str):
        self.name = name


# ── U-LLM-01…03: balanceo ponderado ───────────────────────────
class TestWeightedChoice:
    @pytest.fixture()
    def providers(self):
        from llm_gateway.providers import Provider

        return [
            Provider(name="primario", base_url="http://a:11434",
                     chat_model="gemma3:4b", embed_model="nomic-embed-text",
                     weight=90),
            Provider(name="secundario", base_url="http://b:11434",
                     chat_model="qwen3:14b", embed_model="nomic-embed-text",
                     weight=10),
        ]

    def test_choice_is_always_a_known_provider(self, providers):
        from llm_gateway.providers import weighted_choice

        rng = random.Random(42)
        for _ in range(50):
            chosen = weighted_choice(providers, rng=rng)
            assert chosen in providers

    def test_heavier_weight_dominates(self, providers):
        from llm_gateway.providers import weighted_choice

        rng = random.Random(7)
        picks = [weighted_choice(providers, rng=rng).name
                 for _ in range(300)]
        # peso 90 vs 10 → el primario debe ganar con holgura
        assert picks.count("primario") > 200

    def test_ignores_unhealthy_providers(self, providers):
        from llm_gateway.providers import weighted_choice

        providers[0].consecutive_failures = 3  # caído (umbral)
        rng = random.Random(1)
        picks = {weighted_choice(providers, rng=rng).name
                 for _ in range(30)}
        assert picks == {"secundario"}  # sólo queda el sano

    def test_all_unhealthy_still_picks_someone(self, providers):
        from llm_gateway.providers import weighted_choice

        for p in providers:
            p.consecutive_failures = 3
        rng = random.Random(1)
        assert weighted_choice(providers, rng=rng) in providers

    def test_empty_list_raises(self):
        from llm_gateway.providers import weighted_choice

        with pytest.raises(ValueError, match="no hay proveedores"):
            weighted_choice([])


# ── U-LLM-04…06: backoff exponencial ──────────────────────────
class TestBackoffDelay:
    def test_deterministic_without_jitter(self):
        from llm_gateway.resilience import backoff_delay

        assert backoff_delay(0, base=0.5, jitter=0) == 0.5
        assert backoff_delay(1, base=0.5, jitter=0) == 1.0
        assert backoff_delay(2, base=0.5, jitter=0) == 2.0
        assert backoff_delay(3, base=0.5, jitter=0) == 4.0

    def test_capped_at_max_delay(self):
        from llm_gateway.resilience import backoff_delay

        assert backoff_delay(10, base=0.5, max_delay=8.0, jitter=0) == 8.0

    def test_growth_and_bounded_with_seeded_rng(self):
        from llm_gateway.resilience import backoff_delay

        rng = random.Random(42)
        delays = [backoff_delay(i, base=0.5, jitter=0.2, rng=rng)
                  for i in range(6)]
        assert all(0.0 <= d <= 8.0 for d in delays)
        # la secuencia crece en tendencia y termina en el tope
        assert delays[-1] > delays[0]
        assert delays[-1] == pytest.approx(8.0, abs=1.6)  # tope ±20%

    def test_negative_attempt_treated_as_zero(self):
        from llm_gateway.resilience import backoff_delay

        assert backoff_delay(-5, base=0.5, jitter=0) == 0.5


# ── U-LLM-07…09: reintentos de una llamada ────────────────────
class TestCallWithRetries:
    def test_success_on_first_attempt(self):
        from llm_gateway.resilience import call_with_retries

        attempts = []
        sleeps = []
        out = call_with_retries(
            lambda attempt: attempts.append(attempt) or "ok",
            max_retries=3, sleep=sleeps.append, jitter=0,
        )
        assert out == "ok"
        assert attempts == [0]
        assert sleeps == []

    def test_retries_then_success(self):
        from llm_gateway.resilience import call_with_retries

        calls = {"n": 0}
        sleeps = []

        def flaky(attempt):
            calls["n"] += 1
            if calls["n"] < 3:
                raise ConnectionError("temporal")
            return "recuperado"

        out = call_with_retries(flaky, max_retries=4,
                                base=0.1, jitter=0, sleep=sleeps.append)
        assert out == "recuperado"
        assert calls["n"] == 3
        assert len(sleeps) == 2  # dos esperas con backoff

    def test_non_retryable_error_raises_immediately(self):
        from llm_gateway.resilience import ProviderClientError, call_with_retries

        calls = {"n": 0}
        sleeps = []

        def bad_request(attempt):
            calls["n"] += 1
            raise ProviderClientError("HTTP 400", status_code=400)

        with pytest.raises(ProviderClientError):
            call_with_retries(bad_request, max_retries=3,
                              sleep=sleeps.append)
        assert calls["n"] == 1  # no reintentó ante 4xx
        assert sleeps == []

    def test_exhausted_raises_last_error(self):
        from llm_gateway.resilience import call_with_retries

        def always_down(attempt):
            raise ConnectionError("caído")

        with pytest.raises(ConnectionError, match="caído"):
            call_with_retries(always_down, max_retries=3,
                              base=0.01, jitter=0, sleep=lambda d: None)


# ── U-LLM-10…12: cadena de fallback ───────────────────────────
class TestExecuteWithFallback:
    def test_falls_back_to_second_provider(self):
        from llm_gateway.resilience import execute_with_fallback

        primary, fallback = FakeProvider("primario"), FakeProvider("secundario")

        def call(provider, attempt):
            if provider.name == "primario":
                raise ConnectionError("primario caído")
            return f"respuesta de {provider.name}"

        result, attempts, provider = execute_with_fallback(
            [primary, fallback], call,
            max_retries=2, base=0.01, jitter=0, sleep=lambda d: None,
        )
        assert result == "respuesta de secundario"
        assert provider.name == "secundario"
        assert attempts == 3  # 2 intentos fallidos + 1 exitoso

    def test_all_providers_fail_with_report(self):
        from llm_gateway.resilience import AllProvidersFailed, execute_with_fallback

        def call(provider, attempt):
            raise ConnectionError(f"{provider.name} caído")

        with pytest.raises(AllProvidersFailed) as exc:
            execute_with_fallback(
                [FakeProvider("a"), FakeProvider("b")], call,
                max_retries=2, base=0.01, jitter=0, sleep=lambda d: None,
            )
        assert [e["provider"] for e in exc.value.provider_errors] == ["a", "b"]
        assert exc.value.attempts == 4

    def test_client_error_stops_the_chain(self):
        """Un 4xx no se reintenta NI salta al siguiente proveedor."""
        from llm_gateway.resilience import (
            ProviderClientError,
            execute_with_fallback,
        )

        tried = []

        def call(provider, attempt):
            tried.append(provider.name)
            raise ProviderClientError("prompt inválido", status_code=400)

        with pytest.raises(ProviderClientError) as exc:
            execute_with_fallback(
                [FakeProvider("a"), FakeProvider("b")], call,
                max_retries=3, base=0.01, jitter=0, sleep=lambda d: None,
            )
        assert tried == ["a"]  # no pasó a "b"
        assert exc.value.provider_errors[0]["provider"] == "a"

    def test_empty_provider_list(self):
        from llm_gateway.resilience import (
            AllProvidersFailed,
            execute_with_fallback,
        )

        with pytest.raises(AllProvidersFailed, match="no hay proveedores"):
            execute_with_fallback([], lambda p, a: None)


# ── U-LLM-13…15: registro de proveedores y salud ──────────────
class TestProviderRegistry:
    @pytest.fixture()
    def registry(self):
        from llm_gateway.providers import Provider, ProviderRegistry

        return ProviderRegistry([
            Provider(name="ollama", base_url="http://127.0.0.1:11434",
                     chat_model="gemma3:4b", embed_model="nomic-embed-text",
                     weight=100),
            Provider(name="ollama-fallback", base_url="http://127.0.0.1:11434",
                     chat_model="mistral-nemo", embed_model="nomic-embed-text",
                     weight=50),
        ])

    def test_three_failures_mark_unhealthy_and_success_recovers(self, registry):
        assert registry.healthy_providers()

        registry.record_failure("ollama")
        registry.record_failure("ollama")
        assert registry.get("ollama").healthy  # 2 < umbral(3)

        registry.record_failure("ollama")
        assert not registry.get("ollama").healthy
        assert registry.healthy_providers()[0].name == "ollama-fallback"

        registry.record_success("ollama")
        assert registry.get("ollama").healthy  # rehabilitado

    def test_pick_only_returns_healthy(self, registry):
        registry.record_failure("ollama")
        registry.record_failure("ollama")
        registry.record_failure("ollama")

        rng = random.Random(3)
        picks = {registry.pick(rng=rng).name for _ in range(20)}
        assert picks == {"ollama-fallback"}

    def test_order_starting_at_rotates(self, registry):
        order = registry.order_starting_at(registry.get("ollama-fallback"))
        assert [p.name for p in order] == ["ollama-fallback", "ollama"]

    def test_snapshot_exposes_contract_fields(self, registry):
        snap = registry.snapshot()
        assert {s["name"] for s in snap} == {"ollama", "ollama-fallback"}
        for entry in snap:
            assert {"name", "base_url", "chat_model", "embed_model",
                    "weight", "region", "healthy"} <= set(entry)
            assert entry["healthy"] is True

    def test_from_env_with_fallback_model(self):
        from llm_gateway.providers import ProviderRegistry

        env = {
            "OLLAMA_HOST": "0.0.0.0:11434",
            "OLLAMA_MODEL": "gemma3:4b",
            "LLM_FALLBACK_MODEL": "mistral-nemo",
        }
        registry = ProviderRegistry.from_env(env)

        assert registry.names() == ["ollama", "ollama-fallback"]
        # 0.0.0.0 se mapea a 127.0.0.1 usable
        assert registry.get("ollama").base_url == "http://127.0.0.1:11434"
        assert registry.get("ollama-fallback").chat_model == "mistral-nemo"
        assert registry.default_chat_model == "gemma3:4b"
        assert registry.default_embed_model == "nomic-embed-text"

    def test_build_providers_json_config(self):
        from llm_gateway.providers import build_providers

        env = {"LLM_PROVIDERS": (
            '[{"name": "a", "base_url": "http://a:1", "chat_model": "m1",'
            ' "weight": 70},'
            ' {"name": "b", "base_url": "http://b:2", "chat_model": "m2"}]'
        )}
        providers = build_providers(env)

        assert [p.name for p in providers] == ["a", "b"]
        assert providers[0].weight == 70

    def test_invalid_env_falls_back_to_defaults(self):
        from llm_gateway.providers import build_providers

        assert build_providers({"LLM_PROVIDERS": "no-json"})[0].name == "ollama"
        assert build_providers({"OLLAMA_HOST": "10.0.0.9:1234"})[0].base_url \
            == "http://10.0.0.9:1234"


# ── U-LLM-16…18: caché de prompts ─────────────────────────────
class TestPromptCache:
    def test_cache_key_is_deterministic_and_kind_scoped(self):
        from llm_gateway.cache import cache_key

        k1 = cache_key("generate", ["hola", "mundo", 0.2])
        k2 = cache_key("generate", ["hola", "mundo", 0.2])
        k3 = cache_key("embeddings", ["hola", "mundo", 0.2])
        k4 = cache_key("generate", ["hola", "otro", 0.2])

        assert k1 == k2          # misma entrada → misma clave
        assert k1 != k3          # distinto tipo
        assert k1 != k4          # distinto contenido
        assert k1.startswith("llm:generate:")
        assert k3.startswith("llm:embeddings:")

    def test_cache_key_handles_none_parts(self):
        from llm_gateway.cache import cache_key

        assert cache_key("generate", [None]) == cache_key("generate", [""])

    def test_ttl_per_kind_and_env_override(self, monkeypatch):
        from llm_gateway import cache

        monkeypatch.delenv("CACHE_TTL", raising=False)
        monkeypatch.delenv("EMB_CACHE_TTL", raising=False)
        assert cache.ttl_for("generate") == 3600
        assert cache.ttl_for("embeddings") == 86400

        monkeypatch.setenv("CACHE_TTL", "120")
        assert cache.ttl_for("generate") == 120

        monkeypatch.setenv("CACHE_TTL", "basura")  # inválido → default
        assert cache.ttl_for("generate") == 3600

    def test_dumps_loads_roundtrip_and_bad_input(self):
        from llm_gateway.cache import dumps, loads

        payload = {"content": "idea con acentos ñ", "cached": True}
        assert loads(dumps(payload)) == payload
        assert loads(None) is None
        assert loads("") is None
        assert loads("{roto") is None

    def test_cache_ops_never_raise_when_redis_down(self, monkeypatch):
        """Redis caído → degradar a 'sin caché', jamás tumbar la petición."""
        from llm_gateway import cache

        class BrokenRedis:
            def get(self, key):
                raise ConnectionError("redis caído")

            def setex(self, key, ttl, value):
                raise ConnectionError("redis caído")

        monkeypatch.setattr(cache, "_client", BrokenRedis())
        assert cache.cache_get("llm:generate:x") is None
        assert cache.cache_set("llm:generate:x", "v") is False
