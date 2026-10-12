"""
Tests unitarios de los agentes microservicio (sin servicios externos).

Cubre:
- Esquemas de estado de cada agente (ahora viven en el paquete del agente)
- Compilación de sus grafos LangGraph
- Contratos de invocación de tools (Tool Discovery → REST) y del LLM Gateway
  en cada nodo, con registros falsos (sin red)
- Semántica idempotente de ``run_agent_task`` (reentrega / retoma / nueva)

U-AG-01 … U-AG-05 del plan de pruebas.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest

pytestmark = pytest.mark.unit


# ── Dobles falsos ──────────────────────────────────────────────
class FakeRegistry:
    """Sustituye a ToolRegistry: registra llamadas y devuelve envelopes."""

    def __init__(self, response: dict | None = None):
        self.calls: list = []
        self.response = response or {}

    def call(self, tool, operation, *, params=None, json_body=None,
             timeout=None, task_id=""):
        self.calls.append(
            {"tool": tool, "operation": operation,
             "params": params or {}, "json_body": json_body or {}}
        )
        data = dict(self.response)
        data.setdefault("text", f"texto de {tool}.{operation}")
        data.setdefault("count", 2)
        data.setdefault("id", 42)
        return data


class FakeGraph:
    """Sustituye a un grafo compilado para probar run_agent_task."""

    def __init__(self, values=None, pending=()):
        self.values = values or {}
        self.pending = tuple(pending)
        self.invocations: list = []
        self.configs: list = []

    def get_state(self, config):
        if self.values == {} and not self.pending:
            # distingue "sin checkpoint" de "checkpoint vacío"
            return None
        return SimpleNamespace(values=self.values, next=self.pending)

    def invoke(self, inputs, config=None):
        self.invocations.append(inputs)
        self.configs.append(config)
        if inputs is None:
            return {**self.values, "idea": "retomada"}
        return {"idea": "generada", "idea_id": 1}


def _ideacion_state(**extra):
    state = {
        "brief": {"client_id": 1, "content": "brief de prueba"},
        "client_id": 1,
        "brand_id": 1,
    }
    state.update(extra)
    return state


# ── U-AG-01: esquemas de estado ────────────────────────────────
class TestAgentStateSchemas:
    def test_ideacion_state_keys(self):
        from agente_ideacion.graph import IdeacionState

        expected = {
            "brief", "client_id", "client_profile", "trends",
            "competitors", "similar_ideas", "news", "idea", "idea_id",
            "tool_calls",
        }
        assert expected.issubset(set(IdeacionState.__annotations__))

    def test_publicacion_state_keys(self):
        from agente_publicacion.graph import PublicacionState

        expected = {
            "idea", "client_id", "idea_id", "client_profile", "trends",
            "trending", "publication", "publication_id", "tool_calls",
        }
        assert expected.issubset(set(PublicacionState.__annotations__))


# ── U-AG-02: compilación de grafos ─────────────────────────────
class TestAgentGraphsCompile:
    def test_compile_ideacion_nodes(self):
        from agente_ideacion.graph import create_ideacion_graph

        graph = create_ideacion_graph()
        nodes = set(graph.get_graph().nodes.keys())
        assert {"load_context", "fetch_news",
                "generate_idea", "save_idea"}.issubset(nodes)

    def test_compile_publicacion_nodes(self):
        from agente_publicacion.graph import create_publicacion_graph

        graph = create_publicacion_graph()
        nodes = set(graph.get_graph().nodes.keys())
        assert {"load_context", "fetch_trending",
                "generate_post", "save_post"}.issubset(nodes)


# ── U-AG-03: contratos de invocación en los nodos ──────────────
class TestIdeacionNodeContracts:
    """El agente invoca contratos REST (tools) y el gateway; nada directo."""

    def test_load_context_calls_four_tool_services(self, monkeypatch):
        import agente_ideacion.graph as g

        fake = FakeRegistry()
        monkeypatch.setattr(g, "REGISTRY", fake)

        result = g.load_context(_ideacion_state())

        pairs = [(c["tool"], c["operation"]) for c in fake.calls]
        assert pairs == [
            ("client", "profile"),
            ("trends", "search"),
            ("competitors", "search"),
            ("rag", "similar"),
        ]
        # parámetros correctos (query = contenido del brief)
        assert fake.calls[0]["params"]["client_id"] == 1
        assert fake.calls[1]["params"]["query"] == "brief de prueba"
        assert fake.calls[1]["params"]["limit"] == 5
        assert fake.calls[3]["json_body"]["min_similarity"] == 0.3
        assert fake.calls[3]["json_body"]["brand_id"] == 1
        # textos listos para prompt + trazabilidad
        assert result["client_profile"].startswith("texto de client")
        assert "rag.similar" in result["tool_calls"]

    def test_empty_brief_is_derived_from_brand_profile_and_topics(self, monkeypatch):
        import agente_ideacion.graph as g

        fake = FakeRegistry(response={"profile": {
            "nombre": "EcoBrand",
            "perfil_marca": "cosmética sostenible",
            "pilares_contenido": "educación ambiental",
        }})
        monkeypatch.setattr(g, "REGISTRY", fake)
        state = _ideacion_state(brief={"content": "", "topics": ["verano", "reciclaje"]})

        result = g.load_context(state)

        assert "cosmética sostenible" in result["brief"]["content"]
        assert "educación ambiental" in result["brief"]["content"]
        assert "verano, reciclaje" in result["brief"]["content"]
        assert fake.calls[1]["params"]["query"] == result["brief"]["content"]

    def test_fetch_news_calls_news_service(self, monkeypatch):
        import agente_ideacion.graph as g

        fake = FakeRegistry()
        monkeypatch.setattr(g, "REGISTRY", fake)

        result = g.fetch_news(_ideacion_state())

        assert fake.calls == [
            {"tool": "news", "operation": "news",
             "params": {"query": "brief de prueba", "limit": 3},
             "json_body": {}}
        ]
        assert result["tool_calls"] == ["news.news"]

    def test_generate_idea_goes_through_gateway(self, monkeypatch):
        import agente_ideacion.graph as g

        captured = {}

        def fake_generate(prompt, **kwargs):
            captured["prompt"] = prompt
            captured["kwargs"] = kwargs
            return {"content": """{
                "content_type": "reel",
                "title": "Idea",
                "concept": "IDEA GENERADA",
                "objective": "Objetivo",
                "audience": "Audiencia",
                "key_message": "Mensaje",
                "format": "Reel",
                "duration_seconds": 30,
                "script": [{"scene": 1, "duration_seconds": 30,
                             "visual": "Visual", "action": "Acción",
                             "dialogue_or_voiceover": "Voz",
                             "on_screen_text": "Texto"}],
                "camera": [{"scene": 1, "shot": "Plano medio",
                            "angle": "Frontal", "movement": "Estático",
                            "framing": "Sujeto centrado"}],
                "performance_direction": "Natural",
                "location_and_art_direction": "Estudio",
                "audio": "Música",
                "editing_notes": "Cortes rápidos",
                "post_spec": {"visual_concept": "", "composition": "", "image_direction": "", "text_on_asset": "", "caption_direction": "", "carousel_slides": [], "alt_text": "", "platform_adaptations": ""},
                "cta": "Conoce más",
                "deliverables": ["Video 9:16"],
                "why_it_works": "Es relevante"
            }""", "provider": "p", "model": "m",
                    "cached": False, "attempts": 1}

        monkeypatch.setattr(g.gateway_client, "generate", fake_generate)

        state = _ideacion_state(
            client_profile="perfil eco", trends="tendencia x",
            competitors="competidor y", similar_ideas="idea previa",
            news="noticia z",
        )
        result = g.generate_idea(state)

        assert result["preproduction"]["concept"] == "IDEA GENERADA"
        assert '"script"' in result["idea"]
        assert result["preproduction"]["camera"]
        assert result["tool_calls"] == ["llm-gateway.generate"]
        prompt = captured["prompt"]
        for fragment in ("perfil eco", "tendencia x", "competidor y",
                         "idea previa", "noticia z", "brief de prueba"):
            assert fragment in prompt
        assert "system" in captured["kwargs"]

    def test_save_idea_persists_via_rag_service(self, monkeypatch):
        import agente_ideacion.graph as g

        fake = FakeRegistry(response={"id": 77})
        monkeypatch.setattr(g, "REGISTRY", fake)

        state = _ideacion_state(idea="mi idea")
        state["brief"].update({
            "generation_batch_id": "batch-123",
            "generation_index": 0,
        })
        result = g.save_idea(state)

        assert fake.calls[0]["tool"] == "rag"
        assert fake.calls[0]["operation"] == "save_idea"
        assert fake.calls[0]["json_body"] == {
            "brand_id": 1,
            "client_id": 1,
            "content": "mi idea",
            "generation_batch_id": "batch-123",
            "generation_index": 0,
        }
        assert result["idea_id"] == 77


class TestPublicacionNodeContracts:
    def test_load_context_calls_profile_and_trends(self, monkeypatch):
        import agente_publicacion.graph as g

        fake = FakeRegistry()
        monkeypatch.setattr(g, "REGISTRY", fake)

        state = {"idea": "idea para publicar", "client_id": 2, "brand_id": 2, "idea_id": 5}
        result = g.load_context(state)

        pairs = [(c["tool"], c["operation"]) for c in fake.calls]
        assert pairs == [("client", "profile"), ("trends", "search")]
        assert fake.calls[1]["params"] == {"query": "idea para publicar",
                                           "limit": 3}
        assert "trends.search" in result["tool_calls"]

    def test_load_context_discovers_selected_brand_channels(self, monkeypatch):
        import agente_publicacion.graph as g

        fake = FakeRegistry(response={"channels": [
            {"external_id": "ig-1", "provider": "instagram", "display_name": "Marca IG"},
        ]})
        monkeypatch.setattr(g, "REGISTRY", fake)

        result = g.load_context({
            "idea": "idea para publicar", "client_id": 2, "brand_id": 9,
            "postiz_integration_ids": ["ig-1"],
        })

        assert fake.calls[2]["tool"] == "postiz"
        assert fake.calls[2]["operation"] == "channels"
        assert fake.calls[2]["params"] == {
            "brand_id": 9, "integration_ids": ["ig-1"],
        }
        assert result["target_channels"][0]["provider"] == "instagram"

    def test_generate_post_goes_through_gateway(self, monkeypatch):
        import agente_publicacion.graph as g

        captured = {}

        def fake_generate(prompt, **kwargs):
            captured["prompt"] = prompt
            captured["kwargs"] = kwargs
            return {"content": "POST GENERADO", "provider": "p", "model": "m"}

        monkeypatch.setattr(g.gateway_client, "generate", fake_generate)

        state = {
            "idea": "idea eco", "client_id": 2, "idea_id": 5,
            "client_profile": "tono serio", "trends": "tendencia",
            "trending": "#Eco",
        }
        result = g.generate_post(state)

        assert result["publication"] == "POST GENERADO"
        assert result["tool_calls"] == ["llm-gateway.generate"]
        for fragment in ("tono serio", "tendencia", "#Eco", "idea eco"):
            assert fragment in captured["prompt"]
        assert captured["kwargs"]["temperature"] == 0.7

    def test_generate_post_creates_one_variant_per_platform(self, monkeypatch):
        import agente_publicacion.graph as g

        prompts = []

        def fake_generate(prompt, **kwargs):
            prompts.append(prompt)
            return {"content": f"COPY-{len(prompts)}"}

        monkeypatch.setattr(g.gateway_client, "generate", fake_generate)
        state = {
            "idea": "idea de campaña", "client_id": 2, "brand_id": 2,
            "client_profile": "voz de marca", "trends": "tendencias", "trending": "hashtags",
            "target_channels": [
                {"external_id": "ig-1", "provider": "instagram"},
                {"external_id": "ig-2", "provider": "instagram"},
                {"external_id": "li-1", "provider": "linkedin"},
            ],
        }

        result = g.generate_post(state)

        assert len(prompts) == 2
        assert "Target Platform: instagram" in prompts[0]
        assert "Target Platform: linkedin" in prompts[1]
        assert result["publication"] == "COPY-1"
        assert result["publication_variants"] == [
            {"platform": "instagram", "integration_ids": ["ig-1", "ig-2"], "content": "COPY-1"},
            {"platform": "linkedin", "integration_ids": ["li-1"], "content": "COPY-2"},
        ]

    def test_save_post_persists_with_idea_id(self, monkeypatch):
        import agente_publicacion.graph as g

        fake = FakeRegistry(response={"id": 33})
        monkeypatch.setattr(g, "REGISTRY", fake)

        state = {"idea": "idea eco", "client_id": 2, "brand_id": 2, "idea_id": 5,
                 "publication": "mi post"}
        result = g.save_post(state)

        assert fake.calls[0]["json_body"] == {
            "brand_id": 2, "client_id": 2, "content": "mi post", "idea_id": 5,
            "platform": "platform-neutral",
        }
        assert result["publication_id"] == 33

    def test_schedule_post_sends_variant_for_each_integration(self, monkeypatch):
        import agente_publicacion.graph as g

        fake = FakeRegistry(response={"created": True})
        monkeypatch.setattr(g, "REGISTRY", fake)
        state = {
            "brand_id": 2,
            "publication": "Instagram copy",
            "publication_variants": [
                {"platform": "instagram", "integration_ids": ["ig-1"], "content": "IG variant"},
                {"platform": "linkedin", "integration_ids": ["li-1"], "content": "LinkedIn variant"},
            ],
            "target_channels": [
                {"external_id": "ig-1", "provider": "instagram", "configured": True},
                {"external_id": "li-1", "provider": "linkedin", "configured": True},
            ],
            "postiz_integration_ids": ["ig-1", "li-1"],
            "publish_mode": "draft",
            "postiz_settings": {},
        }

        g.schedule_post(state)

        assert fake.calls[0]["json_body"]["contents"] == {
            "ig-1": "IG variant", "li-1": "LinkedIn variant",
        }

    def test_schedule_post_skips_channels_without_postiz_settings(self, monkeypatch):
        import agente_publicacion.graph as g

        fake = FakeRegistry()
        monkeypatch.setattr(g, "REGISTRY", fake)
        result = g.schedule_post({
            "brand_id": 2,
            "publication": "copy",
            "postiz_integration_ids": ["ig-1"],
            "target_channels": [{"external_id": "ig-1", "configured": False}],
            "publish_mode": "draft",
        })

        assert result["postiz"]["status"] == "skipped"
        assert result["postiz"]["integrations"] == ["ig-1"]
        assert fake.calls == []

    def test_schedule_post_reports_external_failure_without_raising(self, monkeypatch):
        import agente_publicacion.graph as g

        class FailingRegistry(FakeRegistry):
            def call(self, *args, **kwargs):
                raise RuntimeError("Postiz unavailable")

        monkeypatch.setattr(g, "REGISTRY", FailingRegistry())
        result = g.schedule_post({
            "brand_id": 2,
            "publication": "LinkedIn copy",
            "publication_variants": [
                {"platform": "linkedin", "integration_ids": ["li-1"], "content": "LinkedIn copy"},
            ],
            "postiz_integration_ids": ["li-1"],
            "target_channels": [{"external_id": "li-1", "configured": True}],
            "publish_mode": "draft",
        })

        assert result["postiz"]["status"] == "failed"
        assert result["postiz"]["error"] == "Postiz unavailable"


# ── U-AG-04/05: semántica idempotente del runner ───────────────
class TestRunAgentTask:
    def _run(self, graph, **kwargs):
        from common.agent_runner import run_agent_task

        defaults = dict(
            agent="ideacion",
            task_id="t-1",
            graph=graph,
            initial_state={"brief": {"content": "x"}, "client_id": 1},
            extract=lambda s: {"idea": s.get("idea", ""),
                               "idea_id": s.get("idea_id", 0)},
            is_done=lambda s: bool(s.get("idea")),
        )
        defaults.update(kwargs)
        return run_agent_task(**defaults)

    def test_fresh_task_invokes_with_initial_state(self):
        graph = FakeGraph()
        out = self._run(graph)

        assert out == {"idea": "generada", "idea_id": 1}
        assert len(graph.invocations) == 1
        assert graph.invocations[0] is not None
        assert graph.configs[0]["configurable"]["thread_id"] == "ideacion:t-1"

    def test_completed_task_short_circuits_without_invoking(self):
        """Reentrega duplicada → NO reejecuta (idempotente)."""
        graph = FakeGraph(values={"idea": "previa", "idea_id": 9})
        out = self._run(graph)

        assert out == {"idea": "previa", "idea_id": 9}
        assert graph.invocations == []  # nada re-ejecutado

    def test_pending_task_resumes_from_checkpoint(self):
        """Caída a mitad → retoma con invoke(None) desde el checkpoint."""
        graph = FakeGraph(values={"idea": "", "idea_id": 0},
                          pending=("save_idea",))
        out = self._run(graph)

        assert out == {"idea": "retomada", "idea_id": 0}
        assert graph.invocations == [None]
        assert graph.configs[0]["configurable"]["thread_id"] == "ideacion:t-1"

    def test_incomplete_checkpoint_still_invokes_new(self):
        """Checkpoint sin resultados finales y sin pendientes → ejecuta."""
        graph = FakeGraph(values={"idea": ""})
        out = self._run(graph)

        assert out["idea"] == "generada"
        assert len(graph.invocations) == 1
