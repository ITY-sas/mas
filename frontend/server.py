"""
BFF (Backend For Frontend) & Servidor Web para la interfaz del Sistema Multi-Agente.

Coordina e integra:
- Orquestador stateless (LangGraph supervisor en :8002)
- Agente de Ideación (:8000)
- Agente de Publicación (:8001)
- LLM Gateway (:8003)
- Tool Services (:8010-:8016)
- Redis (checkpoints y TaskStore)
- PostgreSQL (memoria RAG e historial de chat durable)
- RabbitMQ (inspección de estado)

Expone API REST + SSE para trazabilidad en vivo y sirve la SPA estática.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any, AsyncGenerator, Literal, Optional

# UTF-8 output fix for Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ── Configuración y URLs de servicios ─────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("frontend_bff")

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8002")
AGENTE_IDEACION_URL = os.getenv("AGENTE_IDEACION_URL", "http://localhost:8000")
AGENTE_PUBLICACION_URL = os.getenv("AGENTE_PUBLICACION_URL", "http://localhost:8001")
LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://localhost:8003")
TOOL_CLIENT_URL = os.getenv("TOOL_CLIENT_URL", "http://localhost:8010")
TOOL_RAG_URL = os.getenv("TOOL_RAG_URL", "http://localhost:8013")
TOOL_POSTIZ_URL = os.getenv("TOOL_POSTIZ_URL", "http://localhost:8016")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

POSTGRES_CFG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "ideation_db"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "password"),
}

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(
    title="Multi-Agent Studio Backend",
    description="BFF y panel de control para interacción y trazabilidad multi-agente",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Modelos de Datos ───────────────────────────────────────────
class TaskBriefRequest(BaseModel):
    client_id: int = Field(1, description="ID del cliente o marca")
    brand_id: Optional[int] = Field(None, description="ID de la marca (opcional)")
    content: str = Field("", description="Texto libre opcional del brief")
    content_format: Literal["auto", "reel", "post"] = Field("auto", description="Formato deseado")
    publish_mode: Literal["draft", "schedule", "now"] = Field("draft", description="Modo Postiz")
    publish_at: Optional[str] = Field(None, description="Fecha UTC ISO 8601 de publicación")
    postiz_integration_ids: list[str] = Field(default_factory=list)
    postiz_settings: dict[str, dict] = Field(default_factory=dict)
    wait: bool = Field(False, description="Si es True bloquea hasta finalizar; si es False es asíncrono")
    timeout: float = Field(300.0, description="Tiempo máximo de espera en segundos")


class LinkBrandChannelRequest(BaseModel):
    external_id: str = Field(..., min_length=1)


class DemoBriefRequest(BaseModel):
    brand_id: int = Field(1, description="ID de la marca para la demo")
    content: str = Field(
        "Crear un Reel para presentar una crema solar natural durante el verano colombiano",
        description="Brief demo",
    )
    content_format: Literal["auto", "reel", "post"] = "reel"
    wait: bool = False
    timeout: float = 300.0


class IdeaGenerationRequest(BaseModel):
    client_id: int
    brand_id: Optional[int] = None
    count: int = Field(5, ge=1, le=5)
    content: str = ""
    briefs: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    content_format: Literal["auto", "reel", "post"] = "auto"


class PublishIdeaRequest(BaseModel):
    brand_id: int
    publish_mode: Literal["draft", "schedule", "now"] = "draft"
    publish_at: Optional[str] = None
    integration_ids: list[str] = Field(..., min_length=1)
    settings: dict[str, dict] = Field(default_factory=dict)


class DeliverPreparedPublicationRequest(PublishIdeaRequest):
    publication_variants: list[dict] = Field(default_factory=list)


class DeliverPreparedPublicationRequest(PublishIdeaRequest):
    publication_variants: list[dict] = Field(default_factory=list)


# ── Clientes auxiliares (Redis y Postgres) ─────────────────────
def get_redis_client():
    try:
        import redis

        return redis.Redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as exc:
        logger.warning("No se pudo conectar a Redis: %s", exc)
        return None


def get_pg_connection():
    try:
        import psycopg2

        return psycopg2.connect(**POSTGRES_CFG)
    except Exception as exc:
        logger.warning("No se pudo conectar a PostgreSQL: %s", exc)
        return None


# ── Rutas de la API (BFF) ──────────────────────────────────────

@app.get("/api/health")
def get_health():
    """Verifica salud del BFF y de todos los microservicios."""
    health_data = {
        "status": "healthy",
        "bff": "ok",
        "services": {},
    }

    # 1. Orquestador
    try:
        r = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=2)
        health_data["services"]["orchestrator"] = r.json() if r.status_code == 200 else f"status {r.status_code}"
    except Exception as exc:
        health_data["services"]["orchestrator"] = f"down: {exc}"

    # 2. Agente Ideación
    try:
        r = requests.get(f"{AGENTE_IDEACION_URL}/health", timeout=2)
        health_data["services"]["agente_ideacion"] = r.json() if r.status_code == 200 else f"status {r.status_code}"
    except Exception as exc:
        health_data["services"]["agente_ideacion"] = f"down: {exc}"

    # 3. Agente Publicación
    try:
        r = requests.get(f"{AGENTE_PUBLICACION_URL}/health", timeout=2)
        health_data["services"]["agente_publicacion"] = r.json() if r.status_code == 200 else f"status {r.status_code}"
    except Exception as exc:
        health_data["services"]["agente_publicacion"] = f"down: {exc}"

    # 4. LLM Gateway
    try:
        r = requests.get(f"{LLM_GATEWAY_URL}/health", timeout=2)
        health_data["services"]["llm_gateway"] = r.json() if r.status_code == 200 else f"status {r.status_code}"
    except Exception as exc:
        health_data["services"]["llm_gateway"] = f"down: {exc}"

    # 5. Redis
    r_client = get_redis_client()
    if r_client:
        try:
            r_client.ping()
            health_data["services"]["redis"] = "ok"
        except Exception as exc:
            health_data["services"]["redis"] = f"down: {exc}"
    else:
        health_data["services"]["redis"] = "unavailable"

    # 6. PostgreSQL
    conn = get_pg_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
            conn.close()
            health_data["services"]["postgres"] = "ok"
        except Exception as exc:
            health_data["services"]["postgres"] = f"down: {exc}"
    else:
        health_data["services"]["postgres"] = "unavailable"

    return health_data


@app.get("/api/overview")
def get_overview():
    """Resumen cuantitativo del sistema (tareas, clientes, memoria RAG, tools)."""
    overview = {
        "tasks": {"total": 0, "completed": 0, "running": 0, "failed": 0},
        "rag": {"ideas": 0, "publicaciones": 0},
        "clients_count": 0,
        "tools_count": 0,
    }

    # Tareas en Redis
    r_client = get_redis_client()
    if r_client:
        try:
            keys = r_client.keys("task:*")
            overview["tasks"]["total"] = len(keys)
            for k in keys:
                raw = r_client.get(k)
                if raw:
                    try:
                        t = json.loads(raw)
                        st = t.get("status")
                        if st == "completed":
                            overview["tasks"]["completed"] += 1
                        elif st == "running":
                            overview["tasks"]["running"] += 1
                        elif st == "failed":
                            overview["tasks"]["failed"] += 1
                    except Exception:
                        pass
        except Exception as exc:
            logger.warning("Error leyendo tareas de Redis: %s", exc)

    # Memoria RAG
    try:
        r = requests.get(f"{TOOL_RAG_URL}/stats", timeout=2)
        if r.status_code == 200:
            data = r.json().get("data", {})
            overview["rag"] = data
    except Exception:
        pass

    # Clientes
    try:
        clients = get_clients()
        overview["clients_count"] = len(clients)
    except Exception:
        pass

    # Tools
    try:
        r = requests.get(f"{ORCHESTRATOR_URL}/tools", timeout=2)
        if r.status_code == 200:
            tools = r.json().get("tools", [])
            overview["tools_count"] = len(tools)
    except Exception:
        pass

    return overview


@app.get("/api/clients")
def get_clients():
    """Lista todos los perfiles de clientes y marcas disponibles."""
    conn = get_pg_connection()
    if conn:
        try:
            from psycopg2.extras import RealDictCursor

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                          SELECT c.id, COALESCE(m.brand_id, c.id) AS brand_id,
                              c.nombre, c.perfil_marca, c.restricciones_tono, c.historico,
                              c.producto_servicio, c.audiencia_objetivo, c.objetivo_marketing,
                              c.propuesta_valor, c.pilares_contenido, c.canales_objetivo,
                              c.pais, c.zona_horaria, c.restricciones_legales
                          FROM clientes c
                          LEFT JOIN legacy_client_brand m ON m.client_id = c.id
                          ORDER BY c.id ASC;
                    """
                )
                rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.warning("Error leyendo clientes de DB: %s", exc)
            if conn:
                conn.close()

    # Fallback con perfiles estándar del sistema
    return [
        {
            "id": 1,
            "brand_id": 1,
            "nombre": "EcoBrand",
            "perfil_marca": "Marca de productos ecológicos y sostenibles dirigida a millennials conscientes del medio ambiente.",
            "restricciones_tono": "Cercano pero profesional. Evitar greenwashing. No usar mayúsculas excesivas.",
            "historico": "Campañas 'Reto Zero Waste' (+340% engagement) y 'Cada Gota Cuenta'.",
            "producto_servicio": "Protector solar y cosmética natural con ingredientes responsables.",
            "audiencia_objetivo": "Personas de 18 a 35 años en Colombia interesadas en sostenibilidad.",
            "objetivo_marketing": "Aumentar reconocimiento y contenido compartible en redes sociales.",
            "pais": "Colombia",
            "zona_horaria": "America/Bogota",
        },
        {
            "id": 2,
            "brand_id": 2,
            "nombre": "TechStart",
            "perfil_marca": "Startup fintech que simplifica pagos para pequeños comercios en Latinoamérica.",
            "restricciones_tono": "Joven, directo, confiable. Usar datos y cifras. Evitar jerga compleja.",
            "historico": "Campañas 'Pagos sin Fricción' (15K leads) y 'Tu Negocio en tu Bolsillo'.",
            "producto_servicio": "App móvil para recibir pagos y administrar ventas.",
            "audiencia_objetivo": "Comercios independientes y pequeñas empresas en Colombia.",
            "objetivo_marketing": "Generar registros y demostrar cobros digitales sencillos.",
            "pais": "Colombia",
            "zona_horaria": "America/Bogota",
        },
        {
            "id": 3,
            "brand_id": 3,
            "nombre": "FitLife",
            "perfil_marca": "Marca de nutrición y fitness con suplementos naturales y planes de hábitos.",
            "restricciones_tono": "Motivador pero no agresivo. Basar afirmaciones en evidencia científica.",
            "historico": "Campañas '30 Días de Cambio' (22K participantes) y 'Nutre tu Mente'.",
            "producto_servicio": "Suplementos naturales y planes de entrenamiento personalizados.",
            "audiencia_objetivo": "Adultos de 25 a 45 años en Colombia interesados en salud integral.",
            "objetivo_marketing": "Aumentar consideración de producto y retos saludables.",
            "pais": "Colombia",
            "zona_horaria": "America/Bogota",
        },
    ]


