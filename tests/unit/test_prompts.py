"""
Tests unitarios de los prompts de los agentes (U06-U10).

Los prompts son **persona del agente** (no código de negocio): cada agente
microservicio posee sus plantillas y compone los datos que los tool services
devuelven ya formateados.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from agente_ideacion.prompts import build_ideacion_prompt
from agente_publicacion.prompts import build_publicacion_prompt

pytestmark = pytest.mark.unit


class TestBuildIdeacionPrompt:
    """U06-U08: Prompt del agente de ideación."""

    def test_prompt_contains_client_profile(self, sample_context):
        """U06: El prompt incluye el perfil del cliente."""
        prompt = build_ideacion_prompt("test brief", sample_context)
        assert "Client Profile" in prompt
        assert "EcoBrand" in prompt

    def test_prompt_contains_trends(self, sample_context):
        """U07: El prompt incluye tendencias."""
        prompt = build_ideacion_prompt("test brief", sample_context)
        assert "Market Trends" in prompt
        assert "UGC" in prompt

    def test_prompt_contains_competitors(self, sample_context):
        """U08: El prompt incluye competencia."""
        prompt = build_ideacion_prompt("test brief", sample_context)
        assert "Competitor" in prompt
        assert "Patagonia" in prompt

    def test_prompt_contains_similar_ideas(self, sample_context):
        """U08b: El prompt incluye ideas similares (RAG)."""
        prompt = build_ideacion_prompt("test brief", sample_context)
        assert "Similar Past Ideas" in prompt

    def test_prompt_contains_brief(self, sample_context):
        """El prompt incluye el brief original."""
        prompt = build_ideacion_prompt("mi brief de prueba", sample_context)
        assert "mi brief de prueba" in prompt

    def test_prompt_contains_instructions(self, sample_context):
        """El prompt incluye instrucciones de formato."""
        prompt = build_ideacion_prompt("brief", sample_context)
        assert "**Title:**" in prompt
        assert "Why it works" in prompt


class TestBuildPublicacionPrompt:
    """U09-U10: Prompt del agente de publicación."""

    def test_prompt_contains_tone_rules(self, sample_context):
        """U09: El prompt incluye reglas de tono."""
        prompt = build_publicacion_prompt("idea de prueba", sample_context)
        assert "Tone Rules" in prompt
        assert "EcoBrand" in prompt

    def test_prompt_contains_trends(self, sample_context):
        """El prompt incluye tendencias para hashtags."""
        prompt = build_publicacion_prompt("idea", sample_context)
        assert "Relevant Trends" in prompt

    def test_prompt_contains_idea(self, sample_context):
        """El prompt incluye la idea a publicar."""
        prompt = build_publicacion_prompt("mi idea original", sample_context)
        assert "mi idea original" in prompt

    def test_prompt_char_limit(self, sample_context):
        """U10: El prompt pide máximo 280 caracteres."""
        prompt = build_publicacion_prompt("idea", sample_context)
        assert "280" in prompt
