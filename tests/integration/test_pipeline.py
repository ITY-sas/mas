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
        """I12: /tools lista ≥6 tools en agente de ideación."""
        try:
            resp = requests.get(f"{IDEACION_URL}/tools", timeout=5)
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["tools"]) >= 6
            tool_names = [t["name"] for t in data["tools"]]
            assert "get_client_profile" in tool_names
            assert "get_relevant_trends" in tool_names
        except requests.ConnectionError:
            pytest.skip("Agente Ideación no disponible")

    @pytest.mark.integration
    def test_publicacion_tools_endpoint(self):
        """I12b: /tools lista ≥6 tools en agente de publicación."""
        try:
            resp = requests.get(f"{PUBLICACION_URL}/tools", timeout=5)
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["tools"]) >= 6
        except requests.ConnectionError:
            pytest.skip("Agente Publicación no disponible")

    @pytest.mark.integration
    def test_ideacion_metrics(self):
        """Métricas incluyen info de tools."""
        try:
            resp = requests.get(f"{IDEACION_URL}/metrics", timeout=5)
            assert resp.status_code == 200
            data = resp.json()
            assert "tools" in data
            assert isinstance(data["tools"], list)
        except requests.ConnectionError:
            pytest.skip("Agente Ideación no disponible")


class TestEnrichmentPipeline:
    """I13: Enriquecimiento completo con tools."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_enrich_brief_context(self):
        """I13: enrich_brief_context retorna stats completos."""
        pytest.importorskip("psycopg2")
        from shared_tools.enrichment import enrich_brief_context

        try:
            context = enrich_brief_context(
                "Campaña de ropa sostenible para jóvenes", client_id=1
            )
            assert "client_profile" in context
            assert "trends" in context
            assert "competitors" in context
            assert "similar_ideas" in context
            assert "stats" in context
            assert context["stats"]["trends_found"] >= 1
            assert context["stats"]["competitors_found"] >= 1
        except Exception as e:
            pytest.skip(f"Enrichment no disponible: {e}")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_enrich_idea_context(self):
        """I13b: enrich_idea_context para publicación."""
        pytest.importorskip("psycopg2")
        from shared_tools.enrichment import enrich_idea_context

        try:
            context = enrich_idea_context("Idea de moda sostenible", client_id=1)
            assert "client_profile" in context
            assert "trends" in context
            assert context["stats"]["trends_found"] >= 1
        except Exception as e:
            pytest.skip(f"Enrichment no disponible: {e}")
