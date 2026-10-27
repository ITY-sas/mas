"""Tools RAG (Retrieval Augmented Generation) con pgvector."""
import logging

from .db import execute_db, query_db
from .embeddings import embedding_to_vector, generate_embedding

logger = logging.getLogger(__name__)


class LifecycleConflictError(ValueError):
    """Operación rechazada por reglas de inmutabilidad o máquina de estados."""


def search_similar_ideas(
    brand_id: int,
    query_text: str,
    limit: int = 5,
    min_similarity: float = 0.0,
) -> list[dict]:
    """Busca ideas similares activas dentro de una marca usando similitud de coseno."""
    embedding = generate_embedding(query_text)
    if embedding is None:
        logger.warning("No se pudo generar embedding para la búsqueda")
        return []

    vector_str = embedding_to_vector(embedding)
    rows = query_db(
        "SELECT id, client_id, content, "
        "1 - (embedding <=> %s::vector) as similarity "
        "FROM ideas_generadas "
        "WHERE brand_id = %s AND embedding IS NOT NULL "
        "AND COALESCE(status, 'approved') != 'archived' "
        "ORDER BY embedding <=> %s::vector "
        "LIMIT %s",
        (vector_str, brand_id, vector_str, limit),
    )
    # Filtrar por similitud mínima
    results = [r for r in rows if r.get("similarity", 0) >= min_similarity]
    logger.info("RAG: %d ideas similares encontradas (de %d candidatas)", len(results), len(rows))
    return results


