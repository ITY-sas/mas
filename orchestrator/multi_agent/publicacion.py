"""
Agente de Publicación — LangGraph StateGraph.

Flujo:
  START → load_context → fetch_trending → generate_post → save_post → END

Recibe la idea generada por el agente de ideación (a través del estado del supervisor).
"""
import logging
import os

from langgraph.graph import END, START, StateGraph

from .state import PublicacionState

logger = logging.getLogger("publicacion_graph")


def _ollama_base_url() -> str:
    host = os.getenv("OLLAMA_HOST", "ollama")
    port = os.getenv("OLLAMA_PORT", "11434")
    if host.startswith("0.0.0.0"):
        host = host.replace("0.0.0.0", "127.0.0.1", 1)
    if ":" in host and not host.startswith("["):
        return f"http://{host}"
    return f"http://{host}:{port or '11434'}"


def _get_llm():
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "gemma3:4b"),
        base_url=_ollama_base_url(),
    )


# ── Nodos ──────────────────────────────────────────────────────
def load_context(state: PublicacionState) -> dict:
    """Carga perfil de cliente (tono) y tendencias relevantes para la publicación."""
    from shared_tools.enrichment import enrich_idea_context

    idea = state["idea"]
    client_id = state["client_id"]
    logger.info("[load_context] Enriqueciendo contexto de publicación …")

    context = enrich_idea_context(idea, client_id)
    return {
        "client_profile": context["client_profile"],
        "trends": context["trends"],
    }


def fetch_trending(state: PublicacionState) -> dict:
    """Obtiene topics en tendencia para hashtags."""
    from shared_tools.fuentes_externas import fetch_trending_topics, format_news_for_prompt

    logger.info("[fetch_trending] Consultando trending topics …")
    trending = fetch_trending_topics("marketing")
    logger.info("[fetch_trending] %d topics obtenidos", len(trending))
    return {"trending": format_news_for_prompt(trending)}


def generate_post(state: PublicacionState) -> dict:
    """Genera la publicación con el LLM."""
    from shared_tools.enrichment import build_publicacion_prompt

    idea = state["idea"]
    context = {
        "client_profile": state["client_profile"],
        "trends": state["trends"],
    }
    prompt = build_publicacion_prompt(idea, context)
    prompt += f"\n\n## Trending Topics (for hashtags)\n{state.get('trending', '')}"

    logger.info("[generate_post] Invocando LLM (prompt=%d chars) …", len(prompt))
    llm = _get_llm()
    response = llm.invoke(prompt)
    publication = response.content
    logger.info("[generate_post] Publicación generada: %s", publication[:120])
    return {"publication": publication}


def save_post(state: PublicacionState) -> dict:
    """Guarda la publicación + embedding en PostgreSQL."""
    from shared_tools.db import execute_db
    from shared_tools.embeddings import embedding_to_vector, generate_embedding

    publication = state["publication"]
    client_id = state["client_id"]
    idea_id = state.get("idea_id")

    embedding = generate_embedding(publication)
    vec = embedding_to_vector(embedding)

    if vec:
        pub_id = execute_db(
            "INSERT INTO publicaciones_generadas (client_id, idea_id, content, embedding) "
            "VALUES (%s, %s, %s, %s::vector) RETURNING id",
            (client_id, idea_id, publication, vec),
        )
    else:
        pub_id = execute_db(
            "INSERT INTO publicaciones_generadas (client_id, idea_id, content) "
            "VALUES (%s, %s, %s) RETURNING id",
            (client_id, idea_id, publication),
        )

    logger.info("[save_post] Publicación guardada con id=%s", pub_id)
    return {"publication_id": pub_id}


# ── Grafo ──────────────────────────────────────────────────────
def create_publicacion_graph():
    """Compila el StateGraph del agente de publicación."""
    builder = StateGraph(PublicacionState)

    builder.add_node("load_context", load_context)
    builder.add_node("fetch_trending", fetch_trending)
    builder.add_node("generate_post", generate_post)
    builder.add_node("save_post", save_post)

    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "fetch_trending")
    builder.add_edge("fetch_trending", "generate_post")
    builder.add_edge("generate_post", "save_post")
    builder.add_edge("save_post", END)

    return builder.compile()
