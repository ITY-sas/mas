"""Generación de embeddings usando Ollama."""
import logging
import os

import requests


def _build_ollama_url() -> str:
    """Construye la URL base de Ollama, manejando host con o sin puerto."""
    host = os.getenv("OLLAMA_HOST", "localhost")
    port = os.getenv("OLLAMA_PORT", "11434")

    # 0.0.0.0 es dirección de escucha, no válida como cliente
    if host.startswith("0.0.0.0"):
        host = host.replace("0.0.0.0", "127.0.0.1", 1)

    # Si OLLAMA_HOST ya contiene ":puerto", usarlo directamente
    if ":" in host and not host.startswith("["):
        return f"http://{host}"
    # Si OLLAMA_PORT está vacío, usar 11434 por defecto
    if not port:
        port = "11434"
    return f"http://{host}:{port}"


OLLAMA_URL = _build_ollama_url()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

logger = logging.getLogger(__name__)
logger.debug("Ollama URL: %s, modelo embeddings: %s", OLLAMA_URL, EMBEDDING_MODEL)


def generate_embedding(text: str) -> list[float] | None:
    """Genera un embedding para un texto usando Ollama."""
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
    except Exception as exc:
        logger.warning("Error generando embedding: %s", exc)
        return None


def generate_embeddings_batch(texts: list[str]) -> list[list[float] | None]:
    """Genera embeddings para una lista de textos."""
    return [generate_embedding(t) for t in texts]


def embedding_to_vector(embedding: list[float]) -> str | None:
    """Convierte una lista de floats al formato vector de pgvector: '[1,2,3]'."""
    if embedding is None:
        return None
    return "[" + ",".join(str(x) for x in embedding) + "]"
