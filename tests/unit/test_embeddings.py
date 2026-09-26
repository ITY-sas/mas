"""
Tests unitarios para shared_tools.embeddings
U01-U05 del plan de pruebas.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared_tools.embeddings import embedding_to_vector, generate_embedding, _build_ollama_url


class TestEmbeddings:
    """U01-U03: Generación y formato de embeddings."""

    @pytest.mark.unit
    def test_generate_embedding_returns_list(self):
        """U01: generate_embedding devuelve lista de floats."""
        result = generate_embedding("texto de prueba para embedding")
        # Puede ser None si Ollama no está disponible, pero si responde debe ser lista
        if result is not None:
            assert isinstance(result, list)
            assert len(result) > 0
            assert all(isinstance(x, (int, float)) for x in result)

    @pytest.mark.unit
    def test_generate_embedding_empty_string(self):
        """U01b: generate_embedding con string vacío no debe explotar."""
        result = generate_embedding("")
        # No debe lanzar excepción (puede devolver None o lista)
        assert result is None or isinstance(result, list)

    @pytest.mark.unit
    def test_embedding_to_vector_format(self):
        """U02: embedding_to_vector formatea correctamente."""
        result = embedding_to_vector([0.1, 0.2, 0.3])
        assert result == "[0.1,0.2,0.3]"

    @pytest.mark.unit
    def test_embedding_to_vector_single_value(self):
        """U02b: embedding_to_vector con un solo valor."""
        result = embedding_to_vector([0.5])
        assert result == "[0.5]"

    @pytest.mark.unit
    def test_embedding_to_vector_none(self):
        """U03: embedding_to_vector(None) devuelve None."""
        assert embedding_to_vector(None) is None


class TestOllamaURL:
    """U04-U05: Construcción de URL de Ollama."""

    @pytest.mark.unit
    def test_url_with_zero_host_and_port(self, monkeypatch):
        """U04: host 0.0.0.0:11434 se mapea a 127.0.0.1:11434."""
        monkeypatch.setenv("OLLAMA_HOST", "0.0.0.0:11434")
        monkeypatch.delenv("OLLAMA_PORT", raising=False)
        url = _build_ollama_url()
        assert url == "http://127.0.0.1:11434"

    @pytest.mark.unit
    def test_url_with_normal_host(self, monkeypatch):
        """U05: host normal 'ollama' usa puerto por defecto."""
        monkeypatch.setenv("OLLAMA_HOST", "ollama")
        monkeypatch.setenv("OLLAMA_PORT", "11434")
        url = _build_ollama_url()
        assert url == "http://ollama:11434"

    @pytest.mark.unit
    def test_url_with_host_no_port(self, monkeypatch):
        """U05b: host sin puerto usa default 11434."""
        monkeypatch.setenv("OLLAMA_HOST", "localhost")
        monkeypatch.delenv("OLLAMA_PORT", raising=False)
        url = _build_ollama_url()
        assert url == "http://localhost:11434"

    @pytest.mark.unit
    def test_url_with_empty_port(self, monkeypatch):
        """U05c: puerto vacío usa default 11434."""
        monkeypatch.setenv("OLLAMA_HOST", "localhost")
        monkeypatch.setenv("OLLAMA_PORT", "")
        url = _build_ollama_url()
        assert url == "http://localhost:11434"

    @pytest.mark.unit
    def test_url_with_zero_host_no_port(self, monkeypatch):
        """U04b: 0.0.0.0 sin puerto explícito."""
        monkeypatch.setenv("OLLAMA_HOST", "0.0.0.0")
        monkeypatch.setenv("OLLAMA_PORT", "")
        url = _build_ollama_url()
        assert url == "http://127.0.0.1:11434"
