"""Tools RAG (Retrieval Augmented Generation) con pgvector."""
import logging

from .db import execute_db, query_db
from .embeddings import embedding_to_vector, generate_embedding

logger = logging.getLogger(__name__)


def search_similar_ideas(query_text: str, limit: int = 5, min_similarity: float = 0.0) -> list[dict]:
    """Busca ideas similares en la base de datos usando similitud de coseno."""
    embedding = generate_embedding(query_text)
    if embedding is None:
        logger.warning("No se pudo generar embedding para la búsqueda")
        return []

    vector_str = embedding_to_vector(embedding)
    rows = query_db(
        "SELECT id, client_id, content, "
        "1 - (embedding <=> %s::vector) as similarity "
        "FROM ideas_generadas "
        "WHERE embedding IS NOT NULL "
        "ORDER BY embedding <=> %s::vector "
        "LIMIT %s",
        (vector_str, vector_str, limit),
    )
    # Filtrar por similitud mínima
    results = [r for r in rows if r.get("similarity", 0) >= min_similarity]
    logger.info("RAG: %d ideas similares encontradas (de %d candidatas)", len(results), len(rows))
    return results


def search_similar_content(
    table: str, query_text: str, limit: int = 5, min_similarity: float = 0.0
) -> list[dict]:
    """Búsqueda RAG genérica en cualquier tabla con columna embedding."""
    # Whitelist de tablas permitidas para evitar SQL injection
    allowed_tables = {"ideas_generadas", "publicaciones_generadas", "tendencias", "referencias_competencia", "clientes"}
    if table not in allowed_tables:
        raise ValueError(f"Tabla no permitida: {table}")

    embedding = generate_embedding(query_text)
    if embedding is None:
        return []

    vector_str = embedding_to_vector(embedding)
    rows = query_db(
        f"SELECT id, content, 1 - (embedding <=> %s::vector) as similarity "
        f"FROM {table} "
        f"WHERE embedding IS NOT NULL "
        f"ORDER BY embedding <=> %s::vector "
        f"LIMIT %s",
        (vector_str, vector_str, limit),
    )
    return [r for r in rows if r.get("similarity", 0) >= min_similarity]


def store_embedding(table: str, record_id: int, content: str) -> bool:
    """Genera y guarda el embedding de un registro existente."""
    allowed_tables = {"ideas_generadas", "publicaciones_generadas", "tendencias", "referencias_competencia", "clientes"}
    if table not in allowed_tables:
        raise ValueError(f"Tabla no permitida: {table}")

    embedding = generate_embedding(content)
    if embedding is None:
        return False

    vector_str = embedding_to_vector(embedding)
    execute_db(
        f"UPDATE {table} SET embedding = %s::vector WHERE id = %s",
        (vector_str, record_id),
    )
    return True


def format_ideas_for_prompt(ideas: list[dict]) -> str:
    """Formatea ideas similares como contexto para el prompt."""
    if not ideas:
        return "No hay ideas previas similares."
    lines = []
    for i in ideas:
        sim = i.get("similarity", 0)
        content = i.get("content", "")[:200]
        lines.append(f"- (similitud: {sim:.2f}) {content}")
    return "\n".join(lines)
