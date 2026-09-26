"""
Tests unitarios para shared_tools.tendencias
U15-U18 del plan de pruebas.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared_tools.tendencias import format_trends, get_all_trends, get_relevant_trends, get_trends_by_categoria


class TestGetAllTrends:
    """U15: Obtención de tendencias."""

    @pytest.mark.unit
    @pytest.mark.integration
    def test_get_trends(self):
        """U15: get_all_trends retorna ≥10 tendencias (con seed)."""
        trends = get_all_trends(limit=20)
        assert isinstance(trends, list)
        assert len(trends) >= 10

    @pytest.mark.unit
    @pytest.mark.integration
    def test_trends_limit(self):
        """U15b: get respeta el límite."""
        trends = get_all_trends(limit=5)
        assert len(trends) <= 5


class TestGetRelevantTrends:
    """U16: Búsqueda RAG de tendencias."""

    @pytest.mark.unit
    @pytest.mark.integration
    def test_relevant_trends(self):
        """U16: get_relevant_trends con query retorna resultados."""
        trends = get_relevant_trends("moda sostenible para jóvenes", limit=3)
        assert isinstance(trends, list)
        if trends:
            # Si hay resultados, deben tener similarity
            assert "similarity" in trends[0] or "content" in trends[0]

    @pytest.mark.unit
    @pytest.mark.integration
    def test_relevant_trends_limit(self):
        """U16b: Respeta el límite."""
        trends = get_relevant_trends("marketing", limit=2)
        assert len(trends) <= 2


class TestFormatTrends:
    """U17: Formateo de tendencias."""

    @pytest.mark.unit
    def test_format_empty(self):
        """U17: format_trends([]) retorna mensaje."""
        result = format_trends([])
        assert "No hay tendencias" in result

    @pytest.mark.unit
    def test_format_valid(self):
        """U17b: format_trends con datos válidos."""
        trends = [
            {"categoria": "marketing", "content": "UGC crece 45%", "similarity": 0.85},
            {"categoria": "tech", "content": "IA en productividad"},
        ]
        result = format_trends(trends)
        assert "UGC crece 45%" in result
        assert "marketing" in result
        assert "0.85" in result  # Muestra similitud
        assert "IA en productividad" in result


class TestGetTrendsByCategoria:
    """U18: Filtro por categoría."""

    @pytest.mark.unit
    @pytest.mark.integration
    def test_filter_by_category(self):
        """U18: get_trends_by_categoria filtra correctamente."""
        trends = get_trends_by_categoria("marketing", limit=10)
        assert isinstance(trends, list)
        for t in trends:
            assert "marketing" in t.get("categoria", "").lower()
