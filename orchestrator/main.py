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
import json

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
    content: str = ""
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


class IdeaBatchRequest(BaseModel):
    client_id: int
    brand_id: int | None = None
    count: int = Field(5, ge=1, le=5)
    content: str = ""
    briefs: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    content_format: Literal["auto", "reel", "post"] = "auto"


class PublishIdeaRequest(BaseModel):
    brand_id: int
    publish_mode: Literal["draft", "schedule", "now"] = "draft"
    publish_at: str | None = None
    integration_ids: list[str] = Field(min_length=1)
    settings: dict[str, dict] = Field(default_factory=dict)


class DeliverPreparedPublicationRequest(PublishIdeaRequest):
    publication_variants: list[dict] = Field(default_factory=list)


class ApprovePreparedPublicationRequest(BaseModel):
    brand_id: int
    publication_variants: list[dict] = Field(..., min_length=1)


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
        "ingress": ["POST /ideas/generate", "POST /ideas/{id}/publish", "POST /process"],
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
            "start → dispatch_ideacion (generate_idea) | dispatch_publicacion (publish_idea)",
            "dispatch_ideacion → END (no automatic publication)",
            "dispatch_publicacion → END",
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
    """Genera y persiste una idea; publicar requiere /ideas/{id}/publish.

    - ``wait=true`` (por defecto): bloquea hasta completar/timeout.
    - ``wait=false``: devuelve ``task_id`` al instante (modo asíncrono).
    """
    rt = _get_runtime()
    logger.info("POST /process client_id=%s wait=%s", brief.client_id, brief.wait)
    try:
        task_id = rt.start_task(
            brief={
                "workflow": "generate_idea",
                "client_id": brief.client_id,
                "brand_id": brief.brand_id or brief.client_id,
                "content": brief.content,
                "content_format": brief.content_format,
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
        "publication_variants": result.get("publication_variants", []),
        "postiz": result.get("postiz", {}),
        "agents": task.get("agents", {}),
    }


@app.post("/ideas/generate")
def generate_ideas(request: IdeaBatchRequest):
    """Dispatch a bounded, asynchronous batch without invoking publication."""
    if len(request.briefs) > request.count:
        raise HTTPException(status_code=422, detail="briefs no puede superar count")
    rt = _get_runtime()
    try:
        return rt.start_idea_batch(
            client_id=request.client_id,
            brand_id=request.brand_id or request.client_id,
            count=request.count,
            content=request.content,
            briefs=request.briefs,
            topics=request.topics,
            content_format=request.content_format,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("no se pudo iniciar el lote de ideas")
        raise HTTPException(status_code=503, detail=f"no se pudo iniciar el lote: {exc}") from exc


@app.get("/ideas/batches/{batch_id}")
def get_idea_batch(batch_id: str, brand_id: int):
    """Return progress and completed child results for a brand-owned batch."""
    rt = _get_runtime()
    batch = rt.store.get(batch_id)
    if not batch or not (batch.get("brief") or {}).get("generation_batch_root"):
        raise HTTPException(status_code=404, detail="lote no encontrado")
    if (batch.get("brief") or {}).get("brand_id") != brand_id:
        raise HTTPException(status_code=404, detail="lote no encontrado")

    children = rt.store.list_by_generation_batch(batch_id)
    results = []
    for task in children:
        result = task.get("result") or {}
        dossier = result.get("preproduction") or {}
        results.append({
            "task_id": task.get("task_id"),
            "status": task.get("status"),
            "error": task.get("error"),
            "generation_index": (task.get("brief") or {}).get("generation_index"),
            "idea_id": result.get("idea_id"),
            "title": dossier.get("title"),
            "dossier": dossier,
        })
    summary = batch.get("result") or {}
    return {
        "generation_batch_id": batch_id,
        "brand_id": brand_id,
        "status": summary.get("status", batch.get("status", "running")),
        "total": summary.get("total", (batch.get("brief") or {}).get("generation_count", 0)),
        "completed": summary.get("completed", 0),
        "failed": summary.get("failed", 0),
        "ideas": results,
    }


@app.post("/ideas/{idea_id}/publish")
def publish_saved_idea(idea_id: int, request: PublishIdeaRequest):
    """Dispatch only the publisher, after loading a brand-scoped saved dossier."""
    if request.publish_mode == "schedule" and not request.publish_at:
        raise HTTPException(status_code=422, detail="publish_at es obligatorio para schedule")
    try:
        idea_record = registry.call(
            "rag", "get_idea", params={"brand_id": request.brand_id, "idea_id": idea_id}
        )
        if not idea_record:
            raise HTTPException(status_code=404, detail="idea no encontrada para la marca")
        channels = registry.call(
            "postiz",
            "channels",
            params={"brand_id": request.brand_id, "integration_ids": request.integration_ids},
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        if "rag.get_idea" in str(exc) and "404" in str(exc):
            raise HTTPException(status_code=404, detail="idea no encontrada para la marca") from exc
        logger.exception("no se pudo validar idea/canales para publicar")
        raise HTTPException(status_code=502, detail=f"no se pudo validar la publicación: {exc}") from exc
    if len(channels.get("channels", [])) != len(set(request.integration_ids)):
        raise HTTPException(status_code=422, detail="los canales deben estar vinculados a la marca")

    raw_content = idea_record.get("content") or ""
    dossier = idea_record.get("dossier") or {}
    if not dossier and raw_content:
        try:
            dossier = json.loads(raw_content)
        except (TypeError, ValueError):
            dossier = {}
    if not dossier:
        raise HTTPException(status_code=422, detail="la idea guardada no contiene un dossier válido")

    client_id = int(idea_record.get("client_id") or request.brand_id)
    publication = {
        "mode": request.publish_mode,
        "publish_at": request.publish_at,
        "integration_ids": request.integration_ids,
        "settings": request.settings,
    }
    rt = _get_runtime()
    try:
        task_id = rt.start_task(
            {
                "workflow": "prepare_publication",
                "publication_action": "prepare",
                "brand_id": request.brand_id,
                "idea_id": idea_id,
                "idea": raw_content,
                "preproduction": dossier,
                "publication": publication,
                "target_channels": channels.get("channels", []),
            },
            client_id=client_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("no se pudo despachar el publicador")
        raise HTTPException(status_code=503, detail=f"no se pudo iniciar la publicación: {exc}") from exc
    return {"task_id": task_id, "idea_id": idea_id, "status": STATUS_RUNNING}


@app.post("/publications/{prepare_task_id}/approve")
def approve_prepared_publication(
    prepare_task_id: str,
    request: ApprovePreparedPublicationRequest,
):
    """Persist reviewed copies as approved without sending them to Postiz."""
    rt = _get_runtime()
    prepared_task = rt.store.get(prepare_task_id)
    if not prepared_task:
        raise HTTPException(status_code=404, detail="preparación no encontrada")
    prepared_brief = prepared_task.get("brief") or {}
    if (
        prepared_brief.get("workflow") != "prepare_publication"
        or prepared_brief.get("brand_id") != request.brand_id
    ):
        raise HTTPException(status_code=404, detail="preparación no encontrada para esta marca")
    if prepared_task.get("status") != STATUS_COMPLETED:
        raise HTTPException(status_code=409, detail="la preparación todavía no termina correctamente")

    prepared_result = prepared_task.get("result") or {}
    postiz = prepared_result.get("postiz") or {}
    if postiz.get("status") not in {"prepared", "approved_pending"}:
        raise HTTPException(status_code=409, detail="la preparación no está pendiente de aprobación")

    publication = prepared_brief.get("publication") or {}
    selected_ids = set(publication.get("integration_ids") or [])
    approved_variants = []
    covered_ids = set()
    for variant in request.publication_variants:
        content = str(variant.get("content") or "").strip()
        variant_ids = set(variant.get("integration_ids") or []) & selected_ids
        if not content or not variant_ids:
            continue
        approved_variants.append({**variant, "content": content, "integration_ids": sorted(variant_ids)})
        covered_ids.update(variant_ids)
    if not approved_variants or covered_ids != selected_ids:
        raise HTTPException(status_code=422, detail="cada canal debe tener un copy aprobado y no vacío")

    approved_postiz = {
        "status": "approved_pending",
        "mode": publication.get("mode", "draft"),
        "publish_at": publication.get("publish_at"),
        "integrations": sorted(selected_ids),
    }
    rt.store.update(
        prepare_task_id,
        result={
            **prepared_result,
            "publication": approved_variants[0]["content"],
            "publication_variants": approved_variants,
            "postiz": approved_postiz,
        },
    )
    return {
        "prepare_task_id": prepare_task_id,
        "status": "approved_pending",
        "postiz": approved_postiz,
        "publication_variants": approved_variants,
    }


@app.post("/publications/{prepare_task_id}/deliver")
def deliver_prepared_publication(
    prepare_task_id: str,
    request: DeliverPreparedPublicationRequest,
):
    """Deliver reviewed platform copies through the publication agent and Postiz."""
    if request.publish_mode == "schedule" and not request.publish_at:
        raise HTTPException(status_code=422, detail="publish_at es obligatorio para schedule")

    rt = _get_runtime()
    prepared_task = rt.store.get(prepare_task_id)
    if not prepared_task:
        raise HTTPException(status_code=404, detail="preparación no encontrada")
    prepared_brief = prepared_task.get("brief") or {}
    if (
        prepared_brief.get("workflow") != "prepare_publication"
        or prepared_brief.get("brand_id") != request.brand_id
    ):
        raise HTTPException(status_code=404, detail="preparación no encontrada para esta marca")
    if prepared_task.get("status") != STATUS_COMPLETED:
        raise HTTPException(status_code=409, detail="la preparación todavía no termina correctamente")

    prepared_result = prepared_task.get("result") or {}
    if (prepared_result.get("postiz") or {}).get("status") not in {"prepared", "approved_pending"}:
        raise HTTPException(status_code=409, detail="la tarea no contiene copies listos para entregar")

    previous_config = prepared_brief.get("publication") or {}
    previous_ids = set(previous_config.get("integration_ids") or [])
    selected_ids = request.integration_ids
    if len(selected_ids) != len(set(selected_ids)) or not set(selected_ids) <= previous_ids:
        raise HTTPException(status_code=422, detail="la entrega solo puede usar canales elegidos al preparar")

    variants = request.publication_variants or prepared_result.get("publication_variants") or []
    selected_set = set(selected_ids)
    approved_variants = []
    covered_ids = set()
    for variant in variants:
        content = str(variant.get("content") or "").strip()
        variant_ids = set(variant.get("integration_ids") or []) & selected_set
        if not content or not variant_ids:
            continue
        approved_variants.append({**variant, "content": content, "integration_ids": sorted(variant_ids)})
        covered_ids.update(variant_ids)
    if not approved_variants or covered_ids != selected_set:
        raise HTTPException(status_code=422, detail="cada canal debe tener un copy aprobado y no vacío")

    try:
        channels = registry.call(
            "postiz",
            "channels",
            params={"brand_id": request.brand_id, "integration_ids": selected_ids},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("no se pudieron validar canales para entregar")
        raise HTTPException(status_code=502, detail=f"no se pudieron validar canales: {exc}") from exc
    target_channels = channels.get("channels", [])
    if len(target_channels) != len(set(selected_ids)):
        raise HTTPException(status_code=422, detail="hay canales que no pertenecen a la marca")
    unconfigured_channels = [
        channel.get("external_id")
        for channel in target_channels
        if not channel.get("configured")
    ]
    if unconfigured_channels:
        raise HTTPException(
            status_code=422,
            detail=f"canales sin configuración Postiz: {unconfigured_channels}",
        )

    publication = {
        "mode": request.publish_mode,
        "publish_at": request.publish_at,
        "integration_ids": selected_ids,
        "settings": request.settings or previous_config.get("settings", {}),
    }
    first_copy = approved_variants[0]["content"]
    try:
        delivery_task_id = rt.start_task(
            {
                "workflow": "deliver_publication",
                "publication_action": "deliver",
                "brand_id": request.brand_id,
                "idea_id": prepared_result.get("idea_id"),
                "idea": prepared_result.get("idea", ""),
                "preproduction": prepared_result.get("preproduction", {}),
                "publication": publication,
                "prepare_task_id": prepare_task_id,
                "publication_id": prepared_result.get("publication_id", 0),
                "publication_variants": approved_variants,
                "prepared_publication": first_copy,
                "target_channels": target_channels,
            },
            client_id=int(prepared_task.get("client_id") or request.brand_id),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("no se pudo despachar la entrega aprobada")
        raise HTTPException(status_code=503, detail=f"no se pudo iniciar la entrega: {exc}") from exc
    return {
        "task_id": delivery_task_id,
        "prepare_task_id": prepare_task_id,
        "status": STATUS_RUNNING,
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


@app.get("/publications")
def list_publication_deliveries(brand_id: int, limit: int = 100):
    """List publication preparations and Postiz deliveries for one brand."""
    if not 1 <= limit <= 200:
        raise HTTPException(status_code=422, detail="limit debe estar entre 1 y 200")

    tasks = _get_runtime().store.list_publication_tasks(brand_id, limit=limit)
    delivery_sources = {
        (task.get("brief") or {}).get("prepare_task_id")
        for task in tasks
        if (task.get("brief") or {}).get("workflow") == "deliver_publication"
    }
    items = []
    for task in tasks:
        brief = task.get("brief") or {}
        workflow = brief.get("workflow")
        if workflow == "prepare_publication" and task.get("task_id") in delivery_sources:
            continue
        result = task.get("result") or {}
        publication = brief.get("publication") or {}
        postiz = result.get("postiz") or {}
        if workflow == "publish_idea" and not postiz:
            continue
        variants = result.get("publication_variants") or brief.get("publication_variants") or []
        variant_by_channel = {
            integration_id: variant
            for variant in variants
            for integration_id in variant.get("integration_ids", [])
        }
        target_channels = {
            channel.get("external_id"): channel
            for channel in brief.get("target_channels", [])
        }
        channels = []
        for integration_id in publication.get("integration_ids", []):
            variant = variant_by_channel.get(integration_id, {})
            channel = target_channels.get(integration_id, {})
            channels.append({
                "external_id": integration_id,
                "display_name": channel.get("display_name") or integration_id,
                "provider": channel.get("provider") or variant.get("platform") or "",
                "content": variant.get("content") or "",
            })

        if task.get("status") == STATUS_RUNNING:
            delivery_status = "preparing" if workflow == "prepare_publication" else "sending"
        elif task.get("status") == STATUS_FAILED or postiz.get("status") == "failed":
            delivery_status = "failed"
        elif postiz.get("status") == "skipped":
            delivery_status = "skipped"
        elif postiz.get("status") == "approved_pending":
            delivery_status = "approved_pending"
        elif postiz.get("status") == "prepared":
            delivery_status = "awaiting_approval"
        elif postiz.get("status") == "created":
            delivery_status = {
                "now": "sent",
                "schedule": "scheduled",
                "draft": "draft",
            }.get(publication.get("mode"), "created")
        else:
            delivery_status = "pending"

        items.append({
            "task_id": task.get("task_id"),
            "prepare_task_id": (
                brief.get("prepare_task_id")
                or (task.get("task_id") if workflow == "prepare_publication" else None)
            ),
            "idea_id": brief.get("idea_id"),
            "workflow": workflow,
            "status": delivery_status,
            "task_status": task.get("status"),
            "mode": publication.get("mode", "draft"),
            "publish_at": publication.get("publish_at"),
            "integration_ids": publication.get("integration_ids") or postiz.get("integrations") or [],
            "settings": publication.get("settings") or {},
            "created_at": task.get("created_at"),
            "updated_at": task.get("updated_at"),
            "error": postiz.get("error") or task.get("error"),
            "channels": channels,
        })
    return {"items": items, "total": len(items)}


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
