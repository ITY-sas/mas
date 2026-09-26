"""
Grafo LangGraph del agente de ideación (microservicio independiente).

    START → load_context → fetch_news → generate_idea → save_idea → END

Todas las operaciones de negocio se invocan como **contratos de API**
(Tools-as-a-Service vía ``ToolRegistry`` con Tool Discovery) y toda
llamada a LLM pasa por el **LLM Gateway**. El agente no importa
``shared_tools``: no ejecuta código de negocio directamente.
"""
from __future__ import annotations

import logging
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from common import gateway_client
from common.tool_client import ToolRegistry

from .prompts import SYSTEM_PROMPT, build_ideacion_prompt

logger = logging.getLogger("agente_ideacion.graph")

# Registro con descubrimiento de tools (manifiestos → endpoints)
REGISTRY = ToolRegistry()


class IdeacionState(TypedDict):
    # ── Entrada (desde agent.task.triggered) ──
    brief: dict
    client_id: int

    # ── Contexto recuperado vía tool services ──
    client_profile: str
    trends: str
    competitors: str
    similar_ideas: str
    news: str

    # ── Salida (hacia agent.task.completed) ──
    idea: str
    idea_id: int

    # ── Trazabilidad de herramientas usadas ──
    tool_calls: Annotated[list[str], operator.add]


# ── Nodos ──────────────────────────────────────────────────────
def load_context(state: IdeacionState) -> dict:
    """Perfil + tendencias + competencia + ideas similares vía REST."""
    client_id = state["client_id"]
    content = state["brief"]["content"]
    logger.info("[load_context] descubriendo/invocando tool services …")

    profile = REGISTRY.call("client", "profile", params={"client_id": client_id})
    trends = REGISTRY.call("trends", "search", params={"query": content, "limit": 5})
    competitors = REGISTRY.call(
        "competitors", "search", params={"query": content, "limit": 5}
    )
    similar = REGISTRY.call(
        "rag", "similar",
        json_body={"query": content, "limit": 3, "min_similarity": 0.3},
    )

    stats = {
        "trends": trends.get("count", 0),
        "competitors": competitors.get("count", 0),
        "similar_ideas": similar.get("count", 0),
    }
    logger.info("[load_context] contexto: %s", stats)
    return {
        "client_profile": profile.get("text", ""),
        "trends": trends.get("text", ""),
        "competitors": competitors.get("text", ""),
        "similar_ideas": similar.get("text", ""),
        "tool_calls": ["client.profile", "trends.search",
                       "competitors.search", "rag.similar"],
    }


def fetch_news(state: IdeacionState) -> dict:
    """Noticias externas (Google News RSS) vía tool service."""
    logger.info("[fetch_news] GET tool-news …")
    data = REGISTRY.call(
        "news", "news", params={"query": state["brief"]["content"], "limit": 3}
    )
    logger.info("[fetch_news] %s noticias", data.get("count", 0))
    return {"news": data.get("text", ""), "tool_calls": ["news.news"]}


def generate_idea(state: IdeacionState) -> dict:
    """Genera la idea con el LLM **a través del LLM Gateway**."""
    context = {
        "client_profile": state["client_profile"],
        "trends": state["trends"],
        "competitors": state["competitors"],
        "similar_ideas": state["similar_ideas"],
    }
    prompt = build_ideacion_prompt(state["brief"]["content"], context)
    if state.get("news"):
        prompt += f"\n\n## Recent News & Signals\n{state['news']}"

    logger.info("[generate_idea] POST llm-gateway (/v1/generate, prompt=%d chars)",
                len(prompt))
    response = gateway_client.generate(
        prompt, system=SYSTEM_PROMPT, timeout=240.0
    )
    idea = response.get("content", "")
    logger.info("[generate_idea] idea vía %s/%s (cached=%s): %s",
                response.get("provider"), response.get("model"),
                response.get("cached"), idea[:100])
    return {"idea": idea, "tool_calls": ["llm-gateway.generate"]}


def save_idea(state: IdeacionState) -> dict:
    """Persiste la idea (con embedding) — dueño: tool-rag."""
    logger.info("[save_idea] POST tool-rag /ideas …")
    data = REGISTRY.call(
        "rag", "save_idea",
        json_body={"client_id": state["client_id"], "content": state["idea"]},
    )
    idea_id = data.get("id", 0)
    logger.info("[save_idea] idea_id=%s", idea_id)
    return {"idea_id": idea_id, "tool_calls": ["rag.save_idea"]}


# ── Grafo ──────────────────────────────────────────────────────
def create_ideacion_graph(checkpointer=None):
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

    return builder.compile(checkpointer=checkpointer)
