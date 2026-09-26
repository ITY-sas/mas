"""
Grafo LangGraph del agente de publicación (microservicio independiente).

    START → load_context → fetch_trending → generate_post → save_post → END

Recibe la idea del orquestador vía ``agent.task.triggered`` y devuelve la
publicación vía ``agent.task.completed``. Todo acceso a datos va por
contratos REST de los tool services; el LLM pasa por el LLM Gateway.
"""
from __future__ import annotations

import logging
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from common import gateway_client
from common.tool_client import ToolRegistry

from .prompts import SYSTEM_PROMPT, build_publicacion_prompt

logger = logging.getLogger("agente_publicacion.graph")

REGISTRY = ToolRegistry()


class PublicacionState(TypedDict):
    # ── Entrada (desde agent.task.triggered) ──
    idea: str
    client_id: int
    idea_id: int

    # ── Contexto recuperado vía tool services ──
    client_profile: str
    trends: str
    trending: str

    # ── Salida (hacia agent.task.completed) ──
    publication: str
    publication_id: int

    # ── Trazabilidad de herramientas usadas ──
    tool_calls: Annotated[list[str], operator.add]


# ── Nodos ──────────────────────────────────────────────────────
def load_context(state: PublicacionState) -> dict:
    """Perfil del cliente (tono) + tendencias relevantes vía REST."""
    client_id = state["client_id"]
    idea = state["idea"]
    logger.info("[load_context] descubriendo/invocando tool services …")

    profile = REGISTRY.call("client", "profile", params={"client_id": client_id})
    trends = REGISTRY.call("trends", "search", params={"query": idea, "limit": 3})

    logger.info("[load_context] %s tendencias para la idea", trends.get("count", 0))
    return {
        "client_profile": profile.get("text", ""),
        "trends": trends.get("text", ""),
        "tool_calls": ["client.profile", "trends.search"],
    }


def fetch_trending(state: PublicacionState) -> dict:
    """Topics en tendencia (hashtags) vía tool service."""
    logger.info("[fetch_trending] GET tool-trending …")
    data = REGISTRY.call("trending", "trending", params={"query": "marketing"})
    logger.info("[fetch_trending] %s topics", data.get("count", 0))
    return {"trending": data.get("text", ""), "tool_calls": ["trending.trending"]}


def generate_post(state: PublicacionState) -> dict:
    """Genera la publicación con el LLM **a través del LLM Gateway**."""
    context = {
        "client_profile": state["client_profile"],
        "trends": state["trends"],
    }
    prompt = build_publicacion_prompt(state["idea"], context)
    if state.get("trending"):
        prompt += f"\n\n## Trending Topics (for hashtags)\n{state['trending']}"

    logger.info("[generate_post] POST llm-gateway (/v1/generate, prompt=%d chars)",
                len(prompt))
    response = gateway_client.generate(
        prompt, system=SYSTEM_PROMPT, temperature=0.7, timeout=240.0
    )
    publication = response.get("content", "")
    logger.info("[generate_post] publicación vía %s/%s (cached=%s): %s",
                response.get("provider"), response.get("model"),
                response.get("cached"), publication[:100])
    return {"publication": publication, "tool_calls": ["llm-gateway.generate"]}


def save_post(state: PublicacionState) -> dict:
    """Persiste la publicación (con embedding) — dueño: tool-rag."""
    logger.info("[save_post] POST tool-rag /publicaciones …")
    data = REGISTRY.call(
        "rag", "save_publicacion",
        json_body={
            "client_id": state["client_id"],
            "content": state["publication"],
            "idea_id": state.get("idea_id") or None,
        },
    )
    publication_id = data.get("id", 0)
    logger.info("[save_post] publication_id=%s", publication_id)
    return {"publication_id": publication_id, "tool_calls": ["rag.save_publicacion"]}


# ── Grafo ──────────────────────────────────────────────────────
def create_publicacion_graph(checkpointer=None):
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

    return builder.compile(checkpointer=checkpointer)
