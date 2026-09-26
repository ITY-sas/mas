"""
Supervisor / Orquestador — LangGraph multi-agent coordinator.

Patrón supervisor:
  START → route → [ideacion | publicacion | END]
   ↑______________________________↓

El supervisor lee el estado global y decide qué agente ejecutar a continuación.
Cada agente es un subgrafo compilado que se añade como nodo.
"""
import logging

from langgraph.graph import END, START, StateGraph

from .ideacion import create_ideacion_graph
from .publicacion import create_publicacion_graph
from .state import SupervisorState

logger = logging.getLogger("supervisor")


# ── Función de enrutamiento ────────────────────────────────────
def decide_next(state: SupervisorState) -> str:
    """Decide qué agente ejecutar a continuación basándose en el estado global.

    - Si no hay idea todavía → agente de ideación.
    - Si hay idea pero no publicación → agente de publicación.
    - Si ambos existen → END (pipeline completo).
    """
    if not state.get("idea"):
        logger.info("[supervisor] → Enrutando a AGENTE DE IDEACIÓN")
        return "ideacion_agent"
    if not state.get("publication"):
        logger.info("[supervisor] → Enrutando a AGENTE DE PUBLICACIÓN")
        return "publicacion_agent"
    logger.info("[supervisor] → Pipeline completo. END")
    return END


# ── Nodo de arranque (para log) ────────────────────────────────
def start(state: SupervisorState) -> dict:
    logger.info(
        "[supervisor] Iniciando pipeline para client_id=%s brief=%r",
        state.get("client_id"),
        (state.get("brief") or {}).get("content", "")[:80],
    )
    return {"log": ["supervisor: pipeline iniciado"]}


# ── Construcción del grafo ─────────────────────────────────────
def create_orchestrator():
    """Compila el grafo supervisor que coordina ambos agentes LangGraph."""
    # Subgrafos compilados (cada uno es un StateGraph propio)
    ideacion_graph = create_ideacion_graph()
    publicacion_graph = create_publicacion_graph()

    builder = StateGraph(SupervisorState)

    # Nodo de arranque
    builder.add_node("start", start)

    # Los agentes se añaden como nodos (subgrafos compilados)
    builder.add_node("ideacion_agent", ideacion_graph)
    builder.add_node("publicacion_agent", publicacion_graph)

    # Arista inicial: START → start
    builder.add_edge(START, "start")

    # Aristas condicionales desde start y desde cada agente
    # (tras cada agente volvemos a evaluar el estado)
    possible_next = ["ideacion_agent", "publicacion_agent", END]
    builder.add_conditional_edges("start", decide_next, possible_next)
    builder.add_conditional_edges("ideacion_agent", decide_next, possible_next)
    builder.add_conditional_edges("publicacion_agent", decide_next, possible_next)

    return builder.compile()


# ── Ejecución directa (helper) ─────────────────────────────────
def run_pipeline(brief: dict, client_id: int) -> dict:
    """Ejecuta el pipeline completo devolviendo el estado final."""
    graph = create_orchestrator()
    initial: SupervisorState = {
        "brief": brief,
        "client_id": client_id,
        "idea": "",
        "idea_id": 0,
        "publication": "",
        "publication_id": 0,
        "log": [],
    }
    final_state = graph.invoke(initial)
    return final_state
