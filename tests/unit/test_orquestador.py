"""
Tests unitarios para el orquestador LangGraph.

Cubre:
- Esquemas de estado (state.py)
- Tools LangChain (tools.py)
- Lógica de enrutamiento del supervisor (supervisor.py)
- Construcción de los grafos (sin ejecutar LLM ni DB)
"""
import sys
from pathlib import Path

# Añadir raíz del repo y orchestrator al path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "orchestrator"))

import pytest

# ── Marca: unit ────────────────────────────────────────────────
pytestmark = pytest.mark.unit


class TestStateSchemas:
    """U-ORQ-01: Los esquemas de estado se definen correctamente."""

    def test_supervisor_state_keys(self):
        from multi_agent.state import SupervisorState

        hints = SupervisorState.__annotations__
        expected = {
            "brief",
            "client_id",
            "idea",
            "idea_id",
            "publication",
            "publication_id",
            "log",
        }
        assert expected.issubset(set(hints.keys()))

    def test_ideacion_state_keys(self):
        from multi_agent.state import IdeacionState

        hints = IdeacionState.__annotations__
        expected = {
            "brief",
            "client_id",
            "client_profile",
            "trends",
            "competitors",
            "similar_ideas",
            "news",
            "idea",
            "idea_id",
        }
        assert expected.issubset(set(hints.keys()))

    def test_publicacion_state_keys(self):
        from multi_agent.state import PublicacionState

        hints = PublicacionState.__annotations__
        expected = {
            "idea",
            "client_id",
            "idea_id",
            "client_profile",
            "trends",
            "trending",
            "publication",
            "publication_id",
        }
        assert expected.issubset(set(hints.keys()))

    def test_shared_keys_compatibility(self):
        """Los estados comparten claves para que los subgrafos lean/escriban en el supervisor."""
        from multi_agent.state import IdeacionState, PublicacionState, SupervisorState

        sup_keys = set(SupervisorState.__annotations__)
        ide_keys = set(IdeacionState.__annotations__)
        pub_keys = set(PublicacionState.__annotations__)

        # Ideación comparte brief, client_id (input) e idea, idea_id (output)
        assert {"brief", "client_id", "idea", "idea_id"}.issubset(sup_keys & ide_keys)

        # Publicación comparte idea, client_id, idea_id (input) y publication, publication_id (output)
        assert {"idea", "client_id", "idea_id", "publication", "publication_id"}.issubset(
            sup_keys & pub_keys
        )


class TestTools:
    """U-ORQ-02: Las tools LangChain están registradas correctamente."""

    def test_all_tools_count(self):
        from multi_agent.tools import ALL_TOOLS

        assert len(ALL_TOOLS) == 6

    def test_tools_have_names_and_descriptions(self):
        from multi_agent.tools import ALL_TOOLS

        for tool in ALL_TOOLS:
            assert tool.name, "Tool sin nombre"
            assert tool.description, "Tool sin descripción"

    def test_tool_names(self):
        from multi_agent.tools import ALL_TOOLS

        names = {t.name for t in ALL_TOOLS}
        expected = {
            "load_client_profile",
            "search_trends",
            "search_competitors",
            "search_similar_ideas_tool",
            "fetch_news",
            "fetch_trending",
        }
        assert names == expected

    def test_tool_is_langchain_tool(self):
        from langchain_core.tools import BaseTool

        from multi_agent.tools import ALL_TOOLS

        for tool in ALL_TOOLS:
            assert isinstance(tool, BaseTool)


class TestSupervisorRouting:
    """U-ORQ-03: La lógica de enrutamiento del supervisor es correcta."""

    def test_route_to_ideacion_when_no_idea(self):
        from multi_agent.supervisor import decide_next

        state = {"idea": "", "publication": ""}
        assert decide_next(state) == "ideacion_agent"

    def test_route_to_publicacion_when_idea_exists(self):
        from multi_agent.supervisor import decide_next

        state = {"idea": "some idea", "publication": ""}
        assert decide_next(state) == "publicacion_agent"

    def test_route_to_end_when_both_exist(self):
        from multi_agent.supervisor import decide_next

        state = {"idea": "some idea", "publication": "some post"}
        result = decide_next(state)
        # END se representa como "__end__" en LangGraph
        assert result in ("__end__", "END", "__end__")

    def test_route_with_none_values(self):
        """Valores None se tratan como 'no existe'."""
        from multi_agent.supervisor import decide_next

        assert decide_next({"idea": None, "publication": None}) == "ideacion_agent"
        assert decide_next({"idea": "x", "publication": None}) == "publicacion_agent"


class TestGraphCompilation:
    """U-ORQ-04: Los grafos se compilan sin ejecutar el pipeline."""

    def test_compile_ideacion_graph(self):
        from multi_agent.ideacion import create_ideacion_graph

        graph = create_ideacion_graph()
        assert graph is not None
        # Verificar nodos
        nodes = list(graph.get_graph().nodes.keys())
        assert "load_context" in nodes
        assert "fetch_news" in nodes
        assert "generate_idea" in nodes
        assert "save_idea" in nodes

    def test_compile_publicacion_graph(self):
        from multi_agent.publicacion import create_publicacion_graph

        graph = create_publicacion_graph()
        assert graph is not None
        nodes = list(graph.get_graph().nodes.keys())
        assert "load_context" in nodes
        assert "fetch_trending" in nodes
        assert "generate_post" in nodes
        assert "save_post" in nodes

    def test_compile_orchestrator_graph(self):
        from multi_agent.supervisor import create_orchestrator

        graph = create_orchestrator()
        assert graph is not None
        nodes = list(graph.get_graph().nodes.keys())
        assert "start" in nodes
        assert "ideacion_agent" in nodes
        assert "publicacion_agent" in nodes
