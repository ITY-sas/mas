"""
Orquestador multi-agente **stateless** (LangGraph + eventos).

Servicio FastAPI que:

- Expone ``/health``, ``/metrics``, ``/tools`` (catálogo por Tool
  Discovery), ``/graph``, ``/process``, ``/tasks/{id}`` y
  ``/tasks/{id}/history``.
- Consume ``agent.task.completed`` de RabbitMQ y reanuda el grafo
  supervisor con ``Command(resume=...)`` (ciclo checkpointeado en Redis).
- Acepta briefs también por ``ideation_queue`` (ingreso por eventos).

No guarda estado en memoria entre peticiones: Redis (ciclo de
planificación + metadatos) y PostgreSQL (historial de chat).
"""
import logging
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from common.events import AGENT_RESULTS_QUEUE, Event, EventConsumer
from common.gateway_client import health as gateway_health
from common.task_store import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
    TaskStore,
)
from common.tool_client import ToolRegistry

from multi_agent.runtime import OrchestratorRuntime, build_checkpointer

# ── Configuración ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("orchestrator")

app = FastAPI(title="Orquestador Multi-Agente stateless (LangGraph + eventos)")

runtime: OrchestratorRuntime | None = None
registry = ToolRegistry()


# ── Modelos ────────────────────────────────────────────────────
class Brief(BaseModel):
    client_id: int
    brand_id: int | None = None
    content: str
    wait: bool = Field(True, description="Esperar a que el pipeline termine")
    timeout: float = Field(300.0, description="Segundos máximos de espera (si wait=true)")
    publish_mode: Literal["draft", "schedule", "now"] = Field(
        "draft", description="Postiz: guardar borrador, programar o publicar ahora"
    )
    publish_at: str | None = Field(None, description="Fecha UTC ISO 8601 para Postiz")
    postiz_integration_ids: list[str] = Field(default_factory=list)
    postiz_settings: dict[str, dict] = Field(default_factory=dict)
    content_format: Literal["auto", "reel", "post"] = Field(
        "auto", description="Tipo de dossier: auto, reel o post"
    )


class DemoRequest(BaseModel):
    brand_id: int = Field(1, description="Marca demo; 1 es EcoBrand")
    content: str = Field(
        "Crear un Reel para presentar una crema solar natural durante el verano colombiano",
        description="Brief reproducible de la demo",
    )
    content_format: Literal["auto", "reel", "post"] = "reel"
    wait: bool = True
    timeout: float = 300.0


def _get_runtime() -> OrchestratorRuntime:
    if runtime is None:
        raise HTTPException(status_code=503, detail="orquestador aún inicializando")
    return runtime


# ── Endpoints ──────────────────────────────────────────────────
@app.get("/health")
def health():
    """Salud con verificación best-effort de cada subsistema externo."""
    subsystems: dict[str, str] = {}
    try:
        TaskStore().r.ping()
        subsystems["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        subsystems["redis"] = f"down: {exc}"
    subsystems["rabbitmq"] = "ok" if _rabbit_reachable() else "down"
    try:
        import history

        history._connection().close()
        subsystems["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001
        subsystems["postgres"] = f"down: {exc}"
    gw = gateway_health()
    subsystems["llm-gateway"] = "ok" if gw.get("status") == "healthy" else str(gw.get("status"))
    healthy = all(v == "ok" for v in subsystems.values())
    return {
        "status": "healthy" if healthy else "degraded",
        "agent": "orchestrator-stateless",
        "pattern": "supervisor + interrupt/eventos",
        "state": {"checkpoints": "redis", "chat_history": "postgresql"},
        "subsystems": subsystems,
    }


@app.get("/metrics")
def metrics():
    return {
        "agent": "orchestrator",
        "framework": "langgraph",
        "status": "running",
        "pattern": "supervisor",
        "stateless": True,
        "state_layer": ["redis (checkpoints + task store)", "postgresql (chat history)"],
        "agents": ["ideacion", "publicacion"],
        "event_bus": ["agent.task.triggered", "agent.task.completed", "task.completed"],
        "ingress": ["POST /process", "ideation_queue"],
    }


@app.get("/tools")
def tools_info(refresh: bool = False):
    """Catálogo de tools agregado por Tool Discovery (manifiestos REST)."""
    try:
        manifests = registry.discover(refresh=refresh, timeout=1.5)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"discovery falló: {exc}")
    if not manifests:
        raise HTTPException(status_code=503, detail="ningún tool service descubierto")
    return {
        "agent": "orchestrator",
        "framework": "langgraph",
        "discovery": "GET /.well-known/tool-manifest por servicio",
        "tools": registry.catalog(),
    }


@app.get("/graph")
def graph_info():
    return {
        "nodes": ["start", "dispatch_ideacion", "dispatch_publicacion"],
        "edges": [
            "START → start",
            "start → [dispatch_ideacion | dispatch_publicacion | END]",
            "dispatch_ideacion → [dispatch_ideacion | dispatch_publicacion | END]",
            "dispatch_publicacion → [dispatch_ideacion | dispatch_publicacion | END]",
        ],
        "suspension": "interrupt() en cada dispatch → agent.task.triggered / resume con agent.task.completed",
        "checkpointer": "RedisSaver (thread_id = task_id)",
        "agents": {
            "ideacion": "microservicio independiente (agente_ideacion:8000)",
            "publicacion": "microservicio independiente (agente_publicacion:8001)",
        },
    }


@app.post("/process")
def process_brief(brief: Brief):
    """Lanza el pipeline multi-agente.

    - ``wait=true`` (por defecto): bloquea hasta completar/timeout.
    - ``wait=false``: devuelve ``task_id`` al instante (modo asíncrono).
    """
    rt = _get_runtime()
    logger.info("POST /process client_id=%s wait=%s", brief.client_id, brief.wait)
    try:
        task_id = rt.start_task(
            brief={
                "client_id": brief.client_id,
                "brand_id": brief.brand_id or brief.client_id,
                "content": brief.content,
                "content_format": brief.content_format,
                "publication": {
                    "mode": brief.publish_mode,
                    "publish_at": brief.publish_at,
                    "integration_ids": brief.postiz_integration_ids,
                    "settings": brief.postiz_settings,
                },
            },
            client_id=brief.client_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("no se pudo iniciar la tarea")
        raise HTTPException(status_code=503, detail=f"no se pudo iniciar: {exc}")

    if not brief.wait:
        return {"task_id": task_id, "status": STATUS_RUNNING, "mode": "async"}

    try:
        task = rt.store.wait_for_status(
            task_id, (STATUS_COMPLETED, STATUS_FAILED), timeout=brief.timeout
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc))

    if task.get("status") == STATUS_FAILED:
        raise HTTPException(status_code=500, detail=task.get("error") or "tarea fallida")

    result = task.get("result") or {}
    return {
        "task_id": task_id,
        "status": STATUS_COMPLETED,
        "idea": result.get("idea", ""),
        "idea_id": result.get("idea_id", 0),
        "preproduction": result.get("preproduction", {}),
        "publication": result.get("publication", ""),
        "publication_id": result.get("publication_id", 0),
        "postiz": result.get("postiz", {}),
        "agents": task.get("agents", {}),
    }


@app.post("/demo")
def process_demo(demo: DemoRequest):
    """Ruta reproducible para validar una marca, su RAG y el dossier."""
    return process_brief(
        Brief(
            client_id=demo.brand_id,
            brand_id=demo.brand_id,
            content=demo.content,
            content_format=demo.content_format,
            wait=demo.wait,
            timeout=demo.timeout,
        )
    )


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    task = _get_runtime().store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="tarea no encontrada")
    return task


