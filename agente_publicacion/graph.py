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
    brand_id: int
    idea_id: int
    preproduction: dict
    postiz_config: dict
    publication_action: str
    publish_mode: str
    publish_at: str | None
    postiz_integration_ids: list[str]
    postiz_settings: dict
    target_channels: list[dict]

    # ── Contexto recuperado vía tool services ──
    client_profile: str
    trends: str
    trending: str

    # ── Salida (hacia agent.task.completed) ──
    publication: str
    publication_id: int
    publication_variants: list[dict]
    postiz: dict

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
    integration_ids = state.get("postiz_integration_ids", [])
    target_channels = []
    if integration_ids:
        channel_data = REGISTRY.call(
            "postiz",
            "channels",
            params={"brand_id": state["brand_id"], "integration_ids": integration_ids},
        )
        target_channels = channel_data.get("channels", [])

    logger.info("[load_context] %s tendencias para la idea", trends.get("count", 0))
    return {
        "client_profile": profile.get("text", ""),
        "trends": trends.get("text", ""),
        "target_channels": target_channels,
        "tool_calls": ["client.profile", "trends.search"]
        + (["postiz.channels"] if integration_ids else []),
    }


def fetch_trending(state: PublicacionState) -> dict:
    """Topics en tendencia (hashtags) vía tool service."""
    logger.info("[fetch_trending] GET tool-trending …")
    data = REGISTRY.call("trending", "trending", params={"query": state["idea"]})
    logger.info("[fetch_trending] %s topics", data.get("count", 0))
    return {"trending": data.get("text", ""), "tool_calls": ["trending.trending"]}


def generate_post(state: PublicacionState) -> dict:
    """Genera la publicación con el LLM **a través del LLM Gateway**."""
    context = {
        "client_profile": state["client_profile"],
        "trends": state["trends"],
        "preproduction": state.get("preproduction", {}),
    }
    channels = state.get("target_channels", [])
    platform_groups: dict[str, list[dict]] = {}
    if channels:
        for channel in channels:
            platform = str(channel.get("provider") or "social").strip().lower()
            platform = "x" if platform == "twitter" else platform
            platform_groups.setdefault(platform, []).append(channel)
    else:
        platform_groups[""] = []

    variants = []
    tool_calls = []
    for platform, platform_channels in platform_groups.items():
        prompt = build_publicacion_prompt(state["idea"], context, platform=platform or None)
        if state.get("trending"):
            prompt += f"\n\n## Trending Topics (for hashtags)\n{state['trending']}"

        logger.info("[generate_post] generando variante platform=%s prompt=%d chars",
                    platform or "platform-neutral", len(prompt))
        response = gateway_client.generate(
            prompt, system=SYSTEM_PROMPT, temperature=0.7, timeout=240.0
        )
        content = response.get("content", "").strip()
        variants.append({
            "platform": platform or "platform-neutral",
            "integration_ids": [channel["external_id"] for channel in platform_channels],
            "content": content,
        })
        tool_calls.append("llm-gateway.generate")
        logger.info("[generate_post] variante %s vía %s/%s (cached=%s)",
                    platform or "platform-neutral", response.get("provider"),
                    response.get("model"), response.get("cached"))

    return {
        "publication": variants[0]["content"] if variants else "",
        "publication_variants": variants,
        "tool_calls": tool_calls,
    }


def save_post(state: PublicacionState) -> dict:
    """Persiste la publicación (con embedding) — dueño: tool-rag."""
    logger.info("[save_post] POST tool-rag /publicaciones …")
    variants = state.get("publication_variants") or [{
        "platform": "platform-neutral",
        "integration_ids": [],
        "content": state["publication"],
    }]
    saved_variants = []
    for variant in variants:
        logger.info("[save_post] persistiendo variante %s", variant["platform"])
        data = REGISTRY.call(
            "rag", "save_publicacion",
            json_body={
                "brand_id": state["brand_id"],
                "client_id": state["client_id"],
                "content": variant["content"],
                "idea_id": state.get("idea_id") or None,
                "platform": variant["platform"],
            },
        )
        saved_variants.append({**variant, "publication_id": data.get("id", 0)})

    return {
        "publication_id": saved_variants[0]["publication_id"] if saved_variants else 0,
        "publication_variants": saved_variants,
        "tool_calls": ["rag.save_publicacion"] * len(saved_variants),
    }