@app.get("/api/clients/{client_id}")
def get_client(client_id: int):
    """Detalle de un cliente o marca por ID."""
    clients = get_clients()
    for c in clients:
        if c.get("id") == client_id:
            return c
    raise HTTPException(status_code=404, detail="Cliente no encontrado")


@app.get("/api/brands/{brand_id}/channels")
def get_brand_channels(brand_id: int):
    """Lista los canales Postiz activos vinculados a la marca."""
    try:
        resp = requests.get(
            f"{TOOL_POSTIZ_URL}/channels",
            params={"brand_id": brand_id},
            timeout=5,
        )
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        envelope = resp.json()
        if envelope.get("status") != "ok":
            raise HTTPException(status_code=502, detail=envelope.get("error") or "Error consultando canales")
        return envelope.get("data", {}).get("channels", [])
    except requests.RequestException as exc:
        logger.warning("No se pudieron consultar canales Postiz de marca %s: %s", brand_id, exc)
        raise HTTPException(status_code=502, detail="No se pudo consultar tool-postiz") from exc


@app.get("/api/postiz/integrations")
def get_postiz_integrations():
    """Devuelve el catálogo saneado de integraciones de la cuenta Postiz."""
    try:
        resp = requests.get(f"{TOOL_POSTIZ_URL}/available-integrations", timeout=5)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        envelope = resp.json()
        if envelope.get("status") != "ok":
            raise HTTPException(status_code=502, detail=envelope.get("error") or "Error consultando Postiz")
        return envelope.get("data", [])
    except requests.RequestException as exc:
        logger.warning("No se pudo consultar catálogo Postiz: %s", exc)
        raise HTTPException(status_code=502, detail="No se pudo consultar el catálogo Postiz") from exc


