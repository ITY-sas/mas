"""
Agente de Ideación — LangGraph StateGraph.

Flujo:
  START → load_context → fetch_news → generate_idea → save_idea → END

Cada nodo es determinista salvo `generate_idea`, que invoca el LLM (Ollama).
"""
import logging
import os

from langgraph.graph import END, START, StateGraph

from .state import IdeacionState

logger = logging.getLogger("ideacion_graph")


def _ollama_base_url() -> str:
    """Construye la URL base de Ollama manejando host con o sin puerto."""
    host = os.getenv("OLLAMA_HOST", "ollama")
    port = os.getenv("OLLAMA_PORT", "11434")
    if host.startswith("0.0.0.0"):
        host = host.replace("0.0.0.0", "127.0.0.1", 1)
    if ":" in host and not host.startswith("["):
        return f"http://{host}"
    return f"http://{host}:{port or '11434'}"


def _get_llm():
    """Devuelve un ChatOllama configurado con el host/modelo del entorno."""
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "gemma3:4b"),
        base_url=_ollama_base_url(),
    )


# ── Nodos ──────────────────────────────────────────────────────
def load_context(state: IdeacionState) -> dict:
    """Carga perfil de cliente, tendencias, competencia e ideas similares."""
    from shared_tools.enrichment import enrich_brief_context

    brief = state["brief"]
    client_id = state["client_id"]
    logger.info("[load_context] Enriqueciendo contexto para client_id=%s", client_id)

    context = enrich_brief_context(brief["content"], client_id)
    return {
        "client_profile": context["client_profile"],
        "trends": context["trends"],
        "competitors": context["competitors"],
        "similar_ideas": context["similar_ideas"],
    }


def fetch_news(state: IdeacionState) -> dict:
    """Obtiene noticias externas de Google News RSS."""
    from shared_tools.fuentes_externas import fetch_google_news, format_news_for_prompt

    brief = state["brief"]
    logger.info("[fetch_news] Consultando Google News …")
    news = fetch_google_news(brief["content"], limit=3)
    logger.info("[fetch_news] %d noticias obtenidas", len(news))
    return {"news": format_news_for_prompt(news)}


def generate_idea(state: IdeacionState) -> dict:
    """Genera la idea con el LLM usando el prompt enriquecido."""
    from shared_tools.enrichment import build_ideacion_prompt

    brief = state["brief"]
    context = {
        "client_profile": state["client_profile"],
        "trends": state["trends"],
        "competitors": state["competitors"],
        "similar_ideas": state["similar_ideas"],
    }
    prompt = build_ideacion_prompt(brief["content"], context)
    prompt += f"\n\n## Recent News & Signals\n{state.get('news', '')}"

    logger.info("[generate_idea] Invocando LLM (prompt=%d chars) …", len(prompt))
    llm = _get_llm()
    response = llm.invoke(prompt)
    idea = response.content
    logger.info("[generate_idea] Idea generada: %s", idea[:120])
    return {"idea": idea}


def save_idea(state: IdeacionState) -> dict:
    """Guarda la idea + embedding en PostgreSQL."""
    from shared_tools.db import execute_db
    from shared_tools.embeddings import embedding_to_vector, generate_embedding

    idea = state["idea"]
    client_id = state["client_id"]

    embedding = generate_embedding(idea)
    vec = embedding_to_vector(embedding)

    if vec:
        idea_id = execute_db(
            "INSERT INTO ideas_generadas (client_id, content, embedding) "
            "VALUES (%s, %s, %s::vector) RETURNING id",
            (client_id, idea, vec),
        )
    else:
        idea_id = execute_db(
            "INSERT INTO ideas_generadas (client_id, content) VALUES (%s, %s) RETURNING id",
            (client_id, idea),
        )

    logger.info("[save_idea] Idea guardada con id=%s", idea_id)
    return {"idea_id": idea_id}


# ── Grafo ──────────────────────────────────────────────────────
def create_ideacion_graph():
    """Compila el StateGraph del agente de ideación."""
    builder = StateGraph(IdeacionState)

    builder.add_node("load_context", load_context)
    builder.add_node("fetch_news", fetch_news)
    builder.add_node("generate_idea", generate_idea)
    builder.add_node("save_idea", save_idea)

    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "fetch_news")
    builder.add_edge("fetch_news", "generate_idea")
    builder.add_edge("generate_idea", "save_idea")
    builder.add_edge("save_idea", END)

    return builder.compile()
