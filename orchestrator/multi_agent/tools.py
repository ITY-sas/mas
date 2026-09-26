"""
LangChain @tool definitions wrapping shared_tools.

These tools are registered so the LLM (and/or ReAct nodes) can call them.
Deterministic graph nodes also call the underlying shared_tools directly.
"""
from langchain_core.tools import tool


@tool
def load_client_profile(client_id: int) -> str:
    """Load the client brand profile, tone restrictions, and content history from the database.

    Args:
        client_id: The client's unique identifier.
    """
    from shared_tools.cliente import format_client_profile, get_client_profile

    profile = get_client_profile(client_id)
    return format_client_profile(profile)


@tool
def search_trends(query: str, limit: int = 5) -> str:
    """Search for market trends relevant to the given query using vector similarity (RAG).

    Args:
        query: Search query (e.g. the campaign brief or idea).
        limit: Maximum number of trends to return.
    """
    from shared_tools.tendencias import format_trends, get_relevant_trends

    trends = get_relevant_trends(query, limit)
    return format_trends(trends)


@tool
def search_competitors(query: str, limit: int = 5) -> str:
    """Search competitor references relevant to the given query using vector similarity.

    Args:
        query: Search query.
        limit: Maximum number of competitor references to return.
    """
    from shared_tools.competencia import format_competitors, get_relevant_competitors

    competitors = get_relevant_competitors(query, limit)
    return format_competitors(competitors)


@tool
def search_similar_ideas_tool(query: str, limit: int = 3) -> str:
    """Search similar past generated ideas using RAG (for inspiration, do NOT copy).

    Args:
        query: Search query.
        limit: Maximum number of similar ideas to return.
    """
    from shared_tools.rag import format_ideas_for_prompt, search_similar_ideas

    ideas = search_similar_ideas(query, limit, min_similarity=0.3)
    return format_ideas_for_prompt(ideas)


@tool
def fetch_news(query: str, limit: int = 3) -> str:
    """Fetch recent news articles from Google News RSS for the given query.

    Args:
        query: News search query.
        limit: Maximum number of news items to return.
    """
    from shared_tools.fuentes_externas import fetch_google_news, format_news_for_prompt

    news = fetch_google_news(query, limit)
    return format_news_for_prompt(news)


@tool
def fetch_trending(query: str = "marketing") -> str:
    """Fetch currently trending topics from Google News for hashtag suggestions.

    Args:
        query: Category for trending topics (default: marketing).
    """
    from shared_tools.fuentes_externas import fetch_trending_topics, format_news_for_prompt

    trending = fetch_trending_topics(query)
    return format_news_for_prompt(trending)


# ── Registry for easy listing ──
ALL_TOOLS = [
    load_client_profile,
    search_trends,
    search_competitors,
    search_similar_ideas_tool,
    fetch_news,
    fetch_trending,
]