@app.get("/tasks/{task_id}/history")
def get_task_history(task_id: str):
    try:
        import history
    except ImportError:  # pragma: no cover
        raise HTTPException(status_code=501, detail="historial no disponible")
    rows = history.get_history(task_id)
    if not rows:
        raise HTTPException(status_code=404, detail="sin historial para esa tarea")
    return {"task_id": task_id, "messages": rows}


# ── Utilidades de conexión ─────────────────────────────────────
def _rabbit_reachable() -> bool:
    try:
        import pika

        params = __import__("common.events", fromlist=["default_rabbit_params"]).default_rabbit_params()
        conn = pika.BlockingConnection(params)
        conn.close()
        return True
    except Exception:  # noqa: BLE001
        return False


# ── Consumidores ───────────────────────────────────────────────
def _ingress_handler(event: Event) -> None:
    """Brief recibido por ideation_queue → arranca una tarea."""
    payload = event.payload or {}
    if event.event_type == "raw":
        data = payload
    else:
        data = payload.get("brief") or payload
    client_id = data.get("client_id")
    content = data.get("content")
    if client_id is None or not content:
        logger.warning("brief inválido en ideation_queue: %s", data)
        return
    try:
        rt = _get_runtime()
    except HTTPException:
        logger.warning("brief recibido antes de inicializar; se descarta")
        return
    rt.start_task(
        brief={"client_id": int(client_id), "content": content},
        client_id=int(client_id),
    )


# ── Arranque ───────────────────────────────────────────────────
def _retry(desc: str, fn, attempts: int = 10, delay: float = 3.0):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last = exc
            logger.warning("%s no disponible (%s). Reintento %d/%d …", desc, exc, i + 1, attempts)
            time.sleep(delay)
    raise RuntimeError(f"{desc} inaccesible tras {attempts} intentos: {last}")


@app.on_event("startup")
async def startup_event():
    global runtime

    # 1) Historial de chat (PostgreSQL)
    def _history():
        import history

        history.init_history_table()

    _retry("PostgreSQL", _history, attempts=10, delay=3)

    # 2) Checkpoints del ciclo de planificación (Redis)
    checkpointer = _retry("Redis (checkpoints)", build_checkpointer, attempts=10, delay=3)

    # 3) Runtime stateless
    runtime = OrchestratorRuntime(checkpointer=checkpointer)
    runtime.start_consumers()

    # 4) Recuperación de tareas pendientes (antes de la caída)
    runtime.recover_running_tasks()

    # 5) Ingreso de briefs por eventos (compatibilidad)
    EventConsumer("ideation_queue", _ingress_handler, name="ideation-ingress").start()

    # 6) Tool Discovery (best-effort, no bloquea el arranque)
    try:
        registry.discover(timeout=1.5)
        logger.info("Tool Discovery: %d servicios descubiertos", len(registry.manifests))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tool Discovery al arrancar: %s", exc)

    logger.info(
        "Orquestador STATELESS listo — supervisor LangGraph, estado en Redis, "
        "historial en PostgreSQL, agentes vía eventos"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8002")))