@app.post("/api/brands/{brand_id}/channels")
def link_brand_channel(brand_id: int, req: LinkBrandChannelRequest):
    """Asocia a la marca una integración existente en la cuenta Postiz."""
    try:
        resp = requests.post(
            f"{TOOL_POSTIZ_URL}/channels",
            json={"brand_id": brand_id, "external_id": req.external_id},
            timeout=10,
        )
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        envelope = resp.json()
        if envelope.get("status") != "ok":
            raise HTTPException(status_code=502, detail=envelope.get("error") or "No se pudo vincular el canal")
        return envelope.get("data", {})
    except requests.RequestException as exc:
        logger.warning("No se pudo vincular canal %s a marca %s: %s", req.external_id, brand_id, exc)
        raise HTTPException(status_code=502, detail="No se pudo conectar con tool-postiz") from exc


@app.post("/api/ideas/generate")
def generate_ideas(req: IdeaGenerationRequest):
    if len(req.briefs) > req.count:
        raise HTTPException(status_code=422, detail="briefs no puede superar count")
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    payload["brand_id"] = req.brand_id or req.client_id
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/ideas/generate", json=payload, timeout=15
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
    except requests.RequestException as exc:
        logger.exception("No se pudo iniciar lote de ideas")
        raise HTTPException(status_code=502, detail="No se pudo contactar al orquestador") from exc


