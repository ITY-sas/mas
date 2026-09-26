"""
Agente de Ideación
Pipeline: brief → tools de contexto → LLM enriquecido → PostgreSQL → publication_queue
"""
import json
import logging
import os
import sys
import threading
import time

# Fix encoding en Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pika
import requests
from fastapi import FastAPI
from pydantic import BaseModel

# ── Tools compartidas ──────────────────────────────────────────
from shared_tools import (
    build_ideacion_prompt,
    enrich_brief_context,
    embedding_to_vector,
    execute_db,
    fetch_google_news,
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
logger = logging.getLogger("agente_ideacion")

app = FastAPI(title="Agente de Ideación")


# ── Modelos de datos ───────────────────────────────────────────
class Brief(BaseModel):
    client_id: int
    content: str


class Idea(BaseModel):
    client_id: int
    content: str
    brief_id: int | None = None


# ── Endpoints FastAPI ──────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "ideacion"}


@app.get("/metrics")
async def metrics():
    return {
        "agent": "ideacion",
        "status": "running",
        "queue": "ideation_queue",
        "llm_model": OLLAMA_MODEL,
        "tools": ["cliente", "tendencias", "competencia", "rag", "fuentes_externas"],
    }


@app.get("/tools")
async def tools_info():
    """Lista las tools disponibles en este agente."""
    return {
        "agent": "ideacion",
        "tools": [
            {"name": "get_client_profile", "desc": "Lee el perfil de marca del cliente"},
            {"name": "get_relevant_trends", "desc": "Busca tendencias relevantes (RAG)"},
            {"name": "get_relevant_competitors", "desc": "Busca referencias de competencia (RAG)"},
            {"name": "search_similar_ideas", "desc": "Busca ideas previas similares (RAG)"},
            {"name": "fetch_google_news", "desc": "Obtiene noticias de Google News RSS"},
            {"name": "enrich_brief_context", "desc": "Combina todas las tools para enriquecer el contexto"},
            {"name": "generate_idea_with_ollama", "desc": "Genera la idea con LLM usando contexto enriquecido"},
            {"name": "save_idea", "desc": "Guarda la idea + embedding en PostgreSQL"},
        ],
    }


# ── PostgreSQL ─────────────────────────────────────────────────
def save_idea(client_id: int, content: str) -> int:
    """Guarda la idea generada (con embedding) y devuelve su ID."""
    embedding = generate_embedding(content)
    vector_str = embedding_to_vector(embedding)

    if vector_str:
        return execute_db(
            "INSERT INTO ideas_generadas (client_id, content, embedding) "
            "VALUES (%s, %s, %s::vector) RETURNING id",
            (client_id, content, vector_str),
        )
    else:
        return execute_db(
            "INSERT INTO ideas_generadas (client_id, content) VALUES (%s, %s) RETURNING id",
            (client_id, content),
        )


# ── Ollama (LLM) ───────────────────────────────────────────────
def generate_idea_with_ollama(prompt: str) -> str:
    """Llama a Ollama con el prompt enriquecido."""
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
        return f"[FALLBACK] Idea generada para el brief. Error: {exc}"


# ── Pipeline principal ─────────────────────────────────────────
def process_brief(brief: Brief):
    """Pipeline completo: brief → tools → LLM enriquecido → DB → publicación."""
    logger.info("━" * 60)
    logger.info("Brief recibido (client_id=%s): %s", brief.client_id, brief.content)

    # ═══ PASO 1: Enriquecer contexto con tools ═══
    logger.info("[1/5] Ejecutando tools de enriquecimiento …")
    context = enrich_brief_context(brief.content, brief.client_id)
    logger.info(
        "  ✓ Contexto: %d tendencias, %d competidores, %d ideas similares",
        context["stats"]["trends_found"],
        context["stats"]["competitors_found"],
        context["stats"]["similar_ideas_found"],
    )

    # ═══ PASO 2: Obtener noticias externas (Google News) ═══
    logger.info("[2/5] Consultando fuentes externas (Google News) …")
    news = fetch_google_news(brief.content, limit=3)
    news_text = format_news_for_prompt(news)
    logger.info("  ✓ %d noticias obtenidas", len(news))
    context["news"] = news_text

    # ═══ PASO 3: Construir prompt enriquecido ═══
    logger.info("[3/5] Construyendo prompt enriquecido …")
    prompt = build_ideacion_prompt(brief.content, context)
    prompt += f"\n\n## Recent News & Signals\n{news_text}"
    logger.info("  ✓ Prompt de %d caracteres", len(prompt))

    # ═══ PASO 4: Generar idea con Ollama ═══
    logger.info("[4/5] Generando idea con %s (puede tardar) …", OLLAMA_MODEL)
    idea_content = generate_idea_with_ollama(prompt)
    logger.info("  ✓ Idea generada: %s", idea_content[:150])

    # ═══ PASO 5: Guardar en PostgreSQL + publicar ═══
    logger.info("[5/5] Guardando en PostgreSQL …")
    idea_id = save_idea(brief.client_id, idea_content)
    logger.info("  ✓ Idea guardada con id=%s + embedding", idea_id)

    publish_idea(Idea(client_id=brief.client_id, content=idea_content, brief_id=idea_id))
    logger.info("  ✓ Idea publicada en publication_queue")
    logger.info("━" * 60)


# ── RabbitMQ ───────────────────────────────────────────────────
def _rabbitmq_params() -> pika.ConnectionParameters:
    return pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=5672,
        credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS),
    )


def publish_idea(idea: Idea):
    conn = pika.BlockingConnection(_rabbitmq_params())
    ch = conn.channel()
    ch.queue_declare(queue="publication_queue")
    ch.basic_publish(exchange="", routing_key="publication_queue", body=idea.json())
    conn.close()


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
                    process_brief(brief)
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
    t = threading.Thread(target=consume_messages, daemon=True)
    t.start()
    logger.info("Agente de Ideación iniciado — tools: cliente, tendencias, competencia, RAG, noticias")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
