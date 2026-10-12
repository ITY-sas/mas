"""
Supervisor / Orquestador — LangGraph **stateless** (patrón supervisor).

    START → decide → [dispatch_ideacion | dispatch_publicacion | END]
       ↑___________________________________________________________↓

Los agentes NO son subgrafos en memoria: son **microservicios
independientes**. Cada nodo ``dispatch_*`` suspende el grafo con
``interrupt()``; el runtime (:mod:`.runtime`) publica
``agent.task.triggered`` en RabbitMQ y, al recibir ``agent.task.completed``,
reanuda el grafo con ``Command(resume=...)``.

Así el ciclo de planificación (re planificar → despachar → esperar →
re planificar) queda checkpointeado en **Redis**: el proceso no guarda nada
entre peticiones (recuperación ante caídas y escalado horizontal).
"""
import logging
from typing import Optional

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from common.events import AGENT_QUEUES

from .state import SupervisorState

logger = logging.getLogger("supervisor")


# ── Función de enrutamiento ────────────────────────────────────
def decide_next(state: SupervisorState) -> str:
    """Route generation and explicitly requested publication as separate flows."""
    workflow = (state.get("brief") or {}).get("workflow", "generate_idea")
    if workflow == "deliver_publication":
        if not state.get("publication_dispatched"):
            logger.info("[supervisor] → entrega aprobada a Postiz")
            return "dispatch_publicacion"
        return END
    if workflow in {"publish_idea", "prepare_publication"}:
        if not state.get("publication"):
            logger.info("[supervisor] → preparar copy para idea seleccionada")
            return "dispatch_publicacion"
        return END
    if not state.get("idea"):
        logger.info("[supervisor] → despachar AGENTE DE IDEACIÓN")
        return "dispatch_ideacion"
    logger.info("[supervisor] → dossier persistido; publicación manual pendiente")
    return END


# ── Nodo de arranque ───────────────────────────────────────────
def start(state: SupervisorState) -> dict:
    logger.info(
        "[supervisor] pipeline iniciado client_id=%s brief=%r",
        state.get("client_id"),
        (state.get("brief") or {}).get("content", "")[:80],
    )
    return {"log": ["supervisor: pipeline iniciado"]}


# ── Nodos de despacho (suspensión → eventos → reanudación) ─────
def _resume_value(result: object, agent: str) -> dict:
    """Valida el resultado devuelto por el agente (Command resume)."""
    if not isinstance(result, dict):
        raise RuntimeError(f"resultado inválido del agente '{agent}': {result!r}")
    if result.get("status") == "failed":
        raise RuntimeError(
            f"agente '{agent}' falló: {result.get('error') or 'error desconocido'}"
        )
    return result


def dispatch_ideacion(state: SupervisorState) -> dict:
    """Suspende el grafo esperando al microservicio de ideación.

    La publicación del evento ``agent.task.triggered`` la hace el runtime
    FUERA del grafo (aquí no hay efectos secundarios: el nodo se ejecuta
    dos veces, al suspendérs y al reanudarse).
    """
    result = interrupt(
        {
            "agent": "ideacion",
            "queue": AGENT_QUEUES["ideacion"],
            "payload": {
                "brief": state["brief"],
                "client_id": state["client_id"],
                "brand_id": state["brand_id"],
            },
        }
    )
    data = _resume_value(result, "ideacion")
    idea = data.get("idea", "") or ""
    idea_id = data.get("idea_id", 0) or 0
    logger.info("[supervisor] ideación completada idea_id=%s", idea_id)
    return {
        "idea": idea,
        "idea_id": idea_id,
        "preproduction": data.get("preproduction", {}),
        "log": [f"ideacion: completado (idea_id={idea_id})"],
    }


def dispatch_publicacion(state: SupervisorState) -> dict:
    """Suspende el grafo esperando al microservicio de publicación."""
    result = interrupt(
        {
            "agent": "publicacion",
            "queue": AGENT_QUEUES["publicacion"],
            "payload": {
                "idea": state["idea"],
                "client_id": state["client_id"],
                "brand_id": state["brand_id"],
                "idea_id": state["idea_id"],
                "preproduction": state.get("preproduction", {}),
                "publication": state.get("brief", {}).get("publication", {}),
                "publication_action": state.get("brief", {}).get("publication_action", "prepare"),
                "publication_variants": state.get("publication_variants", []),
                "publication_id": state.get("publication_id", 0),
                "prepared_publication": state.get("brief", {}).get("prepared_publication", ""),
                "target_channels": state.get("brief", {}).get("target_channels", []),
            },
        }
    )
    data = _resume_value(result, "publicacion")
    publication = data.get("publication", "") or ""
    publication_id = data.get("publication_id", 0) or 0
    logger.info("[supervisor] publicación completada publication_id=%s", publication_id)
    return {
        "publication": publication,
        "publication_id": publication_id,
        "publication_variants": data.get("publication_variants", []),
        "publication_dispatched": True,
        "postiz": data.get("postiz", {}),
        "log": [f"publicacion: completado (publication_id={publication_id})"],
    }


# ── Construcción del grafo ─────────────────────────────────────
def create_orchestrator(checkpointer: Optional[object] = None):
    """Compila el grafo supervisor.

    ``checkpointer`` debe ser un checkpointer externo (``RedisSaver``):
    es lo que permite que el orquestador sea stateless. Sin checkpointer
    ``interrupt()`` no funciona, así que se exige en producción.
    """
    builder = StateGraph(SupervisorState)

    builder.add_node("start", start)
    builder.add_node("dispatch_ideacion", dispatch_ideacion)
    builder.add_node("dispatch_publicacion", dispatch_publicacion)

    builder.add_edge(START, "start")

    possible_next = ["dispatch_ideacion", "dispatch_publicacion", END]
    builder.add_conditional_edges("start", decide_next, possible_next)
    builder.add_conditional_edges("dispatch_ideacion", decide_next, possible_next)
    builder.add_conditional_edges("dispatch_publicacion", decide_next, possible_next)

    return builder.compile(checkpointer=checkpointer)