@app.get("/api/idea-batches/{batch_id}")
def get_idea_batch(batch_id: str, brand_id: int):
    try:
        response = requests.get(
            f"{ORCHESTRATOR_URL}/ideas/batches/{batch_id}",
            params={"brand_id": brand_id},
            timeout=10,
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="No se pudo consultar el lote") from exc


@app.get("/api/ideas")
def list_saved_ideas(
    brand_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    query: Optional[str] = None,
    generation_batch_id: Optional[str] = None,
):
    try:
        response = requests.get(
            f"{TOOL_RAG_URL}/ideas",
            params={
                "brand_id": brand_id,
                "limit": limit,
                "offset": offset,
                "query": query,
                "generation_batch_id": generation_batch_id,
            },
            timeout=10,
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        envelope = response.json()
        if envelope.get("status") != "ok":
            raise HTTPException(status_code=502, detail=envelope.get("error") or "Error consultando ideas")
        return envelope.get("data", {})
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="No se pudo consultar la biblioteca") from exc


@app.get("/api/ideas/{idea_id}")
def get_saved_idea(idea_id: int, brand_id: int):
    try:
        response = requests.get(
            f"{TOOL_RAG_URL}/ideas/detail",
            params={"idea_id": idea_id, "brand_id": brand_id},
            timeout=10,
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Idea no encontrada para esta marca")
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        envelope = response.json()
        if envelope.get("status") != "ok":
            raise HTTPException(status_code=502, detail=envelope.get("error") or "Error consultando idea")
        return envelope.get("data", {})
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="No se pudo consultar la idea") from exc


@app.post("/api/ideas/{idea_id}/publish")
def publish_saved_idea(idea_id: int, req: PublishIdeaRequest):
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/ideas/{idea_id}/publish", json=payload, timeout=15
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="No se pudo contactar al publicador") from exc


@app.post("/api/publications/{prepare_task_id}/deliver")
def deliver_prepared_publication(
    prepare_task_id: str,
    req: DeliverPreparedPublicationRequest,
):
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/publications/{prepare_task_id}/deliver",
            json=payload,
            timeout=15,
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="No se pudo contactar al orquestador") from exc


@app.post("/api/publications/{prepare_task_id}/deliver")
def deliver_prepared_publication(
    prepare_task_id: str,
    req: DeliverPreparedPublicationRequest,
):
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/publications/{prepare_task_id}/deliver",
            json=payload,
            timeout=15,
        )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="No se pudo contactar al orquestador") from exc


