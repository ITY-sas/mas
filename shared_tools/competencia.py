"""Tools para consultar referencias de competencia."""
import logging

from .db import execute_db, query_db
from .embeddings import embedding_to_vector, generate_embedding

logger = logging.getLogger(__name__)


def get_all_competitors(limit: int = 20) -> list[dict]:
    """Obtiene todas las referencias de competencia."""
    return query_db(
        "SELECT id, competidor, content, plataforma "
        "FROM referencias_competencia ORDER BY id DESC LIMIT %s",
        (limit,),
    )


def get_competitor_by_name(competidor: str, limit: int = 10) -> list[dict]:
    """Obtiene referencias de un competidor específico."""
    return query_db(
        "SELECT id, competidor, content, plataforma "
        "FROM referencias_competencia WHERE competidor ILIKE %s "
        "LIMIT %s",
        (f"%{competidor}%", limit),
    )


def get_relevant_competitors(query_text: str, limit: int = 5) -> list[dict]:
    """Busca referencias de competencia relevantes usando similitud vectorial."""
    embedding = generate_embedding(query_text)
    if embedding is None:
        logger.warning("Fallback: devolviendo referencias recientes")
        return get_all_competitors(limit)

    vector_str = embedding_to_vector(embedding)
    rows = query_db(
        "SELECT id, competidor, content, plataforma, "
        "1 - (embedding <=> %s::vector) as similarity "
        "FROM referencias_competencia "
        "WHERE embedding IS NOT NULL "
        "ORDER BY embedding <=> %s::vector "
        "LIMIT %s",
        (vector_str, vector_str, limit),
    )
    logger.info("Encontradas %d referencias de competencia", len(rows))
    return rows


def add_competitor_reference(
    competidor: str, content: str, plataforma: str = "general"
) -> int | None:
    """Agrega una referencia de competencia con embedding."""
    embedding = generate_embedding(content)
    vector_str = embedding_to_vector(embedding)

    if vector_str:
        return execute_db(
            "INSERT INTO referencias_competencia (competidor, content, plataforma, embedding) "
            "VALUES (%s, %s, %s, %s::vector) RETURNING id",
            (competidor, content, plataforma, vector_str),
        )
    else:
        return execute_db(
            "INSERT INTO referencias_competencia (competidor, content, plataforma) "
            "VALUES (%s, %s, %s) RETURNING id",
            (competidor, content, plataforma),
        )


def format_competitors(refs: list[dict]) -> str:
    """Formatea referencias de competencia como texto para el prompt."""
    if not refs:
        return "No hay referencias de competencia disponibles."
    lines = []
    for r in refs:
        comp = r.get("competidor", "Desconocido")
        content = r.get("content", "")
        plat = r.get("plataforma", "")
        lines.append(f"- [{comp} | {plat}] {content}")
    return "\n".join(lines)
