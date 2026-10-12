"""
Tests unitarios del kernel común (``common/``).

Cubre el contrato que sostiene toda la arquitectura de microservicios:
- Eventos del bus (serialización, tipos, colas)            [U-K-01…03]
- Envelope y manifiesto de Tools-as-a-Service              [U-K-04…06]
- Tool Discovery: URLs, endpoint mapping, catálogo,
  adaptador LangChain, invocación REST sobre el contrato   [U-K-07…10]
- TaskStore (metadatos de tarea externos)                  [U-K-11…12]
- Cliente del LLM Gateway                                  [U-K-13…15]

Todos los tests son puros: sin red, sin Redis, sin RabbitMQ.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest

pytestmark = pytest.mark.unit


# ── Dobles falsos ──────────────────────────────────────────────
class FakeRedis:
    def __init__(self):
        self.data: dict = {}
        self.published: list = []

    def set(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)

    def publish(self, channel, message):
        self.published.append((channel, message))
        return 1

    def scan_iter(self, match=None, count=None):
        return iter(list(self.data.keys()))


class FakeResp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


SAMPLE_MANIFEST = {
    "name": "client",
    "service": "tool-client",
    "version": "1.0.0",
    "description": "Perfil de cliente",
    "owner": "tool-client",
    "transport": ["rest", "amqp"],
    "amqp_queue": "tool.client.rpc",
    "operations": [
        {
            "id": "profile",
            "method": "GET",
            "path": "/profile",
            "description": "Devuelve el perfil del cliente",
            "params": [{"name": "client_id", "in": "query", "type": "integer",
                        "required": True, "description": "id"}],
            "returns": "perfil",
        }
    ],
}


# ── U-K-01…03: eventos ────────────────────────────────────────
class TestEvents:
    def test_event_roundtrip(self):
        from common.events import AGENT_TASK_TRIGGERED, Event

        ev = Event(
            event_type=AGENT_TASK_TRIGGERED,
            task_id="t-1",
            agent="ideacion",
            payload={"brief": {"content": "hola"}},
        )
        back = Event.from_body(ev.to_json())

        assert back == ev
        assert back.correlation_id == "t-1"  # hereda de task_id
        assert back.ok is True

    def test_event_from_raw_json_fallback(self):
        """JSON arbitrario (p.ej. un brief en bruto) → evento 'raw'."""
        from common.events import Event

        brief = {"client_id": 7, "content": "lanzamiento"}
        back = Event.from_body(json.dumps(brief).encode())

        assert back.event_type == "raw"
        assert back.payload == brief

    def test_queue_and_event_type_constants(self):
        from common.events import (
            AGENT_QUEUES,
            AGENT_RESULTS_QUEUE,
            AGENT_TASK_COMPLETED,
            AGENT_TASK_TRIGGERED,
            TASK_COMPLETED,
            TASK_RESULTS_QUEUE,
            TOOL_TASK_COMPLETED,
            TOOL_TASK_TRIGGERED,
            tool_rpc_queue,
        )

        assert AGENT_QUEUES["ideacion"] == "agent.ideacion.tasks"
        assert AGENT_QUEUES["publicacion"] == "agent.publicacion.tasks"
        assert AGENT_RESULTS_QUEUE == "agent.results"
        assert TASK_RESULTS_QUEUE == "task.results"
        assert tool_rpc_queue("trends") == "tool.trends.rpc"
        # tipos de evento fijados en la arquitectura
        assert AGENT_TASK_TRIGGERED == "agent.task.triggered"
        assert AGENT_TASK_COMPLETED == "agent.task.completed"
        assert TOOL_TASK_TRIGGERED == "tool.task.triggered"
        assert TOOL_TASK_COMPLETED == "tool.task.completed"
        assert TASK_COMPLETED == "task.completed"


# ── U-K-04…06: contrato envelope/manifiesto ───────────────────
class TestContracts:
    def test_make_and_parse_envelope(self):
        from common.contracts import make_envelope, parse_envelope

        env = make_envelope("trends.search", {"count": 2}, 12.5)
        assert env["tool"] == "trends.search"
        assert env["status"] == "ok"
        assert env["duration_ms"] == 12.5
        assert parse_envelope(env) == {"count": 2}

    def test_parse_error_envelope_raises(self):
        from common.contracts import EnvelopeError, make_envelope, parse_envelope

        env = make_envelope("rag.similar", None, 1.0,
                            status="error", error="boom")
        with pytest.raises(EnvelopeError, match="boom"):
            parse_envelope(env, tool="rag.similar")

    def test_parse_non_envelope_raises(self):
        from common.contracts import EnvelopeError, parse_envelope

        with pytest.raises(EnvelopeError, match="envelope"):
            parse_envelope({"algo": 1})

    def test_build_and_validate_manifest(self):
        from common.contracts import TOOL_MANIFEST_PATH, build_manifest, validate_manifest

        manifest = build_manifest(
            name="trends",
            service="tool-trends",
            description="Tendencias",
            operations=[SAMPLE_MANIFEST["operations"][0]],
            amqp_queue="tool.trends.rpc",
        )
        validate_manifest(manifest)  # no lanza
        assert manifest["transport"] == ["rest", "amqp"]
        assert TOOL_MANIFEST_PATH == "/.well-known/tool-manifest"

    def test_invalid_manifest_raises(self):
        from common.contracts import build_manifest, validate_manifest

        bad = build_manifest(name="", service="x", description="d",
                             operations=[])
        with pytest.raises(ValueError, match="name"):
            validate_manifest(bad)


# ── U-K-07…10: Tool Discovery ─────────────────────────────────
class TestToolDiscovery:
    def test_default_tool_urls(self, monkeypatch):
        from common.tool_client import DEFAULT_TOOL_URLS, load_tool_urls

        monkeypatch.delenv("TOOL_URLS", raising=False)
        urls = load_tool_urls()
        assert urls == DEFAULT_TOOL_URLS
        assert set(DEFAULT_TOOL_URLS) == {
            "client", "trends", "competitors", "rag", "news", "trending", "postiz"}

    def test_env_tool_urls_override(self, monkeypatch):
        from common.tool_client import load_tool_urls

        monkeypatch.setenv("TOOL_URLS", json.dumps(
            {"client": "http://tool-client:8010"}))
        urls = load_tool_urls()
        assert urls["client"] == "http://tool-client:8010"
        assert urls["trends"] == "http://localhost:8011"  # merge con defaults

    def test_invalid_env_json_falls_back(self, monkeypatch):
        from common.tool_client import DEFAULT_TOOL_URLS, load_tool_urls

        monkeypatch.setenv("TOOL_URLS", "{no-json")
        assert load_tool_urls() == DEFAULT_TOOL_URLS

    @pytest.fixture()
    def registry(self):
        from common.tool_client import ToolRegistry

        reg = ToolRegistry(base_urls={"client": "http://tool-client:8010"})
        reg._manifests = {"client": SAMPLE_MANIFEST}
        return reg

    def test_endpoint_mapping(self, registry):
        method, url = registry.endpoint("client", "profile")
        assert method == "GET"
        assert url == "http://tool-client:8010/profile"

    def test_unknown_operation_raises(self, registry):
        from common.tool_client import ToolServiceError

        with pytest.raises(ToolServiceError, match="no existe"):
            registry.endpoint("client", "nope")
        with pytest.raises(ToolServiceError, match="no descubierto"):
            registry.endpoint("trends", "search")

    def test_discover_fetches_manifests(self, monkeypatch):
        import common.tool_client as tc
        from common.tool_client import ToolRegistry

        def fake_get(url, timeout=None, **kwargs):
            assert url.endswith("/.well-known/tool-manifest")
            return FakeResp(SAMPLE_MANIFEST)

        monkeypatch.setattr(tc.requests, "get", fake_get)
        reg = ToolRegistry(base_urls={"client": "http://tool-client:8010"})
        found = reg.discover(refresh=True)

        assert "client" in found
        assert reg.catalog()[0]["tool"] == "client"
        assert reg.catalog()[0]["operations"][0]["id"] == "profile"

    def test_discover_survives_down_service(self, monkeypatch):
        import common.tool_client as tc
        from common.tool_client import ToolRegistry

        def fake_get(url, timeout=None, **kwargs):
            raise ConnectionError("caído")

        monkeypatch.setattr(tc.requests, "get", fake_get)
        reg = ToolRegistry(base_urls={"client": "http://down:8010"})
        assert reg.discover(refresh=True) == {}

    def test_call_rest_over_contract(self, monkeypatch, registry):
        """call() mapea (tool, op) → endpoint y extrae `data` del envelope."""
        import common.tool_client as tc
        from common.contracts import make_envelope

        captured = {}

        def fake_get(url, params=None, timeout=None, **kwargs):
            captured.update(url=url, params=params, timeout=timeout)
            return FakeResp(make_envelope(
                "client.profile", {"name": "EcoBrand"}, 3.0))

        monkeypatch.setattr(tc.requests, "get", fake_get)
        data = registry.call("client", "profile", params={"client_id": 1})

        assert data == {"name": "EcoBrand"}
        assert captured["url"] == "http://tool-client:8010/profile"
        assert captured["params"] == {"client_id": 1}

    def test_call_error_envelope_raises(self, monkeypatch, registry):
        import common.tool_client as tc
        from common.contracts import EnvelopeError, make_envelope

        monkeypatch.setattr(
            tc.requests, "get",
            lambda *a, **k: FakeResp(make_envelope(
                "client.profile", None, 1.0, status="error", error="x")),
        )
        with pytest.raises(EnvelopeError):
            registry.call("client", "profile", params={"client_id": 1})

    def test_call_preserves_error_envelope_on_http_502(self, monkeypatch, registry):
        import common.tool_client as tc
        from common.contracts import EnvelopeError, make_envelope

        monkeypatch.setattr(
            tc.requests, "post",
            lambda *a, **k: FakeResp(make_envelope(
                "postiz.create_post", None, 1.0, status="error",
                error="Postiz HTTP 400: date must be an ISO string",
            ), status_code=502),
        )
        registry._manifests = {"postiz": {
            **SAMPLE_MANIFEST,
            "name": "postiz",
            "service": "tool-postiz",
            "operations": [{
                "id": "create_post", "method": "POST", "path": "/posts",
                "description": "Creates a post", "params": [], "returns": "result",
            }],
        }}

        with pytest.raises(EnvelopeError, match="date must be an ISO string"):
            registry.call("postiz", "create_post", json_body={"type": "draft"})

    def test_as_langchain_tools_from_manifest(self, registry):
        """Definición de manifiesto → objeto BaseTool invocable (puente formal)."""
        tools = registry.as_langchain_tools()

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "client_profile"
        assert "perfil" in tool.description.lower()
        assert "client_id" in tool.args


# ── U-K-11…12: TaskStore externo ──────────────────────────────
class TestTaskStore:
    @pytest.fixture()
    def store(self):
        from common.task_store import TaskStore

        return TaskStore(client=FakeRedis())

    def test_create_and_get(self, store):
        task = store.create("t-1", brief={"content": "hola"}, client_id=3)

        assert task["status"] == "running"
        loaded = store.get("t-1")
        assert loaded["client_id"] == 3
        assert loaded["brief"]["content"] == "hola"
        assert loaded["result"] == {}

    def test_get_unknown_returns_none(self, store):
        assert store.get("nope") is None

    def test_update_and_status(self, store):
        store.create("t-1", brief={}, client_id=1)
        store.set_status("t-1", "failed", error="boom")

        task = store.get("t-1")
        assert task["status"] == "failed"
        assert task["error"] == "boom"

    def test_record_agent_result(self, store):
        store.create("t-1", brief={}, client_id=1)
        store.record_agent_result("t-1", "ideacion", {"idea_id": 9})

        task = store.get("t-1")
        assert task["agents"]["ideacion"]["status"] == "completed"
        assert task["result"]["idea_id"] == 9

    def test_list_by_status(self, store):
        store.create("t-run", brief={}, client_id=1)
        store.create("t-done", brief={}, client_id=1)
        store.set_status("t-done", "completed")

        running = [t["task_id"] for t in store.list_by_status("running")]
        assert running == ["t-run"]

    def test_list_by_generation_batch_excludes_parent_and_sorts(self, store):
        store.create("batch-1", brief={
            "generation_batch_id": "batch-1",
            "generation_batch_root": True,
        }, client_id=1)
        store.create("idea-2", brief={
            "generation_batch_id": "batch-1",
            "generation_index": 2,
        }, client_id=1)
        store.create("idea-0", brief={
            "generation_batch_id": "batch-1",
            "generation_index": 0,
        }, client_id=1)
        store.create("other", brief={
            "generation_batch_id": "another-batch",
            "generation_index": 1,
        }, client_id=1)

        tasks = store.list_by_generation_batch("batch-1")
        assert [task["task_id"] for task in tasks] == ["idea-0", "idea-2"]


# ── U-K-13…15: cliente del LLM Gateway ────────────────────────
class TestGatewayClient:
    def test_gateway_base_env(self, monkeypatch):
        from common.gateway_client import gateway_base

        monkeypatch.setenv("LLM_GATEWAY_URL", "http://llm-gateway:8003/")
        assert gateway_base() == "http://llm-gateway:8003"

        monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
        assert gateway_base() == "http://localhost:8003"

    def test_generate_calls_gateway_endpoint(self, monkeypatch):
        import common.gateway_client as gc

        captured = {}

        def fake_post(url, json=None, timeout=None, **kwargs):
            captured.update(url=url, json=json, timeout=timeout)
            return FakeResp({"content": "hola", "provider": "ollama",
                             "model": "gemma3:4b", "cached": False,
                             "attempts": 1, "duration_ms": 4})

        monkeypatch.setattr(gc.requests, "post", fake_post)
        out = gc.generate("di hola", system="sys", temperature=0.3, timeout=9)

        assert captured["url"] == "http://localhost:8003/v1/generate"
        assert captured["json"] == {
            "prompt": "di hola", "cache": True, "system": "sys",
            "temperature": 0.3,
        }
        assert captured["timeout"] == 9
        assert out["content"] == "hola"

    def test_generate_failure_raises_gateway_error(self, monkeypatch):
        import common.gateway_client as gc
        from common.gateway_client import GatewayError

        monkeypatch.setattr(
            gc.requests, "post",
            lambda *a, **k: FakeResp({"error": "todos los proveedores fallan"},
                                     status_code=502),
        )
        with pytest.raises(GatewayError, match="502"):
            gc.generate("x")

    def test_embed_returns_vectors(self, monkeypatch):
        import common.gateway_client as gc

        monkeypatch.setattr(
            gc.requests, "post",
            lambda *a, **k: FakeResp({"embeddings": [[0.1, 0.2, 0.3]]}),
        )
        vectors = gc.embed("hola mundo")

        assert vectors == [[0.1, 0.2, 0.3]]
        assert gc.embed_text("hola mundo") == [0.1, 0.2, 0.3]

    def test_health_best_effort(self, monkeypatch):
        import common.gateway_client as gc

        def boom(*a, **k):
            raise ConnectionError("sin gateway")

        monkeypatch.setattr(gc.requests, "get", boom)
        assert gc.health()["status"] == "unreachable"
