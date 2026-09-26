"""
Tests unitarios para shared_tools.competencia
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared_tools.competencia import format_competitors, get_all_competitors, get_relevant_competitors


class TestGetCompetitors:
    """Obtención de referencias de competencia."""

    @pytest.mark.unit
    @pytest.mark.integration
    def test_get_all(self):
        """get_all_competitors retorna ≥10 (con seed)."""
        refs = get_all_competitors(limit=20)
        assert isinstance(refs, list)
        assert len(refs) >= 10

    @pytest.mark.unit
    @pytest.mark.integration
    def test_get_relevant(self):
        """get_relevant_competitors con query retorna resultados."""
        refs = get_relevant_competitors("campaña sostenible", limit=3)
        assert isinstance(refs, list)
        assert len(refs) <= 3


class TestFormatCompetitors:
    """Formateo de competencia."""

    @pytest.mark.unit
    def test_format_empty(self):
        """Lista vacía retorna mensaje."""
        result = format_competitors([])
        assert "No hay referencias" in result

    @pytest.mark.unit
    def test_format_valid(self):
        """Con datos muestra competidor y contenido."""
        refs = [
            {"competidor": "Patagonia", "content": "Campaña anti-consumo", "plataforma": "instagram"},
            {"competidor": "Lush", "content": "Marketing sin embalaje", "plataforma": "tiktok"},
        ]
        result = format_competitors(refs)
        assert "Patagonia" in result
        assert "anti-consumo" in result
        assert "instagram" in result
        assert "Lush" in result
