"""
Tools compartidas para los microservicios de tools (Tools-as-a-Service).
Incluye: cliente, tendencias, competencia, RAG, embeddings, fuentes externas.

NB: los agentes NO importan este paquete (no ejecutan código de negocio):
las consumen exclusivamente los tool services vía contratos REST/AMQP.
"""
from .db import get_db_connection, query_db, execute_db
from .embeddings import generate_embedding, generate_embeddings_batch, embedding_to_vector
from .cliente import get_client_profile, get_client_by_name, list_all_clients, format_client_profile
from .tendencias import (
    get_all_trends, get_trends_by_categoria, get_relevant_trends,
    add_trend, format_trends,
)
from .competencia import (
    get_all_competitors, get_competitor_by_name, get_relevant_competitors,
    add_competitor_reference, format_competitors,
)
from .rag import search_similar_ideas, search_similar_content, store_embedding, format_ideas_for_prompt
from .fuentes_externas import (
    fetch_google_news, fetch_trending_topics, format_news_for_prompt,
)