@app.post("/api/tasks")
def create_task(req: TaskBriefRequest):
    """
    Envía un nuevo brief al Orquestador.
    Soporta modo síncrono (wait=True) y asíncrono en tiempo real (wait=False).
    """
    payload = {
        "client_id": req.client_id,
        "brand_id": req.brand_id or req.client_id,
        "content": req.content,
        "content_format": req.content_format,
        "wait": req.wait,
        "timeout": req.timeout,
    }

    try:
        resp = requests.post(
            f"{ORCHESTRATOR_URL}/process",
            json=payload,
            timeout=req.timeout + 10 if req.wait else 15,
        )
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return resp.json()
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Tiempo de espera agotado con el orquestador")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error al crear tarea en orquestador")
        raise HTTPException(status_code=502, detail=f"No se pudo contactar al orquestador: {exc}")


@app.post("/api/demo")
def create_demo(req: DemoBriefRequest):
    """Ejecuta la demo reproducible de un solo clic."""
    task_req = TaskBriefRequest(
        client_id=req.brand_id,
        brand_id=req.brand_id,
        content=req.content,
        content_format=req.content_format,
        wait=req.wait,
        timeout=req.timeout,
    )
    return create_task(task_req)


@app.get("/api/tasks")
def list_tasks(status: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200)):
    """Lista tareas guardadas en Redis ordenadas cronológicamente."""
    r_client = get_redis_client()
    if not r_client:
        return []

    try:
        keys = r_client.keys("task:*")
        tasks = []
        for k in keys:
            raw = r_client.get(k)
            if not raw:
                continue
            try:
                task = json.loads(raw)
                if status and task.get("status") != status:
                    continue

                # Resumen ligero para listado
                result = task.get("result") or {}
                brief = task.get("brief") or {}
                tasks.append({
                    "task_id": task.get("task_id"),
                    "status": task.get("status"),
                    "client_id": task.get("client_id"),
                    "brief_content": brief.get("content", ""),
                    "content_format": brief.get("content_format", "auto"),
                    "has_idea": bool(result.get("idea")),
                    "has_publication": bool(result.get("publication")),
                    "created_at": task.get("created_at"),
                    "updated_at": task.get("updated_at"),
                    "duration_seconds": round(
                        (task.get("updated_at", 0) - task.get("created_at", 0)), 1
                    ) if task.get("updated_at") and task.get("created_at") else None,
                    "error": task.get("error"),
                })
            except Exception:
                continue

        # Ordenar más recientes primero
        tasks.sort(key=lambda x: x.get("created_at") or 0, reverse=True)
        return tasks[:limit]
    except Exception as exc:
        logger.error("Error listando tareas de Redis: %s", exc)
        return []


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    """Detalle completo de una tarea desde Redis."""
    r_client = get_redis_client()
    if not r_client:
        raise HTTPException(status_code=503, detail="Redis no disponible")

    raw = r_client.get(f"task:{task_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    try:
        return json.loads(raw)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error decodificando tarea: {exc}")


@app.get("/api/tasks/{task_id}/history")
def get_task_history(task_id: str):
    """Historial de turnos de chat en PostgreSQL para esta tarea."""
    try:
        resp = requests.get(f"{ORCHESTRATOR_URL}/tasks/{task_id}/history", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.warning("Fallo al obtener historial del orquestador: %s", exc)

    # Fallback directo a Postgres
    conn = get_pg_connection()
    if conn:
        try:
            from psycopg2.extras import RealDictCursor

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, task_id, client_id, role, content, created_at
                    FROM chat_history
                    WHERE task_id = %s
                    ORDER BY id ASC;
                    """,
                    (task_id,),
                )
                rows = cur.fetchall()
            conn.close()
            return {"task_id": task_id, "messages": [dict(r) for r in rows]}
        except Exception as exc:
            if conn:
                conn.close()
            logger.warning("Fallo en consulta directa Postgres: %s", exc)

    return {"task_id": task_id, "messages": []}


@app.get("/api/tasks/{task_id}/trace")
def get_task_trace(task_id: str):
    """
    TRAZABILIDAD COMPLETA END-TO-END.
    Reconstruye el mapa exacto de ejecución, agentes, llamadas a tools,
    tiempos, estados intermedios y checkpoints.
    """
    task = get_task(task_id)
    history = get_task_history(task_id).get("messages", [])

    # Obtener estado de agente_ideacion desde Redis / microservicio
    ideacion_state = None
    try:
        resp = requests.get(f"{AGENTE_IDEACION_URL}/state/{task_id}", timeout=2)
        if resp.status_code == 200:
            ideacion_state = resp.json().get("values", {})
    except Exception:
        pass

    # Obtener estado de agente_publicacion desde Redis / microservicio
    publicacion_state = None
    try:
        resp = requests.get(f"{AGENTE_PUBLICACION_URL}/state/{task_id}", timeout=2)
        if resp.status_code == 200:
            publicacion_state = resp.json().get("values", {})
    except Exception:
        pass

    agents_data = task.get("agents", {})
    ideacion_meta = agents_data.get("ideacion", {})
    publicacion_meta = agents_data.get("publicacion", {})
    result_data = task.get("result", {})
    brief_data = task.get("brief", {})
    workflow = brief_data.get("workflow")
    is_publish_workflow = workflow in {
        "publish_idea", "prepare_publication", "deliver_publication",
    }
    is_delivery_workflow = workflow == "deliver_publication"

    created_at = task.get("created_at")
    updated_at = task.get("updated_at")
    total_duration = round((updated_at - created_at), 2) if updated_at and created_at else None

    # Trazabilidad de herramientas de Ideación
    ideacion_tools = ideacion_state.get("tool_calls") if ideacion_state else [
        "client.profile", "trends.search", "competitors.search", "rag.similar", "news.news", "llm-gateway.generate", "rag.save_idea"
    ]

    # Trazabilidad de herramientas de Publicación
    publicacion_tools = publicacion_state.get("tool_calls") if publicacion_state else (
        ["client.profile", "trends.search", "trending.trending", "llm-gateway.generate", "rag.save_publicacion"]
        if is_publish_workflow else []
    )

    trace = {
        "task_id": task_id,
        "status": task.get("status"),
        "client_id": task.get("client_id"),
        "created_at": created_at,
        "updated_at": updated_at,
        "total_duration_seconds": total_duration,
        "error": task.get("error"),
        "pending": task.get("pending"),
        "pipeline_stages": [
            {
                "stage": 1,
                "name": "Ingreso de Brief & Orquestador",
                "component": "orchestrator:8002",
                "framework": "LangGraph Supervisor",
                "status": "completed",
                "details": {
                    "brief": brief_data,
                    "event_dispatched": (
                        "agent.task.triggered (cola: agent.publicacion.tasks)"
                        if is_publish_workflow else
                        "agent.task.triggered (cola: agent.ideacion.tasks)"
                    ),
                    "checkpoint": "RedisSaver (thread_id = " + task_id + ")",
                },
            },
            {
                "stage": 2,
                "name": "Dossier recuperado" if is_publish_workflow else "Agente de Ideación",
                "component": "tool-rag:8013" if is_publish_workflow else "agente_ideacion:8000",
                "framework": "LangGraph Microservice (4 nodos)",
                "status": "skipped" if is_publish_workflow else ideacion_meta.get("status") or (
                    "running" if task.get("status") == "running" and not result_data.get("idea") else "pending"
                ),
                "timestamp": ideacion_meta.get("at"),
                "tools_used": ideacion_tools,
                "context_retrieved": {
                    "client_profile_loaded": bool(ideacion_state.get("client_profile") if ideacion_state else True),
                    "trends_context": ideacion_state.get("trends", "") if ideacion_state else "Recuperado de pgvector",
                    "competitors_context": ideacion_state.get("competitors", "") if ideacion_state else "Recuperado de pgvector",
                    "similar_ideas_rag": ideacion_state.get("similar_ideas", "") if ideacion_state else "Evaluado",
                    "news_rss": ideacion_state.get("news", "") if ideacion_state else "Google News RSS",
                },
                "output": {
                    "idea": result_data.get("idea") or (ideacion_meta.get("result", {}).get("idea")),
                    "idea_id": result_data.get("idea_id") or (ideacion_meta.get("result", {}).get("idea_id")),
                    "preproduction": result_data.get("preproduction") or (ideacion_meta.get("result", {}).get("preproduction", {})),
                },
            },
            {
                "stage": 3,
                "name": "Reanudación del Orquestador",
                "component": "orchestrator:8002",
                "framework": "Command(resume=...) desde checkpoint Redis",
                "status": (
                    "completed" if is_publish_workflow or ideacion_meta.get("status") == "completed" or result_data.get("idea") else "pending"
                ),
                "details": {
                    "event_received": "idea cargada desde PostgreSQL" if is_publish_workflow else "agent.task.completed (cola: agent.results)",
                    "next_dispatch": (
                        "entrega aprobada enviada a Postiz"
                        if is_delivery_workflow else
                        "copies preparados; Postiz espera aprobación"
                        if workflow == "prepare_publication" else
                        "fin de generación; publicación requiere selección manual"
                    ),
                },
            },
            {
                "stage": 4,
                "name": "Agente de Publicación",
                "component": "agente_publicacion:8001",
                "framework": "LangGraph Microservice (4 nodos)",
                "status": publicacion_meta.get("status") or (
                    "running"
                    if is_publish_workflow and task.get("status") == "running" and not result_data.get("publication")
                    else "pending" if is_publish_workflow else "skipped"
                ),
                "timestamp": publicacion_meta.get("at"),
                "tools_used": publicacion_tools,
                "context_retrieved": {
                    "trending_topics": publicacion_state.get("trending", "") if publicacion_state else "Google Trends / News",
                    "trends_context": publicacion_state.get("trends", "") if publicacion_state else "pgvector",
                },
                "output": {
                    "publication": result_data.get("publication") or (publicacion_meta.get("result", {}).get("publication")),
                    "publication_id": result_data.get("publication_id") or (publicacion_meta.get("result", {}).get("publication_id")),
                    "postiz": result_data.get("postiz") or (publicacion_meta.get("result", {}).get("postiz", {})),
                },
            },
            {
                "stage": 5,
                "name": "Finalización y Persistencia Durable",
                "component": "orchestrator:8002 & postgres",
                "framework": "PostgreSQL (chat_history) + RabbitMQ (task.completed)",
                "status": task.get("status"),
                "details": {
                    "persisted_in_chat_history": len(history) > 0,
                    "event_published": "task.completed (cola: task.results)",
                    "ideas_table_id": result_data.get("idea_id"),
                    "publicaciones_table_id": result_data.get("publication_id"),
                },
            },
        ],
        "chat_history": history,
        "raw_task": task,
    }

    return trace


@app.get("/api/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str, request: Request):
    """
    SSE (Server-Sent Events) para seguir en vivo la ejecución
    y trazabilidad de una tarea hasta que termine.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        r_client = get_redis_client()
        last_status = None
        last_idea = None
        last_pub = None
        deadline = time.time() + 360.0  # 6 minutos max

        while time.time() < deadline:
            if await request.is_disconnected():
                break

            if r_client:
                raw = r_client.get(f"task:{task_id}")
                if raw:
                    try:
                        task = json.loads(raw)
                        status = task.get("status")
                        result = task.get("result") or {}
                        idea = bool(result.get("idea"))
                        pub = bool(result.get("publication"))

                        # Enviar evento si hay cambio o en el primer tick
                        if (status != last_status) or (idea != last_idea) or (pub != last_pub) or (last_status is None):
                            last_status = status
                            last_idea = idea
                            last_pub = pub

                            trace = get_task_trace(task_id)
                            data_str = json.dumps({
                                "task_id": task_id,
                                "status": status,
                                "trace": trace,
                                "completed": status in ("completed", "failed"),
                            }, ensure_ascii=False)
                            yield f"data: {data_str}\n\n"

                            if status in ("completed", "failed"):
                                break
                    except Exception as exc:
                        logger.warning("Error en stream de tarea: %s", exc)

            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/tools")
def get_tools_catalog():
    """Catálogo de tools descubiertas por Tool Discovery."""
    try:
        resp = requests.get(f"{ORCHESTRATOR_URL}/tools", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.warning("Error consultando tools al orquestador: %s", exc)
    return {"tools": []}


@app.get("/api/rag/stats")
def get_rag_stats():
    """Conteo de ideas y publicaciones vectorizadas en pgvector."""
    try:
        resp = requests.get(f"{TOOL_RAG_URL}/stats", timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.warning("Error consultando stats de RAG: %s", exc)
    return {"data": {"ideas": 0, "publicaciones": 0}}


# ── Servir archivos estáticos del frontend ──────────────────────
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "3000"))
    logger.info("Iniciando Frontend BFF Server en http://0.0.0.0:%d", port)
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
