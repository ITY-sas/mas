"""
Tests de integración para el orquestador LangGraph.

Ejecuta el pipeline completo (o nodos individuales) contra servicios reales:
- PostgreSQL (perfil de cliente, tendencias, competencia, RAG)
- Ollama (generación de texto)

Se saltan automáticamente si los servicios no están disponibles.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "orchestrator"))

import pytest

pytestmark = pytest.mark.integration


def _ollama_available() -> bool:
    try:
        import requests

        host = "127.0.0.1"
        r = requests.get(f"http://{host}:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _postgres_available() -> bool:
    try:
        import psycopg2

        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="password",
            dbname="ideation_db",
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


requires_ollama = pytest.mark.skipif(
    not _ollama_available(), reason="Ollama no disponible en 127.0.0.1:11434"
)
requires_postgres = pytest.mark.skipif(
    not _postgres_available(), reason="PostgreSQL no disponible en localhost:5432"
)


class TestIdeacionNodes:
    """I-ORQ-01: Nodos del agente de ideación contra servicios reales."""

    @requires_postgres
    def test_load_context_node(self):
        from multi_agent.ideacion import load_context

        state = {
            "brief": {"client_id": 1, "content": "Summer skincare campaign"},
            "client_id": 1,
        }
        result = load_context(state)
        assert "client_profile" in result
        assert "trends" in result
        assert "competitors" in result
        assert "similar_ideas" in result
        assert len(result["client_profile"]) > 0

    @requires_postgres
    @requires_ollama
    def test_generate_idea_node(self):
        from multi_agent.ideacion import generate_idea

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
        assert "idea" in result
        assert len(result["idea"]) > 20


class TestPublicacionNodes:
    """I-ORQ-02: Nodos del agente de publicación contra servicios reales."""

    @requires_postgres
    def test_load_context_node(self):
        from multi_agent.publicacion import load_context

        state = {
            "idea": "A campaign about sustainable summer skincare",
            "client_id": 1,
            "idea_id": 1,
        }
        result = load_context(state)
        assert "client_profile" in result
        assert "trends" in result

    @requires_postgres
    @requires_ollama
    def test_generate_post_node(self):
        from multi_agent.publicacion import generate_post

        state = {
            "idea": "Summer skincare campaign for young professionals",
            "client_id": 1,
            "idea_id": 1,
            "client_profile": "EcoBrand - sustainable fashion",
            "trends": "- Sustainable living\n- Clean beauty",
            "trending": "- #SustainableFashion\n- #CleanBeauty",
        }
        result = generate_post(state)
        assert "publication" in result
        assert len(result["publication"]) > 10


class TestFullPipeline:
    """I-ORQ-03: Pipeline completo del orquestador."""

    @requires_postgres
    @requires_ollama
    def test_run_pipeline_end_to_end(self):
        from multi_agent.supervisor import run_pipeline

        brief = {
            "client_id": 1,
            "content": "Create a back-to-school campaign for sustainable stationery",
        }
        result = run_pipeline(brief=brief, client_id=1)

        assert result.get("idea"), "El pipeline no generó una idea"
        assert result.get("idea_id", 0) > 0, "La idea no se guardó en DB"
        assert result.get("publication"), "El pipeline no generó una publicación"
        assert result.get("publication_id", 0) > 0, "La publicación no se guardó en DB"
        assert "supervisor: pipeline iniciado" in result.get("log", [])
