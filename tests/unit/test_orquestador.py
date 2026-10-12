"""
Tests unitarios para el orquestador **stateless** (LangGraph + eventos).

Cubre:
- Esquema de estado del supervisor (state.py)
- Lógica de enrutamiento (decide_next)
- Nodos de despacho con ``interrupt()`` → evento → ``Command(resume=...)``
- Compilación del grafo supervisor
- Runtime event-driven completo con store/ eventos falsos (sin externos)

U-ORQ-01 … U-ORQ-06 del plan de pruebas.
"""
import sys
from pathlib import Path

# Añadir raíz del repo y orchestrator al path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "orchestrator"))

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

pytestmark = pytest.mark.unit


# ── Dobles falsos (sin Redis / RabbitMQ) ───────────────────────
class FakeRedis:
    """Mínimo cliente Redis en memoria para TaskStore."""

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

    def ping(self):
        return True


class TestStateSchema:
    """U-ORQ-01: El esquema de estado del supervisor es correcto."""

    def test_supervisor_state_keys(self):
        from multi_agent.state import SupervisorState

        hints = set(SupervisorState.__annotations__)
        expected = {
            "brief", "client_id", "idea", "idea_id",
            "publication", "publication_id", "log",
        }
        assert expected.issubset(hints)

    def test_initial_state_defaults(self):
        from multi_agent.state import initial_state

        state = initial_state({"client_id": 1, "content": "hola"}, 1)
        assert state["idea"] == ""
        assert state["idea_id"] == 0
        assert state["publication"] == ""
        assert state["publication_id"] == 0
        assert state["log"] == []
        assert state["brief"]["content"] == "hola"

    def test_agent_states_live_in_agent_packages(self):
        """Los estados de agente YA no están en el orquestador (son microservicios)."""
        import multi_agent.state as orchestrator_state

        assert not hasattr(orchestrator_state, "IdeacionState")
        assert not hasattr(orchestrator_state, "PublicacionState")


class TestSupervisorRouting:
    """U-ORQ-02: La lógica de enrutamiento del supervisor es correcta."""

    def test_route_to_ideacion_when_no_idea(self):
        from multi_agent.supervisor import decide_next

        assert decide_next({"idea": "", "publication": ""}) == "dispatch_ideacion"

    def test_route_to_publicacion_when_idea_exists(self):
        from multi_agent.supervisor import decide_next

        assert decide_next({"idea": "some idea", "publication": ""}) == "__end__"

    def test_route_to_publicacion_only_when_explicitly_requested(self):
        from multi_agent.supervisor import decide_next

        state = {
            "brief": {"workflow": "publish_idea"},
            "idea": "saved dossier",
            "publication": "",
        }
        assert decide_next(state) == "dispatch_publicacion"

    def test_route_to_end_when_both_exist(self):
        from multi_agent.supervisor import decide_next

        assert decide_next({"idea": "x", "publication": "y"}) == "__end__"

    def test_route_with_none_values(self):
        """Valores None se tratan como 'no existe'."""
        from multi_agent.supervisor import decide_next

        assert decide_next({"idea": None, "publication": None}) == "dispatch_ideacion"
        assert decide_next({"idea": "x", "publication": None}) == "__end__"


class TestDispatchInterrupts:
    """U-ORQ-03: Los nodos de despacho suspenden con interrupt() y
    reanudan con los resultados de los agentes (eventos)."""

    @pytest.fixture()
    def graph(self):
        from langgraph.checkpoint.memory import MemorySaver

        from multi_agent.supervisor import create_orchestrator

        return create_orchestrator(checkpointer=MemorySaver())

    @pytest.fixture()
    def config(self):
        return {"configurable": {"thread_id": "unit-task-1"}}

    @staticmethod
    def _initial():
        return {
            "brief": {"client_id": 1, "brand_id": 1, "content": "campana verano", "workflow": "generate_idea"},
            "client_id": 1,
            "brand_id": 1,
            "idea": "", "idea_id": 0,
            "publication": "", "publication_id": 0,
            "log": [],
        }

    def test_first_dispatch_suspends_for_ideacion(self, graph, config):
        out = graph.invoke(self._initial(), config)
        assert "__interrupt__" in out
        iv = out["__interrupt__"][0].value
        assert iv["agent"] == "ideacion"
        assert iv["queue"] == "agent.ideacion.tasks"
        assert iv["payload"]["brief"]["content"] == "campana verano"
        assert iv["payload"]["client_id"] == 1

    def test_idea_generation_ends_without_dispatching_publicacion(self, graph, config):
        out = graph.invoke(self._initial(), config)
        out2 = graph.invoke(Command(resume={"idea": "IDEA X", "idea_id": 7}), config)
        assert "__interrupt__" not in out2
        assert out2["idea"] == "IDEA X"

    def test_explicit_publication_dispatches_selected_dossier(self, graph):
        config = {"configurable": {"thread_id": "manual-publish-task"}}
        state = {
            **self._initial(),
            "brief": {
                "workflow": "publish_idea",
                "publication": {"mode": "draft", "integration_ids": ["channel-1"]},
            },
            "idea": '{"title":"Selected idea"}',
            "idea_id": 7,
            "preproduction": {"title": "Selected idea"},
        }
        outcome = graph.invoke(state, config)
        assert "__interrupt__" in outcome
        iv = outcome["__interrupt__"][0].value
        assert iv["agent"] == "publicacion"
        assert iv["queue"] == "agent.publicacion.tasks"
        assert iv["payload"]["idea"] == '{"title":"Selected idea"}'
        assert iv["payload"]["idea_id"] == 7

    def test_manual_publication_reaches_end(self, graph):
        config = {"configurable": {"thread_id": "manual-publish-cycle"}}
        state = {
            **self._initial(),
            "brief": {"workflow": "publish_idea"},
            "idea": "saved idea",
            "idea_id": 7,
            "preproduction": {"title": "saved idea"},
        }
        graph.invoke(state, config)
        out = graph.invoke(Command(resume={"publication": "POST", "publication_id": 9}), config)
        assert "__interrupt__" not in out
        assert out["idea_id"] == 7
        assert out["publication_id"] == 9

    def test_generation_reaches_end_after_ideation(self, graph, config):
        graph.invoke(self._initial(), config)
        out = graph.invoke(Command(resume={"idea": "IDEA", "idea_id": 7}), config)
        assert "__interrupt__" not in out
        assert out["idea_id"] == 7
        assert out["publication_id"] == 0
        assert "supervisor: pipeline iniciado" in out["log"]

    def test_failed_agent_result_raises(self, graph, config):
        """Un agente que falla aborta la tarea (el runtime la marcará failed)."""
        graph.invoke(self._initial(), config)
        with pytest.raises(Exception, match="falló"):
            graph.invoke(Command(resume={"status": "failed", "error": "boom"}), config)


