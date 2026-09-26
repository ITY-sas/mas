"""
Agente de Publicación
Pipeline: idea → tools de contexto (tono cliente, tendencias) → LLM enriquecido → PostgreSQL
"""
import json
import logging
import os
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pika
import requests
from fastapi import FastAPI
from pydantic import BaseModel

# ── Tools compartidas ──────────────────────────────────────────
from shared_tools import (
    build_publicacion_prompt,
    embedding_to_vector,
    enrich_idea_context,
    execute_db,
    fetch_trending_topics,
    format_news_for_prompt,
    generate_embedding,
)

# ── Configuración ──────────────────────────────────────────────
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


def _ollama_url() -> str:
    """Construye la URL de Ollama manejando host con o sin puerto."""
    host = os.getenv("OLLAMA_HOST", "ollama")
    port = os.getenv("OLLAMA_PORT", "11434")
    # 0.0.0.0 es dirección de escucha, no válida como cliente
    if host.startswith("0.0.0.0"):
        host = host.replace("0.0.0.0", "127.0.0.1", 1)
    if ":" in host and not host.startswith("["):
        return f"http://{host}"
    if not port:
        port = "11434"
    return f"http://{host}:{port}"


OLLAMA_BASE = _ollama_url()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("agente_publicacion")

app = FastAPI(title="Agente de Publicación")


# ── Modelos de datos ───────────────────────────────────────────
class Idea(BaseModel):
    client_id: int
    content: str
    brief_id: int | None = None


# ── Endpoints FastAPI ──────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "publicacion"}


@app.get("/metrics")
async def metrics():
    return {
        "agent": "publicacion",
        "status": "running",
        "queue": "publication_queue",
        "llm_model": OLLAMA_MODEL,
        "tools": ["cliente", "tendencias", "fuentes_externas"],
    }


@app.get("/tools")
async def tools_info():
    return {
        "agent": "publicacion",
        "tools": [
            {"name": "get_client_profile", "desc": "Lee perfil y restricciones de tono del cliente"},
            {"name": "get_relevant_trends", "desc": "Busca tendencias relevantes para hashtags"},
            {"name": "fetch_trending_topics", "desc": "Obtiene topics en tendencia (Google News)"},
            {"name": "enrich_idea_context", "desc": "Combina tools para enriquecer la publicación"},
            {"name": "generate_publicacion_with_ollama", "desc": "Genera el post con LLM"},
            {"name": "save_publicacion", "desc": "Guarda la publicación + embedding en PostgreSQL"},
        ],
    }


# ── PostgreSQL ─────────────────────────────────────────────────
def save_publicacion(client_id: int, idea_id: int | None, content: str) -> int:
    embedding = generate_embedding(content)
    vector_str = embedding_to_vector(embedding)

    if vector_str:
        return execute_db(
            "INSERT INTO publicaciones_generadas (client_id, idea_id, content, embedding) "
            "VALUES (%s, %s, %s, %s::vector) RETURNING id",
            (client_id, idea_id, content, vector_str),
        )
    else:
        return execute_db(
            "INSERT INTO publicaciones_generadas (client_id, idea_id, content) "
            "VALUES (%s, %s, %s) RETURNING id",
            (client_id, idea_id, content),
        )


# ── Ollama (LLM) ───────────────────────────────────────────────
def generate_publicacion_with_ollama(prompt: str) -> str:
    try:
        resp = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()
    except Exception as exc:
        logger.error("Ollama error: %s", exc)
        return f"[FALLBACK] Publicación generada. Error: {exc}"


# ── Pipeline principal ─────────────────────────────────────────
def process_idea(idea: Idea):
    logger.info("━" * 60)
    logger.info("Idea recibida (client_id=%s): %s", idea.client_id, idea.content[:120])

    # ═══ PASO 1: Enriquecir contexto con tools ═══
    logger.info("[1/4] Ejecutando tools de enriquecimiento …")
    context = enrich_idea_context(idea.content, idea.client_id)
    logger.info("  ✓ Perfil de cliente y %d tendencias cargadas", context["stats"]["trends_found"])

    # ═══ PASO 2: Obtener topics en tendencia ═══
    logger.info("[2/4] Consultando topics en tendencia …")
    trending = fetch_trending_topics("marketing")
    trending_text = format_news_for_prompt(trending)
    logger.info("  ✓ %d trending topics", len(trending))
    context["trending"] = trending_text

    # ═══ PASO 3: Construir prompt enriquecido ═══
    logger.info("[3/4] Construyendo prompt enriquecido …")
    prompt = build_publicacion_prompt(idea.content, context)
    prompt += f"\n\n## Trending Topics (for hashtags)\n{trending_text}"
    logger.info("  ✓ Prompt de %d caracteres", len(prompt))

    # ═══ PASO 4: Generar publicación + guardar ═══
    logger.info("[4/4] Generando publicación con %s …", OLLAMA_MODEL)
    pub_content = generate_publicacion_with_ollama(prompt)
    logger.info("  ✓ Publicación: %s", pub_content[:150])

    pub_id = save_publicacion(idea.client_id, idea.brief_id, pub_content)
    logger.info("  ✓ Publicación guardada con id=%s + embedding", pub_id)
    logger.info("━" * 60)


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
            ch.queue_declare(queue="publication_queue")

            def on_message(ch, method, properties, body):
                try:
                    data = json.loads(body)
                    idea = Idea(**data)
                    process_idea(idea)
                except json.JSONDecodeError as exc:
                    logger.error("Mensaje no es JSON válido: %s", exc)
                except Exception as exc:
                    logger.exception("Error procesando mensaje: %s", exc)

            ch.basic_consume(
                queue="publication_queue", on_message_callback=on_message, auto_ack=True
            )
            logger.info("Esperando ideas en publication_queue …")
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
    t = threading.Thread(target=consume_messages, daemon=True)
    t.start()
    logger.info("Agente de Publicación iniciado — tools: cliente, tendencias, fuentes_externas")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
