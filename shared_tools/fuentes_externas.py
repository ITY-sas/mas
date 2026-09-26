"""
Tools para obtener datos de fuentes externas (tendencias, noticias, etc).
- Google Trends vía RSS (sin API key)
- Google Noticias RSS
- Mock data como fallback
"""
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=es-419&gl=AR&ceid=AR:es-419"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def fetch_google_news(query: str, limit: int = 5) -> list[dict]:
    """Obtiene noticias de Google News RSS para una query."""
    try:
        url = GOOGLE_NEWS_RSS.format(query=requests.utils.quote(query))
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        items = []
        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title", "")
            pub_date = item.findtext("pubDate", "")
            source = item.findtext("source", "")
            items.append({
                "titulo": title,
                "fecha": pub_date,
                "fuente": source or "Google News",
            })
        logger.info("Google News: %d noticias para '%s'", len(items), query)
        return items
    except Exception as exc:
        logger.warning("Error fetching Google News: %s", exc)
        return _mock_news(query)


def fetch_trending_topics(category: str = "marketing") -> list[dict]:
    """Obtiene topics en tendencia (mock + real fallback)."""
    try:
        news = fetch_google_news(f"{category} tendencias 2026", limit=5)
        if news:
            return [{"content": n["titulo"], "fuente": n["fuente"]} for n in news]
    except Exception:
        pass
    return _mock_trends(category)


def format_news_for_prompt(news: list[dict]) -> str:
    """Formatea noticias como contexto para el prompt."""
    if not news:
        return "No hay noticias/recientes disponibles."
    lines = []
    for n in news:
        if "titulo" in n:
            lines.append(f"- {n['titulo']} ({n.get('fuente', '')})")
        else:
            lines.append(f"- {n.get('content', '')}")
    return "\n".join(lines)


# ── Mock data (fallback cuando no hay conexión) ────────────────

def _mock_news(query: str) -> list[dict]:
    return [
        {"titulo": f"Tendencia emergente en {query}: audiencias buscan autenticidad",
         "fecha": datetime.now().isoformat(), "fuente": "Mock"},
        {"titulo": f"El 78% de los usuarios prefiere contenido corto sobre {query}",
         "fecha": datetime.now().isoformat(), "fuente": "Mock"},
    ]


def _mock_trends(category: str) -> list[dict]:
    mocks = {
        "marketing": [
            "Contenido UGC (User Generated Content) dominará 2026",
            "Storytelling auténtico supera al contenido pulido",
            "Micro-influencers generan 60% más engagement",
        ],
        "tech": [
            "IA generativa en herramientas de productividad personal",
            "Web3 y experiencias inmersivas para marcas",
            "Sostenibilidad como diferenciador tech",
        ],
        "ecommerce": [
            "Live shopping experimenta crecimiento del 300%",
            "Personalización con IA en tiempo real",
            "Experiencias post-compra como factor de retención",
        ],
    }
    return [{"content": t, "fuente": "mock"} for t in mocks.get(category, mocks["marketing"])]
