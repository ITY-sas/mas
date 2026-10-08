"""
Grafo LangGraph del agente de ideación (microservicio independiente).

    START → load_context → fetch_news → generate_idea → save_idea → END

Todas las operaciones de negocio se invocan como **contratos de API**
(Tools-as-a-Service vía ``ToolRegistry`` con Tool Discovery) y toda
llamada a LLM pasa por el **LLM Gateway**. El agente no importa
``shared_tools``: no ejecuta código de negocio directamente.
"""
from __future__ import annotations

import json
import logging
import operator
from copy import deepcopy
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from common import gateway_client
from common.tool_client import ToolRegistry

from .prompts import SYSTEM_PROMPT, build_ideacion_prompt

logger = logging.getLogger("agente_ideacion.graph")

# Registro con descubrimiento de tools (manifiestos → endpoints)
REGISTRY = ToolRegistry()

_DOSSIER_DEFAULTS = {
    "content_type": "reel",
    "title": "",
    "concept": "",
    "objective": "",
    "audience": "",
    "key_message": "",
    "format": "video corto vertical",
    "duration_seconds": 30,
    "script": [],
    "camera": [],
    "performance_direction": "",
    "location_and_art_direction": "",
    "audio": "",
    "editing_notes": "",
    "post_spec": {
        "visual_concept": "",
        "composition": "",
        "image_direction": "",
        "text_on_asset": "",
        "caption_direction": "",
        "carousel_slides": [],
        "alt_text": "",
        "platform_adaptations": "",
    },
    "cta": "",
    "deliverables": [],
    "why_it_works": "",
}

DOSSIER_JSON_SCHEMA = {
    "type": "object",
    "required": [
        "content_type", "title", "concept", "objective", "audience",
        "key_message", "format", "cta", "why_it_works", "post_spec",
    ],
    "properties": {
        "title": {"type": "string"},
        "content_type": {"type": "string", "enum": ["reel", "post"]},
        "concept": {"type": "string"},
        "objective": {"type": "string"},
        "audience": {"type": "string"},
        "key_message": {"type": "string"},
        "format": {"type": "string"},
        "duration_seconds": {"type": "integer"},
        "script": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["scene", "duration_seconds", "visual", "action", "dialogue_or_voiceover", "on_screen_text"],
                "properties": {
                    "scene": {"type": "integer"},
                    "duration_seconds": {"type": "integer"},
                    "visual": {"type": "string"},
                    "action": {"type": "string"},
                    "dialogue_or_voiceover": {"type": "string"},
                    "on_screen_text": {"type": "string"},
                },
            },
        },
        "camera": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["scene", "shot", "angle", "movement", "framing"],
                "properties": {
                    "scene": {"type": "integer"},
                    "shot": {"type": "string"},
                    "angle": {"type": "string"},
                    "movement": {"type": "string"},
                    "framing": {"type": "string"},
                },
            },
        },
        "performance_direction": {"type": "string"},
        "location_and_art_direction": {"type": "string"},
        "audio": {"type": "string"},
        "editing_notes": {"type": "string"},
        "post_spec": {
            "type": "object",
            "properties": {
                "visual_concept": {"type": "string"},
                "composition": {"type": "string"},
                "image_direction": {"type": "string"},
                "text_on_asset": {"type": "string"},
                "caption_direction": {"type": "string"},
                "carousel_slides": {"type": "array", "items": {"type": "string"}},
                "alt_text": {"type": "string"},
                "platform_adaptations": {"type": "string"},
            },
        },
        "cta": {"type": "string"},
        "deliverables": {"type": "array", "items": {"type": "string"}},
        "why_it_works": {"type": "string"},
    },
}


def dossier_schema_for(requested_format: str) -> dict:
    """Devuelve un esquema especializado para no mezclar Reel y Post."""
    schema = deepcopy(DOSSIER_JSON_SCHEMA)
    required = schema["required"]
    if requested_format == "reel":
        required.extend([
            "duration_seconds", "script", "camera", "performance_direction",
            "location_and_art_direction", "audio", "editing_notes",
        ])
    elif requested_format == "post":
        required.append("post_spec")
    return schema


