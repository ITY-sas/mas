"""
Prompts del agente de publicación (persona del agente — no es código de
negocio: los datos llegan ya formateados desde los tool services).
"""

SYSTEM_PROMPT = (
    "You are a social media copywriter. You always answer in the language "
    "specified by the client profile."
)


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
