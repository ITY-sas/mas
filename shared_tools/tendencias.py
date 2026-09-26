"""Tools para consultar tendencias del mercado."""
import logging

from .db import execute_db, query_db
from .embeddings import embedding_to_vector, generate_embedding

logger = logging.getLogger(__name__)


def get_all_trends(limit: int = 20) -> list[dict]:
    """Obtiene todas las tendencias ordenadas por fecha."""
    return query_db(
        "SELECT id, categoria, content, fuente, fecha "
        "FROM tendencias ORDER BY fecha DESC LIMIT %s",
        (limit,),
    )


def get_trends_by_categoria(categoria: str, limit: int = 10) -> list[dict]:
    """Obtiene tendencias de una categoría específica."""
    return query_db(
        "SELECT id, categoria, content, fuente, fecha "
        "FROM tendencias WHERE categoria ILIKE %s "
        "ORDER BY fecha DESC LIMIT %s",
        (f"%{categoria}%", limit),
    )


def get_relevant_trends(query_text: str, limit: int = 5) -> list[dict]:
    """Busca tendencias relevantes al texto usando similitud vectorial."""
    embedding = generate_embedding(query_text)
    if embedding is None:
        # Fallback: obtener las más recientes
        logger.warning("Fallback: devolviendo tendencias recientes")
        return get_all_trends(limit)

    vector_str = embedding_to_vector(embedding)
    rows = query_db(
        "SELECT id, categoria, content, fuente, fecha, "
        "1 - (embedding <=> %s::vector) as similarity "
        "FROM tendencias "
        "WHERE embedding IS NOT NULL "
        "ORDER BY embedding <=> %s::vector "
        "LIMIT %s",
        (vector_str, vector_str, limit),
    )
    logger.info("Encontradas %d tendencias relevantes", len(rows))
    return rows


def add_trend(categoria: str, content: str, fuente: str = "manual") -> int | None:
    """Agrega una nueva tendencia y genera su embedding."""
    embedding = generate_embedding(content)
    vector_str = embedding_to_vector(embedding)

    if vector_str:
        return execute_db(
            "INSERT INTO tendencias (categoria, content, fuente, embedding) "
            "VALUES (%s, %s, %s, %s::vector) RETURNING id",
            (categoria, content, fuente, vector_str),
        )
    else:
        return execute_db(
            "INSERT INTO tendencias (categoria, content, fuente) "
            "VALUES (%s, %s, %s) RETURNING id",
            (categoria, content, fuente),
        )


def format_trends(trends: list[dict]) -> str:
    """Formatea tendencias como texto para el prompt."""
    if not trends:
        return "No hay tendencias disponibles."
    lines = []
    for t in trends:
        cat = t.get("categoria", "General")
        content = t.get("content", "")
        sim = t.get("similarity")
        sim_str = f" (relevancia: {sim:.2f})" if sim else ""
        lines.append(f"- [{cat}] {content}{sim_str}")
    return "\n".join(lines)