def search_similar_content(
    table: str,
    brand_id: int | None,
    query_text: str,
    limit: int = 5,
    min_similarity: float = 0.0,
) -> list[dict]:
    """Búsqueda RAG genérica en cualquier tabla con columna embedding."""
    # Whitelist de tablas permitidas para evitar SQL injection
    allowed_tables = {"ideas_generadas", "publicaciones_generadas", "tendencias", "referencias_competencia", "clientes"}
    if table not in allowed_tables:
        raise ValueError(f"Tabla no permitida: {table}")
    if table in {"ideas_generadas", "publicaciones_generadas"} and brand_id is None:
        raise ValueError(f"brand_id es obligatorio para buscar en {table}")

    embedding = generate_embedding(query_text)
    if embedding is None:
        return []

    vector_str = embedding_to_vector(embedding)
    scope_sql = " AND brand_id = %s" if brand_id is not None and table in {
        "ideas_generadas", "publicaciones_generadas"
    } else ""
    lifecycle_sql = " AND COALESCE(status, 'approved') != 'archived'" if table in {
        "ideas_generadas", "publicaciones_generadas"
    } else ""
    params = (vector_str, brand_id, vector_str, limit) if scope_sql else (vector_str, vector_str, limit)
    rows = query_db(
        f"SELECT id, content, 1 - (embedding <=> %s::vector) as similarity "
        f"FROM {table} "
        f"WHERE embedding IS NOT NULL{scope_sql}{lifecycle_sql} "
        f"ORDER BY embedding <=> %s::vector "
        f"LIMIT %s",
        params,
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


def update_idea(
    idea_id: int,
    brand_id: int,
    content: str,
    status: str | None = None,
) -> dict:
    """Actualiza una idea, regenerando su embedding y marcando updated_at."""
    existing = query_db(
        "SELECT id, brand_id, status FROM ideas_generadas WHERE id = %s AND brand_id = %s",
        (idea_id, brand_id),
    )
    if not existing:
        raise ValueError(f"Idea {idea_id} no encontrada para la marca {brand_id}")

    if existing[0].get("status") == "archived":
        raise LifecycleConflictError("No se puede editar una idea archivada")

    embedding = generate_embedding(content)
    vec = embedding_to_vector(embedding)

    new_status = status or existing[0].get("status") or "approved"
    if vec:
        execute_db(
            "UPDATE ideas_generadas SET content = %s, embedding = %s::vector, "
            "status = %s, updated_at = NOW() WHERE id = %s AND brand_id = %s",
            (content, vec, new_status, idea_id, brand_id),
        )
    else:
        execute_db(
            "UPDATE ideas_generadas SET content = %s, status = %s, updated_at = NOW() "
            "WHERE id = %s AND brand_id = %s",
            (content, new_status, idea_id, brand_id),
        )
    return {"id": idea_id, "brand_id": brand_id, "status": new_status, "content": content}


def delete_idea(idea_id: int, brand_id: int) -> dict:
    """Soft-delete de una idea. Rechaza si tiene publicaciones enviadas a redes."""
    existing = query_db(
        "SELECT id, brand_id, status FROM ideas_generadas WHERE id = %s AND brand_id = %s",
        (idea_id, brand_id),
    )
    if not existing:
        raise ValueError(f"Idea {idea_id} no encontrada para la marca {brand_id}")

    current_status = existing[0].get("status")
    if current_status == "archived":
        return {"id": idea_id, "brand_id": brand_id, "status": "archived", "already_archived": True}

    # Validar si tiene publicaciones enviadas o activas
    pubs = query_db(
        "SELECT id, status FROM publicaciones_generadas "
        "WHERE idea_id = %s AND brand_id = %s AND status IN ('sent_to_postiz', 'published')",
        (idea_id, brand_id),
    )
    if pubs or current_status == "published":
        raise LifecycleConflictError(
            "No se puede eliminar la idea: ya tiene publicaciones despachadas a redes sociales"
        )

    # Soft delete de la idea
    execute_db(
        "UPDATE ideas_generadas SET status = 'archived', deleted_at = NOW(), updated_at = NOW() "
        "WHERE id = %s AND brand_id = %s",
        (idea_id, brand_id),
    )
    # Archivar borradores derivados que no se hayan enviado
    execute_db(
        "UPDATE publicaciones_generadas SET status = 'archived', deleted_at = NOW(), updated_at = NOW() "
        "WHERE idea_id = %s AND brand_id = %s AND status NOT IN ('sent_to_postiz', 'published')",
        (idea_id, brand_id),
    )
    logger.info("Idea %s archivada exitosamente (soft delete)", idea_id)
    return {"id": idea_id, "brand_id": brand_id, "status": "archived"}


def get_publicacion(pub_id: int, brand_id: int) -> dict | None:
    """Obtiene una publicación de una marca."""
    rows = query_db(
        "SELECT id, brand_id, client_id, idea_id, platform, status, content, created_at, updated_at "
        "FROM publicaciones_generadas WHERE id = %s AND brand_id = %s LIMIT 1",
        (pub_id, brand_id),
    )
    return rows[0] if rows else None


def list_publicaciones(
    brand_id: int,
    idea_id: int | None = None,
    include_archived: bool = False,
) -> list[dict]:
    """Lista publicaciones de una marca."""
    conditions = ["brand_id = %s"]
    params: list = [brand_id]
    if idea_id is not None:
        conditions.append("idea_id = %s")
        params.append(idea_id)
    if not include_archived:
        conditions.append("COALESCE(status, 'draft') != 'archived'")
    where = " AND ".join(conditions)
    return query_db(
        f"SELECT id, brand_id, client_id, idea_id, platform, status, content, created_at, updated_at "
        f"FROM publicaciones_generadas WHERE {where} ORDER BY id DESC",
        tuple(params),
    )


def update_publicacion(
    pub_id: int,
    brand_id: int,
    content: str,
    status: str | None = None,
) -> dict:
    """Actualiza una publicación. Si ya fue enviada a Postiz, bloquea la edición."""
    existing = get_publicacion(pub_id, brand_id)
    if not existing:
        raise ValueError(f"Publicación {pub_id} no encontrada para la marca {brand_id}")

    current_status = existing.get("status")
    if current_status in {"sent_to_postiz", "published"}:
        raise LifecycleConflictError(
            "Publicación inmutable: ya fue enviada a redes sociales y no puede ser modificada"
        )
    if current_status == "archived":
        raise LifecycleConflictError("No se puede editar una publicación archivada")

    embedding = generate_embedding(content)
    vec = embedding_to_vector(embedding)
    new_status = status or current_status or "draft"

    if vec:
        execute_db(
            "UPDATE publicaciones_generadas SET content = %s, embedding = %s::vector, "
            "status = %s, updated_at = NOW() WHERE id = %s AND brand_id = %s",
            (content, vec, new_status, pub_id, brand_id),
        )
    else:
        execute_db(
            "UPDATE publicaciones_generadas SET content = %s, status = %s, updated_at = NOW() "
            "WHERE id = %s AND brand_id = %s",
            (content, new_status, pub_id, brand_id),
        )
    return {"id": pub_id, "brand_id": brand_id, "status": new_status, "content": content}


def delete_publicacion(pub_id: int, brand_id: int) -> dict:
    """Soft-delete de una publicación. Bloquea si ya fue enviada a redes."""
    existing = get_publicacion(pub_id, brand_id)
    if not existing:
        raise ValueError(f"Publicación {pub_id} no encontrada para la marca {brand_id}")

    current_status = existing.get("status")
    if current_status in {"sent_to_postiz", "published"}:
        raise LifecycleConflictError(
            "No se puede eliminar: la publicación ya fue enviada a redes sociales"
        )
    if current_status == "archived":
        return {"id": pub_id, "brand_id": brand_id, "status": "archived", "already_archived": True}

    execute_db(
        "UPDATE publicaciones_generadas SET status = 'archived', deleted_at = NOW(), updated_at = NOW() "
        "WHERE id = %s AND brand_id = %s",
        (pub_id, brand_id),
    )
    logger.info("Publicación %s archivada exitosamente (soft delete)", pub_id)
    return {"id": pub_id, "brand_id": brand_id, "status": "archived"}


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
