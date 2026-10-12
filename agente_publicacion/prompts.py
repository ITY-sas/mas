"""
Prompts del agente de publicación (persona del agente — no es código de
negocio: los datos llegan ya formateados desde los tool services).
"""

SYSTEM_PROMPT = (
    "You are a social media copywriter. You always answer in the language "
    "specified by the client profile."
)

PLATFORM_GUIDANCE = {
    "instagram": "Write a visual-first caption with a concise opening hook, natural line breaks, and a clear save, share, or comment action. Use a small set of relevant hashtags; do not stuff hashtags.",
    "linkedin": "Use a professional, insight-led voice. Explain the audience or business value, avoid influencer-style hashtag blocks and engagement bait, and use at most three relevant hashtags.",
    "facebook": "Use a warm, conversational community voice. Make the post easy to read and invite a genuine response without clickbait.",
    "tiktok": "Write a short, conversational, spoken-style caption that supports a video hook. Keep hashtags selective and avoid formal corporate phrasing unless the brand profile requires it.",
    "x": "Write a concise, self-contained post with a strong first phrase. Keep the final text within 280 characters and use only a few relevant hashtags.",
    "twitter": "Write a concise, self-contained post with a strong first phrase. Keep the final text within 280 characters and use only a few relevant hashtags.",
}


def build_publicacion_prompt(
    idea_content: str,
    context: dict,
    platform: str | None = None,
) -> str:
    """Construye el prompt final enriquecido para el agente de publicación."""
    platform_name = (platform or "").strip()
    platform_guidance = PLATFORM_GUIDANCE.get(
        platform_name.lower(),
        "Create a platform-neutral base copy suitable for adaptation to a social network.",
    )
    platform_section = (
        f"\n## Target Platform: {platform_name}\n{platform_guidance}\n"
        if platform_name
        else f"\n## Platform Guidance\n{platform_guidance}\n"
    )
    return f"""You are a social media copywriter creating a ready-to-publish post.

{platform_section}
## Client Profile & Tone Rules
{context['client_profile']}

## Relevant Trends (for hashtags and hooks)
{context['trends']}

## Content Idea to Publish
{idea_content}

## Audiovisual Preproduction Context
{context.get('preproduction', 'No additional audiovisual context')}

## Instructions
Create a social media post that:
1. Follows the client's tone rules EXACTLY
2. Includes a hook in the first line
2. Uses relevant hashtags (mix branded + trending)
3. Ends with a clear call to action
4. Adapt structure, length, vocabulary, calls to action, and hashtag use to the target platform guidance above
5. Preserve the client's brand voice while applying platform conventions
6. If no target platform is specified, keep the platform-neutral copy within 280 characters

Respond ONLY with the post text."""