def schedule_post(state: PublicacionState) -> dict:
    """Crea un borrador/programación en Postiz cuando el brief lo solicita."""
    integration_ids = state.get("postiz_integration_ids", [])
    if state.get("publication_action", "prepare") != "deliver":
        return {
            "postiz": {
                "status": "prepared",
                "mode": state.get("publish_mode", "draft"),
                "publish_at": state.get("publish_at"),
                "integrations": integration_ids,
            }
        }
    if not integration_ids:
        return {"postiz": {"status": "skipped", "reason": "sin canales Postiz"}}

    channels_by_id = {
        channel["external_id"]: channel
        for channel in state.get("target_channels", [])
    }
    ready_ids = [
        integration_id
        for integration_id in integration_ids
        if channels_by_id.get(integration_id, {}).get("configured")
    ]
    skipped_ids = [integration_id for integration_id in integration_ids if integration_id not in ready_ids]
    if not ready_ids:
        return {
            "postiz": {
                "status": "skipped",
                "reason": "canales sin settings Postiz __type",
                "mode": state.get("publish_mode", "draft"),
                "publish_at": state.get("publish_at"),
                "integrations": skipped_ids,
            }
        }

    try:
        result = REGISTRY.call(
            "postiz",
            "create_post",
            json_body={
                "brand_id": state["brand_id"],
                "content": state["publication"],
                "integration_ids": ready_ids,
                "contents": {
                    integration_id: variant["content"]
                    for variant in state.get("publication_variants", [])
                    for integration_id in variant.get("integration_ids", [])
                    if integration_id in ready_ids
                },
                "mode": state.get("publish_mode", "draft"),
                "publish_at": state.get("publish_at"),
                "settings": state.get("postiz_settings", {}),
            },
        )
    except Exception as exc:  # noqa: BLE001 - keep generated copies available if external publishing fails
        logger.exception("[schedule_post] Postiz falló; se conserva el copy generado")
        return {
            "postiz": {
                "status": "failed",
                "mode": state.get("publish_mode", "draft"),
                "publish_at": state.get("publish_at"),
                "integrations": ready_ids,
                "skipped_integrations": skipped_ids,
                "error": str(exc),
            },
            "tool_calls": ["postiz.create_post"],
        }
    return {
        "publication": state["publication"],
        "publication_id": state.get("publication_id", 0),
        "publication_variants": state.get("publication_variants", []),
        "postiz": {
            "status": "created",
            "mode": state.get("publish_mode", "draft"),
            "publish_at": state.get("publish_at"),
            "integrations": ready_ids,
            "skipped_integrations": skipped_ids,
            "result": result,
        },
        "tool_calls": ["postiz.create_post"],
    }


# ── Grafo ──────────────────────────────────────────────────────
def create_publicacion_graph(checkpointer=None):
    """Compila el StateGraph del agente de publicación."""
    builder = StateGraph(PublicacionState)

    builder.add_node("load_context", load_context)
    builder.add_node("fetch_trending", fetch_trending)
    builder.add_node("generate_post", generate_post)
    builder.add_node("save_post", save_post)
    builder.add_node("schedule_post", schedule_post)

    builder.add_conditional_edges(
        START,
        lambda state: "schedule_post" if state.get("publication_action") == "deliver" else "load_context",
        ["load_context", "schedule_post"],
    )
    builder.add_edge("load_context", "fetch_trending")
    builder.add_edge("fetch_trending", "generate_post")
    builder.add_edge("generate_post", "save_post")
    builder.add_edge("save_post", "schedule_post")
    builder.add_edge("schedule_post", END)

    return builder.compile(checkpointer=checkpointer)
