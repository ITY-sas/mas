"""
Fixtures compartidos para todas las pruebas.
"""
import os
import sys

import pytest

# Agregar la raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def sample_brief() -> dict:
    """Brief de ejemplo para pruebas."""
    return {
        "client_id": 1,
        "content": "Create a launch campaign for an eco-friendly water bottle",
    }


@pytest.fixture(scope="session")
def sample_context() -> dict:
    """Contexto de ejemplo enriquecido para pruebas de prompt."""
    return {
        "client_profile": "Cliente: EcoBrand\nPerfil: Marca ecológica",
        "trends": "- [marketing] UGC crece 45%",
        "competitors": "- [Patagonia] Campaña anti-consumo",
        "similar_ideas": "- (similitud: 0.85) Campaña previa exitosa",
        "news": "- Noticia relevante del sector",
        "stats": {"trends_found": 1, "competitors_found": 1, "similar_ideas_found": 1},
    }


@pytest.fixture(scope="session")
def sample_embedding() -> list:
    """Embedding de ejemplo (768 floats)."""
    return [0.1] * 768
