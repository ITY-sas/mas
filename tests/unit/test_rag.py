"""
Tests unitarios para shared_tools.rag
U19-U21 del plan de pruebas.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared_tools.rag import format_ideas_for_prompt, search_similar_content, search_similar_ideas, store_embedding


class TestSearchSimilarIdeas:
    """U19: Búsqueda RAG de ideas."""

    @pytest.mark.unit
    @pytest.mark.integration
    def test_search_returns_list(self):
        """U19: search_similar_ideas retorna lista."""
        results = search_similar_ideas("campaña ropa sostenible", limit=3)
        assert isinstance(results, list)

    @pytest.mark.unit
    @pytest.mark.integration
    def test_search_with_no_results(self):
        """U19b: Query irrelevante puede retornar lista vacía."""
        results = search_similar_ideas("xyzabc123 nonexistent query", limit=5, min_similarity=0.95)
        assert isinstance(results, list)
        # Con min_similarity alto, probablemente vacío
        assert len(results) <= 5


class TestSearchSimilarContent:
    """U20: Búsqueda genérica con whitelist de tablas."""

    @pytest.mark.unit
    def test_invalid_table_raises(self):
        """U20: Tabla no permitida lanza ValueError."""
        with pytest.raises(ValueError, match="no permitida"):
            search_similar_content("tabla_hackeada", "query")

    @pytest.mark.unit
    @pytest.mark.integration
    def test_valid_table(self):
        """U20b: Tabla válida funciona."""
        results = search_similar_content("tendencias", "marketing sostenible", limit=3)
        assert isinstance(results, list)

    @pytest.mark.unit
    @pytest.mark.integration
    def test_valid_table_ideas(self):
        """U20c: Tabla ideas_generadas funciona."""
        results = search_similar_content("ideas_generadas", "eco-friendly campaign", limit=3)
        assert isinstance(results, list)


class TestStoreEmbedding:
    """U21: Almacenamiento de embeddings."""

    @pytest.mark.unit
    @pytest.mark.integration
    def test_store_embedding_valid(self):
        """U21: store_embedding con tabla válida no explota."""
        result = store_embedding("ideas_generadas", 1, "Contenido de prueba")
        assert result in [True, False]

    @pytest.mark.unit
    def test_store_embedding_invalid_table(self):
        """U21b: Tabla inválida lanza ValueError."""
        with pytest.raises(ValueError, match="no permitida"):
            store_embedding("tabla_maliciosa", 1, "test")


class TestFormatIdeasForPrompt:
    """Formateo de ideas para prompt."""

    @pytest.mark.unit
    def test_format_empty(self):
        """Lista vacía retorna mensaje."""
        result = format_ideas_for_prompt([])
        assert "No hay ideas previas" in result

    @pytest.mark.unit
    def test_format_with_data(self):
        """Con datos muestra contenido y similitud."""
        ideas = [
            {"content": "Idea sobre moda sostenible", "similarity": 0.87},
            {"content": "Otra idea de marketing", "similarity": 0.72},
        ]
        result = format_ideas_for_prompt(ideas)
        assert "moda sostenible" in result
        assert "0.87" in result
        assert "0.72" in result