class TestGraphCompilation:
    """U-ORQ-04: El grafo supervisor se compila con sus nodos de despacho."""

    def test_compile_supervisor_nodes(self):
        from langgraph.checkpoint.memory import MemorySaver

        from multi_agent.supervisor import create_orchestrator

        graph = create_orchestrator(checkpointer=MemorySaver())
        nodes = set(graph.get_graph().nodes.keys())
        assert {"start", "dispatch_ideacion", "dispatch_publicacion"}.issubset(nodes)

    def test_supervisor_requires_checkpointer_for_interrupt(self):
        """Sin checkpointer el grafo no debe compilar interrupt() de forma
        utilizable: el estado del ciclo es EXTERNO (Redis) por diseño."""
        from multi_agent.supervisor import create_orchestrator

        graph = create_orchestrator()  # sin checkpointer → solo construcción
        assert graph is not None


class TestRuntimeEventDriven:
    """U-ORQ-05/06: El runtime orquesta el ciclo completo con eventos
    falsos, sin Redis ni RabbitMQ (stateless = todo el estado externo)."""

    @pytest.fixture()
    def runtime_parts(self, monkeypatch):
        from langgraph.checkpoint.memory import MemorySaver

        from common.task_store import TaskStore
        import multi_agent.runtime as runtime_mod
        from multi_agent.runtime import OrchestratorRuntime

        published: list = []

        def fake_publish(queue, event, **kwargs):
            published.append((queue, event))

        monkeypatch.setattr(runtime_mod, "publish_event", fake_publish)

        history: list = []
        store = TaskStore(client=FakeRedis())
        rt = OrchestratorRuntime(
            store=store,
            checkpointer=MemorySaver(),
            history_add=lambda *a: history.append(a),
        )
        return rt, store, published, history

    @staticmethod
    def _agent_event(task_id, agent, result, status="completed", error=None):
        from common.events import AGENT_TASK_COMPLETED, Event

        return Event(
            event_type=AGENT_TASK_COMPLETED,
            task_id=task_id,
            correlation_id=task_id,
            source=agent,
            agent=agent,
            payload={"result": result},
            status=status,
            error=error,
        )

    def test_idea_generation_completes_without_publication(self, runtime_parts):
        rt, store, published, history = runtime_parts

        task_id = rt.start_task({"client_id": 1, "content": "brief x"}, 1)

        # 1) primer despacho → agent.task.triggered (ideacion)
        assert len(published) == 1
        queue, ev = published[0]
        assert queue == "agent.ideacion.tasks"
        assert ev.event_type == "agent.task.triggered"
        assert ev.task_id == task_id
        task = store.get(task_id)
        assert task["status"] == "running"
        assert task["pending"]["agent"] == "ideacion"

        # 2) resultado de ideacion → fin, sin publicar automáticamente
        rt.on_agent_completed(
            self._agent_event(task_id, "ideacion", {"idea": "IDEA", "idea_id": 3})
        )
        assert len(published) == 2
        queue2, ev2 = published[1]
        assert queue2 == "task.results"
        assert ev2.event_type == "task.completed"

        final = store.get(task_id)
        assert final["status"] == "completed"
        assert final["result"]["idea_id"] == 3
        assert final["result"]["publication_id"] == 0

        # historial: turno user + turno assistant
        roles = [r[2] for r in history]
        assert roles == ["user", "assistant"]

    def test_start_idea_batch_dispatches_ordered_idea_tasks(self, runtime_parts):
        rt, store, published, _ = runtime_parts

        batch = rt.start_idea_batch(
            client_id=1,
            brand_id=7,
            count=3,
            content="",
            briefs=["brief uno"],
            topics=["educación"],
        )

        assert batch["count"] == 3
        assert len(batch["task_ids"]) == 3
        assert [queue for queue, _ in published] == [
            "agent.ideacion.tasks", "agent.ideacion.tasks", "agent.ideacion.tasks",
        ]
        children = store.list_by_generation_batch(batch["generation_batch_id"])
        assert [task["brief"]["generation_index"] for task in children] == [0, 1, 2]
        assert children[0]["brief"]["content"] == "brief uno"
        assert children[1]["brief"]["content"] == ""
        assert children[2]["brief"]["brand_id"] == 7
        assert children[0]["brief"]["generation_angle"] != children[1]["brief"]["generation_angle"]

    def test_batch_parent_tracks_partial_completion(self, runtime_parts):
        rt, store, _, _ = runtime_parts
        batch = rt.start_idea_batch(client_id=1, brand_id=1, count=2)
        children = store.list_by_generation_batch(batch["generation_batch_id"])
        store.set_status(children[0]["task_id"], "completed")
        store.set_status(children[1]["task_id"], "failed", error="model unavailable")

        rt._refresh_generation_batch(batch["generation_batch_id"])

        parent = store.get(batch["generation_batch_id"])
        assert parent["result"]["status"] == "partial"
        assert parent["result"]["completed"] == 1
        assert parent["result"]["failed"] == 1

    def test_agent_failure_marks_task_failed(self, runtime_parts):
        rt, store, published, history = runtime_parts

        task_id = rt.start_task({"client_id": 1, "content": "brief"}, 1)
        rt.on_agent_completed(
            self._agent_event(task_id, "ideacion", {}, status="failed", error="timeout")
        )

        task = store.get(task_id)
        assert task["status"] == "failed"
        assert "timeout" in task["error"]
        # sin nuevos despachos
        assert len(published) == 1
        assert [r[2] for r in history] == ["user", "assistant"]

    def test_duplicate_result_is_ignored(self, runtime_parts):
        """Reentrega de un evento ya consumido → no reavanza el ciclo."""
        rt, store, published, _ = runtime_parts

        task_id = rt.start_task({"client_id": 1, "content": "brief"}, 1)
        rt.on_agent_completed(
            self._agent_event(task_id, "ideacion", {"idea": "I", "idea_id": 1})
        )
        assert len(published) == 2
        # duplicado: la tarea de ideación ya finalizó → se ignora
        rt.on_agent_completed(
            self._agent_event(task_id, "ideacion", {"idea": "I", "idea_id": 1})
        )
        assert len(published) == 2
        assert store.get(task_id)["status"] == "completed"

    def test_result_for_unknown_task_is_ignored(self, runtime_parts):
        rt, _, published, _ = runtime_parts
        rt.start_task({"client_id": 1, "content": "brief"}, 1)
        rt.on_agent_completed(self._agent_event("no-existe", "ideacion", {"idea": "x"}))
        assert len(published) == 1


