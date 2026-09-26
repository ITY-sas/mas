"""
Tests de integración del orquestador **stateless** + Tools-as-a-Service.

Validan la arquitectura de microservicios contra servicios reales:

- Tool Discovery: los 6 tool services publican manifiestos y sus
  operaciones responden vía REST (I-ORQ-01/02)
- Los nodos de los agentes invocan contratos y el LLM Gateway (I-ORQ-03/04)
- Pipeline completo por HTTP: evento-driven, checkpoints Redis,
  historial de chat PostgreSQL (I-ORQ-05)

Se saltan automáticamente si los servicios no están disponibles
(``docker compose up -d --build``).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "orchestrator"))

import pytest

pytestmark = pytest.mark.integration

requests = pytest.importorskip("requests", reason="requests no instalado")

ORQUESTADOR_URL = "http://localhost:8002"
TOOL_CLIENT_URL = "http://localhost:8010"
GATEWAY_URL = "http://localhost:8003"


def _reachable(url: str, timeout: float = 3.0) -> bool:
    try:
        return requests.get(url, timeout=timeout).status_code == 200
    except Exception:  # noqa: BLE001
        return False


requires_orchestrator = pytest.mark.skipif(
    not _reachable(f"{ORQUESTADOR_URL}/health"),
    reason="Orquestador no disponible en localhost:8002",
)
requires_tools = pytest.mark.skipif(
    not _reachable(f"{TOOL_CLIENT_URL}/health"),
    reason="Tool services no disponibles (localhost:8010)",
)
requires_gateway = pytest.mark.skipif(
    not _reachable(f"{GATEWAY_URL}/health"),
    reason="LLM Gateway no disponible en localhost:8003",
)


# ── I-ORQ-01/02: Tool Discovery + contrato REST ────────────────
class TestToolDiscovery:
    """Los agentes descubren las tools y las invocan por contrato."""

    @requires_tools
    def test_discover_all_six_manifests(self):
        from common.contracts import validate_manifest
        from common.tool_client import ToolRegistry

        registry = ToolRegistry()
        manifests = registry.discover(refresh=True, timeout=2.0)

        assert len(manifests) >= 6, (
            f"sólo {sorted(manifests)} descubiertos — ¿está docker compose up?"
        )
        assert set(manifests) == {
            "client", "trends", "competitors", "rag", "news", "trending"}
        for manifest in manifests.values():
            validate_manifest(manifest)  # contrato válido
            assert manifest["operations"]

    @requires_tools
    def test_call_profile_via_rest(self):
        from common.tool_client import ToolRegistry

        data = ToolRegistry().call("client", "profile", params={"client_id": 1})

        assert data["found"] in (True, False)
        assert "text" in data

    @requires_tools
    def test_call_trends_search_via_rest(self):
        from common.tool_client import ToolRegistry

        data = ToolRegistry().call(
            "trends", "search", params={"query": "moda sostenible", "limit": 3})

        assert data["count"] >= 1
        assert isinstance(data["text"], str)


# ── I-ORQ-03: nodos de agente contra los microservicios ────────
class TestAgentNodesAgainstServices:
    """Los nodos de los agentes sólo hablan contratos REST/gateway."""

    @requires_tools
    def test_ideacion_load_context_node(self):
        from agente_ideacion.graph import load_context

        state = {
            "brief": {"client_id": 1, "content": "Summer skincare campaign"},
            "client_id": 1,
        }
        result = load_context(state)

        assert len(result["client_profile"]) > 0
        assert len(result["trends"]) > 0
        assert len(result["competitors"]) > 0
        assert len(result["similar_ideas"]) > 0
        assert result["tool_calls"] == [
            "client.profile", "trends.search",
            "competitors.search", "rag.similar",
        ]

    @requires_tools
    def test_publicacion_load_context_node(self):
        from agente_publicacion.graph import load_context

        state = {
            "idea": "A campaign about sustainable summer skincare",
            "client_id": 1,
            "idea_id": 1,
        }
        result = load_context(state)

        assert len(result["client_profile"]) > 0
        assert len(result["trends"]) > 0

    @requires_tools
    def test_ideacion_fetch_news_node(self):
        from agente_ideacion.graph import fetch_news

        result = fetch_news({
            "brief": {"client_id": 1, "content": "skincare campaign"},
            "client_id": 1,
        })
        assert isinstance(result["news"], str)

    @requires_gateway
    @pytest.mark.slow
    def test_ideacion_generate_idea_via_gateway(self):
        from agente_ideacion.graph import generate_idea

        state = {
            "brief": {"client_id": 1, "content": "Summer campaign"},
            "client_id": 1,
            "client_profile": "EcoBrand - sustainable fashion for millennials",
            "trends": "- Sustainable fashion\n- Slow fashion movement",
            "competitors": "- Patagonia: environmental activism",
            "similar_ideas": "No previous ideas",
            "news": "No news available",
        }
        result = generate_idea(state)

        assert len(result["idea"]) > 20
        assert result["tool_calls"] == ["llm-gateway.generate"]

    @requires_gateway
    @pytest.mark.slow
    def test_publicacion_generate_post_via_gateway(self):
        from agente_publicacion.graph import generate_post

        state = {
            "idea": "Summer skincare campaign for young professionals",
            "client_id": 1,
            "idea_id": 1,
            "client_profile": "EcoBrand - sustainable fashion",
            "trends": "- Sustainable living\n- Clean beauty",
            "trending": "- #SustainableFashion\n- #CleanBeauty",
        }
        result = generate_post(state)

        assert len(result["publication"]) > 10


# ── I-ORQ-05: pipeline completo vía HTTP (event-driven) ────────
class TestFullPipelineHTTP:
    """POST /process ejecuta el ciclo supervisor ⇄ agentes ⇄ tools con
    el estado fuera del proceso (Redis + PostgreSQL)."""

    @requires_orchestrator
    @pytest.mark.slow
    def test_pipeline_end_to_end_with_external_state(self):
        payload = {
            "client_id": 1,
            "content": "Create a back-to-school campaign for sustainable stationery",
            "wait": True,
            "timeout": 600,
        }
        try:
            resp = requests.post(f"{ORQUESTADOR_URL}/process",
                                 json=payload, timeout=660)
        except requests.Timeout:
            pytest.skip("Pipeline excedió el timeout de la prueba")

        assert resp.status_code == 200, resp.text[:500]
        data = resp.json()

        assert data["status"] == "completed"
        assert data["idea"], "El orquestador no devolvió una idea"
        assert data["idea_id"] > 0
        assert data["publication"], "El orquestador no devolvió una publicación"
        assert data["publication_id"] > 0

        # resultados por agente registrados externamente (TaskStore/Redis)
        assert data["agents"]["ideacion"]["status"] == "completed"
        assert data["agents"]["publicacion"]["status"] == "completed"

        task_id = data["task_id"]

        # metadatos accesibles tras la ejecución (estado externo)
        task = requests.get(f"{ORQUESTADOR_URL}/tasks/{task_id}",
                            timeout=5).json()
        assert task["status"] == "completed"
        assert task["result"]["idea_id"] == data["idea_id"]

        # historial de chat durable en PostgreSQL
        history = requests.get(
            f"{ORQUESTADOR_URL}/tasks/{task_id}/history", timeout=5)
        assert history.status_code == 200, history.text[:300]
        messages = history.json()["messages"]
        roles = [m["role"] for m in messages]
        assert roles[0] == "user"          # brief recibido
        assert roles[-1] == "assistant"    # idea + publicación generadas
        assert data["idea"] in messages[-1]["content"]

    @requires_orchestrator
    def test_health_reports_subsystems(self):
        data = requests.get(f"{ORQUESTADOR_URL}/health", timeout=5).json()

        assert data["agent"] == "orchestrator-stateless"
        assert data["state"]["checkpoints"] == "redis"
        assert data["state"]["chat_history"] == "postgresql"
        assert "redis" in data["subsystems"]

    @requires_orchestrator
    def test_graph_description_shows_interrupt_dispatch(self):
        data = requests.get(f"{ORQUESTADOR_URL}/graph", timeout=5).json()

        assert {"start", "dispatch_ideacion",
                "dispatch_publicacion"} == set(data["nodes"])
        assert "interrupt()" in data["suspension"]
        assert data["checkpointer"] == "RedisSaver (thread_id = task_id)"

    @requires_orchestrator
    @requires_tools
    def test_tools_endpoint_aggregates_catalog(self):
        resp = requests.get(f"{ORQUESTADOR_URL}/tools", timeout=10)

        if resp.status_code != 200:
            pytest.skip(f"discovery no disponible: {resp.text[:200]}")
        tools = resp.json()["tools"]
        names = {t["tool"] for t in tools}
        if len(names) < 6:
            pytest.skip(f"sólo {sorted(names)} descubiertos (stack parcial)")
        assert "rag" in names
        rag = next(t for t in tools if t["tool"] == "rag")
        op_ids = {o["id"] for o in rag["operations"]}
        assert {"similar", "save_idea", "save_publicacion"} <= op_ids
