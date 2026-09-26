"""
Orquestador multi-agente con LangGraph.

Servicio FastAPI que:
- Expone endpoints de salud, tools y ejecución directa del pipeline.
- Consume briefs desde RabbitMQ (ideation_queue).
- Ejecuta el grafo supervisor de LangGraph que coordina los agentes
  de ideación y publicación como subgrafos.
"""
import json
import logging
import os
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pika
from fastapi import FastAPI
from pydantic import BaseModel

from multi_agent import ALL_TOOLS, create_orchestrator
from multi_agent.supervisor import run_pipeline

# ── Configuración ──────────────────────────────────────────────
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("orchestrator")

app = FastAPI(title="Orquestador Multi-Agente (LangGraph)")

# Grafo supervisor compilado (una sola vez)
_orchestrator = None


def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        logger.info("Compilando grafo supervisor de LangGraph …")
        _orchestrator = create_orchestrator()
        logger.info("Grafo supervisor compilado ✓")
    return _orchestrator


# ── Modelos ────────────────────────────────────────────────────
class Brief(BaseModel):
    client_id: int
    content: str


# ── Endpoints ──────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "orchestrator-langgraph"}


@app.get("/metrics")
async def metrics():
    return {
        "agent": "orchestrator",
        "framework": "langgraph",
        "status": "running",
        "queue": "ideation_queue",
        "llm_model": OLLAMA_MODEL,
        "agents": ["ideacion", "publicacion"],
        "pattern": "supervisor",
    }


@app.get("/tools")
async def tools_info():
    """Lista las LangChain tools registradas en el orquestador."""
    return {
        "agent": "orchestrator",
        "framework": "langgraph",
        "tools": [
            {"name": t.name, "description": t.description}
            for t in ALL_TOOLS
        ],
    }


@app.get("/graph")
async def graph_info():
    """Devuelve la estructura del grafo supervisor."""
    graph = get_orchestrator()
    return {
        "nodes": ["start", "ideacion_agent", "publicacion_agent"],
        "edges": [
            "START → start",
            "start → [ideacion_agent | publicacion_agent | END]",
            "ideacion_agent → [ideacion_agent | publicacion_agent | END]",
            "publicacion_agent → [ideacion_agent | publicacion_agent | END]",
        ],
        "subgraphs": {
            "ideacion_agent": ["load_context", "fetch_news", "generate_idea", "save_idea"],
            "publicacion_agent": ["load_context", "fetch_trending", "generate_post", "save_post"],
        },
    }


@app.post("/process")
async def process_brief(brief: Brief):
    """Ejecuta el pipeline completo directamente (sin RabbitMQ)."""
    logger.info("Solicitud directa: client_id=%s", brief.client_id)
    result = run_pipeline(
        brief={"client_id": brief.client_id, "content": brief.content},
        client_id=brief.client_id,
    )
    return {
        "idea": result.get("idea", ""),
        "idea_id": result.get("idea_id", 0),
        "publication": result.get("publication", ""),
        "publication_id": result.get("publication_id", 0),
        "log": result.get("log", []),
    }


# ── RabbitMQ ───────────────────────────────────────────────────
def _rabbitmq_params() -> pika.ConnectionParameters:
    return pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=5672,
        credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS),
    )


def consume_messages():
    while True:
        try:
            conn = pika.BlockingConnection(_rabbitmq_params())
            ch = conn.channel()
            ch.queue_declare(queue="ideation_queue")

            def on_message(ch, method, properties, body):
                try:
                    data = json.loads(body)
                    brief = Brief(**data)
                    logger.info("━" * 60)
                    logger.info("Brief recibido (client_id=%s)", brief.client_id)
                    result = run_pipeline(
                        brief={"client_id": brief.client_id, "content": brief.content},
                        client_id=brief.client_id,
                    )
                    logger.info("Pipeline completado: idea_id=%s pub_id=%s",
                                result.get("idea_id"), result.get("publication_id"))
                    logger.info("Log: %s", result.get("log"))
                    logger.info("━" * 60)
                except json.JSONDecodeError as exc:
                    logger.error("Mensaje no es JSON válido: %s", exc)
                except Exception as exc:
                    logger.exception("Error procesando mensaje: %s", exc)

            ch.basic_consume(
                queue="ideation_queue", on_message_callback=on_message, auto_ack=True
            )
            logger.info("Esperando briefs en ideation_queue …")
            ch.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            logger.warning("RabbitMQ no disponible. Reintentando en 5 s …")
            time.sleep(5)
        except Exception as exc:
            logger.error("Error inesperado: %s. Reintentando en 5 s …", exc)
            time.sleep(5)


# ── Arranque ───────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    # Pre-compilar el grafo
    get_orchestrator()
    # Iniciar consumidor RabbitMQ en hilo separado
    t = threading.Thread(target=consume_messages, daemon=True)
    t.start()
    logger.info(
        "Orquestador LangGraph iniciado — agentes: ideación + publicación (patrón supervisor)"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
