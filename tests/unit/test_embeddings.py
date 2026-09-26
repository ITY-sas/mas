"""
Tests unitarios para shared_tools.embeddings
U01-U03 + centralización vía LLM Gateway (U04-U05 redefinidos).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared_tools.embeddings import embedding_to_vector, generate_embedding  # noqa: E402


class TestEmbeddings:
    """U01-U03: Generación y formato de embeddings."""

    @pytest.mark.unit
    def test_generate_embedding_returns_list(self):
        """U01: generate_embedding devuelve lista de floats (vía gateway) o None."""
        result = generate_embedding("texto de prueba para embedding")
        if result is not None:
            assert isinstance(result, list)
            assert len(result) > 0
            assert all(isinstance(x, (int, float)) for x in result)

    @pytest.mark.unit
    def test_generate_embedding_empty_string(self):
        """U01b: generate_embedding con string vacío no debe explotar."""
        result = generate_embedding("")
        assert result is None or isinstance(result, list)

    @pytest.mark.unit
    def test_embedding_to_vector_format(self):
        """U02: embedding_to_vector formatea correctamente."""
        assert embedding_to_vector([0.1, 0.2, 0.3]) == "[0.1,0.2,0.3]"

    @pytest.mark.unit
    def test_embedding_to_vector_single_value(self):
        """U02b: embedding_to_vector con un solo valor."""
        assert embedding_to_vector([0.5]) == "[0.5]"

    @pytest.mark.unit
    def test_embedding_to_vector_none(self):
        """U03: embedding_to_vector(None) devuelve None."""
        assert embedding_to_vector(None) is None

    @pytest.mark.unit
    def test_embedding_to_vector_empty_list(self):
        """U03b: embedding_to_vector([]) devuelve '[]'."""
        assert embedding_to_vector([]) == "[]"


class TestGatewayCentralization:
    """U04-U05: los embeddings pasan por el LLM Gateway (no Ollama directo)."""

    @pytest.mark.unit
    def test_gateway_base_default(self, monkeypatch):
        """U04: LLM_GATEWAY_URL por defecto es localhost:8003."""
        from common import gateway_client

        monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
        assert gateway_client.gateway_base() == "http://localhost:8003"

    @pytest.mark.unit
    def test_gateway_base_custom_and_strips_slash(self, monkeypatch):
        """U05: LLM_GATEWAY_URL personalizada y sin barra final."""
        from common import gateway_client

        monkeypatch.setenv("LLM_GATEWAY_URL", "http://llm-gateway:8003/")
        assert gateway_client.gateway_base() == "http://llm-gateway:8003"

    @pytest.mark.unit
    def test_no_direct_ollama_calls_in_shared_tools(self):
        """U06: shared_tools ya no construye URLs directas a Ollama."""
        base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "shared_tools",
        )
        offenders = []
        for fname in os.listdir(base):
            if not fname.endswith(".py"):
                continue
            with open(os.path.join(base, fname), encoding="utf-8") as fh:
                content = fh.read()
            if "/api/chat" in content or "/api/generate" in content or "/api/embeddings" in content:
                offenders.append(fname)
        assert not offenders, f"llamadas directas a Ollama en: {offenders}"