def validate_dossier(dossier: dict) -> None:
    """Rechaza dossiers vacíos o incompletos antes de persistirlos."""
    required_text = ("title", "concept", "objective", "audience", "key_message", "format", "cta", "why_it_works")
    missing = [key for key in required_text if not str(dossier.get(key, "")).strip()]
    content_type = dossier.get("content_type")
    if content_type not in {"reel", "post"}:
        missing.append("content_type (reel o post)")
    if content_type == "reel":
        reel_text = ("performance_direction", "location_and_art_direction", "audio", "editing_notes")
        missing.extend(key for key in reel_text if not str(dossier.get(key, "")).strip())
        scripts = dossier.get("script")
        cameras = dossier.get("camera")
        if not isinstance(scripts, list) or not scripts:
            missing.append("script")
        if not isinstance(cameras, list) or not cameras:
            missing.append("camera")
        for index, scene in enumerate(scripts or [], start=1):
            for key in ("scene", "visual", "action", "dialogue_or_voiceover", "on_screen_text"):
                if scene.get(key) in (None, ""):
                    missing.append(f"script[{index}].{key}")
        for index, shot in enumerate(cameras or [], start=1):
            for key in ("scene", "shot", "angle", "movement", "framing"):
                if shot.get(key) in (None, ""):
                    missing.append(f"camera[{index}].{key}")
    elif content_type == "post":
        post_spec = dossier.get("post_spec")
        if not isinstance(post_spec, dict):
            missing.append("post_spec")
            post_spec = {}
        for key in ("visual_concept", "composition", "image_direction", "text_on_asset", "caption_direction", "alt_text", "platform_adaptations"):
            if not str(post_spec.get(key, "")).strip():
                missing.append(f"post_spec.{key}")
        if not isinstance(post_spec.get("carousel_slides"), list) or not post_spec.get("carousel_slides"):
            missing.append("post_spec.carousel_slides")
    if missing:
        raise ValueError("dossier de ideación incompleto: " + ", ".join(missing))


def _parse_dossier(raw_content: object) -> dict:
    """Extrae y normaliza el dossier aunque el LLM lo envuelva en Markdown."""
    raw_text = str(raw_content or "").strip()
    candidate = raw_text
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[1] if "\n" in candidate else candidate
        candidate = candidate.rsplit("```", 1)[0].strip()
    if not candidate.startswith("{"):
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start:end + 1]
    try:
        parsed = json.loads(candidate)
    except (TypeError, ValueError, json.JSONDecodeError):
        parsed = {}
    dossier = dict(_DOSSIER_DEFAULTS)
    if isinstance(parsed, dict):
        dossier.update({key: value for key, value in parsed.items() if value is not None})
    if not dossier["concept"]:
        dossier["concept"] = raw_text
    return dossier


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
    preproduction: dict

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
        "requested_format": state["brief"].get("content_format", "auto"),
    }
    requested_format = state["brief"].get("content_format", "auto")
    dossier_schema = dossier_schema_for(requested_format)
    prompt = build_ideacion_prompt(state["brief"]["content"], context)
    if state.get("news"):
        prompt += f"\n\n## Recent News & Signals\n{state['news']}"

    logger.info("[generate_idea] POST llm-gateway (/v1/generate, prompt=%d chars)",
                len(prompt))
    response = gateway_client.generate(
        prompt, system=SYSTEM_PROMPT, timeout=240.0, format=dossier_schema
    )
    raw_idea = response.get("content", "")
    preproduction = _parse_dossier(raw_idea)
    try:
        validate_dossier(preproduction)
    except ValueError as first_error:
        logger.warning("[generate_idea] dossier incompleto; solicitando reparación: %s", first_error)
        repair_prompt = (
            f"{prompt}\n\nREPAIR REQUIRED: The previous draft was incomplete: {first_error}. "
            "Return the complete JSON again. Every script scene must contain a non-empty "
            "dialogue_or_voiceover, even for B-roll scenes; every camera entry must contain "
            "shot, angle, movement and framing. Do not leave any required field empty."
        )
        response = gateway_client.generate(
            repair_prompt,
            system=SYSTEM_PROMPT,
            timeout=240.0,
            cache=False,
            format=dossier_schema,
        )
        preproduction = _parse_dossier(response.get("content", ""))
        validate_dossier(preproduction)
    idea = json.dumps(preproduction, ensure_ascii=False, indent=2)
    logger.info("[generate_idea] idea vía %s/%s (cached=%s): %s",
                response.get("provider"), response.get("model"),
                response.get("cached"), idea[:100])
    return {
        "idea": idea,
        "preproduction": preproduction,
        "tool_calls": ["llm-gateway.generate"],
    }


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
