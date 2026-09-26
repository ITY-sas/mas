"""Generación de embeddings — siempre vía **LLM Gateway**.

Requisito de arquitectura: centralización de LLM. Ningún componente habla
directamente con Ollama; el gateway aplica balanceo de carga, reintentos
(exponential backoff), fallback entre proveedores y caché de prompts.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def generate_embedding(text: str) -> Optional[list[float]]:
    """Genera un embedding para un texto. Devuelve ``None`` si el gateway falla."""
    try:
        from common import gateway_client

        vectors = gateway_client.embed([text], timeout=30)
        return vectors[0] if vectors else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error generando embedding (LLM Gateway): %s", exc)
        return None


def generate_embeddings_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """Genera embeddings por lote con una sola llamada al gateway."""
    if not texts:
        return []
    try:
        from common import gateway_client

        vectors = gateway_client.embed(texts, timeout=60)
        return [vectors[i] if i < len(vectors) else None for i in range(len(texts))]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error generando embeddings por lote (LLM Gateway): %s", exc)
        return [None] * len(texts)


def embedding_to_vector(embedding: list[float]) -> Optional[str]:
    """Convierte una lista de floats al formato vector de pgvector: '[1,2,3]'."""
    if embedding is None:
        return None
    return "[" + ",".join(str(x) for x in embedding) + "]"
