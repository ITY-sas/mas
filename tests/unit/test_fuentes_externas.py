"""
Tests unitarios para shared_tools.fuentes_externas
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared_tools.fuentes_externas import (
    _mock_news,
    _mock_trends,
    fetch_google_news,
    fetch_trending_topics,
    format_news_for_prompt,
)


class TestFetchGoogleNews:
    """Google News RSS."""

    @pytest.mark.unit
    @pytest.mark.slow
    def test_fetch_news_returns_list(self):
        """fetch_google_news retorna lista (real o mock)."""
        news = fetch_google_news("marketing trends 2026", limit=3)
        assert isinstance(news, list)
        # Puede ser mock si no hay conexión
        if news:
            assert "titulo" in news[0] or "content" in news[0]

    @pytest.mark.unit
    @pytest.mark.slow
    def test_fetch_news_limit(self):
        """Respeta el límite."""
        news = fetch_google_news("test query", limit=2)
        assert len(news) <= 2

    @pytest.mark.unit
    def test_mock_news(self):
        """_mock_news retorna datos de ejemplo."""
        news = _mock_news("test")
        assert len(news) >= 1
        assert "titulo" in news[0]


class TestFetchTrendingTopics:
    """Trending topics."""

    @pytest.mark.unit
    @pytest.mark.slow
    def test_fetch_trending_returns_list(self):
        """fetch_trending_topics retorna lista."""
        topics = fetch_trending_topics("marketing")
        assert isinstance(topics, list)
        assert len(topics) >= 1

    @pytest.mark.unit
    def test_mock_trends_marketing(self):
        """_mock_trends('marketing') retorna datos."""
        trends = _mock_trends("marketing")
        assert len(trends) >= 3
        assert all("content" in t for t in trends)

    @pytest.mark.unit
    def test_mock_trends_unknown_category(self):
        """Categoría desconocida usa marketing por defecto."""
        trends = _mock_trends("categoria_inexistente")
        assert len(trends) >= 1


class TestFormatNewsForPrompt:
    """Formateo de noticias."""

    @pytest.mark.unit
    def test_format_empty(self):
        """Lista vacía retorna mensaje."""
        result = format_news_for_prompt([])
        assert "No hay noticias" in result

    @pytest.mark.unit
    def test_format_news_items(self):
        """Items con 'titulo' se formatean."""
        news = [{"titulo": "Noticia importante", "fuente": "CNN"}]
        result = format_news_for_prompt(news)
        assert "Noticia importante" in result
        assert "CNN" in result

    @pytest.mark.unit
    def test_format_trend_items(self):
        """Items con 'content' (trending) se formatean."""
        trends = [{"content": "Tendencia del día"}]
        result = format_news_for_prompt(trends)
        assert "Tendencia del día" in result
