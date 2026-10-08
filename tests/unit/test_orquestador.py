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

        assert decide_next({"idea": "some idea", "publication": ""}) == "dispatch_publicacion"

    def test_route_to_end_when_both_exist(self):
        from multi_agent.supervisor import decide_next

        assert decide_next({"idea": "x", "publication": "y"}) == "__end__"

    def test_route_with_none_values(self):
        """Valores None se tratan como 'no existe'."""
        from multi_agent.supervisor import decide_next

        assert decide_next({"idea": None, "publication": None}) == "dispatch_ideacion"
        assert decide_next({"idea": "x", "publication": None}) == "dispatch_publicacion"


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
            "brief": {"client_id": 1, "content": "campana verano"},
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

    def test_resume_then_dispatch_publicacion(self, graph, config):
        out = graph.invoke(self._initial(), config)
        out2 = graph.invoke(Command(resume={"idea": "IDEA X", "idea_id": 7}), config)
        assert "__interrupt__" in out2
        iv = out2["__interrupt__"][0].value
        assert iv["agent"] == "publicacion"
        assert iv["queue"] == "agent.publicacion.tasks"
        assert iv["payload"]["idea"] == "IDEA X"
        assert iv["payload"]["idea_id"] == 7

    def test_full_cycle_reaches_end(self, graph, config):
        graph.invoke(self._initial(), config)
        graph.invoke(Command(resume={"idea": "IDEA", "idea_id": 7}), config)
        out3 = graph.invoke(Command(resume={"publication": "POST", "publication_id": 9}), config)
        assert "__interrupt__" not in out3
        assert out3["idea_id"] == 7
        assert out3["publication_id"] == 9
        assert "supervisor: pipeline iniciado" in out3["log"]

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

    def test_full_cycle_with_fake_events(self, runtime_parts):
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

        # 2) resultado de ideacion → segundo despacho (publicacion)
        rt.on_agent_completed(
            self._agent_event(task_id, "ideacion", {"idea": "IDEA", "idea_id": 3})
        )
        assert len(published) == 2
        queue2, ev2 = published[1]
        assert queue2 == "agent.publicacion.tasks"
        assert store.get(task_id)["result"]["idea_id"] == 3

        # 3) resultado de publicacion → fin + task.completed
        rt.on_agent_completed(
            self._agent_event(task_id, "publicacion",
                              {"publication": "POST", "publication_id": 8})
        )
        assert len(published) == 3
        queue3, ev3 = published[2]
        assert queue3 == "task.results"
        assert ev3.event_type == "task.completed"

        final = store.get(task_id)
        assert final["status"] == "completed"
        assert final["result"]["idea_id"] == 3
        assert final["result"]["publication_id"] == 8

        # historial: turno user + turno assistant
        roles = [r[2] for r in history]
        assert roles == ["user", "assistant"]

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
        # duplicado: ya no estamos esperando a ideacion → se ignora
        rt.on_agent_completed(
            self._agent_event(task_id, "ideacion", {"idea": "I", "idea_id": 1})
        )
        assert len(published) == 2
        assert store.get(task_id)["status"] == "running"

    def test_result_for_unknown_task_is_ignored(self, runtime_parts):
        rt, _, published, _ = runtime_parts
        rt.start_task({"client_id": 1, "content": "brief"}, 1)
        rt.on_agent_completed(self._agent_event("no-existe", "ideacion", {"idea": "x"}))
        assert len(published) == 1
