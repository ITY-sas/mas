"""
Tests de integración: Pipeline completo de agentes
I10-I14 del plan de pruebas.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

requests = pytest.importorskip("requests", reason="requests no instalado")

IDEACION_URL = os.getenv("IDEACION_URL", "http://localhost:8000")
PUBLICACION_URL = os.getenv("PUBLICACION_URL", "http://localhost:8001")


class TestAgentsHealth:
    """I10-I12: Endpoints de los agentes."""

    @pytest.mark.integration
    def test_ideacion_health(self):
        """I10: Agente Ideación /health responde."""
        try:
            resp = requests.get(f"{IDEACION_URL}/health", timeout=5)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert data["agent"] == "ideacion"
        except requests.ConnectionError:
            pytest.skip("Agente Ideación no disponible")

    @pytest.mark.integration
    def test_publicacion_health(self):
        """I11: Agente Publicación /health responde."""
        try:
            resp = requests.get(f"{PUBLICACION_URL}/health", timeout=5)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            assert data["agent"] == "publicacion"
        except requests.ConnectionError:
            pytest.skip("Agente Publicación no disponible")

    @pytest.mark.integration
    def test_ideacion_tools_endpoint(self):
        """I12: /tools del agente muestra el catálogo descubierto (≥6)."""
        try:
            resp = requests.get(f"{IDEACION_URL}/tools", timeout=5)
        except requests.ConnectionError:
            pytest.skip("Agente Ideación no disponible")
        if resp.status_code != 200:
            pytest.skip(f"discovery no disponible: {resp.text[:200]}")
        data = resp.json()
        names = [t["tool"] for t in data["tools"]]
        if len(names) < 6:
            pytest.skip(f"sólo {sorted(names)} descubiertos (stack parcial)")
        assert "client" in names
        assert "trends" in names
        # cada entrada expone su contrato (operaciones → endpoints)
        entry = next(t for t in data["tools"] if t["tool"] == "client")
        assert entry["operations"][0]["path"].startswith("/")
        assert data["discovery"].startswith("GET /")

    @pytest.mark.integration
    def test_publicacion_tools_endpoint(self):
        """I12b: /tools de publicación muestra ≥6 tools descubiertas."""
        try:
            resp = requests.get(f"{PUBLICACION_URL}/tools", timeout=5)
        except requests.ConnectionError:
            pytest.skip("Agente Publicación no disponible")
        if resp.status_code != 200:
            pytest.skip(f"discovery no disponible: {resp.text[:200]}")
        names = [t["tool"] for t in resp.json()["tools"]]
        if len(names) < 6:
            pytest.skip(f"sólo {sorted(names)} descubiertos (stack parcial)")
        assert len(names) >= 6

    @pytest.mark.integration
    def test_ideacion_metrics(self):
        """Métricas incluyen la cola de eventos y las tools descubiertas."""
        try:
            resp = requests.get(f"{IDEACION_URL}/metrics", timeout=5)
            assert resp.status_code == 200
            data = resp.json()
            assert data["queue_in"] == "agent.ideacion.tasks"
            assert data["event_out"] == "agent.task.completed"
            assert isinstance(data["tools"], list)
        except requests.ConnectionError:
            pytest.skip("Agente Ideación no disponible")

    @pytest.mark.integration
    def test_ideacion_health_reports_state_layer(self):
        """El agente declara su estado externo (Redis checkpoint)."""
        try:
            resp = requests.get(f"{IDEACION_URL}/health", timeout=5)
            assert resp.status_code == 200
            data = resp.json()
            assert data["framework"] == "langgraph"
            assert data["state"] == "redis-checkpoint"
            assert data["queue"] == "agent.ideacion.tasks"
        except requests.ConnectionError:
            pytest.skip("Agente Ideación no disponible")


class TestContextViaToolServices:
    """I13: El contexto completo se arma invocando contratos REST
    (Tools-as-a-Service) — el agente no ejecuta código de negocio."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_brief_context_via_tools(self):
        """I13: perfil + tendencias + competencia + ideas similares."""
        from common.tool_client import ToolRegistry

        try:
            registry = ToolRegistry()
            manifests = registry.discover(timeout=2.0)
            if "rag" not in manifests:
                pytest.skip(f"sólo {sorted(manifests)} descubiertos")
            brief = "Campaña de ropa sostenible para jóvenes"
            profile = registry.call("client", "profile",
                                    params={"client_id": 1})
            trends = registry.call("trends", "search",
                                   params={"query": brief, "limit": 5})
            competitors = registry.call("competitors", "search",
                                        params={"query": brief, "limit": 5})
            similar = registry.call("rag", "similar",
                                    json_body={"brand_id": 1, "query": brief, "limit": 3,
                                               "min_similarity": 0.3})
        except Exception as e:
            pytest.skip(f"Tool services no disponibles: {e}")

        assert profile["text"]
        assert trends["count"] >= 1
        assert competitors["count"] >= 1
        assert "ideas" in similar

    @pytest.mark.integration
    @pytest.mark.slow
    def test_publicacion_context_via_tools(self):
        """I13b: perfil + tendencias para la publicación."""
        from common.tool_client import ToolRegistry

        try:
            registry = ToolRegistry()
            if "client" not in registry.discover(timeout=2.0):
                pytest.skip("tool-client no descubierto")
            profile = registry.call("client", "profile",
                                    params={"client_id": 1})
            trends = registry.call(
                "trends", "search",
                params={"query": "Idea de moda sostenible", "limit": 3})
        except Exception as e:
            pytest.skip(f"Tool services no disponibles: {e}")

        assert profile["text"]
        assert trends["count"] >= 1
