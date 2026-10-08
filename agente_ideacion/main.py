"""
Agente de Ideación — microservicio independiente (event-driven + LangGraph).

- Consume ``agent.task.triggered`` (RabbitMQ) y responde con
  ``agent.task.completed`` en ``agent.results``.
- Ejecuta su propio grafo LangGraph cuyo estado se checkpointea en
  **Redis** (``{agente}:{task_id}``) → retoma tras caída y deduplica
  reentregas (idempotente).
- Tools vía contratos REST (Tool Discovery) y LLM vía LLM Gateway:
  el agente NO importa ``shared_tools`` (no ejecuta negocio directo).
"""
from __future__ import annotations

import logging
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, HTTPException

from common.agent_runner import run_agent_task
from common.events import (
    AGENT_QUEUES,
    AGENT_RESULTS_QUEUE,
    AGENT_TASK_COMPLETED,
    Event,
    EventConsumer,
    publish_event,
)
from common.tool_client import ToolRegistry

from .graph import create_ideacion_graph

SERVICE = "agente-ideacion"
AGENT = "ideacion"
QUEUE = AGENT_QUEUES[AGENT]
PORT = int(os.getenv("PORT", "8000"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(SERVICE)

app = FastAPI(title="Agente de Ideación (microservicio)")
registry = ToolRegistry()
GRAPH = None


# ── Endpoints ──────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "agent": AGENT,
        "service": SERVICE,
        "queue": QUEUE,
        "framework": "langgraph",
        "state": "redis-checkpoint",
    }


@app.get("/metrics")
def metrics():
    return {
        "agent": AGENT,
        "status": "running",
        "queue_in": QUEUE,
        "queue_out": AGENT_RESULTS_QUEUE,
        "state": "redis (thread_id=ideacion:{task_id})",
        "event_in": "agent.task.triggered",
        "event_out": "agent.task.completed",
        "tools": sorted(registry.manifests.keys()),
    }


@app.get("/tools")
def tools_info():
    """Tools descubiertas por este agente (manifiestos → endpoints)."""
    return {
        "agent": AGENT,
        "discovery": "GET /.well-known/tool-manifest por servicio",
        "tools": registry.catalog(),
    }


@app.get("/state/{task_id}")
def task_state(task_id: str):
    """Checkpoint del ciclo del agente en Redis (estado externo)."""
    if GRAPH is None:
        raise HTTPException(status_code=503, detail="grafo no inicializado")
    snap = GRAPH.get_state({"configurable": {"thread_id": f"{AGENT}:{task_id}"}})
    if snap is None or not snap.values:
        raise HTTPException(status_code=404, detail="sin estado para esa tarea")
    return {
        "task_id": task_id,
        "thread_id": f"{AGENT}:{task_id}",
        "pending_nodes": list(snap.next or ()),
        "values": snap.values,
    }


# ── Procesamiento de agent.task.triggered ──────────────────────
def handle_triggered(event: Event) -> None:
    task_id = event.task_id
    if not task_id:
        logger.warning("evento sin task_id: %s", event.event_type)
        return
    correlation_id = event.correlation_id or task_id
    payload = event.payload or {}
    brief = payload.get("brief") or {}
    client_id = payload.get("client_id", brief.get("client_id"))
    started = time.perf_counter()
    status, result, error = "completed", {}, None

    logger.info("━" * 60)
    logger.info("agent.task.triggered [%s] task=%s client_id=%s", AGENT, task_id, client_id)

    if GRAPH is None:
        status, error = "failed", "grafo no inicializado"
    elif not brief.get("content") or client_id is None:
        status, error = "failed", f"payload inválido: {payload}"
    else:
        try:
            result = run_agent_task(
                agent=AGENT,
                task_id=task_id,
                graph=GRAPH,
                initial_state={
                    "brief": brief,
                    "client_id": int(client_id),
                    "tool_calls": [],
                },
                extract=lambda s: {
                    "idea": s.get("idea", ""),
                    "idea_id": s.get("idea_id", 0),
                    "preproduction": s.get("preproduction", {}),
                },
                is_done=lambda s: bool(s.get("idea")),
            )
            logger.info("idea_id=%s → agent.task.completed", result.get("idea_id"))
        except Exception as exc:  # noqa: BLE001
            logger.exception("ejecución fallida")
            status, result, error = "failed", {}, str(exc)

    publish_event(
        AGENT_RESULTS_QUEUE,
        Event(
            event_type=AGENT_TASK_COMPLETED,
            task_id=task_id,
            correlation_id=correlation_id,
            source=AGENT,
            agent=AGENT,
            payload={"result": result},
            status=status,
            error=error,
            duration_ms=int((time.perf_counter() - started) * 1000),
        ),
    )
    logger.info("fin tarea %s (%s, %d ms)", task_id, status,
                (time.perf_counter() - started) * 1000)
    logger.info("━" * 60)


# ── Arranque ───────────────────────────────────────────────────
def _retry(desc: str, fn, attempts: int = 10, delay: float = 3.0):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last = exc
            logger.warning("%s no disponible (%s). Reintento %d/%d …",
                           desc, exc, i + 1, attempts)
            time.sleep(delay)
    raise RuntimeError(f"{desc} inaccesible: {last}")


def _build_graph():
    from langgraph.checkpoint.redis import RedisSaver

    saver = RedisSaver(os.getenv("REDIS_URL", "redis://localhost:6379"))
    saver.setup()
    return create_ideacion_graph(checkpointer=saver)


@app.on_event("startup")
async def startup_event():
    global GRAPH
    GRAPH = _retry("Redis (checkpoints)", _build_graph)
    # auto_ack=False → si el proceso cae a mitad, RabbitMQ reentrega el
    # evento y el grafo se retoma desde el checkpoint (idempotente).
    EventConsumer(QUEUE, handle_triggered, auto_ack=False, name=AGENT).start()
    try:
        registry.discover(timeout=1.5)
        logger.info("Tool Discovery: %s", sorted(registry.manifests.keys()))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tool Discovery al arrancar: %s", exc)
    logger.info("Agente de Ideación listo — escuchando '%s'", QUEUE)
