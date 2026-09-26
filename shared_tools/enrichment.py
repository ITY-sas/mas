"""
Módulo de enriquecimiento de contexto.
Combina todas las tools para construir un prompt enriquecido.
"""
import logging

from .cliente import format_client_profile, get_client_profile
from .competencia import format_competitors, get_relevant_competitors
from .rag import format_ideas_for_prompt, search_similar_ideas
from .tendencias import format_trends, get_relevant_trends

logger = logging.getLogger(__name__)


def enrich_brief_context(brief_content: str, client_id: int) -> dict:
    """
    Construye contexto completo para el agente de ideación:
    - Perfil del cliente
    - Tendencias relevantes
    - Referencias de competencia
    - Ideas similares previas (RAG)
    """
    logger.info("Enriqueciendo contexto para brief de client_id=%s", client_id)

    # 1. Perfil del cliente
    profile = get_client_profile(client_id)
    client_text = format_client_profile(profile)

    # 2. Tendencias relevantes
    trends = get_relevant_trends(brief_content, limit=5)
    trends_text = format_trends(trends)

    # 3. Referencias de competencia
    competitors = get_relevant_competitors(brief_content, limit=5)
    competitors_text = format_competitors(competitors)

    # 4. Ideas similares previas (RAG)
    similar_ideas = search_similar_ideas(brief_content, limit=3, min_similarity=0.3)
    similar_text = format_ideas_for_prompt(similar_ideas)

    context = {
        "client_profile": client_text,
        "trends": trends_text,
        "competitors": competitors_text,
        "similar_ideas": similar_text,
        "stats": {
            "trends_found": len(trends),
            "competitors_found": len(competitors),
            "similar_ideas_found": len(similar_ideas),
        },
    }

    logger.info(
        "Contexto enriquecido: %d tendencias, %d competidores, %d ideas similares",
        len(trends), len(competitors), len(similar_ideas),
    )
    return context


def build_ideacion_prompt(brief_content: str, context: dict) -> str:
    """Construye el prompt final enriquecido para el agente de ideación."""
    return f"""You are a creative marketing strategist creating content ideas.

## Client Profile
{context['client_profile']}

## Current Market Trends
{context['trends']}

## Competitor References
{context['competitors']}

## Similar Past Ideas (for inspiration, do NOT copy)
{context['similar_ideas']}

## Brief
{brief_content}

## Instructions
Generate ONE original content idea that:
1. Aligns with the client's brand profile and tone restrictions
2. Leverages current market trends where relevant
3. Differentiates from competitor approaches
4. Builds on past successful ideas without repeating them

Format your response as:
**Title:** [Catchy title]
**Description:** [2-3 sentence description]
**Why it works:** [Brief rationale tied to trends/client profile]"""


def enrich_idea_context(idea_content: str, client_id: int) -> dict:
    """
    Construye contexto para el agente de publicación:
    - Perfil del cliente (tono)
    - Tendencias relevantes para la publicación
    """
    logger.info("Enriqueciendo contexto de publicación para client_id=%s", client_id)

    profile = get_client_profile(client_id)
    client_text = format_client_profile(profile)

    trends = get_relevant_trends(idea_content, limit=3)
    trends_text = format_trends(trends)

    return {
        "client_profile": client_text,
        "trends": trends_text,
        "stats": {"trends_found": len(trends)},
    }


def build_publicacion_prompt(idea_content: str, context: dict) -> str:
    """Construye el prompt final enriquecido para el agente de publicación."""
    return f"""You are a social media copywriter creating a ready-to-publish post.

## Client Profile & Tone Rules
{context['client_profile']}

## Relevant Trends (for hashtags and hooks)
{context['trends']}

## Content Idea to Publish
{idea_content}

## Instructions
Create a social media post that:
1. Follows the client's tone rules EXACTLY
2. Includes a hook in the first line
3. Uses relevant hashtags (mix branded + trending)
4. Ends with a clear call to action
5. Maximum 280 characters

Respond ONLY with the post text."""