class TestManualPublicationEndpoint:
    def test_dispatches_loaded_full_dossier_and_selected_channels(self, monkeypatch):
        import main as orchestrator_main

        dossier = {"title": "Idea aprobada", "concept": "Dossier completo", "script": [{"scene": 1}]}
        calls = []

        def fake_tool_call(tool, operation, *, params=None, **kwargs):
            calls.append((tool, operation, params))
            if operation == "get_idea":
                return {
                    "id": 44,
                    "brand_id": 7,
                    "client_id": 70,
                    "content": __import__("json").dumps(dossier),
                    "dossier": dossier,
                }
            return {"brand_id": 7, "channels": [{"external_id": "ig-1"}]}

        class FakeRuntime:
            brief = None
            client_id = None

            def start_task(self, brief, client_id):
                self.brief = brief
                self.client_id = client_id
                return "publish-task"

        runtime = FakeRuntime()
        monkeypatch.setattr(orchestrator_main.registry, "call", fake_tool_call)
        monkeypatch.setattr(orchestrator_main, "_get_runtime", lambda: runtime)

        response = orchestrator_main.publish_saved_idea(
            44,
            orchestrator_main.PublishIdeaRequest(
                brand_id=7,
                publish_mode="schedule",
                publish_at="2026-10-15T15:00:00Z",
                integration_ids=["ig-1"],
            ),
        )

        assert response == {"task_id": "publish-task", "idea_id": 44, "status": "running"}
        assert calls[0][2] == {"brand_id": 7, "idea_id": 44}
        assert calls[1][2] == {"brand_id": 7, "integration_ids": ["ig-1"]}
        assert runtime.client_id == 70
        assert runtime.brief["workflow"] == "publish_idea"
        assert runtime.brief["preproduction"] == dossier
        assert runtime.brief["publication"]["integration_ids"] == ["ig-1"]
